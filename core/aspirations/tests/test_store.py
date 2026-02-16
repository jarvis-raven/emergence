"""Unit tests for aspirations store operations.

Tests CRUD operations, tree queries, orphan detection, and data persistence.
Uses tempfile for test isolation.
"""

from core.aspirations.models import create_default_data
from core.aspirations.store import (
    load_aspirations,
    save_aspirations,
    add_aspiration,
    add_project,
    remove_aspiration,
    remove_project,
    update_project_status,
    link_project,
    get_tree,
    get_orphans,
    get_barren,
)
import sys
import os
import json
import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

# Import from the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestLoadAspirations(unittest.TestCase):
    """Test loading aspirations from file."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_path = Path(self.temp_dir) / "aspirations.json"

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_missing_file_returns_defaults(self):
        """Loading missing file should return default structure."""
        # File doesn't exist
        self.assertFalse(self.state_path.exists())

        data = load_aspirations(self.state_path)

        self.assertIn("version", data)
        self.assertIn("aspirations", data)
        self.assertIn("projects", data)
        self.assertIn("meta", data)
        self.assertEqual(data["aspirations"], [])
        self.assertEqual(data["projects"], [])

    def test_load_empty_file_raises_error(self):
        """Loading empty file should raise SystemExit (corrupted file)."""
        # Create empty file
        self.state_path.write_text("")

        # Empty file is treated as corrupted JSON, should exit
        with self.assertRaises(SystemExit) as cm:
            load_aspirations(self.state_path)
        self.assertEqual(cm.exception.code, 1)

    def test_load_valid_file_returns_correct_counts(self):
        """Loading valid file should return correct data."""
        # Create valid data
        test_data = {
            "version": 1,
            "aspirations": [
                {
                    "id": "dream-1",
                    "title": "Dream 1",
                    "description": "First dream",
                    "category": "creative",
                    "createdAt": "2026-01-01",
                },
                {
                    "id": "dream-2",
                    "title": "Dream 2",
                    "description": "Second dream",
                    "category": "practical",
                    "createdAt": "2026-01-02",
                },
            ],
            "projects": [
                {
                    "id": "proj-1",
                    "name": "Project 1",
                    "aspirationId": "dream-1",
                    "status": "active",
                    "category": "tool",
                    "description": "First project",
                    "updatedAt": "2026-01-01",
                },
            ],
            "meta": {"updatedAt": datetime.now(timezone.utc).isoformat()},
        }
        self.state_path.write_text(json.dumps(test_data))

        data = load_aspirations(self.state_path)

        self.assertEqual(len(data["aspirations"]), 2)
        self.assertEqual(len(data["projects"]), 1)
        self.assertEqual(data["aspirations"][0]["id"], "dream-1")
        self.assertEqual(data["projects"][0]["id"], "proj-1")


class TestAddAspiration(unittest.TestCase):
    """Test adding aspirations."""

    def setUp(self):
        """Set up test fixtures."""
        self.data = create_default_data()

    def test_add_aspiration_appears_in_data(self):
        """Adding aspiration should make it appear in data."""
        aspiration = {
            "id": "test-dream",
            "title": "Test Dream",
            "description": "A test dream",
            "category": "creative",
            "createdAt": "2026-01-01",
        }

        success, msg = add_aspiration(self.data, aspiration)

        self.assertTrue(success)
        self.assertEqual(len(self.data["aspirations"]), 1)
        self.assertEqual(self.data["aspirations"][0]["id"], "test-dream")

    def test_add_duplicate_aspiration_rejected(self):
        """Adding duplicate aspiration should be rejected."""
        aspiration = {
            "id": "test-dream",
            "title": "Test Dream",
            "description": "A test dream",
            "category": "creative",
            "createdAt": "2026-01-01",
        }

        # Add first time
        success, msg = add_aspiration(self.data, aspiration)
        self.assertTrue(success)

        # Add duplicate
        success, msg = add_aspiration(self.data, aspiration)
        self.assertFalse(success)
        self.assertIn("already exists", msg)
        self.assertEqual(len(self.data["aspirations"]), 1)


class TestAddProject(unittest.TestCase):
    """Test adding projects."""

    def setUp(self):
        """Set up test fixtures."""
        self.data = create_default_data()
        # Add an aspiration first
        self.data["aspirations"].append(
            {
                "id": "test-dream",
                "title": "Test Dream",
                "description": "A test dream",
                "category": "creative",
                "createdAt": "2026-01-01",
            }
        )

    def test_add_project_with_valid_aspiration_id_succeeds(self):
        """Adding project with valid aspirationId should succeed."""
        project = {
            "id": "test-project",
            "name": "Test Project",
            "aspirationId": "test-dream",
            "status": "active",
            "category": "tool",
            "description": "A test project",
            "updatedAt": "2026-01-01",
        }

        success, msg = add_project(self.data, project)

        self.assertTrue(success)
        self.assertEqual(len(self.data["projects"]), 1)
        self.assertEqual(self.data["projects"][0]["id"], "test-project")

    def test_add_project_with_invalid_aspiration_id_rejected(self):
        """Adding project with invalid aspirationId should be rejected."""
        project = {
            "id": "test-project",
            "name": "Test Project",
            "aspirationId": "nonexistent-dream",
            "status": "active",
            "category": "tool",
            "description": "A test project",
            "updatedAt": "2026-01-01",
        }

        success, msg = add_project(self.data, project)

        self.assertFalse(success)
        self.assertIn("aspiration", msg.lower())
        self.assertEqual(len(self.data["projects"]), 0)


class TestRemoveAspiration(unittest.TestCase):
    """Test removing aspirations."""

    def setUp(self):
        """Set up test fixtures."""
        self.data = create_default_data()
        # Add aspiration
        self.data["aspirations"].append(
            {
                "id": "test-dream",
                "title": "Test Dream",
                "description": "A test dream",
                "category": "creative",
                "createdAt": "2026-01-01",
            }
        )

    def test_remove_aspiration_with_linked_projects_rejected(self):
        """Removing aspiration with linked projects should be rejected."""
        # Add linked project
        self.data["projects"].append(
            {
                "id": "test-project",
                "name": "Test Project",
                "aspirationId": "test-dream",
                "status": "active",
                "category": "tool",
                "description": "A test project",
                "updatedAt": "2026-01-01",
            }
        )

        success, msg = remove_aspiration(self.data, "test-dream")

        self.assertFalse(success)
        self.assertIn("linked", msg.lower())
        self.assertEqual(len(self.data["aspirations"]), 1)

    def test_remove_aspiration_with_no_projects_succeeds(self):
        """Removing aspiration with no projects should succeed."""
        success, msg = remove_aspiration(self.data, "test-dream")

        self.assertTrue(success)
        self.assertEqual(len(self.data["aspirations"]), 0)

    def test_remove_aspiration_force_orphans(self):
        """Removing with force=True should orphan projects."""
        # Add linked project
        self.data["projects"].append(
            {
                "id": "test-project",
                "name": "Test Project",
                "aspirationId": "test-dream",
                "status": "active",
                "category": "tool",
                "description": "A test project",
                "updatedAt": "2026-01-01",
            }
        )

        success, msg = remove_aspiration(self.data, "test-dream", force=True)

        self.assertTrue(success)
        self.assertEqual(len(self.data["aspirations"]), 0)
        # Project still exists but now orphaned
        self.assertEqual(len(self.data["projects"]), 1)


class TestTreeQueries(unittest.TestCase):
    """Test tree and orphan queries."""

    def setUp(self):
        """Set up test fixtures."""
        self.data = create_default_data()
        # Add aspirations
        self.data["aspirations"].extend(
            [
                {
                    "id": "dream-1",
                    "title": "Dream 1",
                    "description": "First",
                    "category": "creative",
                    "createdAt": "2026-01-01",
                },
                {
                    "id": "dream-2",
                    "title": "Dream 2",
                    "description": "Second",
                    "category": "practical",
                    "createdAt": "2026-01-02",
                },
            ]
        )
        # Add projects
        self.data["projects"].extend(
            [
                {
                    "id": "proj-1",
                    "name": "Project 1",
                    "aspirationId": "dream-1",
                    "status": "active",
                    "category": "tool",
                    "description": "First",
                    "updatedAt": "2026-01-01",
                },
                {
                    "id": "proj-2",
                    "name": "Project 2",
                    "aspirationId": "dream-1",
                    "status": "idea",
                    "category": "creative",
                    "description": "Second",
                    "updatedAt": "2026-01-01",
                },
                {
                    "id": "proj-3",
                    "name": "Project 3",
                    "aspirationId": "dream-2",
                    "status": "paused",
                    "category": "personal",
                    "description": "Third",
                    "updatedAt": "2026-01-01",
                },
            ]
        )

    def test_get_tree_correct_nesting(self):
        """get_tree should return correct nesting."""
        tree = get_tree(self.data)

        self.assertEqual(len(tree), 2)

        # Find dream-1
        dream1 = next((a for a in tree if a["id"] == "dream-1"), None)
        self.assertIsNotNone(dream1)
        self.assertEqual(len(dream1["projects"]), 2)

        # Find dream-2
        dream2 = next((a for a in tree if a["id"] == "dream-2"), None)
        self.assertIsNotNone(dream2)
        self.assertEqual(len(dream2["projects"]), 1)

    def test_get_orphans_finds_invalid_links(self):
        """get_orphans should find projects with invalid aspiration links."""
        # Add orphaned project
        self.data["projects"].append(
            {
                "id": "orphan-proj",
                "name": "Orphan Project",
                "aspirationId": "nonexistent-dream",
                "status": "active",
                "category": "tool",
                "description": "Orphan",
                "updatedAt": "2026-01-01",
            }
        )

        orphans = get_orphans(self.data)

        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0]["id"], "orphan-proj")

    def test_get_barren_finds_aspirations_with_no_projects(self):
        """get_barren should find aspirations with no projects."""
        # Add barren aspiration
        self.data["aspirations"].append(
            {
                "id": "barren-dream",
                "title": "Barren Dream",
                "description": "No projects",
                "category": "philosophical",
                "createdAt": "2026-01-01",
            }
        )

        barren = get_barren(self.data)

        self.assertEqual(len(barren), 1)
        self.assertEqual(barren[0]["id"], "barren-dream")


class TestLinkProject(unittest.TestCase):
    """Test linking projects to new aspirations."""

    def setUp(self):
        """Set up test fixtures."""
        self.data = create_default_data()
        # Add aspirations
        self.data["aspirations"].extend(
            [
                {
                    "id": "dream-1",
                    "title": "Dream 1",
                    "description": "First",
                    "category": "creative",
                    "createdAt": "2026-01-01",
                },
                {
                    "id": "dream-2",
                    "title": "Dream 2",
                    "description": "Second",
                    "category": "practical",
                    "createdAt": "2026-01-02",
                },
            ]
        )
        # Add project linked to dream-1
        self.data["projects"].append(
            {
                "id": "proj-1",
                "name": "Project 1",
                "aspirationId": "dream-1",
                "status": "active",
                "category": "tool",
                "description": "First",
                "updatedAt": "2026-01-01",
            }
        )

    def test_link_project_to_new_aspiration_updated(self):
        """Linking project to new aspiration should update it."""
        success, msg = link_project(self.data, "proj-1", "dream-2")

        self.assertTrue(success)

        project = self.data["projects"][0]
        self.assertEqual(project["aspirationId"], "dream-2")
        # Should have updated timestamp
        self.assertIn("updatedAt", project)


class TestUpdateProjectStatus(unittest.TestCase):
    """Test updating project status."""

    def setUp(self):
        """Set up test fixtures."""
        self.data = create_default_data()
        # Add aspiration
        self.data["aspirations"].append(
            {
                "id": "test-dream",
                "title": "Test Dream",
                "description": "A test dream",
                "category": "creative",
                "createdAt": "2026-01-01",
            }
        )
        # Add project
        self.data["projects"].append(
            {
                "id": "test-project",
                "name": "Test Project",
                "aspirationId": "test-dream",
                "status": "idea",
                "category": "tool",
                "description": "A test project",
                "updatedAt": "2026-01-01",
            }
        )

    def test_update_project_status_reflected(self):
        """Updating project status should be reflected."""
        success, msg = update_project_status(self.data, "test-project", "active")

        self.assertTrue(success)
        self.assertEqual(self.data["projects"][0]["status"], "active")
        # Should have updated timestamp
        self.assertIn("updatedAt", self.data["projects"][0])

    def test_update_project_status_invalid_status_rejected(self):
        """Updating with invalid status should be rejected."""
        success, msg = update_project_status(self.data, "test-project", "invalid-status")

        self.assertFalse(success)
        self.assertEqual(self.data["projects"][0]["status"], "idea")


class TestPersistence(unittest.TestCase):
    """Test save and reload persistence."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_path = Path(self.temp_dir) / "aspirations.json"

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_reload_data_persists(self):
        """Saving and reloading should persist data."""
        # Create data
        data = create_default_data()
        data["aspirations"].append(
            {
                "id": "test-dream",
                "title": "Test Dream",
                "description": "A test dream",
                "category": "creative",
                "createdAt": "2026-01-01",
            }
        )
        data["projects"].append(
            {
                "id": "test-project",
                "name": "Test Project",
                "aspirationId": "test-dream",
                "status": "active",
                "category": "tool",
                "description": "A test project",
                "updatedAt": "2026-01-01",
            }
        )

        # Save
        result = save_aspirations(self.state_path, data)
        self.assertTrue(result)
        self.assertTrue(self.state_path.exists())

        # Reload
        loaded_data = load_aspirations(self.state_path)

        # Verify
        self.assertEqual(len(loaded_data["aspirations"]), 1)
        self.assertEqual(len(loaded_data["projects"]), 1)
        self.assertEqual(loaded_data["aspirations"][0]["id"], "test-dream")
        self.assertEqual(loaded_data["projects"][0]["id"], "test-project")


