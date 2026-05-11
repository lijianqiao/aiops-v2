# Hermes Bootstrap Boundary Notes

## Scope

This runbook captures the Hermes integration facts validated for Task 0. The actual
Hermes runtime is hosted in the user's VM, so repository-side work here focuses on
plugin packaging, boundary contracts, and the manual checks to perform inside that VM.

## Plugin Discovery

- Hermes entry-point group: `hermes_agent.plugins`
- Pip-packaged plugins are auto-discovered on Hermes startup after installation.
- Plugin management and inspection commands include `hermes plugins list` and `/plugins` inside the Hermes runtime.
- Debug discovery in the VM with `HERMES_PLUGINS_DEBUG=1 hermes plugins list`.
- Repository plugin entry point used by this project:
  - `aiops`
- Hermes plugin packages should expose a single `register(ctx)` entry point target.
- Hermes plugin packages should also ship a `plugin.yaml` manifest.

## Current Hermes Plugin API Surface

Current Hermes plugin docs describe a registration-context API, not decorator-based registration.

- Hook registration: `ctx.register_hook(name, handler)`
- Tool registration: `ctx.register_tool(name=..., toolset=..., schema=..., handler=..., description=...)`
- CLI command registration: `ctx.register_cli_command(name, help, setup_fn, handler_fn)`

Implication for this repo:

- There is no confirmed current `@hook` import path to rely on.
- There is no confirmed current `@tool` import path to rely on.
- The practical integration boundary for Task 0 is `register_*` functions that Hermes can load via entry points.
- The practical runtime boundary is one plugin entry point that resolves to `aiops.hermes_plugin:register`.

## Skill Bundle Format

Hermes skills are Markdown files with YAML frontmatter. The current metadata used by this repo is:

```yaml
---
name: aiops-ping
description: Use when verifying Hermes plugin discovery, AIOps plugin entry-point loading, or the aiops_ping boundary probe tool during Task 0 integration checks.
version: 1.0.0
author: AIOps Team
license: MIT
metadata:
  hermes:
    tags: [aiops, hermes, plugin, discovery, validation, ping]
    requires_toolsets: [terminal]
---
```

Recommended sections:

- `# Skill Title`
- `## Preconditions`
- `## Quick Reference`
- `## When to Use`
- `## Procedure`
- `## Decision Points`
- `## Pitfalls`
- `## Verification`

Skill locations documented by Hermes:

- Local writable skills: `~/.hermes/skills/`
- Shared external skills: `~/.agents/skills/`
- Plugin-bundled skills: `~/.hermes/plugins/<plugin>/skills/<skill-name>/SKILL.md`

Repository convention for future packaging:

- Source-controlled skill files live under `src/aiops/bot/skills/`
- Current Task 0 probe skill path: `src/aiops/bot/skills/aiops-ping/SKILL.md`

## Config And Data Paths

- Main config: `~/.hermes/config.yaml`
- Secrets and platform env vars: `~/.hermes/.env`
- Installed skills: `$HERMES_HOME/skills/`

## Webhook Route Schema

Hermes webhook routing is configured in `~/.hermes/config.yaml` under `platforms.webhook.extra.routes`.

Minimal shape:

```yaml
platforms:
  webhook:
    enabled: true
    extra:
      host: 0.0.0.0
      port: 8644
      secret: ""
      rate_limit: 30
      max_body_bytes: 1048576
      routes:
        route-name:
          secret: "per-route-secret"
          events: []
          prompt: "..."
          skills: []
          deliver: "log"
          deliver_extra: {}
```

For this repo, generated route definitions will be stored under `config/hermes/routes.yaml` and then mirrored into the VM-side Hermes config.

## Feishu Configuration Keys

