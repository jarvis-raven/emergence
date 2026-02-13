#!/usr/bin/env python3
"""Tests for emergence migrate module."""

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from core.setup.migrate.migrate import (
    export_bundle,
    import_bundle,
    rewrite_openclaw_state,
    rewrite_paths,
    scan_for_paths,
    validate_workspace,
)


class TestScanForPaths(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.workspace = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_finds_paths_in_json(self):
        (self.workspace / "test.json").write_text(
            json.dumps({"path": "/home/dan/workspace/sessions"})
        )
        matches = scan_for_paths(self.workspace, "/home/dan")
        self.assertEqual(len(matches), 1)
        self.assertIn("/home/dan", matches[0][2])

    def test_finds_paths_in_markdown(self):
        (self.workspace / "SOUL.md").write_text(
            "My home is /home/dan/emergence\n"
        )
        matches = scan_for_paths(self.workspace, "/home/dan")
        self.assertEqual(len(matches), 1)

    def test_no_false_positives(self):
        (self.workspace / "test.json").write_text('{"key": "value"}')
        matches = scan_for_paths(self.workspace, "/home/dan")
        self.assertEqual(len(matches), 0)

    def test_skips_git_dirs(self):
        git_dir = self.workspace / ".git"
        git_dir.mkdir()
        (git_dir / "config.txt").write_text("/home/dan/old/path")
        matches = scan_for_paths(self.workspace, "/home/dan")
        self.assertEqual(len(matches), 0)

    def test_finds_paths_in_sqlite(self):
        db_path = self.workspace / "sessions.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE sessions (id INTEGER, path TEXT)")
        conn.execute(
            "INSERT INTO sessions VALUES (1, '/home/dan/.openclaw/sessions/abc.json')"
        )
        conn.commit()
        conn.close()

        matches = scan_for_paths(self.workspace, "/home/dan", include_binary=True)
        self.assertEqual(len(matches), 1)

    def test_multiple_matches_same_file(self):
        (self.workspace / "config.json").write_text(json.dumps({
            "path1": "/home/dan/a",
            "path2": "/home/dan/b",
        }))
        matches = scan_for_paths(self.workspace, "/home/dan")
        # JSON is on one line typically, but our dump might be multi-line
        self.assertGreaterEqual(len(matches), 1)


class TestRewritePaths(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.workspace = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_rewrites_json(self):
        path = self.workspace / "emergence.json"
        path.write_text(json.dumps({
            "paths": {"workspace": "/home/dan/aurora"},
        }))
        stats = rewrite_paths(self.workspace, "/home/dan", "/home/aurora")
        self.assertEqual(stats["files_modified"], 1)
        self.assertEqual(stats["replacements"], 1)
        result = json.loads(path.read_text())
        self.assertEqual(result["paths"]["workspace"], "/home/aurora/aurora")

    def test_rewrites_multiple_occurrences(self):
        """Simulates the Aurora sessions.json bug — many paths in one file."""
        sessions = {
            f"session_{i}": f"/home/dan/.openclaw/sessions/sess_{i}.json"
            for i in range(279)
        }
        path = self.workspace / "sessions.json"
        path.write_text(json.dumps(sessions))

        stats = rewrite_paths(self.workspace, "/home/dan", "/home/aurora")
        self.assertEqual(stats["replacements"], 279)
        self.assertEqual(stats["files_modified"], 1)

        result = json.loads(path.read_text())
        for v in result.values():
            self.assertTrue(v.startswith("/home/aurora/"))
            self.assertNotIn("/home/dan", v)

    def test_dry_run_no_changes(self):
        path = self.workspace / "test.json"
        original = json.dumps({"path": "/home/dan/test"})
        path.write_text(original)

        stats = rewrite_paths(self.workspace, "/home/dan", "/home/aurora", dry_run=True)
        self.assertEqual(stats["replacements"], 1)
        self.assertTrue(stats["dry_run"])
        # File unchanged
        self.assertEqual(path.read_text(), original)

    def test_rewrites_sqlite(self):
        db_path = self.workspace / "state.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE paths (id INTEGER, p TEXT)")
        conn.execute("INSERT INTO paths VALUES (1, '/home/dan/.openclaw/s.json')")
        conn.execute("INSERT INTO paths VALUES (2, '/home/dan/.openclaw/t.json')")
        conn.commit()
        conn.close()

        stats = rewrite_paths(self.workspace, "/home/dan", "/home/aurora")
        self.assertEqual(stats["replacements"], 2)

        conn = sqlite3.connect(str(db_path))
        rows = conn.execute("SELECT p FROM paths").fetchall()
        conn.close()
        for (p,) in rows:
            self.assertTrue(p.startswith("/home/aurora/"))

    def test_trailing_slash_handling(self):
        path = self.workspace / "test.json"
        path.write_text('{"p": "/home/dan/stuff"}')
        stats = rewrite_paths(self.workspace, "/home/dan/", "/home/aurora/")
        self.assertEqual(stats["replacements"], 1)
        self.assertIn("/home/aurora", path.read_text())

    def test_no_matches(self):
        path = self.workspace / "test.json"
        path.write_text('{"p": "/home/other/stuff"}')
        stats = rewrite_paths(self.workspace, "/home/dan", "/home/aurora")
        self.assertEqual(stats["files_modified"], 0)
        self.assertEqual(stats["replacements"], 0)

    def test_markdown_rewrite(self):
        path = self.workspace / "SOUL.md"
        path.write_text("# Soul\nI live at /home/dan/emergence\n")
        stats = rewrite_paths(self.workspace, "/home/dan", "/home/aurora")
        self.assertEqual(stats["replacements"], 1)
        self.assertIn("/home/aurora/emergence", path.read_text())


