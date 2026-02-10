#!/usr/bin/env python3
"""Unit tests for the detection module."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from detection import (
    EMERGENCE_MARKER,
    FileDecision,
    FileDisposition,
    FileRecommendation,
    augment_agents_md,
    backup_all_files,
    classify_agent_type,
    classify_file,
    classify_files,
    create_backup,
    discover_identity_files,
    generate_placement_plan,
    invert_disposition,
)


class TestDiscoverIdentityFiles(unittest.TestCase):
    """Test file discovery logic."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_discover_empty_workspace(self) -> None:
        """Empty workspace returns None for all files."""
        result = discover_identity_files(self.temp_dir)

        self.assertEqual(len(result), 9)
        for filename, path in result.items():
            self.assertIsNone(path)

    def test_discover_some_files(self) -> None:
        """Workspace with some files returns paths for existing files."""
        (self.temp_dir / "SOUL.md").write_text("# SOUL", encoding="utf-8")
        (self.temp_dir / "USER.md").write_text("# USER", encoding="utf-8")

        result = discover_identity_files(self.temp_dir)

        self.assertIsNotNone(result["SOUL.md"])
        self.assertIsNotNone(result["USER.md"])
        self.assertIsNone(result["SELF.md"])
        self.assertIsNone(result["AGENTS.md"])

    def test_discover_all_files(self) -> None:
        """Workspace with all identity files."""
        for name in ["SOUL.md", "SELF.md", "USER.md", "AGENTS.md",
                     "INTERESTS.md", "THREAD.md", "BOOTSTRAP.md",
                     "IDENTITY.md", "SECURITY.md"]:
            (self.temp_dir / name).write_text(f"# {name}", encoding="utf-8")

        result = discover_identity_files(self.temp_dir)

        for filename, path in result.items():
            self.assertIsNotNone(path)
            self.assertTrue(path.exists())


class TestClassifyFile(unittest.TestCase):
    """Test single file classification."""

    def test_classify_soul_fresh(self) -> None:
        """SOUL.md on fresh install should be CREATE."""
        result = classify_file("SOUL.md", agent_mode="fresh")
        self.assertEqual(result, "create")

    def test_classify_soul_existing(self) -> None:
        """SOUL.md on existing install should be REPLACE."""
        result = classify_file("SOUL.md", agent_mode="existing")
        self.assertEqual(result, "replace")

    def test_classify_user(self) -> None:
        """USER.md on existing install should be KEEP."""
        result = classify_file("USER.md", agent_mode="existing")
        self.assertEqual(result, "keep")

    def test_classify_agents(self) -> None:
        """AGENTS.md on existing install should be AUGMENT."""
        result = classify_file("AGENTS.md", agent_mode="existing")
        self.assertEqual(result, "augment")

    def test_classify_self(self) -> None:
        """SELF.md on existing install should be BACKUP_REPLACE."""
        result = classify_file("SELF.md", agent_mode="existing")
        self.assertEqual(result, "backup_replace")

    def test_classify_interests(self) -> None:
        """INTERESTS.md should be CREATE on both modes."""
        result = classify_file("INTERESTS.md", agent_mode="existing")
        self.assertEqual(result, "create")

    def test_classify_thread(self) -> None:
        """THREAD.md on existing install should be KEEP."""
        result = classify_file("THREAD.md", agent_mode="existing")
        self.assertEqual(result, "keep")

    def test_classify_bootstrap(self) -> None:
        """BOOTSTRAP.md on existing install should be BACKUP_REPLACE."""
        result = classify_file("BOOTSTRAP.md", agent_mode="existing")
        self.assertEqual(result, "backup_replace")

    def test_classify_unknown(self) -> None:
        """Unknown file raises ValueError."""
        with self.assertRaises(ValueError):
            classify_file("UNKNOWN.md")

    def test_classify_agents_already_augmented(self) -> None:
        """AGENTS.md with marker should be KEEP."""
        content = f"# AGENTS\n\n{EMERGENCE_MARKER}\n\nSome content"
        result = classify_file("AGENTS.md", content)
        self.assertEqual(result, "keep")


