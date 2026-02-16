"""Unit tests for Self-History Snapshots.

Tests snapshot creation, listing, hash calculation, and state management.
"""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from core.memory.self_history import (
    load_config,
    calculate_hash,
    snapshot_exists,
    create_snapshot,
    list_snapshots,
    get_self_path,
    get_snapshot_dir,
    get_status,
)


class TestConfigLoading(unittest.TestCase):
    """Test configuration loading."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "emergence.json"

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_default_config(self):
        """Should return defaults when no config exists."""
        config = load_config(Path(self.temp_dir) / "nonexistent.json")

        self.assertIn("memory", config)
        self.assertEqual(config["memory"]["self_history_dir"], "memory/self-history")

    def test_load_custom_config(self):
        """Should load custom config values."""
        custom = {"agent": {"name": "Test Agent"}, "memory": {"self_history_dir": "custom/history"}}
        self.config_file.write_text(json.dumps(custom))

        config = load_config(self.config_file)

        self.assertEqual(config["memory"]["self_history_dir"], "custom/history")


class TestHashCalculation(unittest.TestCase):
    """Test content hash calculation."""

    def test_calculate_hash(self):
        """Should return consistent hash for same content."""
        content = "Test content for hashing"

        hash1 = calculate_hash(content)
        hash2 = calculate_hash(content)

        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 16)  # Truncated to 16 chars

    def test_different_content_different_hash(self):
        """Should return different hashes for different content."""
        hash1 = calculate_hash("Content A")
        hash2 = calculate_hash("Content B")

        self.assertNotEqual(hash1, hash2)

    def test_hash_is_hex(self):
        """Should return hexadecimal string."""
        content = "Test"
        hash_str = calculate_hash(content)

        self.assertTrue(all(c in "0123456789abcdef" for c in hash_str))


class TestSnapshotExistence(unittest.TestCase):
    """Test snapshot existence checking."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.snapshot_dir = Path(self.temp_dir) / "snapshots"
        self.snapshot_dir.mkdir()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_snapshot_exists_true(self):
        """Should return True when snapshot exists."""
        snapshot_path = self.snapshot_dir / "SELF-2026-02-07.md"
        snapshot_path.write_text("test")

        exists = snapshot_exists(self.snapshot_dir, "2026-02-07")

        self.assertTrue(exists)

    def test_snapshot_exists_false(self):
        """Should return False when snapshot doesn't exist."""
        exists = snapshot_exists(self.snapshot_dir, "2026-02-06")

        self.assertFalse(exists)


class TestSnapshotCreation(unittest.TestCase):
    """Test snapshot creation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.identity_dir = Path(self.temp_dir) / "identity"
        self.identity_dir.mkdir()
        self.snapshot_dir = Path(self.temp_dir) / "snapshots"

        # Create SELF.md
        self.self_path = self.identity_dir / "SELF.md"
        self.self_path.write_text("# SELF.md\n\nWho I am.")

        self.config = {
            "paths": {
                "workspace": self.temp_dir,
                "identity": str(self.identity_dir.relative_to(self.temp_dir)),
            },
            "memory": {"self_history_dir": str(self.snapshot_dir.relative_to(self.temp_dir))},
        }

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_snapshot_success(self):
        """Should create snapshot successfully."""
        result = create_snapshot(self.config, date_str="2026-02-07", verbose=False)

        self.assertIsNotNone(result)
        self.assertTrue(result.exists())
        self.assertEqual(result.name, "SELF-2026-02-07.md")

    def test_snapshot_has_header(self):
        """Should add metadata header to snapshot."""
        create_snapshot(self.config, date_str="2026-02-07", verbose=False)

        snapshot_path = self.snapshot_dir / "SELF-2026-02-07.md"
        content = snapshot_path.read_text()

        self.assertIn("SELF-HISTORY SNAPSHOT", content)
        self.assertIn("Original: SELF.md", content)
        self.assertIn("Date: 2026-02-07", content)
        self.assertIn("Hash:", content)

    def test_snapshot_skips_if_exists(self):
        """Should skip if snapshot already exists."""
        # Create first snapshot
        create_snapshot(self.config, date_str="2026-02-07", verbose=False)

        # Try to create again
        result = create_snapshot(self.config, date_str="2026-02-07", verbose=False)

        self.assertIsNone(result)

    def test_snapshot_missing_self_md(self):
        """Should fail if SELF.md doesn't exist."""
        self.self_path.unlink()

        result = create_snapshot(self.config, date_str="2026-02-07", verbose=False)

        self.assertIsNone(result)

    def test_create_snapshot_dry_run(self):
        """Should not create file in dry run mode."""
        result = create_snapshot(self.config, date_str="2026-02-07", dry_run=True, verbose=False)

        self.assertIsNotNone(result)
        self.assertFalse(result.exists())

    def test_create_snapshot_default_date(self):
        """Should use today's date when not specified."""
        result = create_snapshot(self.config, verbose=False)

        self.assertIsNotNone(result)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.assertIn(today, result.name)


