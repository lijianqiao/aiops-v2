# Hermes Bootstrap Boundary Notes

## Scope

This runbook only covers the Task 0 bootstrap boundary: how this repo is loaded by
Hermes, how to verify plugin discovery, and how to fix the most common environment mismatch.

## Recommended Loading Strategy For This Repo

This repo should use a pip-installed plugin package via `hermes_agent.plugins`.

Why this is the right choice here:

- The repo is already a versioned Python package with `pyproject.toml`.
- The plugin implementation lives inside the project codebase under `src/aiops/`.
- Integration tests already validate package metadata and entry-point discovery.
- Future CI, editable installs, and packaging all fit this model naturally.

## Plugin Discovery

- Hermes entry-point group: `hermes_agent.plugins`
- Pip-installed plugins are auto-discovered on Hermes startup after installation.
- This repo currently exposes one plugin entry point: `aiops`
- That entry point resolves to `aiops.hermes_plugin:register`
- The plugin package also ships `src/aiops/hermes_plugin/plugin.yaml`

## Manual Validation In The VM

Run these in the Hermes VM after installing this repo into the Python interpreter used by Hermes:

```bash
hermes plugins list
```

Expected output includes the `aiops` plugin.

If discovery fails:

```bash
HERMES_PLUGINS_DEBUG=1 hermes plugins list
```

If the plugin is visible and you want a low-risk runtime probe, trigger `aiops_ping`.

## Common Failure: `uv sync` Succeeds But `hermes plugins list` Shows Nothing

Most likely cause:

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

then the package metadata is correct in the repo environment, and the remaining problem is interpreter mismatch.

Next, inspect which Hermes binary you are actually running:

```bash
which hermes
head -n 1 "$(which hermes)"
```

If the shebang points to a different Python interpreter than the repo `.venv`, you have an environment mismatch.

### What To Do

Primary fix: install the repo into the Python interpreter used by Hermes.

Generic command:

```bash
<python-used-by-hermes> -m pip install -e /path/to/aiops-v2
hermes plugins list
```

### Recommended Verification Order

1. `uv run python -c "import importlib.metadata as m; print(sorted(ep.name for ep in m.entry_points(group='hermes_agent.plugins')))"`
2. `which hermes`
3. `head -n 1 "$(which hermes)"`
4. Install the repo into the Hermes interpreter with `pip install -e .`
5. Re-run `hermes plugins list`

## Recommended Working Loop

For this project, keep the loop simple:

1. Edit the repo
2. Make the repo visible inside Ubuntu VM
3. Install the repo into the Hermes interpreter with `pip install -e <repo-path>`
4. Validate with `hermes plugins list`