class TestClassifyFiles(unittest.TestCase):
    """Test batch file classification."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_classify_new_workspace_fresh(self) -> None:
        """Fresh agent: all files → CREATE."""
        discovered = {
            "SOUL.md": None,
            "SELF.md": None,
            "USER.md": None,
            "AGENTS.md": None,
            "INTERESTS.md": None,
            "THREAD.md": None,
            "BOOTSTRAP.md": None,
            "IDENTITY.md": None,
            "SECURITY.md": None,
        }

        recommendations = classify_files(discovered, agent_mode="fresh")

        by_name = {r.filename: r for r in recommendations}
        for name in discovered:
            self.assertEqual(by_name[name].disposition, FileDisposition.CREATE)

    def test_classify_new_workspace_existing(self) -> None:
        """Existing agent: files missing → appropriate recommendations."""
        discovered = {
            "SOUL.md": None,
            "SELF.md": None,
            "USER.md": None,
            "AGENTS.md": None,
            "INTERESTS.md": None,
            "THREAD.md": None,
            "BOOTSTRAP.md": None,
        }

        recommendations = classify_files(discovered, agent_mode="existing")

        by_name = {r.filename: r for r in recommendations}
        self.assertEqual(by_name["SOUL.md"].disposition, FileDisposition.REPLACE)
        self.assertEqual(by_name["SELF.md"].disposition, FileDisposition.BACKUP_REPLACE)
        self.assertEqual(by_name["USER.md"].disposition, FileDisposition.KEEP)
        self.assertEqual(by_name["AGENTS.md"].disposition, FileDisposition.AUGMENT)
        self.assertEqual(by_name["INTERESTS.md"].disposition, FileDisposition.CREATE)
        self.assertEqual(by_name["THREAD.md"].disposition, FileDisposition.KEEP)

    def test_classify_existing_soul(self) -> None:
        """Existing SOUL.md on existing agent → REPLACE recommendation."""
        soul_path = self.temp_dir / "SOUL.md"
        soul_path.write_text("# Old SOUL", encoding="utf-8")

        discovered = {"SOUL.md": soul_path}
        recommendations = classify_files(discovered, agent_mode="existing")

        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0].disposition, FileDisposition.REPLACE)
        self.assertTrue(recommendations[0].backup_required)

    def test_classify_existing_user(self) -> None:
        """Existing USER.md on existing agent → KEEP recommendation."""
        user_path = self.temp_dir / "USER.md"
        user_path.write_text("# User info", encoding="utf-8")

        discovered = {"USER.md": user_path}
        recommendations = classify_files(discovered, agent_mode="existing")

        self.assertEqual(recommendations[0].disposition, FileDisposition.KEEP)
        self.assertFalse(recommendations[0].backup_required)

        self.assertEqual(recommendations[0].disposition, FileDisposition.KEEP)


class TestBackup(unittest.TestCase):
    """Test backup creation logic."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.workspace = self.temp_dir / "workspace"
        self.workspace.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_backup(self) -> None:
        """Backup is created with timestamp."""
        source = self.workspace / "test.md"
        source.write_text("# Test content", encoding="utf-8")
        backup_dir = self.workspace / ".emergence" / "backups"

        backup_path = create_backup(source, backup_dir)

        self.assertTrue(backup_path.exists())
        self.assertEqual(backup_path.read_text(encoding="utf-8"), "# Test content")
        self.assertTrue(".emergence/backups" in str(backup_path))

    def test_backup_preserves_content(self) -> None:
        """Backup preserves file content exactly."""
        source = self.workspace / "SOUL.md"
        content = "# SOUL\n\nThis is the soul content.\n\n- Item 1\n- Item 2"
        source.write_text(content, encoding="utf-8")
        backup_dir = self.workspace / ".emergence" / "backups"

        backup_path = create_backup(source, backup_dir)

        self.assertEqual(backup_path.read_text(encoding="utf-8"), content)

    def test_backup_nonexistent_file(self) -> None:
        """Backing up nonexistent file raises FileNotFoundError."""
        source = self.workspace / "nonexistent.md"
        backup_dir = self.workspace / ".emergence" / "backups"

        with self.assertRaises(FileNotFoundError):
            create_backup(source, backup_dir)

    def test_backup_all_files(self) -> None:
        """Backup multiple files returns correct mapping."""
        files = []
        for name in ["SOUL.md", "SELF.md", "USER.md"]:
            path = self.workspace / name
            path.write_text(f"# {name}", encoding="utf-8")
            files.append(path)

        result = backup_all_files(files, self.workspace)

        self.assertEqual(len(result), 3)
        for name in ["SOUL.md", "SELF.md", "USER.md"]:
            self.assertIn(name, result)
            self.assertTrue(result[name].exists())


class TestAugmentAgents(unittest.TestCase):
    """Test AGENTS.md augmentation logic."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_augment_preserves_content(self) -> None:
        """Augmentation preserves existing content."""
        existing = self.temp_dir / "AGENTS.md"
        existing.write_text("# Original content\n\nExisting rules.", encoding="utf-8")

        result = augment_agents_md(existing)

        self.assertIn("# Original content", result)
        self.assertIn("Existing rules.", result)
        self.assertIn(EMERGENCE_MARKER, result)

    def test_augment_idempotent(self) -> None:
        """Augmentation is idempotent - won't double-add."""
        existing = self.temp_dir / "AGENTS.md"
        existing.write_text(f"# AGENTS\n\n{EMERGENCE_MARKER}\n\nAlready there", encoding="utf-8")

        result = augment_agents_md(existing)

        self.assertEqual(result.count(EMERGENCE_MARKER), 1)

    def test_augment_adds_emergence_section(self) -> None:
        """Augmentation adds Emergence Integration section."""
        existing = self.temp_dir / "AGENTS.md"
        existing.write_text("# AGENTS\n\nSome rules.", encoding="utf-8")

        result = augment_agents_md(existing)

        self.assertIn("## Emergence Integration", result)
        self.assertIn("First Run", result)
        self.assertIn("Every Session", result)


