"""Integration checks for Hermes plugin discovery metadata."""

import importlib.metadata
import shutil
import subprocess
from pathlib import Path

import pytest


def test_aiops_plugin_registered_under_hermes_entry_point() -> None:
    """The package should expose the Hermes plugin entry point after installation."""
    entry_points = importlib.metadata.entry_points(group="hermes_agent.plugins")
    names = {entry_point.name for entry_point in entry_points}

    assert "aiops" in names


def test_aiops_plugin_manifest_exists() -> None:
    """The Hermes plugin package should ship a manifest file."""
    manifest_path = Path("src/aiops/hermes_plugin/plugin.yaml")

    assert manifest_path.exists()


@pytest.mark.hermes_runtime
def test_hermes_lists_our_plugin_via_cli() -> None:
    """Hermes CLI should list the AIOps plugin when available."""
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
    assert "aiops" in completed.stdout
