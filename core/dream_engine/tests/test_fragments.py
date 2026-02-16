"""Tests for fragment generation module."""

import unittest
from datetime import datetime, timezone

from core.dream_engine.fragments import (
    get_template_key,
    FragmentGenerator,
    generate_fragment,
    generate_fragments,
    DREAM_TEMPLATES,
    list_templates,
    get_template_count,
)


class TestGetTemplateKey(unittest.TestCase):
    """Tests for get_template_key function."""

    def test_basic_key_generation(self):
        """Should generate key from significant words."""
        template = "A {a} tends a garden where {b} bloom"
        key = get_template_key(template)

        self.assertIsInstance(key, str)
        self.assertGreater(len(key), 0)

    def test_consistent_keys(self):
        """Should generate consistent keys for same template."""
        template = "The {a} remembers {b}"
        key1 = get_template_key(template)
        key2 = get_template_key(template)

        self.assertEqual(key1, key2)


class TestFragmentGenerator(unittest.TestCase):
    """Tests for FragmentGenerator class."""

    def test_basic_generation(self):
        """Should generate fragment with concepts."""
        generator = FragmentGenerator()

        result = generator.generate("neural network", "garden")

        self.assertIn("fragment", result)
        self.assertIn("template", result)
        self.assertIn("concepts", result)
        self.assertEqual(result["concepts"], ["neural network", "garden"])
        self.assertIn("neural network", result["fragment"])
        self.assertIn("garden", result["fragment"])

    def test_fragment_content(self):
        """Should contain both concepts in output."""
        generator = FragmentGenerator()

        result = generator.generate("consciousness", "code")

        fragment = result["fragment"]
        self.assertIn("consciousness", fragment)
        self.assertIn("code", fragment)

    def test_template_tracking(self):
        """Should track used templates."""
        generator = FragmentGenerator()

        # Generate multiple fragments
        for _ in range(5):
            generator.generate("a", "b")

        self.assertEqual(len(generator.used_templates), 5)

    def test_batch_generation(self):
        """Should generate fragments for multiple pairs."""
        generator = FragmentGenerator()

        class MockPair:
            def __init__(self, a, b):
                self.concept_a = a
                self.concept_b = b

        pairs = [MockPair("a", "b"), MockPair("c", "d"), MockPair("e", "f")]
        fragments = generator.generate_batch(pairs)

        self.assertEqual(len(fragments), 3)
        for frag in fragments:
            self.assertIn("fragment", frag)
            self.assertIn("template", frag)

    def test_tuple_pairs(self):
        """Should handle tuple/list pairs."""
        generator = FragmentGenerator()

        pairs = [("a", "b"), ("c", "d")]
        fragments = generator.generate_batch(pairs)

        self.assertEqual(len(fragments), 2)

    def test_reproducibility(self):
        """Should produce reproducible results with same seed."""
        generator1 = FragmentGenerator(seed=42)
        generator2 = FragmentGenerator(seed=42)

        result1 = generator1.generate("a", "b")
        result2 = generator2.generate("a", "b")

        self.assertEqual(result1["fragment"], result2["fragment"])
        self.assertEqual(result1["template"], result2["template"])


class TestGenerateFragment(unittest.TestCase):
    """Tests for generate_fragment convenience function."""

    def test_basic_usage(self):
        """Should generate a single fragment."""
        result = generate_fragment("mind", "machine")

        self.assertIn("fragment", result)
        self.assertIn("template", result)
        self.assertIn("mind", result["fragment"])
        self.assertIn("machine", result["fragment"])

    def test_specific_template(self):
        """Should use provided template."""
        template = "What if {a} could {b}?"
        result = generate_fragment("thoughts", "dream", template=template)

        self.assertEqual(result["fragment"], "What if thoughts could dream?")

    def test_reproducibility(self):
        """Should produce same result with same seed."""
        result1 = generate_fragment("a", "b", seed=42)
        result2 = generate_fragment("a", "b", seed=42)

        self.assertEqual(result1["fragment"], result2["fragment"])


class TestGenerateFragments(unittest.TestCase):
    """Tests for generate_fragments convenience function."""

    def test_basic_usage(self):
        """Should generate fragments for pairs."""

        class MockPair:
            def __init__(self, a, b):
                self.concept_a = a
                self.concept_b = b

        pairs = [MockPair("x", "y"), MockPair("z", "w")]
        fragments = generate_fragments(pairs)

        self.assertEqual(len(fragments), 2)

    def test_date_based_seed(self):
        """Should use date for seed."""

        class MockPair:
            def __init__(self, a, b):
                self.concept_a = a
                self.concept_b = b

        pairs = [MockPair("a", "b")]
        date = datetime(2026, 2, 7, tzinfo=timezone.utc)

        fragments1 = generate_fragments(pairs, reference_date=date)
        fragments2 = generate_fragments(pairs, reference_date=date)

        self.assertEqual(fragments1[0]["fragment"], fragments2[0]["fragment"])


class TestDreamTemplates(unittest.TestCase):
    """Tests for dream templates."""

    def test_templates_exist(self):
        """Should have templates defined."""
        self.assertGreater(len(DREAM_TEMPLATES), 0)

    def test_minimum_template_count(self):
        """Should have at least 15 templates as specified."""
        self.assertGreaterEqual(len(DREAM_TEMPLATES), 15)

    def test_templates_have_placeholders(self):
        """All templates should have {a} and {b} placeholders."""
        for template in DREAM_TEMPLATES:
            self.assertIn("{a}", template)
            self.assertIn("{b}", template)

    def test_list_templates(self):
        """Should list all template keys."""
        keys = list_templates()
        self.assertEqual(len(keys), len(DREAM_TEMPLATES))

    def test_get_template_count(self):
        """Should return correct count."""
        count = get_template_count()
        self.assertEqual(count, len(DREAM_TEMPLATES))


if __name__ == "__main__":
    unittest.main()
