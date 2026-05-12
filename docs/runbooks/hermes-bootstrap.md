# Hermes Bootstrap Boundary Notes

## Scope

This runbook covers Task 0 bootstrap: how this repo is loaded by Hermes,
how to verify plugin discovery, and how to recover from the common failure modes.

Architecture reference: [§5.5 of `docs/AIOps架构设计.md`](../AIOps架构设计.md).

## Installation Methods

This plugin supports both Hermes plugin discovery paths. **Use Method A
unless you actively need editable installs for testing.**

### Method A (Recommended) — Hermes Web: Install from Git URL

This is the fastest and most reliable path for operators. Hermes Web clones
the repo into `~/.hermes/plugins/<name>/` and handles directory-mode
discovery via the repo-root `plugin.yaml` without touching the Python
interpreter.

Steps:

1. Open Hermes Web → **Plugins** → **Install from GitHub / Git URL**.
2. Enter the repo URL, for example `https://github.com/<org>/aiops-v2.git`.
3. When prompted **Enable 'aiops' now?**, choose **Yes**.
4. Set the per-instance role in `~/.hermes/config.yaml`:

   ```yaml
   plugins:
     enabled:
       - aiops
     env:
       aiops:
         AIOPS_HERMES_INSTANCE: gateway   # one of: gateway | linux | network | infra
   ```

5. Restart Hermes (or whichever lifecycle command Hermes Web exposes).

Why this works:

- Hermes Web clones to `~/.hermes/plugins/<name>/` — a directory plugin source.
- Hermes scans the clone root for `plugin.yaml` + `__init__.py`. Our repo
  ships `plugin.yaml` at the root, so discovery succeeds.
- Hermes uses its own Python interpreter to load the plugin — no
  interpreter mismatch problem (see Method B's pitfall below).

To update the plugin: re-run the Git URL install in Hermes Web, or
`cd ~/.hermes/plugins/aiops && git pull`.

### Method B (Dev) — Pip editable install

Use this only when you are actively editing the plugin code and need
in-place reloads, or when running the integration test suite against the
same interpreter Hermes uses.

```bash
# Install the repo into the Python interpreter used by Hermes
<python-used-by-hermes> -m pip install -e /path/to/aiops-v2
```

How to find the right interpreter:

```bash
which hermes
head -n 1 "$(which hermes)"   # the shebang reveals the interpreter path
```

Add the same `plugins.enabled` + `plugins.env` block as Method A.

## Plugin Discovery Reference

| Source | Path / Mechanism | Used by |
| --- | --- | --- |
| Bundled | `<hermes_repo>/plugins/` | Hermes built-ins |
| User (directory) | `~/.hermes/plugins/<name>/` | **Method A** |
| Project (directory) | `./.hermes/plugins/<name>/` (opt-in via `HERMES_ENABLE_PROJECT_PLUGINS=1`) | Local project overrides |
| Pip entry-point | `hermes_agent.plugins` group | **Method B** |

Discovery requirements:

- **Directory sources** require both `plugin.yaml` *and* `__init__.py` with
  a `register(ctx)` function at the scanned root. We ship `plugin.yaml`
  at the repo root and the package's `__init__.py` is auto-loaded via the
  entry-point in `pyproject.toml`.
- **Pip source** only requires the entry-point pointing to a module whose
  `register(ctx)` is callable.

## Per-Instance Role

The plugin reads `AIOPS_HERMES_INSTANCE` and registers a different tool
subset per role to preserve credential isolation (architecture §6.3, §5.5.4):

| Role | What is registered | Typical use |
| --- | --- | --- |
| `gateway` (default) | `gateway:webhook_received` hook + Bot slash commands | Webhook ingest + Bot |
| `linux` | Linux / Windows server tools (Task 5 / 9) | Server alerts |
| `network` | Scrapli + NAPALM device tools (Task 5 / 9) | H3C / Huawei / Cisco alerts |
| `infra` | DB / Zabbix-self tools (Task 5) | DB / monitoring alerts |

Always-on (every role): `post_tool_call` hook + `aiops_ping` tool.

Unknown roles fail loud with `RuntimeError` — better than silently
loading the wrong subset.

## Verification

After enabling, in the Hermes VM:

```bash
# 1. Plugin is recognized
hermes plugins list
# Expected: aiops appears, no "has no plugin.yaml / __init__.py" warning

# 2. Trigger the always-on probe
#    In the 飞书 DM with the bot, ask it to call the `aiops_ping` tool
#    OR run via Hermes CLI / API
```

For deeper diagnostics:

```bash
HERMES_PLUGINS_DEBUG=1 hermes plugins list 2>&1 | grep -i aiops
# Shows the source path Hermes picked for the plugin (directory vs pip)
```

## Common Failures

### "aiops-v2 has no plugin.yaml / __init__.py" warning

Symptom seen on first install before v3.5 fix.

Root cause: distribution name in `pyproject.toml` was `aiops-v2` but
`plugin.yaml` declared `name: aiops`. Hermes used the distribution name
to look for `aiops-v2/plugin.yaml` and didn't find it.

Fix: already applied in repo — `pyproject.toml` `name = "aiops"` matches
`plugin.yaml.name`. Pull the latest main and reinstall.

### Method B only: `hermes plugins list` shows nothing after `uv sync`

Root cause: `uv sync` installs into the repo's `.venv`. Hermes runs in
its own interpreter. Entry-points registered in `.venv` are invisible to
that interpreter.

Quick proof:

```bash
# Repo interpreter sees us:
uv run python -c "import importlib.metadata as m; print(sorted(ep.name for ep in m.entry_points(group='hermes_agent.plugins')))"
# Expected: ['aiops']

# Hermes interpreter does not:
$(head -n1 "$(which hermes)" | tr -d '#!') -c \
  "import importlib.metadata as m; print(sorted(ep.name for ep in m.entry_points(group='hermes_agent.plugins')))"
```

Fix: either switch to Method A (Hermes Web) or install into the Hermes
interpreter as shown in Method B.

### Unknown `AIOPS_HERMES_INSTANCE` value

The plugin raises `RuntimeError: unknown AIOPS_HERMES_INSTANCE=<value>;
expected one of ['gateway', 'infra', 'linux', 'network']`. Hermes will
disable the plugin and continue. Fix the env value and restart.

## Recommended Working Loop

For operators (Method A):

1. Push code changes to GitHub.
2. Hermes Web → Plugins → reinstall from Git URL (or `git pull` in
   `~/.hermes/plugins/aiops`).
3. Restart Hermes if needed; verify with `hermes plugins list`.

For developers iterating locally (Method B):

1. Edit code in repo.
2. Tests live in `tests/`, run with `uv run pytest`.
3. For integration against a live Hermes: `pip install -e .` into the
   Hermes interpreter (one-time), then code changes take effect on the
   next plugin reload.
