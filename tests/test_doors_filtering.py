"""Test door filtering feature for Nautilus search (#160)."""

import json
import subprocess
import sys


def test_door_flag_is_alias_for_context():
    """Test that --door flag works as an alias for --context."""
    # Run search with --door flag
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "core.nautilus.nautilus_cli",
            "search",
            "memory",
            "--n",
            "5",
            "--door",
            "memory",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"Search failed: {result.stderr}"

    output = json.loads(result.stdout)
    assert "query" in output
    assert output["query"] == "memory"
    assert "results" in output

    # All results should have the "memory" tag
    for r in output["results"]:
        assert "context_tags" in r
        assert "memory" in r["context_tags"], f"Result missing 'memory' tag: {r}"


def test_door_query_command():
    """Test the doors query command."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "core.nautilus.doors",
            "query",
            "memory",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"Query failed: {result.stderr}"

    output = json.loads(result.stdout)
    assert "door_tag" in output
    assert output["door_tag"] == "memory"
    assert "count" in output
    assert output["count"] > 0
    assert "chunks" in output
    assert len(output["chunks"]) > 0


def test_door_filter_with_verbose():
    """Test verbose output shows door filter info."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "core.nautilus.nautilus_cli",
            "search",
            "memory",
            "--door",
            "memory",
            "--verbose",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"Search failed: {result.stderr}"

    # Verbose output should mention the context filter
    assert "Context filter" in result.stderr or "context" in result.stderr.lower()
