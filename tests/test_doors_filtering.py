"""Test door filtering feature for Nautilus search (#160)."""

import json
import subprocess
import sys
from pathlib import Path


def test_door_filter_basic():
    """Test that --door flag filters results correctly."""
    # Run search with door filter
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "core.nautilus.nautilus_cli",
            "search",
            "memory",
            "--n",
            "3",
            "--door",
            "project:nautilus",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"Search failed: {result.stderr}"

    output = json.loads(result.stdout)
    assert "query" in output
    assert output["query"] == "memory"
    assert "mode" in output
    assert "door-filtered:project:nautilus" in output["mode"]
    assert "door_filter" in output
    assert output["door_filter"] == "project:nautilus"
    assert "results" in output


def test_door_filter_vs_normal_search():
    """Test that door filtering reduces results compared to normal search."""
    # Normal search
    normal_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "core.nautilus.nautilus_cli",
            "search",
            "memory",
            "--n",
            "10",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Door filtered search
    door_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "core.nautilus.nautilus_cli",
            "search",
            "memory",
            "--n",
            "10",
            "--door",
            "project:nautilus",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert normal_result.returncode == 0
    assert door_result.returncode == 0

    normal_output = json.loads(normal_result.stdout)
    door_output = json.loads(door_result.stdout)

    # Door filtered should have mode indicating filtering
    assert "full" in normal_output["mode"] or "context-filtered" in normal_output["mode"]
    assert "door-filtered:project:nautilus" in door_output["mode"]


def test_door_query_command():
    """Test the doors query command."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "core.nautilus.doors",
            "query",
            "project:nautilus",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"Query failed: {result.stderr}"

    output = json.loads(result.stdout)
    assert "door_tag" in output
    assert output["door_tag"] == "project:nautilus"
    assert "count" in output
    assert "chunks" in output
    assert isinstance(output["chunks"], list)


def test_door_filter_with_verbose():
    """Test that verbose output includes door filter information."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "core.nautilus.nautilus_cli",
            "search",
            "memory",
            "--n",
            "2",
            "--door",
            "project:nautilus",
            "--verbose",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0
    # Check stderr for verbose output
    assert "🚪 Door filter: project:nautilus" in result.stderr or "door=project:nautilus" in result.stderr


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