Documented Hermes Feishu/Lark env vars:

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_DOMAIN`
- `FEISHU_CONNECTION_MODE`

Optional but recommended:

- `FEISHU_ALLOWED_USERS`
- `FEISHU_HOME_CHANNEL`

Common VM-side values:

- `FEISHU_DOMAIN=feishu` for China deployments
- `FEISHU_CONNECTION_MODE=websocket`

## Manual Validation In The VM

Run these in the Hermes VM after packaging or editable-installing this repository:

```bash
hermes plugins list
```

Expected output includes the `aiops` plugin.

If discovery fails:

```bash
HERMES_PLUGINS_DEBUG=1 hermes plugins list
```

If the plugin is visible and you want an in-runtime check, use `/plugins` inside Hermes and then trigger the `aiops_ping` probe tool.

## Common Failure: `uv sync` Succeeds But `hermes plugins list` Shows Nothing

This is the most likely cause when entry points exist in the repo but Hermes still cannot see them.

Why it happens:

- `uv sync` installs the current project into the repository virtual environment.
- `hermes plugins list` uses the Python environment that the `hermes` executable was installed into.
- If those are different interpreters, Hermes will not see the repo's entry points.

### Quick Proof

Inside the repo in Ubuntu, run:

```bash
uv run python -c "import importlib.metadata as m; print(sorted(ep.name for ep in m.entry_points(group='hermes_agent.plugins')))"
```

If this prints:

```text
['aiops']
```

then the package metadata is correct in the repo environment.

Next, inspect which Hermes binary you are actually running:

```bash
which hermes
head -n 1 "$(which hermes)"
```

If the shebang points to a different Python interpreter than the repo `.venv`, you have an environment mismatch.

### What To Do

Choose one of these two fixes:

#### Fix A: Install the repo into the Python environment used by Hermes

If Hermes is installed globally, via its own installer, or in another venv, install your plugin package into that same interpreter.

Generic pattern:

```bash
<python-used-by-hermes> -m pip install -e /path/to/aiops-v2
hermes plugins list
```

#### Fix B: Run Hermes from the repo environment

Only use this if Hermes itself is installed in the repo `.venv`.

```bash
source .venv/bin/activate
hermes plugins list
```

or, if Hermes is importable in that environment:

```bash
uv run hermes plugins list
```

### Recommended Verification Order

1. `uv run python -c "import importlib.metadata as m; print(sorted(ep.name for ep in m.entry_points(group='hermes_agent.plugins')))"`
2. `which hermes`
3. `head -n 1 "$(which hermes)"`
4. Install the repo into the Hermes interpreter with `pip install -e .`
5. Re-run `hermes plugins list`

## Windows Host To VMware Ubuntu Workflow

Your setup is split across two machines from Hermes' perspective:

- Windows host: edits the repository
- Ubuntu VM: runs Hermes and performs plugin discovery/runtime checks

That means "联通" has two separate problems:

1. How Windows reaches the Ubuntu VM
2. How the repository changes reach the Python environment used by Hermes inside Ubuntu

### Recommended Path: VMware Shared Folder + Editable Install

This is the best setup for rapid iteration.

1. In VMware Workstation, enable Shared Folders for the Ubuntu VM.
2. Share the project directory from Windows into Ubuntu.
3. In Ubuntu, confirm the shared folder is mounted, commonly under `/mnt/hgfs/`.
4. In the Python environment used by Hermes, install the repo in editable mode.

Example in Ubuntu:

```bash
cd /mnt/hgfs/project/aiops-v2
python -m venv .venv
source .venv/bin/activate
pip install -e .
hermes plugins list
```

Why this is preferred:

- You edit on Windows and Hermes immediately sees the same source tree.
- Reinstall cost is low because editable install keeps the package linked to the shared folder.
- Task 0 and later hook/tool iterations are faster than repeatedly copying files into the VM.

### Stable Path: Git Clone Inside Ubuntu

This is better if you want the VM to behave like a production-like isolated runtime.

1. Push your repo changes from Windows.
2. In Ubuntu, clone or pull the repo.
3. Install into the Hermes Python environment.

Example:

```bash
git clone <your-repo-url>
cd aiops-v2
python -m venv .venv
source .venv/bin/activate
pip install -e .
hermes plugins list
```

Why to use it:

- Cleaner separation between development host and runtime VM.
- Fewer edge cases from VMware shared-folder file semantics.

Tradeoff:

- Every code change must be committed/pulled or copied into the VM.

### Terminal Access Path: SSH Into The Ubuntu VM

This solves control-plane access from Windows to Ubuntu. It does not by itself synchronize code.

Use it when you want to run Hermes commands in Ubuntu directly from Windows Terminal or VS Code.

Typical approaches:

- Bridged network: the VM gets its own LAN IP, then Windows connects with `ssh user@<vm-ip>`.
- NAT + port forwarding: forward host port to guest port 22, then connect with `ssh -p <forwarded-port> user@127.0.0.1`.

Once connected, run:

```bash
hermes plugins list
HERMES_PLUGINS_DEBUG=1 hermes plugins list
```

### What You Actually Need For This Project Right Now

For Task 0 through early Task 1, the simplest working loop is:

1. Windows edits repository
2. VMware shared folder exposes repository to Ubuntu
3. Ubuntu Hermes environment runs `pip install -e <shared-path>`
4. Ubuntu validates with `hermes plugins list`

That is enough to verify plugin discovery without introducing extra deployment machinery.