class TestSnapshotListing(unittest.TestCase):
    """Test snapshot listing."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.snapshot_dir = Path(self.temp_dir) / "snapshots"
        self.snapshot_dir.mkdir()

        self.config = {
            "paths": {"workspace": self.temp_dir},
            "memory": {"self_history_dir": "snapshots"},
        }

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_empty(self):
        """Should return empty list when no snapshots."""
        snapshots = list_snapshots(self.config)

        self.assertEqual(snapshots, [])

    def test_list_snapshots(self):
        """Should list all snapshots with metadata."""
        # Create some snapshots
        (self.snapshot_dir / "SELF-2026-02-05.md").write_text("<!--\nHash: abc123\n-->\nContent")
        (self.snapshot_dir / "SELF-2026-02-06.md").write_text("<!--\nHash: def456\n-->\nContent")
        (self.snapshot_dir / "SELF-2026-02-07.md").write_text("<!--\nHash: ghi789\n-->\nContent")

        snapshots = list_snapshots(self.config)

        self.assertEqual(len(snapshots), 3)
        self.assertEqual(snapshots[0]["date"], "2026-02-05")
        self.assertEqual(snapshots[1]["date"], "2026-02-06")
        self.assertEqual(snapshots[2]["date"], "2026-02-07")

    def test_list_includes_metadata(self):
        """Should include size and hash in metadata."""
        (self.snapshot_dir / "SELF-2026-02-07.md").write_text(
            "<!--\nHash: sha256:testhash123\n-->\n# SELF\n\nContent here"
        )

        snapshots = list_snapshots(self.config)

        self.assertEqual(len(snapshots), 1)
        self.assertIn("size_bytes", snapshots[0])
        self.assertIn("modified", snapshots[0])
        self.assertIn("hash", snapshots[0])


class TestPathResolution(unittest.TestCase):
    """Test path resolution."""

    def test_get_self_path(self):
        """Should resolve SELF.md path."""
        config = {"paths": {"workspace": "/workspace", "identity": "."}}

        path = get_self_path(config)

        self.assertIn("SELF.md", str(path))

    def test_get_snapshot_dir(self):
        """Should resolve snapshot directory."""
        config = {
            "paths": {"workspace": "/workspace"},
            "memory": {"self_history_dir": "memory/self-history"},
        }

        path = get_snapshot_dir(config)

        self.assertIn("self-history", str(path))


class TestStatus(unittest.TestCase):
    """Test status reporting."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.snapshot_dir = Path(self.temp_dir) / "snapshots"
        self.snapshot_dir.mkdir()

        self.self_path = Path(self.temp_dir) / "SELF.md"
        self.self_path.write_text("# SELF")

        self.config = {
            "paths": {"workspace": self.temp_dir, "identity": "."},
            "memory": {"self_history_dir": "snapshots"},
        }

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_status_empty(self):
        """Should report status with no snapshots."""
        status = get_status(self.config)

        self.assertEqual(status["snapshot_count"], 0)
        self.assertTrue(status["self_exists"])
        self.assertEqual(status["total_storage_bytes"], 0)

    def test_get_status_with_snapshots(self):
        """Should report correct status with snapshots."""
        # Create some snapshots
        (self.snapshot_dir / "SELF-2026-02-06.md").write_text("Content A")
        (self.snapshot_dir / "SELF-2026-02-07.md").write_text("Content B here")

        status = get_status(self.config)

        self.assertEqual(status["snapshot_count"], 2)
        self.assertEqual(status["total_storage_bytes"], len("Content A") + len("Content B here"))


if __name__ == "__main__":
    unittest.main()
