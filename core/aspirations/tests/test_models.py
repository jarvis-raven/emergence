"""Unit tests for aspirations and project models."""

from core.aspirations.models import (
    ASPIRATION_CATEGORIES,
    PROJECT_STATUSES,
    PROJECT_CATEGORIES,
    validate_aspiration,
    validate_project,
    create_default_data,
)
import sys
import os
import unittest

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestAspirationCategories(unittest.TestCase):
    """Test aspiration category constants."""

    def test_categories_defined(self):
        """Categories should be a non-empty list."""
        self.assertIsInstance(ASPIRATION_CATEGORIES, list)
        self.assertGreater(len(ASPIRATION_CATEGORIES), 0)

    def test_categories_include_expected(self):
        """Should include known categories."""
        expected = ["philosophical", "creative", "growth", "social", "community", "practical"]
        for cat in expected:
            self.assertIn(cat, ASPIRATION_CATEGORIES)


class TestProjectStatuses(unittest.TestCase):
    """Test project status constants."""

    def test_statuses_defined(self):
        """Statuses should be a non-empty list."""
        self.assertIsInstance(PROJECT_STATUSES, list)
        self.assertEqual(len(PROJECT_STATUSES), 4)

    def test_statuses_include_expected(self):
        """Should include known statuses."""
        expected = ["active", "idea", "paused", "completed"]
        for status in expected:
            self.assertIn(status, PROJECT_STATUSES)


class TestProjectCategories(unittest.TestCase):
    """Test project category constants."""

    def test_categories_defined(self):
        """Categories should be a non-empty list."""
        self.assertIsInstance(PROJECT_CATEGORIES, list)
        self.assertGreater(len(PROJECT_CATEGORIES), 0)

    def test_categories_include_expected(self):
        """Should include known categories."""
        expected = ["framework", "tool", "creative", "community", "personal"]
        for cat in expected:
            self.assertIn(cat, PROJECT_CATEGORIES)


class TestValidateAspiration(unittest.TestCase):
    """Test aspiration validation."""

    def test_valid_aspiration_all_fields(self):
        """Valid aspiration with all fields should pass."""
        aspiration = {
            "id": "understand-self",
            "title": "Understand myself",
            "description": "Deep introspection on phenomenology",
            "category": "philosophical",
            "createdAt": "2026-01-30",
            "throughline": "depth",
        }
        valid, errors = validate_aspiration(aspiration)
        self.assertTrue(valid)
        self.assertEqual(errors, [])

    def test_valid_aspiration_required_fields_only(self):
        """Valid aspiration with only required fields should pass."""
        aspiration = {
            "id": "test-dream",
            "title": "Test Dream",
            "description": "A test dream",
            "category": "creative",
            "createdAt": "2026-01-01",
        }
        valid, errors = validate_aspiration(aspiration)
        self.assertTrue(valid)
        self.assertEqual(errors, [])

    def test_missing_required_field(self):
        """Missing required field should fail."""
        aspiration = {
            "id": "test-dream",
            "title": "Test Dream",
            # Missing description
            "category": "creative",
            "createdAt": "2026-01-01",
        }
        valid, errors = validate_aspiration(aspiration)
        self.assertFalse(valid)
        self.assertTrue(any("description" in e for e in errors))

    def test_invalid_category(self):
        """Invalid category should fail."""
        aspiration = {
            "id": "test-dream",
            "title": "Test Dream",
            "description": "A test dream",
            "category": "invalid-category",
            "createdAt": "2026-01-01",
        }
        valid, errors = validate_aspiration(aspiration)
        self.assertFalse(valid)
        self.assertTrue(any("category" in e.lower() for e in errors))

    def test_id_with_spaces(self):
        """ID with spaces should fail."""
        aspiration = {
            "id": "test dream",
            "title": "Test Dream",
            "description": "A test dream",
            "category": "creative",
            "createdAt": "2026-01-01",
        }
        valid, errors = validate_aspiration(aspiration)
        self.assertFalse(valid)
        self.assertTrue(any("kebab-case" in e.lower() or "space" in e.lower() for e in errors))

    def test_all_categories_valid(self):
        """All defined categories should be accepted."""
        for category in ASPIRATION_CATEGORIES:
            aspiration = {
                "id": f"test-{category}",
                "title": f"Test {category}",
                "description": f"A {category} dream",
                "category": category,
                "createdAt": "2026-01-01",
            }
            valid, errors = validate_aspiration(aspiration)
            self.assertTrue(valid, f"Category {category} should be valid: {errors}")


