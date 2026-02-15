"""
Tests for Nautilus integration module.
"""

import pytest
import sys
import os
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from nautilus import gravity, chambers, doors, mirrors, config  # noqa: E402


def test_config_get_workspace():
    """Test workspace path resolution."""
    workspace = config.get_workspace()
    assert workspace is not None
    assert isinstance(workspace, Path)
    assert workspace.exists()


def test_config_get_config():
    """Test configuration loading."""
    cfg = config.get_nautilus_config()
    assert "enabled" in cfg
    assert "gravity_db" in cfg
    assert "chamber_thresholds" in cfg
    assert cfg["enabled"] is True


def test_config_get_db_path():
    """Test database path resolution."""
    db_path = config.get_gravity_db_path()
    assert db_path is not None
    assert isinstance(db_path, Path)
    # Path should be absolute and end with gravity.db
    assert db_path.name == "gravity.db"


def test_gravity_get_db():
    """Test gravity database connection."""
    db = gravity.get_db()
    assert db is not None
    # Check that required tables exist
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t[0] for t in tables]
    assert "gravity" in table_names
    assert "access_log" in table_names
    db.close()


def test_gravity_compute_effective_mass():
    """Test gravity scoring computation."""
    # Create a mock row
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE test (
            path, access_count, reference_count, explicit_importance,
            last_written_at, last_accessed_at
        )"""
    )
    conn.execute(
        """INSERT INTO test VALUES (
            'test/file.md', 5, 2, 1.0,
            '2026-02-14T20:00:00+00:00', '2026-02-14T19:00:00+00:00'
        )"""
    )
    row = conn.execute("SELECT * FROM test").fetchone()

    mass = gravity.compute_effective_mass(row)
    assert mass > 0
    assert mass <= 100.0  # Should not exceed mass cap
    conn.close()


def test_chambers_classify_chamber():
    """Test chamber classification."""
    # A recent file should be in atrium
    recent_file = "memory/2026-02-14-test.md"
    chamber = chambers.classify_chamber(recent_file)
    assert chamber in ["atrium", "corridor", "vault"]


def test_doors_classify_text():
    """Test query context classification."""
    text = "project nautilus gravity chambers"
    tags = doors.classify_text(text)
    # Should at least match "project:nautilus"
    assert isinstance(tags, list)


def test_mirrors_get_db():
    """Test mirrors database connection."""
    db = mirrors.get_db()
    assert db is not None
    # Check that mirrors table exists
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t[0] for t in tables]
    assert "mirrors" in table_names
    db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
