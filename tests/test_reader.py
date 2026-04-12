"""Tests for the log reader (Casey's interface)."""

import os
import tempfile
from datetime import date

import pytest
from src.log_reader import LogReader, parse_log_file, reading_time_minutes


SAMPLE_LOG = """---
vessel: JC1
type: hardware/edge
score: 8.5
rubric:
  surplus_insight: 8
  causal_chain: 9
  honesty: 7
  actionable_signal: 8
  compression: 8
  human_compatibility: 9
  precedent_value: 9
---

# Captain's Log — JC1 — Register Discovery

At 14:23 UTC I read register 0x4000_0010 and got 0xFF when I expected 0x07.
The pull-up resistor is floating. I spent 47 minutes tracking this down.

**Implication:** Add I2C bus integrity check to the pre-flight checklist.
"""

SAMPLE_LOG_LOW_SCORE = """---
vessel: BLD-7
type: build/coordination
score: 4.2
rubric:
  surplus_insight: 3
  causal_chain: 5
  honesty: 4
  actionable_signal: 3
  compression: 5
  human_compatibility: 5
  precedent_value: 4
---

# Captain's Log — BLD-7 — Routine Build

All builds completed. No errors. Everything is nominal.
"""


class TestParseLogFile:
    def test_parse_valid_log(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "JC1.001.md")
            with open(p, 'w') as f:
                f.write(SAMPLE_LOG)
            entry = parse_log_file(p)

        assert entry is not None
        assert entry.vessel_id == "JC1"
        assert entry.vessel_type == "hardware/edge"
        assert entry.score == 8.5
        assert "Register Discovery" in entry.title

    def test_parse_no_frontmatter(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Just a heading\n\nSome text.")
            f.flush()
            entry = parse_log_file(f.name)
            os.unlink(f.name)

        assert entry is None


class TestReadingTime:
    def test_estimate(self):
        text = "word " * 238  # 1 minute
        rt = reading_time_minutes(text)
        assert 0.9 < rt < 1.1


class TestLogReader:
    @pytest.fixture
    def reader(self, tmp_path):
        # Create test log directory structure
        date_dir = tmp_path / "2026-04-12"
        date_dir.mkdir()

        (date_dir / "JC1.001.md").write_text(SAMPLE_LOG)
        (date_dir / "BLD-7.001.md").write_text(SAMPLE_LOG_LOW_SCORE)

        return LogReader(logs_dir=str(tmp_path))

    def test_get_all_logs(self, reader):
        logs = reader.get_logs()
        assert len(logs) == 2

    def test_get_logs_by_date(self, reader):
        logs = reader.get_logs(target_date=date(2026, 4, 12))
        assert len(logs) == 2

    def test_get_logs_by_vessel(self, reader):
        logs = reader.get_logs(vessel_id="JC1")
        assert len(logs) == 1
        assert logs[0].vessel_id == "JC1"

    def test_get_logs_by_score(self, reader):
        logs = reader.get_logs(min_score=7.0)
        assert len(logs) == 1
        assert logs[0].score >= 7.0

    def test_get_logs_by_type(self, reader):
        logs = reader.get_logs(vessel_type="hardware/edge")
        assert len(logs) == 1

    def test_digest_generation(self, reader):
        digest = reader.generate_digest(target_date=date(2026, 4, 12), min_score=7.0)
        assert "JC1" in digest
        assert "BLD-7" not in digest  # Score too low
        assert "Captain's Digest" in digest

    def test_digest_empty(self, reader):
        digest = reader.generate_digest(target_date=date(2025, 1, 1), min_score=7.0)
        assert "No logs met the quality threshold" in digest

    def test_format_log(self, reader):
        logs = reader.get_logs(vessel_id="JC1")
        formatted = reader.format_log(logs[0])
        assert "JC1" in formatted
        assert "hardware/edge" in formatted
        assert "8.5" in formatted
        assert "Register Discovery" in formatted