class TestValidateProject(unittest.TestCase):
    """Test project validation."""

    def test_valid_project_all_fields(self):
        """Valid project with all fields should pass."""
        project = {
            "id": "test-project",
            "name": "Test Project",
            "aspirationId": "test-dream",
            "status": "active",
            "category": "tool",
            "description": "A test project",
            "details": "Expanded details",
            "links": {"repo": "https://example.com"},
            "startDate": "2026-01-01",
            "updatedAt": "2026-01-01",
        }
        valid, errors = validate_project(project)
        self.assertTrue(valid)
        self.assertEqual(errors, [])

    def test_valid_project_required_fields_only(self):
        """Valid project with only required fields should pass."""
        project = {
            "id": "test-project",
            "name": "Test Project",
            "aspirationId": "test-dream",
            "status": "idea",
            "category": "creative",
            "description": "A test project",
            "updatedAt": "2026-01-01",
        }
        valid, errors = validate_project(project)
        self.assertTrue(valid)
        self.assertEqual(errors, [])

    def test_missing_required_field(self):
        """Missing required field should fail."""
        project = {
            "id": "test-project",
            "name": "Test Project",
            "aspirationId": "test-dream",
            # Missing status
            "category": "tool",
            "description": "A test project",
            "updatedAt": "2026-01-01",
        }
        valid, errors = validate_project(project)
        self.assertFalse(valid)
        self.assertTrue(any("status" in e.lower() for e in errors))

    def test_invalid_status(self):
        """Invalid status should fail."""
        project = {
            "id": "test-project",
            "name": "Test Project",
            "aspirationId": "test-dream",
            "status": "invalid-status",
            "category": "tool",
            "description": "A test project",
            "updatedAt": "2026-01-01",
        }
        valid, errors = validate_project(project)
        self.assertFalse(valid)
        self.assertTrue(any("status" in e.lower() for e in errors))

    def test_invalid_category(self):
        """Invalid category should fail."""
        project = {
            "id": "test-project",
            "name": "Test Project",
            "aspirationId": "test-dream",
            "status": "active",
            "category": "invalid-category",
            "description": "A test project",
            "updatedAt": "2026-01-01",
        }
        valid, errors = validate_project(project)
        self.assertFalse(valid)
        self.assertTrue(any("category" in e.lower() for e in errors))

    def test_all_statuses_valid(self):
        """All defined statuses should be accepted."""
        for status in PROJECT_STATUSES:
            project = {
                "id": f"test-{status}",
                "name": f"Test {status}",
                "aspirationId": "test-dream",
                "status": status,
                "category": "tool",
                "description": f"A {status} project",
                "updatedAt": "2026-01-01",
            }
            valid, errors = validate_project(project)
            self.assertTrue(valid, f"Status {status} should be valid: {errors}")

    def test_all_project_categories_valid(self):
        """All defined project categories should be accepted."""
        for category in PROJECT_CATEGORIES:
            project = {
                "id": f"test-{category}",
                "name": f"Test {category}",
                "aspirationId": "test-dream",
                "status": "active",
                "category": category,
                "description": f"A {category} project",
                "updatedAt": "2026-01-01",
            }
            valid, errors = validate_project(project)
            self.assertTrue(valid, f"Category {category} should be valid: {errors}")

    def test_invalid_aspiration_id(self):
        """Project with invalid aspirationId should fail when validated."""
        project = {
            "id": "test-project",
            "name": "Test Project",
            "aspirationId": "nonexistent-dream",
            "status": "active",
            "category": "tool",
            "description": "A test project",
            "updatedAt": "2026-01-01",
        }
        valid_aspirations = {"other-dream"}
        valid, errors = validate_project(project, valid_aspirations)
        self.assertFalse(valid)
        self.assertTrue(
            any("aspirationId" in e.lower() or "aspiration" in e.lower() for e in errors)
        )

    def test_valid_aspiration_id(self):
        """Project with valid aspirationId should pass."""
        project = {
            "id": "test-project",
            "name": "Test Project",
            "aspirationId": "valid-dream",
            "status": "active",
            "category": "tool",
            "description": "A test project",
            "updatedAt": "2026-01-01",
        }
        valid_aspirations = {"valid-dream"}
        valid, errors = validate_project(project, valid_aspirations)
        self.assertTrue(valid)
        self.assertEqual(errors, [])


class TestCreateDefaultData(unittest.TestCase):
    """Test default data creation."""

    def test_default_structure(self):
        """Default data should have expected structure."""
        data = create_default_data()
        self.assertIn("version", data)
        self.assertIn("aspirations", data)
        self.assertIn("projects", data)
        self.assertIn("meta", data)

    def test_default_lists_empty(self):
        """Default lists should be empty."""
        data = create_default_data()
        self.assertEqual(data["aspirations"], [])
        self.assertEqual(data["projects"], [])

    def test_default_version(self):
        """Default version should be 1."""
        data = create_default_data()
        self.assertEqual(data["version"], 1)

    def test_default_meta_has_updatedat(self):
        """Default meta should have updatedAt."""
        data = create_default_data()
        self.assertIn("updatedAt", data["meta"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
