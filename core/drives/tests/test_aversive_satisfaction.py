"""Tests for aversive state satisfaction mechanisms (Issue #42).

Tests cover:
- Aversive-specific satisfaction approaches
- Different prompt generation based on valence
- Investigation vs direct satisfaction
- Threshold adjustment recommendations
- Integration with existing satisfaction system
"""

import pytest
from core.drives.satisfaction import calculate_satisfaction_depth, get_aversive_satisfaction_options
from core.drives.spawn import build_session_prompt


class TestAversiveSatisfactionOptions:
    """Test aversive-specific satisfaction option generation."""

    def test_aversive_options_structure(self):
        """Aversive options should have correct structure."""
        opts = get_aversive_satisfaction_options("CREATIVE", 32.0, 20.0, 3)

        assert opts["approach"] == "aversive"
        assert "options" in opts
        assert len(opts["options"]) >= 3
        assert "threshold_adjustment" in opts

    def test_investigate_option_exists(self):
        """Investigation option should be available for aversive drives."""
        opts = get_aversive_satisfaction_options("CREATIVE", 32.0, 20.0, 3)

        investigate = next((o for o in opts["options"] if o["name"] == "investigate"), None)
        assert investigate is not None
        assert investigate["pressure_reduction"] == 0.0
        assert investigate["resets_thwarting"] is False
        assert "blocking" in investigate["prompt"].lower()

    def test_alternative_option_gentle_reduction(self):
        """Alternative approach should have gentler reduction than appetitive."""
        opts = get_aversive_satisfaction_options("CREATIVE", 32.0, 20.0, 3)

        alternative = next((o for o in opts["options"] if o["name"] == "alternative"), None)
        assert alternative is not None
        assert 0.0 < alternative["pressure_reduction"] < 0.5
        assert alternative["resets_thwarting"] is False

    def test_deep_option_resets_thwarting(self):
        """Deep satisfaction should reset thwarting count."""
        opts = get_aversive_satisfaction_options("CREATIVE", 32.0, 20.0, 3)

        deep = next((o for o in opts["options"] if o["name"] == "deep"), None)
        assert deep is not None
        assert deep["pressure_reduction"] > 0.5
        assert deep["resets_thwarting"] is True

    def test_threshold_adjustment_high_thwarting(self):
        """Threshold adjustment recommended when thwarting_count >= 3."""
        opts = get_aversive_satisfaction_options("CREATIVE", 32.0, 20.0, 3)

        assert opts["threshold_adjustment"]["recommended"] is True
        assert "thwarted 3 times" in opts["threshold_adjustment"]["reason"]

    def test_no_threshold_adjustment_low_thwarting(self):
        """No threshold adjustment when thwarting_count < 3."""
        opts = get_aversive_satisfaction_options("CREATIVE", 32.0, 20.0, 2)

        # Should still have the key, but not recommended
        # Or may not have the key at all
        if "threshold_adjustment" in opts:
            assert opts["threshold_adjustment"].get("recommended", False) is False


class TestCalculateSatisfactionDepthValence:
    """Test satisfaction depth calculation with valence awareness."""

    def test_appetitive_normal_reduction(self):
        """Appetitive drives use normal satisfaction ratios."""
        band, depth, ratio = calculate_satisfaction_depth(10.0, 20.0, valence="appetitive")

        assert ratio > 0.0
        assert depth != "auto-investigate"

    def test_aversive_investigation_default(self):
        """Aversive drives default to investigation (no reduction)."""
        band, depth, ratio = calculate_satisfaction_depth(32.0, 20.0, valence="aversive")

        assert ratio == 0.0
        assert depth == "auto-investigate"

    def test_aversive_preserves_band(self):
        """Aversive satisfaction still calculates correct band."""
        band, depth, ratio = calculate_satisfaction_depth(32.0, 20.0, valence="aversive")

        assert band in ["triggered", "crisis", "emergency"]

    def test_neutral_uses_appetitive_logic(self):
        """Neutral valence uses appetitive satisfaction logic."""
        band_app, depth_app, ratio_app = calculate_satisfaction_depth(
            15.0, 20.0, valence="appetitive"
        )
        band_neu, depth_neu, ratio_neu = calculate_satisfaction_depth(15.0, 20.0, valence="neutral")

        assert band_app == band_neu
        assert ratio_app == ratio_neu

    def test_aversive_all_bands(self):
        """Aversive drives use investigation across all pressure bands."""
        # Available
        band, depth, ratio = calculate_satisfaction_depth(8.0, 20.0, valence="aversive")
        assert depth == "auto-investigate"
        assert ratio == 0.0

        # Elevated
        band, depth, ratio = calculate_satisfaction_depth(17.0, 20.0, valence="aversive")
        assert depth == "auto-investigate"
        assert ratio == 0.0

        # Triggered
        band, depth, ratio = calculate_satisfaction_depth(22.0, 20.0, valence="aversive")
        assert depth == "auto-investigate"
        assert ratio == 0.0

        # Crisis
        band, depth, ratio = calculate_satisfaction_depth(35.0, 20.0, valence="aversive")
        assert depth == "auto-investigate"
        assert ratio == 0.0


