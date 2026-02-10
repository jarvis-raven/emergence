"""Tests for main dream module and CLI."""

import unittest
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from core.dream_engine.dream import (
    generate_dreams,
    save_dreams,
    run_dream_generation,
    get_status,
    parse_date,
)
from core.dream_engine.config import load_config


class TestParseDate(unittest.TestCase):
    """Tests for parse_date function."""
    
    def test_valid_date(self):
        """Should parse valid date string."""
        result = parse_date("2026-02-07")
        
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 7)
    
    def test_invalid_date(self):
        """Should return None for invalid date."""
        result = parse_date("not-a-date")
        self.assertIsNone(result)
        
        result = parse_date("2026-13-45")  # Invalid month/day
        self.assertIsNone(result)
        
        result = parse_date("")
        self.assertIsNone(result)


class TestGenerateDreams(unittest.TestCase):
    """Tests for generate_dreams function."""
    
    def setUp(self):
        """Create temporary directory with test files."""
        self.temp_dir = TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        
        # Create memory directory
        self.memory_dir = self.base_path / "memory"
        self.memory_dir.mkdir()
        
        # Create test memory file
        test_file = self.memory_dir / "2026-02-07.md"
        test_file.write_text("""---
drive: CURIOSITY
timestamp: 2026-02-07T10:00:00Z
---

## Session — Machine Learning

Deep learning neural networks are fascinating. Machine learning algorithms
process data efficiently. Neural networks learn patterns automatically.

## Another Section

Creative coding projects involve interesting concepts. Digital art and
interactive installations explore new possibilities.
""")
        
        # Another test file for cross-source pairing
        test_file2 = self.memory_dir / "2026-02-06.md"
        test_file2.write_text("""
## Garden Session

Beautiful garden with flowers blooming. Nature and plants create peaceful
environments. Garden design requires careful planning.
""")
    
    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()
    
    def test_basic_generation(self):
        """Should generate dreams with correct structure."""
        config = {
            'paths': {'workspace': str(self.base_path)},
            'memory': {
                'daily_dir': 'memory',
                'dream_dir': 'memory/dreams'
            },
            'dream_engine': {
                'lookback_days': 7,
                'concepts_per_run': 50,
                'pairs_to_generate': 4,
            }
        }
        
        reference_date = datetime(2026, 2, 7, tzinfo=timezone.utc)
        
        result = generate_dreams(config, reference_date, verbose=False)
        
        # Check structure
        self.assertEqual(result['date'], '2026-02-07')
        self.assertIn('generated_at', result)
        self.assertIn('source_files', result)
        self.assertIn('source_concepts', result)
        self.assertIn('dreams', result)
        
        # Should have some dreams (may be fewer than requested if not enough concepts)
        self.assertIsInstance(result['dreams'], list)
    
    def test_dream_structure(self):
        """Generated dreams should have correct structure."""
        config = {
            'paths': {'workspace': str(self.base_path)},
            'memory': {
                'daily_dir': 'memory',
                'dream_dir': 'memory/dreams'
            },
            'dream_engine': {
                'lookback_days': 7,
                'concepts_per_run': 50,
                'pairs_to_generate': 2,
            }
        }
        
        reference_date = datetime(2026, 2, 7, tzinfo=timezone.utc)
        result = generate_dreams(config, reference_date)
        
        if result['dreams']:
            dream = result['dreams'][0]
            
            # Check required fields
            self.assertIn('concepts', dream)
            self.assertIn('fragment', dream)
            self.assertIn('insight_score', dream)
            self.assertIn('sources', dream)
            self.assertIn('template', dream)
            
            # Check types
            self.assertIsInstance(dream['concepts'], list)
            self.assertEqual(len(dream['concepts']), 2)
            self.assertIsInstance(dream['insight_score'], int)
            self.assertGreaterEqual(dream['insight_score'], 0)
            self.assertLessEqual(dream['insight_score'], 100)
    
    def test_no_memory_files(self):
        """Should handle missing memory files gracefully."""
        empty_dir = self.base_path / "empty"
        empty_dir.mkdir()
        
        config = {
            'paths': {'workspace': str(self.base_path)},
            'memory': {
                'daily_dir': 'empty',
                'dream_dir': 'memory/dreams'
            },
            'dream_engine': {
                'lookback_days': 7,
                'concepts_per_run': 50,
                'pairs_to_generate': 4,
            }
        }
        
        result = generate_dreams(config, verbose=False)
        
        # Should return empty dreams with error info
        self.assertIn('dreams', result)
        self.assertEqual(len(result['dreams']), 0)
        self.assertIn('error', result)