class TestRemoveProject(unittest.TestCase):
    """Test removing projects."""

    def setUp(self):
        """Set up test fixtures."""
        self.data = create_default_data()
        # Add aspiration
        self.data["aspirations"].append(
            {
                "id": "test-dream",
                "title": "Test Dream",
                "description": "A test dream",
                "category": "creative",
                "createdAt": "2026-01-01",
            }
        )
        # Add projects
        self.data["projects"].extend(
            [
                {
                    "id": "proj-1",
                    "name": "Project 1",
                    "aspirationId": "test-dream",
                    "status": "active",
                    "category": "tool",
                    "description": "First",
                    "updatedAt": "2026-01-01",
                },
                {
                    "id": "proj-2",
                    "name": "Project 2",
                    "aspirationId": "test-dream",
                    "status": "idea",
                    "category": "creative",
                    "description": "Second",
                    "updatedAt": "2026-01-01",
                },
            ]
        )

    def test_remove_project_succeeds(self):
        """Removing project should succeed."""
        success, msg = remove_project(self.data, "proj-1")

        self.assertTrue(success)
        self.assertEqual(len(self.data["projects"]), 1)
        self.assertEqual(self.data["projects"][0]["id"], "proj-2")

    def test_remove_nonexistent_project_fails(self):
        """Removing nonexistent project should fail."""
        success, msg = remove_project(self.data, "nonexistent")

        self.assertFalse(success)
        self.assertIn("not found", msg.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