class TestBuildSessionPromptValence:
    """Test session prompt generation with valence awareness."""

    def test_appetitive_prompt_normal(self):
        """Appetitive drives get normal engagement prompts."""
        config = {"paths": {"workspace": "."}, "memory": {"session_dir": "memory/sessions"}}
        prompt = build_session_prompt(
            "CREATIVE", "Make something new", 25.0, 20.0, config, valence="appetitive"
        )

        assert "Make something new" in prompt
        assert "AVERSIVE STATE" not in prompt
        assert "blockage" not in prompt.lower()

    def test_aversive_prompt_investigation(self):
        """Aversive drives get investigation-focused prompts."""
        config = {"paths": {"workspace": "."}, "memory": {"session_dir": "memory/sessions"}}
        prompt = build_session_prompt(
            "CREATIVE", "Make something new", 32.0, 20.0, config, valence="aversive"
        )

        assert "AVERSIVE STATE" in prompt
        assert "blockage" in prompt.lower() or "blocking" in prompt.lower()
        # Check for investigation-related keywords
        prompt_lower = prompt.lower()
        assert any(
            word in prompt_lower
            for word in ["investigate", "investigation", "reflect", "reflection"]
        )

    def test_aversive_prompt_includes_original(self):
        """Aversive prompts should still reference original drive prompt."""
        config = {"paths": {"workspace": "."}, "memory": {"session_dir": "memory/sessions"}}
        prompt = build_session_prompt(
            "CREATIVE", "Make something new", 32.0, 20.0, config, valence="aversive"
        )

        assert "Make something new" in prompt

    def test_aversive_prompt_has_reflection_points(self):
        """Aversive prompts should guide reflection."""
        config = {"paths": {"workspace": "."}, "memory": {"session_dir": "memory/sessions"}}
        prompt = build_session_prompt(
            "SOCIAL", "Connect with someone", 40.0, 20.0, config, valence="aversive"
        )

        # Check for reflection guidance
        assert "obstacles" in prompt.lower() or "blockage" in prompt.lower()
        assert "alternative" in prompt.lower()

    def test_aversive_prompt_includes_blockage_section(self):
        """Aversive prompts should have dedicated blockage analysis section."""
        config = {"paths": {"workspace": "."}, "memory": {"session_dir": "memory/sessions"}}
        prompt = build_session_prompt(
            "CREATIVE", "Make something new", 32.0, 20.0, config, valence="aversive"
        )

        assert "Blockage Analysis" in prompt
        assert "What prevents satisfaction?" in prompt

    def test_appetitive_no_blockage_section(self):
        """Appetitive prompts should not have blockage section."""
        config = {"paths": {"workspace": "."}, "memory": {"session_dir": "memory/sessions"}}
        prompt = build_session_prompt(
            "CREATIVE", "Make something new", 25.0, 20.0, config, valence="appetitive"
        )

        assert "Blockage Analysis" not in prompt

    def test_neutral_prompt_normal(self):
        """Neutral valence should use normal prompts."""
        config = {"paths": {"workspace": "."}, "memory": {"session_dir": "memory/sessions"}}
        prompt = build_session_prompt(
            "CREATIVE", "Make something new", 5.0, 20.0, config, valence="neutral"
        )

        assert "Make something new" in prompt
        assert "AVERSIVE STATE" not in prompt


class TestAversiveSatisfactionIntegration:
    """Integration tests for aversive satisfaction with engine."""

    def test_aversive_drive_gets_correct_options(self):
        """Full flow: aversive drive → get options → verify structure."""
        # Simulate a drive that's been thwarted
        drive_data = {
            "name": "CREATIVE",
            "pressure": 32.0,
            "threshold": 20.0,
            "valence": "aversive",
            "thwarting_count": 3,
        }

        opts = get_aversive_satisfaction_options(
            drive_data["name"],
            drive_data["pressure"],
            drive_data["threshold"],
            drive_data["thwarting_count"],
        )

        # Should have investigation option as recommended
        assert opts["approach"] == "aversive"
        assert opts["recommended_action"] == "investigate"

        # Should have threshold adjustment suggestion
        assert opts["threshold_adjustment"]["recommended"] is True

    def test_appetitive_to_aversive_transition(self):
        """Satisfaction approach changes when drive becomes aversive."""
        # Start appetitive
        band1, depth1, ratio1 = calculate_satisfaction_depth(15.0, 20.0, valence="appetitive")
        assert ratio1 > 0.0

        # Become aversive
        band2, depth2, ratio2 = calculate_satisfaction_depth(15.0, 20.0, valence="aversive")
        assert ratio2 == 0.0
        assert depth2 == "auto-investigate"

    def test_satisfaction_doesnt_break_existing_behavior(self):
        """Adding valence parameter doesn't break existing calls."""
        # Call without valence (should default to appetitive)
        band, depth, ratio = calculate_satisfaction_depth(15.0, 20.0)

        assert ratio > 0.0
        assert depth != "auto-investigate"


class TestEdgeCases:
    """Edge cases for aversive satisfaction."""

    def test_zero_pressure_aversive(self):
        """Aversive drive with zero pressure (edge case)."""
        opts = get_aversive_satisfaction_options("CREATIVE", 0.0, 20.0, 3)

        assert opts["approach"] == "aversive"
        # Still should offer investigation
        investigate = next((o for o in opts["options"] if o["name"] == "investigate"), None)
        assert investigate is not None

    def test_zero_threshold_aversive(self):
        """Aversive drive with zero threshold (invalid config)."""
        band, depth, ratio = calculate_satisfaction_depth(10.0, 0.0, valence="aversive")

        # Should fallback gracefully
        assert isinstance(ratio, float)

    def test_high_thwarting_count(self):
        """Very high thwarting count (10+)."""
        opts = get_aversive_satisfaction_options("CREATIVE", 32.0, 20.0, 10)

        # Should still work
        assert opts["threshold_adjustment"]["recommended"] is True
        assert "10 times" in opts["threshold_adjustment"]["reason"]

    def test_negative_pressure_aversive(self):
        """Negative pressure (should not happen, but handle gracefully)."""
        band, depth, ratio = calculate_satisfaction_depth(-5.0, 20.0, valence="aversive")

        # Should handle gracefully
        assert isinstance(ratio, float)
        assert ratio >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