class TestSaveDreams(unittest.TestCase):
    """Tests for save_dreams function."""
    
    def setUp(self):
        """Create temporary directory."""
        self.temp_dir = TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()
    
    def test_save_creates_file(self):
        """Should save dreams to JSON file."""
        dream_dir = self.base_path / "dreams"
        
        config = {
            'paths': {'workspace': str(self.base_path)},
            'memory': {'dream_dir': 'dreams'}
        }
        
        dreams_data = {
            'date': '2026-02-07',
            'generated_at': '2026-02-07T04:00:00Z',
            'source_files': 2,
            'source_concepts': 10,
            'dreams': [
                {
                    'concepts': ['a', 'b'],
                    'fragment': 'Test dream',
                    'insight_score': 50,
                    'sources': ['file1.md'],
                    'template': 'test'
                }
            ]
        }
        
        success = save_dreams(dreams_data, config, dry_run=False, verbose=False)
        
        self.assertTrue(success)
        
        # Check file was created
        output_file = dream_dir / '2026-02-07.json'
        self.assertTrue(output_file.exists())
        
        # Check content
        with open(output_file) as f:
            saved = json.load(f)
        
        self.assertEqual(saved['date'], '2026-02-07')
        self.assertEqual(len(saved['dreams']), 1)
    
    def test_dry_run(self):
        """Should not write file in dry-run mode."""
        config = {
            'paths': {'workspace': str(self.base_path)},
            'memory': {'dream_dir': 'dreams'}
        }
        
        dreams_data = {
            'date': '2026-02-07',
            'generated_at': '2026-02-07T04:00:00Z',
            'source_files': 0,
            'source_concepts': 0,
            'dreams': []
        }
        
        success = save_dreams(dreams_data, config, dry_run=True, verbose=False)
        
        self.assertTrue(success)
        
        # Check file was NOT created
        output_file = self.base_path / "dreams" / "2026-02-07.json"
        self.assertFalse(output_file.exists())


class TestGetStatus(unittest.TestCase):
    """Tests for get_status function."""
    
    def setUp(self):
        """Create temporary directory."""
        self.temp_dir = TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        
        # Create directories
        (self.base_path / "memory").mkdir()
        (self.base_path / "memory" / "dreams").mkdir()
        
        # Create test files
        (self.base_path / "memory" / "2026-02-07.md").write_text("test")
        (self.base_path / "memory" / "dreams" / "2026-02-06.json").write_text("{}")
    
    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()
    
    def test_status_structure(self):
        """Should return status dictionary."""
        config = {
            'paths': {'workspace': str(self.base_path)},
            'memory': {
                'daily_dir': 'memory',
                'dream_dir': 'memory/dreams'
            },
            'dream_engine': {
                'lookback_days': 7,
                'concepts_per_run': 50,
                'pairs_to_generate': 4,
            }
        }
        
        status = get_status(config)
        
        self.assertIn('memory_dir', status)
        self.assertIn('dream_dir', status)
        self.assertIn('recent_memory_files', status)
        self.assertIn('existing_dreams', status)
        self.assertIn('config', status)


class TestRunDreamGeneration(unittest.TestCase):
    """Tests for run_dream_generation function."""
    
    def setUp(self):
        """Create temporary directory with test files."""
        self.temp_dir = TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        
        # Create memory directory with content
        self.memory_dir = self.base_path / "memory"
        self.memory_dir.mkdir()
        
        test_file = self.memory_dir / "2026-02-07.md"
        test_file.write_text("""
Deep learning neural networks machine learning fascinating concepts.
Digital art creative coding interactive installations exploring.
""")
    
    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()
    
    def test_full_generation(self):
        """Should run complete generation process."""
        config = {
            'paths': {'workspace': str(self.base_path)},
            'memory': {
                'daily_dir': 'memory',
                'dream_dir': 'memory/dreams'
            },
            'dream_engine': {
                'lookback_days': 7,
                'concepts_per_run': 50,
                'pairs_to_generate': 2,
            }
        }
        
        reference_date = datetime(2026, 2, 7, tzinfo=timezone.utc)
        
        success, dreams_data = run_dream_generation(
            config=config,
            reference_date=reference_date,
            dry_run=True,
            verbose=False
        )
        
        # Should succeed (even if no dreams generated due to test data)
        self.assertTrue(success)
        self.assertIn('date', dreams_data)
        self.assertIn('dreams', dreams_data)


if __name__ == '__main__':
    unittest.main()
