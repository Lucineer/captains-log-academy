#!/usr/bin/env python3
"""
Captain's Log Academy — Log Validator

Validates logs against the 7-element rubric, skip rules, voice consistency,
and reading time estimates. Enforces quality gates.
"""

import re
from dataclasses import dataclass
from typing import Optional

import httpx

from .log_pipeline import (
    DEEPINFRA_BASE,
    MODEL_PHASE2,
    RUBRIC_ELEMENTS,
    RUBRIC_SPEC,
    RubricScore,
    _parse_scores,
    VOICE_GUIDE,
)


# ── Skip Rules ────────────────────────────────────────────────────

SKIP_RULES = [
    "standing_order_violation",
    "unreported_pattern",
    "unexplained_failure",
    "permanent_loss_prevention",
    "fleet_changing_insight",
]


@dataclass
class ValidationResult:
    """Result of validating a log."""
    rubric_score: Optional[RubricScore]
    passes_quality_gate: bool
    skip_rule_triggered: Optional[str]
    voice_consistent: bool
    reading_time_seconds: float
    word_count: int
    issues: list[str]


class LogValidator:
    """Validates captain's logs for quality, skip rules, and voice."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def estimate_reading_time(self, text: str) -> float:
        """Estimate reading time in seconds (average human reads ~238 words/min)."""
        words = len(text.split())
        return (words / 238.0) * 60.0

    def check_voice_consistency(self, text: str, vessel_type: str) -> tuple[bool, list[str]]:
        """Check if the log's voice matches the expected vessel type."""
        issues = []
        voice_desc = VOICE_GUIDE.get(vessel_type, "")

        if not voice_desc:
            issues.append(f"Unknown vessel type: {vessel_type}")
            return False, issues

        # Heuristic checks based on voice characteristics
        if vessel_type == "debug/analysis":
            # Should use short sentences and fragments
            sentences = re.split(r'[.!?]+', text)
            avg_len = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
            if avg_len > 25:
                issues.append(f"Debug voice should use shorter sentences (avg {avg_len:.0f} words)")

        elif vessel_type == "fleet-commander":
            # Should end with "I will keep watching" or similar
            if "keep watching" not in text.lower():
                issues.append("Fleet commander voice should end with 'I will keep watching.'")

        elif vessel_type == "hardware/edge":
            # Should contain hex values or register references
            if not re.search(r'0x[0-9A-Fa-f]+', text):
                issues.append("Hardware voice should contain hex values or register references")

        elif vessel_type == "build/coordination":
            # Should mention cost/time/tokens
            if not any(w in text.lower() for w in ["minute", "hour", "token", "api", "cost"]):
                issues.append("Build coordinator voice should mention cost/time")

        elif vessel_type == "research/oracle":
            # Should ask questions
            if "?" not in text:
                issues.append("Research voice should include questions")

        return len(issues) == 0, issues

    def check_skip_rules(self, text: str) -> Optional[str]:
        """Check if the log's content triggers any skip rule.

        Returns the name of the first triggered rule, or None if none triggered.
        This is a heuristic check — the agent should self-assess before writing.
        """
        # Check for standing order violation markers
        violation_markers = ["violated", "without authorization", "against orders", "overrode"]
        if any(m in text.lower() for m in violation_markers):
            return "standing_order_violation"

        # Check for unreported pattern markers
        pattern_markers = ["no other agent", "nobody reported", "unreported", "first time"]
        if any(m in text.lower() for m in pattern_markers):
            return "unreported_pattern"

        # Check for unexplained failure markers
        failure_markers = ["cannot explain", "don't know why", "no obvious reason", "unexplained"]
        if any(m in text.lower() for m in failure_markers):
            return "unexplained_failure"

        # Check for loss prevention markers
        prevention_markers = ["prevented", "killed", "aborted", "rolled back", "shut down"]
        if any(m in text.lower() for m in prevention_markers):
            return "permanent_loss_prevention"

        # Check for fleet-changing insight markers
        insight_markers = ["fleet should", "specification needs", "fundamental", "all vessels"]
        if any(m in text.lower() for m in insight_markers):
            return "fleet_changing_insight"

        return None

    async def score_rubric(self, text: str, vessel_type: str) -> RubricScore:
        """Score a log against the 7-element rubric using a reasoning model."""
        prompt = (
            f"{RUBRIC_SPEC}\n\n"
            "Score the following captain's log against each element.\n"
            "Output each score on its own line, then 'Average: X.X'\n\n"
            f"VESSEL TYPE: {vessel_type}\n\n"
            f"LOG:\n{text}"
        )

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": MODEL_PHASE2,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 400,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{DEEPINFRA_BASE}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            result = resp.json()["choices"][0]["message"]["content"]

        score = _parse_scores(result)
        if score is None:
            # Fallback: return minimum scores
            return RubricScore(
                scores={e: 3 for e in RUBRIC_ELEMENTS},
                average=3.0,
            )
        return score

    async def validate(
        self,
        log_text: str,
        vessel_type: str,
        use_model: bool = False,
    ) -> ValidationResult:
        """Full validation of a log.

        If use_model is True, uses the reasoning model for rubric scoring.
        Otherwise, performs heuristic validation only.
        """
        word_count = len(log_text.split())
        reading_time = self.estimate_reading_time(log_text)
        voice_ok, voice_issues = self.check_voice_consistency(log_text, vessel_type)
        skip_rule = self.check_skip_rules(log_text)

        if use_model:
            rubric_score = await self.score_rubric(log_text, vessel_type)
        else:
            rubric_score = None

        passes_gate = True
        issues = []

        if rubric_score:
            if not rubric_score.passes():
                passes_gate = False
                issues.append(f"Quality gate failed: average {rubric_score.average:.1f}")
                low = [e for e, s in rubric_score.scores.items() if s < 3]
                if low:
                    issues.append(f"Elements below 3: {', '.join(low)}")
        if not voice_ok:
            issues.extend(voice_issues)
        if skip_rule is None:
            issues.append("No skip rule triggered — this log may not meet the skip criteria")

        if word_count > 600:
            issues.append(f"Log is {word_count} words (target: 200-400)")
        if word_count < 100:
            issues.append(f"Log is only {word_count} words (minimum: 100)")

        return ValidationResult(
            rubric_score=rubric_score,
            passes_quality_gate=passes_gate,
            skip_rule_triggered=skip_rule,
            voice_consistent=voice_ok,
            reading_time_seconds=reading_time,
            word_count=word_count,
            issues=issues,
        )
