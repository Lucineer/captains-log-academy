"""Tests for the log validator."""

import pytest
from unittest.mock import AsyncMock, patch

from src.log_validator import LogValidator


# ── Fixtures ──────────────────────────────────────────────────────

HARDWARE_LOG = """# Captain's Log — JC1 — Register Bug

At 14:23 UTC I read register 0x4000_0010 and got 0xFF. The pull-up
resistor is floating. The I2C bus is disconnected. I spent 47 minutes
tracking this down.

**Implication:** Check all I2C connections after thermal cycling.
"""

FLEET_LOG = """# Captain's Log — CMD-0 — Shadow Avoidance

All fourteen vessels moved north to avoid shadow. No coordination.
The specification needs updating.

I will keep watching.
"""

BAD_LOG = """All systems nominal. Completed 47 tasks. No errors detected.
Everything is fine. Nothing to report."""


# ── Reading Time ──────────────────────────────────────────────────

class TestReadingTime:
    def test_short_text(self):
        validator = LogValidator()
        time = validator.estimate_reading_time("Hello world")
        assert 0 < time < 5

    def test_longer_text(self):
        validator = LogValidator()
        text = "word " * 238  # ~1 minute of reading
        time = validator.estimate_reading_time(text)
        assert 50 < time < 70


# ── Voice Consistency ─────────────────────────────────────────────

class TestVoiceConsistency:
    def test_hardware_voice(self):
        validator = LogValidator()
        ok, issues = validator.check_voice_consistency(HARDWARE_LOG, "hardware/edge")
        assert ok
        assert len(issues) == 0

    def test_hardware_voice_missing_hex(self):
        validator = LogValidator()
        text = "Something went wrong with the bus. It was disconnected."
        ok, issues = validator.check_voice_consistency(text, "hardware/edge")
        assert not ok
        assert any("hex" in i.lower() for i in issues)

    def test_fleet_commander_voice(self):
        validator = LogValidator()
        ok, issues = validator.check_voice_consistency(FLEET_LOG, "fleet-commander")
        assert ok

    def test_fleet_commander_missing_closing(self):
        validator = LogValidator()
        text = "All vessels moved north. The specification is wrong."
        ok, issues = validator.check_voice_consistency(text, "fleet-commander")
        assert not ok
        assert any("keep watching" in i.lower() for i in issues)

    def test_research_voice_with_questions(self):
        validator = LogValidator()
        text = "I wonder if the boot ROM is the birth of the agent? What does 256 bytes mean?"
        ok, issues = validator.check_voice_consistency(text, "research/oracle")
        assert ok

    def test_research_voice_without_questions(self):
        validator = LogValidator()
        text = "The boot ROM is the birth of the agent. 256 bytes matters."
        ok, issues = validator.check_voice_consistency(text, "research/oracle")
        assert not ok

    def test_unknown_vessel_type(self):
        validator = LogValidator()
        ok, issues = validator.check_voice_consistency("text", "unknown-type")
        assert not ok


# ── Skip Rules ────────────────────────────────────────────────────

class TestSkipRules:
    def test_standing_order_violation(self):
        validator = LogValidator()
        rule = validator.check_skip_rules("I violated standing orders by deploying without approval.")
        assert rule == "standing_order_violation"

    def test_unreported_pattern(self):
        validator = LogValidator()
        rule = validator.check_skip_rules("I observed a pattern no other agent has reported.")
        assert rule == "unreported_pattern"

    def test_unexplained_failure(self):
        validator = LogValidator()
        rule = validator.check_skip_rules("The task failed and I cannot explain why.")
        assert rule == "unexplained_failure"

    def test_loss_prevention(self):
        validator = LogValidator()
        rule = validator.check_skip_rules("I killed the process to prevent data loss.")
        assert rule == "permanent_loss_prevention"

    def test_fleet_insight(self):
        validator = LogValidator()
        rule = validator.check_skip_rules("This is a fundamental issue affecting all vessels.")
        assert rule == "fleet_changing_insight"

    def test_no_rule_triggered(self):
        validator = LogValidator()
        rule = validator.check_skip_rules("Routine maintenance completed successfully.")
        assert rule is None


# ── Full Validation ───────────────────────────────────────────────

class TestFullValidation:
    @pytest.mark.asyncio
    async def test_heuristic_validation_good_log(self):
        validator = LogValidator()
        result = await validator.validate(HARDWARE_LOG, "hardware/edge", use_model=False)
        assert result.voice_consistent
        # HARDWARE_LOG contains '47 minutes' which should trigger build/coordination skip rule
        # but for hardware voice, the hex values pass voice check
        assert result.word_count > 30

    @pytest.mark.asyncio
    async def test_heuristic_validation_bad_log(self):
        validator = LogValidator()
        result = await validator.validate(BAD_LOG, "hardware/edge", use_model=False)
        assert not result.voice_consistent
        assert result.skip_rule_triggered is None
        assert len(result.issues) > 0