class TestAgentTypeClassification(unittest.TestCase):
    """Test agent type classification."""

    def test_new_agent(self) -> None:
        """No existing files → new agent."""
        decisions = [
            FileDecision("SOUL.md", None, FileDisposition.CREATE),
            FileDecision("SELF.md", None, FileDisposition.CREATE),
        ]
        self.assertEqual(classify_agent_type(decisions), "new")

    def test_existing_full(self) -> None:
        """4+ core files → existing_full."""
        temp_dir = Path(tempfile.mkdtemp())
        decisions = [
            FileDecision("SOUL.md", temp_dir / "SOUL.md", FileDisposition.REPLACE),
            FileDecision("SELF.md", temp_dir / "SELF.md", FileDisposition.BACKUP_REPLACE),
            FileDecision("USER.md", temp_dir / "USER.md", FileDisposition.KEEP),
            FileDecision("AGENTS.md", temp_dir / "AGENTS.md", FileDisposition.AUGMENT),
            FileDecision("INTERESTS.md", None, FileDisposition.CREATE),
        ]
        self.assertEqual(classify_agent_type(decisions), "existing_full")
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_existing_partial(self) -> None:
        """Some but not all files → existing_partial."""
        temp_dir = Path(tempfile.mkdtemp())
        decisions = [
            FileDecision("SOUL.md", temp_dir / "SOUL.md", FileDisposition.REPLACE),
            FileDecision("SELF.md", temp_dir / "SELF.md", FileDisposition.BACKUP_REPLACE),
            FileDecision("USER.md", None, FileDisposition.CREATE),
            FileDecision("AGENTS.md", None, FileDisposition.CREATE),
        ]
        self.assertEqual(classify_agent_type(decisions), "existing_partial")
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestGeneratePlacementPlan(unittest.TestCase):
    """Test full placement plan generation."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.workspace = self.temp_dir / "workspace"
        self.workspace.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_new_workspace_plan(self) -> None:
        """Empty workspace generates new agent plan."""
        plan = generate_placement_plan(
            workspace=self.workspace,
            interactive=False,
            auto_backup=False,
        )

        self.assertEqual(plan["agent_type"], "new")
        self.assertEqual(plan["summary"]["total_files"], 9)
        self.assertEqual(len(plan["files"]), 9)
        self.assertEqual(plan["version"], "1.0.0")

    def test_existing_workspace_plan(self) -> None:
        """Workspace with files generates existing agent plan."""
        (self.workspace / "SOUL.md").write_text("# Old SOUL", encoding="utf-8")
        (self.workspace / "USER.md").write_text("# User info", encoding="utf-8")

        plan = generate_placement_plan(
            workspace=self.workspace,
            interactive=False,
            auto_backup=True,
            agent_mode="existing",
        )

        self.assertEqual(plan["agent_type"], "existing_partial")
        # SOUL.md is REPLACE → backed up, USER.md is KEEP → not backed up
        self.assertIn("SOUL.md", plan["backups"])
        self.assertNotIn("USER.md", plan["backups"])

        # Verify backups exist
        for backup_path in plan["backups"].values():
            self.assertTrue(Path(backup_path).exists())

    def test_plan_structure(self) -> None:
        """Plan has correct structure."""
        (self.workspace / "SOUL.md").write_text("# SOUL", encoding="utf-8")

        plan = generate_placement_plan(
            workspace=self.workspace,
            interactive=False,
            auto_backup=True,
        )

        # Check required keys
        self.assertIn("version", plan)
        self.assertIn("timestamp", plan)
        self.assertIn("workspace", plan)
        self.assertIn("agent_type", plan)
        self.assertIn("backups", plan)
        self.assertIn("files", plan)
        self.assertIn("summary", plan)

        # Check summary keys
        summary = plan["summary"]
        self.assertIn("total_files", summary)
        self.assertIn("new_files", summary)
        self.assertIn("preserved_files", summary)
        self.assertIn("replaced_files", summary)
        self.assertIn("augmented_files", summary)
        self.assertIn("archived_files", summary)


class TestDispositionInversion(unittest.TestCase):
    """Test disposition inversion logic."""

    def test_invert_replace(self) -> None:
        """REPLACE inverts to KEEP."""
        self.assertEqual(invert_disposition(FileDisposition.REPLACE), FileDisposition.KEEP)

    def test_invert_backup_replace(self) -> None:
        """BACKUP_REPLACE inverts to KEEP."""
        self.assertEqual(invert_disposition(FileDisposition.BACKUP_REPLACE), FileDisposition.KEEP)

    def test_invert_augment(self) -> None:
        """AUGMENT inverts to KEEP."""
        self.assertEqual(invert_disposition(FileDisposition.AUGMENT), FileDisposition.KEEP)

    def test_invert_keep(self) -> None:
        """KEEP stays KEEP."""
        self.assertEqual(invert_disposition(FileDisposition.KEEP), FileDisposition.KEEP)

    def test_invert_create(self) -> None:
        """CREATE stays CREATE."""
        self.assertEqual(invert_disposition(FileDisposition.CREATE), FileDisposition.CREATE)


if __name__ == "__main__":
    unittest.main()