class TestExportImport(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.source = Path(self.tmpdir) / "source"
        self.dest = Path(self.tmpdir) / "dest"
        self.source.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def _setup_workspace(self):
        """Create a minimal emergence workspace."""
        (self.source / "SOUL.md").write_text("# Aurora\nI am Aurora.\n")
        (self.source / "SELF.md").write_text("# Self\nPath: /home/dan/aurora\n")
        (self.source / "emergence.json").write_text(json.dumps({
            "agent": {"name": "Aurora"},
            "paths": {"workspace": "/home/dan/aurora"},
        }))
        mem = self.source / "memory" / "daily"
        mem.mkdir(parents=True)
        (mem / "2026-02-13.md").write_text("# Today\nDid stuff at /home/dan/aurora\n")

        state = self.source / ".emergence" / "state"
        state.mkdir(parents=True)
        (state / "drives.json").write_text(json.dumps({"CREATIVE": {"pressure": 18}}))

    def test_export_creates_bundle(self):
        self._setup_workspace()
        output = Path(self.tmpdir) / "test.tar.gz"
        result = export_bundle(self.source, output)
        self.assertTrue(result.exists())
        self.assertGreater(result.stat().st_size, 0)

    def test_export_validates_workspace(self):
        empty = Path(self.tmpdir) / "empty"
        empty.mkdir()
        with self.assertRaises(ValueError):
            export_bundle(empty)

    def test_full_roundtrip(self):
        """Export from source, import to dest, verify paths rewritten."""
        self._setup_workspace()
        bundle = export_bundle(self.source, Path(self.tmpdir) / "bundle.tar.gz")

        result = import_bundle(
            bundle, self.dest,
            old_home="/home/dan",
            new_home="/home/aurora",
        )

        self.assertGreater(result["files_extracted"], 0)

        # Check paths were rewritten
        self_md = (self.dest / "SELF.md").read_text()
        self.assertIn("/home/aurora", self_md)
        self.assertNotIn("/home/dan", self_md)

        config = json.loads((self.dest / "emergence.json").read_text())
        self.assertEqual(config["paths"]["workspace"], "/home/aurora/aurora")

        daily = (self.dest / "memory" / "daily" / "2026-02-13.md").read_text()
        self.assertNotIn("/home/dan", daily)

    def test_import_auto_detects_old_home(self):
        """Import should auto-detect old home from manifest."""
        self._setup_workspace()
        bundle = export_bundle(self.source, Path(self.tmpdir) / "bundle.tar.gz")

        # Import without specifying old_home
        result = import_bundle(bundle, self.dest, new_home="/home/newuser")
        # Should have detected and rewritten
        self.assertIsNotNone(result["rewrite_stats"])

    def test_import_creates_backup(self):
        self._setup_workspace()
        bundle = export_bundle(self.source, Path(self.tmpdir) / "bundle.tar.gz")

        # Create existing content in dest
        self.dest.mkdir(parents=True)
        (self.dest / "existing.txt").write_text("existing")

        result = import_bundle(bundle, self.dest, old_home="/home/dan", new_home="/home/aurora")
        self.assertIsNotNone(result["backup_path"])
        self.assertTrue(Path(result["backup_path"]).is_dir())

    def test_import_dry_run(self):
        self._setup_workspace()
        bundle = export_bundle(self.source, Path(self.tmpdir) / "bundle.tar.gz")

        result = import_bundle(
            bundle, self.dest,
            old_home="/home/dan", new_home="/home/aurora",
            dry_run=True,
        )
        # Dest should not have extracted files (may exist as empty dir)
        if self.dest.exists():
            files = list(self.dest.rglob("*"))
            self.assertEqual(len(files), 0, f"Dry run should not extract files, found: {files}")

    def test_import_rejects_path_traversal(self):
        """Security: reject bundles with .. in paths."""
        import tarfile, io
        bad_bundle = Path(self.tmpdir) / "bad.tar.gz"
        with tarfile.open(str(bad_bundle), "w:gz") as tar:
            info = tarfile.TarInfo(name="../../../etc/passwd")
            info.size = 4
            tar.addfile(info, io.BytesIO(b"evil"))

        with self.assertRaises(ValueError):
            import_bundle(bad_bundle, self.dest)


class TestValidateWorkspace(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.workspace = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_valid_workspace(self):
        (self.workspace / "SOUL.md").write_text("# Soul\n")
        (self.workspace / "emergence.json").write_text(json.dumps({
            "agent": {"name": "Test"},
            "paths": {"workspace": "."},
        }))
        results = validate_workspace(self.workspace)
        self.assertTrue(results["valid"])

    def test_detects_stale_paths(self):
        (self.workspace / "SOUL.md").write_text("I live at /home/olduser/stuff\n")
        results = validate_workspace(self.workspace)
        # Should warn about /home/olduser
        self.assertGreater(len(results["warnings"]), 0)

    def test_invalid_json(self):
        (self.workspace / "SOUL.md").write_text("# Soul\n")
        (self.workspace / "emergence.json").write_text("{invalid json")
        results = validate_workspace(self.workspace)
        self.assertFalse(results["valid"])

    def test_nonexistent_workspace(self):
        results = validate_workspace(Path("/nonexistent/path"))
        self.assertFalse(results["valid"])


class TestRewriteOpenClawState(unittest.TestCase):
    """Tests for rewriting paths in OpenClaw state directories.

    This specifically covers the bug that broke Aurora's communication:
    sessions.json files under ~/.openclaw/agents/*/sessions/ contained
    hardcoded absolute paths that weren't updated during migration.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.oc_root = Path(self.tmpdir) / ".openclaw"
        # Create agent sessions structure
        sessions_dir = self.oc_root / "agents" / "main" / "sessions"
        sessions_dir.mkdir(parents=True)
        # Create a sessions.json with old paths (the Aurora bug)
        self.sessions_file = sessions_dir / "sessions.json"
        self.sessions_data = {
            f"sess_{i}": {
                "path": f"/home/dan/.openclaw/agents/main/sessions/sess_{i}.json",
                "workspace": "/home/dan/.openclaw/workspace",
            }
            for i in range(5)
        }
        self.sessions_file.write_text(json.dumps(self.sessions_data))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_rewrites_sessions_json(self):
        """The core Aurora bug: sessions.json paths must be rewritten."""
        stats = rewrite_openclaw_state(
            self.oc_root, "/home/dan", "/home/aurora",
        )
        self.assertEqual(stats["files_modified"], 1)
        self.assertGreater(stats["replacements"], 0)

        result = json.loads(self.sessions_file.read_text())
        for sess in result.values():
            self.assertIn("/home/aurora/", sess["path"])
            self.assertNotIn("/home/dan", sess["path"])

    def test_dry_run_no_changes(self):
        original = self.sessions_file.read_text()
        stats = rewrite_openclaw_state(
            self.oc_root, "/home/dan", "/home/aurora", dry_run=True,
        )
        self.assertGreater(stats["replacements"], 0)
        self.assertTrue(stats["dry_run"])
        self.assertEqual(self.sessions_file.read_text(), original)

    def test_handles_multiple_agents(self):
        """Should process sessions for all agents, not just main."""
        other_dir = self.oc_root / "agents" / "aurora" / "sessions"
        other_dir.mkdir(parents=True)
        other_file = other_dir / "sessions.json"
        other_file.write_text(json.dumps({
            "s1": "/home/dan/.openclaw/agents/aurora/sessions/s1.json",
        }))

        stats = rewrite_openclaw_state(
            self.oc_root, "/home/dan", "/home/aurora",
        )
        self.assertEqual(stats["files_modified"], 2)

        result = json.loads(other_file.read_text())
        self.assertNotIn("/home/dan", result["s1"])

    def test_handles_missing_openclaw_root(self):
        stats = rewrite_openclaw_state(
            Path("/nonexistent"), "/home/dan", "/home/aurora",
        )
        self.assertEqual(stats["files_modified"], 0)
        self.assertGreater(len(stats["errors"]), 0)

    def test_rewrite_paths_with_openclaw_root(self):
        """rewrite_paths should process openclaw state when root is given."""
        workspace = Path(self.tmpdir) / "workspace"
        workspace.mkdir()
        (workspace / "test.json").write_text('{"p": "/home/dan/stuff"}')

        stats = rewrite_paths(
            workspace, "/home/dan", "/home/aurora",
            openclaw_root=self.oc_root,
        )
        # Should have modified both workspace file and sessions.json
        self.assertGreaterEqual(stats["files_modified"], 2)
        self.assertIn("openclaw_stats", stats)

    def test_also_rewrites_top_level_json(self):
        """Config JSON at the openclaw root level should also be rewritten."""
        config = self.oc_root / "config.json"
        config.write_text(json.dumps({"home": "/home/dan/.openclaw"}))

        # Need config dir too
        config_dir = self.oc_root / "config"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "settings.json").write_text(
            json.dumps({"root": "/home/dan/.openclaw"})
        )

        stats = rewrite_openclaw_state(
            self.oc_root, "/home/dan", "/home/aurora",
        )
        # sessions.json + config.json + config/settings.json
        self.assertGreaterEqual(stats["files_modified"], 2)


class TestManifestRelativePaths(unittest.TestCase):
    """Test that export manifests include relative path info for robustness."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.source = Path(self.tmpdir) / "source"
        self.source.mkdir()
        (self.source / "SOUL.md").write_text("# Test\n")
        (self.source / "emergence.json").write_text(json.dumps({
            "agent": {"name": "Test"},
        }))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_manifest_contains_relative_paths(self):
        import tarfile
        bundle = export_bundle(self.source, Path(self.tmpdir) / "b.tar.gz")
        with tarfile.open(str(bundle), "r:gz") as tar:
            f = tar.extractfile("__manifest__.json")
            manifest = json.loads(f.read())

        self.assertEqual(manifest["version"], "1.1")
        self.assertIn("workspace_rel_home", manifest)
        self.assertIn("openclaw_root", manifest)
        self.assertIn("openclaw_root_rel", manifest)
        self.assertIn("source_home", manifest)


class TestCLI(unittest.TestCase):
    """Test CLI argument parsing and basic flow."""

    def test_help_exits(self):
        from core.setup.migrate.migrate import main
        with self.assertRaises(SystemExit):
            main(["--help"])

    def test_no_subcommand_exits(self):
        from core.setup.migrate.migrate import main
        with self.assertRaises(SystemExit):
            main([])


if __name__ == "__main__":
    unittest.main()
