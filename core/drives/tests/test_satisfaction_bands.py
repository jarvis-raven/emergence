"""Tests for band-based satisfaction depth calculation.

Tests implementation of issue #38: satisfaction depth based on threshold bands.
"""

import pytest
import sys
import os
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.drives.satisfaction import calculate_satisfaction_depth
from core.drives.models import get_drive_thresholds, get_threshold_label


class TestCalculateSatisfactionDepth:
    """Test calculate_satisfaction_depth with threshold bands."""
    
    def test_below_available_band(self):
        """Below available threshold (< 30%) is still 'available' band but gets minimal satisfaction."""
        band, depth, ratio = calculate_satisfaction_depth(5.0, 20.0)
        assert band == "available"
        assert depth == "auto-shallow"
        assert ratio == 0.25
    
    def test_available_band(self):
        """Available band (30-75%) should give 25% reduction."""
        # 50% pressure
        band, depth, ratio = calculate_satisfaction_depth(10.0, 20.0)
        assert band == "available"
        assert depth == "auto-shallow"
        assert ratio == 0.25
        
        # 60% pressure
        band, depth, ratio = calculate_satisfaction_depth(12.0, 20.0)
        assert band == "available"
        assert depth == "auto-shallow"
        assert ratio == 0.25
    
    def test_elevated_band(self):
        """Elevated band (75-100%) should give 50% reduction."""
        # 80% pressure
        band, depth, ratio = calculate_satisfaction_depth(16.0, 20.0)
        assert band == "elevated"
        assert depth == "auto-moderate"
        assert ratio == 0.50
        
        # 95% pressure
        band, depth, ratio = calculate_satisfaction_depth(19.0, 20.0)
        assert band == "elevated"
        assert depth == "auto-moderate"
        assert ratio == 0.50
    
    def test_triggered_band(self):
        """Triggered band (100-150%) should give 75% reduction."""
        # 100% pressure (exactly at threshold)
        band, depth, ratio = calculate_satisfaction_depth(20.0, 20.0)
        assert band == "triggered"
        assert depth == "auto-deep"
        assert ratio == 0.75
        
        # 120% pressure
        band, depth, ratio = calculate_satisfaction_depth(24.0, 20.0)
        assert band == "triggered"
        assert depth == "auto-deep"
        assert ratio == 0.75
    
    def test_crisis_band(self):
        """Crisis band (150-200%) should give 90% reduction."""
        # 160% pressure (crisis band)
        band, depth, ratio = calculate_satisfaction_depth(32.0, 20.0)
        assert band == "crisis"
        assert depth == "auto-full"
        assert ratio == 0.90
        
        # 180% pressure (crisis band)
        band, depth, ratio = calculate_satisfaction_depth(36.0, 20.0)
        assert band == "crisis"
        assert depth == "auto-full"
        assert ratio == 0.90
    
    def test_emergency_band(self):
        """Emergency band (200%+) should give 90% reduction."""
        # 220% pressure
        band, depth, ratio = calculate_satisfaction_depth(44.0, 20.0)
        assert band == "emergency"
        assert depth == "auto-full"
        assert ratio == 0.90
    
    def test_with_custom_thresholds(self):
        """Should work with custom thresholds dict."""
        custom_thresholds = {
            "available": 10.0,
            "elevated": 20.0,
            "triggered": 30.0,
            "crisis": 45.0,
            "emergency": 60.0,
        }
        
        # 35 pressure with 30 threshold -> triggered band with custom thresholds
        band, depth, ratio = calculate_satisfaction_depth(35.0, 30.0, custom_thresholds)
        assert band == "triggered"
        assert depth == "auto-deep"
        assert ratio == 0.75
    
    def test_zero_threshold_fallback(self):
        """Zero threshold should return fallback values."""
        band, depth, ratio = calculate_satisfaction_depth(10.0, 0.0)
        assert band == "unknown"
        assert depth == "auto-moderate"
        assert ratio == 0.50


