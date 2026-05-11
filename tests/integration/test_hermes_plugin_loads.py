"""Integration checks for Hermes plugin discovery metadata."""

import importlib.metadata
import shutil
import subprocess

import pytest


def test_aiops_plugin_registered_under_hermes_entry_point() -> None:
    """The package should expose Hermes plugin entry points after installation."""
    entry_points = importlib.metadata.entry_points(group="hermes_agent.plugins")
    names = {entry_point.name for entry_point in entry_points}

    assert "aiops_hooks" in names
    assert "aiops_tools" in names
    assert "aiops_bot" in names


@pytest.mark.hermes_runtime
def test_hermes_lists_our_plugin_via_cli() -> None:
    """Hermes CLI should list our plugin entry points when available."""
    pytest.importorskip("hermes_agent")

    hermes_binary = shutil.which("hermes")
    if hermes_binary is None:
        pytest.skip("Hermes CLI is not available in this environment")

    completed = subprocess.run(
        [hermes_binary, "plugins", "list"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "aiops_hooks" in completed.stdout
    assert "aiops_tools" in completed.stdout
    assert "aiops_bot" in completed.stdout
