"""Tests for the 3-phase log pipeline."""

import pytest
from unittest.mock import AsyncMock, patch

from src.log_pipeline import (
    LogPipeline,
    PipelineResult,
    RubricScore,
    _parse_scores,
    RUBRIC_ELEMENTS,
)


# ── Score Parsing ─────────────────────────────────────────────────

class TestParseScores:
    def test_full_scores(self):
        text = "Surplus Insight: 7\nCausal Chain: 8\nHonesty: 6\nActionable Signal: 7\nCompression: 5\nHuman Compatibility: 6\nPrecedent Value: 8\nAverage: 6.7"
        score = _parse_scores(text)
        assert score is not None
        assert score.average == 6.7
        assert score.scores["Surplus Insight"] == 7

    def test_partial_scores(self):
        text = "Surplus Insight: 9\nCausal Chain: 8\nHonesty: 7\nPrecedent Value: 8\nAverage: 8.0"
        score = _parse_scores(text)
        assert score is not None
        assert score.scores["Surplus Insight"] == 9
        assert score.scores["Honesty"] == 7
        # Missing elements default to 5
        assert score.scores["Compression"] == 5

    def test_no_scores(self):
        text = "The log is about a bug."
        score = _parse_scores(text)
        assert score is None

    def test_fails_quality_gate(self):
        scores = {e: 2 for e in RUBRIC_ELEMENTS}
        score = RubricScore(scores=scores, average=2.0)
        assert not score.passes()

    def test_one_element_below_3(self):
        scores = {e: 8 for e in RUBRIC_ELEMENTS}
        scores["Honesty"] = 2
        avg = sum(scores.values()) / len(scores)
        score = RubricScore(scores=scores, average=avg)
        assert not score.passes()

    def test_passes_quality_gate(self):
        scores = {e: 7 for e in RUBRIC_ELEMENTS}
        score = RubricScore(scores=scores, average=7.0)
        assert score.passes()


# ── Pipeline Phases ───────────────────────────────────────────────

class TestLogPipeline:
    @pytest.fixture
    def pipeline(self):
        return LogPipeline(api_key="test-key")

    @pytest.mark.asyncio
    async def test_phase1_null(self, pipeline):
        """Phase 1 returns NULL when nothing happened."""
        with patch("src.log_pipeline._call_model", new_callable=AsyncMock) as mock:
            mock.return_value = "NULL"
            result = await pipeline.phase1_raw_dump(
                "nothing happened", "JC1", "hardware/edge", "00:00", "01:00"
            )
            assert result == "NULL"

    @pytest.mark.asyncio
    async def test_phase1_content(self, pipeline):
        """Phase 1 returns content when something happened."""
        with patch("src.log_pipeline._call_model", new_callable=AsyncMock) as mock:
            mock.return_value = "At 14:23 detected anomaly in register 0x4000"
            result = await pipeline.phase1_raw_dump(
                "anomaly detected", "JC1", "hardware/edge", "14:00", "15:00"
            )
            assert "0x4000" in result

    @pytest.mark.asyncio
    async def test_phase2_skip(self, pipeline):
        """Phase 2 returns SKIP for low-quality dumps."""
        with patch("src.log_pipeline._call_model", new_callable=AsyncMock) as mock:
            mock.return_value = "SKIP"
            result, score = await pipeline.phase2_reasoner(
                "All systems nominal. Nothing happened.", "JC1", "hardware/edge"
            )
            assert result == "SKIP"
            assert score is None

    @pytest.mark.asyncio
    async def test_phase2_pass(self, pipeline):
        """Phase 2 returns signal for high-quality dumps."""
        phase2_response = (
            "Surplus Insight: 8\nCausal Chain: 9\nHonesty: 7\n"
            "Actionable Signal: 8\nCompression: 7\nHuman Compatibility: 8\n"
            "Precedent Value: 9\nAverage: 8.0\n\n"
            "SIGNAL:\n- Discovered ISA v1/v2 opcode divergence at 0x4B\n"
            "- [UNCERTAIN] affects all v2 hardware\n"
            "- [DEVIATION] spent 47 minutes before reporting"
        )
        with patch("src.log_pipeline._call_model", new_callable=AsyncMock) as mock:
            mock.return_value = phase2_response
            result, score = await pipeline.phase2_reasoner(
                "Found opcode mismatch", "JC1", "hardware/edge"
            )
            assert result != "SKIP"
            assert score is not None
            assert score.passes()

    @pytest.mark.asyncio
    async def test_full_pipeline_skip_on_null(self, pipeline):
        """Full pipeline returns skip when Phase 1 returns NULL."""
        with patch("src.log_pipeline._call_model", new_callable=AsyncMock) as mock:
            mock.return_value = "NULL"
            result = await pipeline.run(
                "nothing", "JC1", "hardware/edge", "00:00", "01:00"
            )
            assert result.status == "skip"
            assert result.phase1_output == "NULL"

    @pytest.mark.asyncio
    async def test_full_pipeline_skip_on_phase2(self, pipeline):
        """Full pipeline returns skip when Phase 2 returns SKIP."""
        with patch("src.log_pipeline._call_model", new_callable=AsyncMock) as mock:
            mock.side_effect = [
                "Some stuff happened",  # Phase 1
                "SKIP",                # Phase 2
            ]
            result = await pipeline.run(
                "minor stuff", "JC1", "hardware/edge", "00:00", "01:00"
            )
            assert result.status == "skip"
            assert result.phase2_output == "SKIP"

    @pytest.mark.asyncio
    async def test_full_pipeline_published(self, pipeline):
        """Full pipeline returns published when all phases pass."""
        phase2_response = (
            "Surplus Insight: 8\nCausal Chain: 8\nHonesty: 7\n"
            "Actionable Signal: 8\nCompression: 7\nHuman Compatibility: 8\n"
            "Precedent Value: 9\nAverage: 7.9\n\n"
            "SIGNAL:\n- Critical finding about ISA divergence"
        )
        phase3_response = "# Captain's Log\n\nISA v1 and v2 have different opcodes..."

        with patch("src.log_pipeline._call_model", new_callable=AsyncMock) as mock:
            mock.side_effect = [
                "Found critical ISA bug",  # Phase 1
                phase2_response,            # Phase 2
                phase3_response,            # Phase 3
            ]
            result = await pipeline.run(
                "ISA bug", "JC1", "hardware/edge", "14:00", "15:00"
            )
            assert result.status == "published"
            assert result.phase3_output is not None

    @pytest.mark.asyncio
    async def test_full_pipeline_error_handling(self, pipeline):
        """Full pipeline returns error on API failure."""
        with patch("src.log_pipeline._call_model", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("API timeout")
            result = await pipeline.run(
                "something", "JC1", "hardware/edge", "00:00", "01:00"
            )
            assert result.status == "error"
            assert "timeout" in result.error.lower()