class TestThresholdBandTransitions:
    """Test transitions between threshold bands."""
    
    def test_band_boundaries(self):
        """Verify exact boundary conditions."""
        threshold = 20.0
        drive = {"threshold": threshold}
        thresholds = get_drive_thresholds(drive)
        
        # Just below available (29.9%)
        assert get_threshold_label(5.98, thresholds) == "available"
        
        # At available boundary (30%)
        assert get_threshold_label(6.0, thresholds) == "available"
        
        # Just below elevated (74.9%)
        assert get_threshold_label(14.98, thresholds) == "available"
        
        # At elevated boundary (75%)
        assert get_threshold_label(15.0, thresholds) == "elevated"
        
        # Just below triggered (99.9%)
        assert get_threshold_label(19.98, thresholds) == "elevated"
        
        # At triggered boundary (100%)
        assert get_threshold_label(20.0, thresholds) == "triggered"
        
        # Just below crisis (149.9%)
        assert get_threshold_label(29.98, thresholds) == "triggered"
        
        # At crisis boundary (150%)
        assert get_threshold_label(30.0, thresholds) == "crisis"
        
        # At emergency boundary (200%)
        assert get_threshold_label(40.0, thresholds) == "emergency"
    
    def test_band_progression(self):
        """Test that bands progress correctly as pressure increases."""
        threshold = 20.0
        
        pressures = [0, 5, 10, 15, 20, 25, 30, 40]
        expected_bands = [
            "available",   # 0% - below available threshold but still "available" band
            "available",   # 25% - below available threshold
            "available",   # 50% - in available range (30-75%)
            "elevated",    # 75% - at elevated boundary
            "triggered",   # 100% - triggered
            "triggered",   # 125% - triggered (100-150%)
            "crisis",      # 150% - crisis
            "emergency"    # 200% - emergency
        ]
        
        for pressure, expected_band in zip(pressures, expected_bands):
            band, _, _ = calculate_satisfaction_depth(pressure, threshold)
            assert band == expected_band, f"Pressure {pressure} should be in {expected_band}, got {band}"


class TestSatisfactionHistory:
    """Test satisfaction history tracking."""
    
    def test_log_satisfaction(self):
        """Should log satisfaction events to history file."""
        from core.drives.satisfaction import log_satisfaction, get_recent_satisfaction_history, get_history_path
        
        # Clean up history file
        history_path = get_history_path()
        if history_path.exists():
            history_path.unlink()
        
        # Log a satisfaction event
        log_satisfaction(
            drive_name="TEST_DRIVE",
            pressure_before=20.0,
            pressure_after=5.0,
            band="triggered",
            depth="auto-deep",
            ratio=0.75,
            source="test"
        )
        
        # Verify it was logged
        history = get_recent_satisfaction_history(drive_name="TEST_DRIVE", limit=1)
        assert len(history) == 1
        
        event = history[0]
        assert event["drive"] == "TEST_DRIVE"
        assert event["pressure_before"] == 20.0
        assert event["pressure_after"] == 5.0
        assert event["band"] == "triggered"
        assert event["depth"] == "auto-deep"
        assert event["ratio"] == 0.75
        assert event["source"] == "test"
        assert "timestamp" in event
        
        # Clean up
        if history_path.exists():
            history_path.unlink()
    
    def test_get_recent_history_filtered(self):
        """Should filter history by drive name."""
        from core.drives.satisfaction import log_satisfaction, get_recent_satisfaction_history, get_history_path
        
        # Clean up history file
        history_path = get_history_path()
        if history_path.exists():
            history_path.unlink()
        
        # Log events for different drives
        log_satisfaction("DRIVE_A", 10.0, 5.0, "available", "auto-shallow", 0.25, "test")
        log_satisfaction("DRIVE_B", 20.0, 10.0, "triggered", "auto-deep", 0.75, "test")
        log_satisfaction("DRIVE_A", 15.0, 7.5, "elevated", "auto-moderate", 0.50, "test")
        
        # Filter by drive name
        history_a = get_recent_satisfaction_history(drive_name="DRIVE_A")
        assert len(history_a) == 2
        assert all(e["drive"] == "DRIVE_A" for e in history_a)
        
        history_b = get_recent_satisfaction_history(drive_name="DRIVE_B")
        assert len(history_b) == 1
        assert history_b[0]["drive"] == "DRIVE_B"
        
        # Get all history
        all_history = get_recent_satisfaction_history()
        assert len(all_history) == 3
        
        # Clean up
        if history_path.exists():
            history_path.unlink()
    
    def test_history_limit(self):
        """Should respect limit parameter."""
        from core.drives.satisfaction import log_satisfaction, get_recent_satisfaction_history, get_history_path
        
        # Clean up history file
        history_path = get_history_path()
        if history_path.exists():
            history_path.unlink()
        
        # Log 10 events
        for i in range(10):
            log_satisfaction(f"DRIVE_{i % 3}", 10.0, 5.0, "available", "auto-shallow", 0.25, "test")
        
        # Request only 5 most recent
        history = get_recent_satisfaction_history(limit=5)
        assert len(history) == 5
        
        # Clean up
        if history_path.exists():
            history_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
