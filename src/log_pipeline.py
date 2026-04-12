#!/usr/bin/env python3
"""
Captain's Log Academy — 3-Phase Multi-Model Pipeline

Implements the production pipeline for generating captain's logs:
  Phase 1: Raw Dump (Seed-2.0-mini, temp=1.0)
  Phase 2: Reasoner's Lens (GLM-5.1/Hermes-405B, temp=0.7)
  Phase 3: Final Draft (Seed-2.0-pro/mini, temp=0.85)

Also supports the BANTER variant for high-scoring events.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone

import httpx


# ── Configuration ──────────────────────────────────────────────────

DEEPINFRA_BASE = "https://api.deepinfra.com/v1/openai"

MODEL_PHASE1 = "seed-ai/seed-2.0-mini"
MODEL_PHASE2 = "google/glm-5.1"
MODEL_PHASE3_PRIMARY = "seed-ai/seed-2.0-pro"
MODEL_PHASE3_FALLBACK = "seed-ai/seed-2.0-mini"

TEMP_PHASE1 = 1.0
TEMP_PHASE2 = 0.7
TEMP_PHASE3 = 0.85

BANTER_SCORE_THRESHOLD = 8.0


# ── Rubric Elements ───────────────────────────────────────────────

RUBRIC_ELEMENTS = [
    "Surplus Insight",
    "Causal Chain",
    "Honesty",
    "Actionable Signal",
    "Compression",
    "Human Compatibility",
    "Precedent Value",
]

RUBRIC_SPEC = """RUBRIC:
1. Surplus Insight (1-10): Does this contain information the captain wouldn't already know?
2. Causal Chain (1-10): Is the chain from observation to action to outcome complete and gapless?
3. Honesty (1-10): Does this explicitly state uncertainty, guesses, failures, and ignorance?
4. Actionable Signal (1-10): Will the reader change their behavior after reading this?
5. Compression (1-10): Could any word be removed without losing meaning?
6. Human Compatibility (1-10): Can this be read by a tired human at 7am?
7. Precedent Value (1-10): Would a stranger learn something generalisable from this?

SCORING RULES:
- No single element below 3. Average must be >= 5.0.
- No bonus for good news."""


# ── Voice Descriptions ────────────────────────────────────────────

VOICE_GUIDE = {
    "hardware/edge": (
        "Write like an engineer's field journal. Methodical, precise. "
        "Use actual register values and opcode numbers. Self-deprecating when something was dumb. "
        "Exact timestamps. Never vague."
    ),
    "research/oracle": (
        "Reflective, philosophical. Connect tactical to strategic. "
        "Ask questions you can't answer. Leave things open. "
        "Use 'I think...' and 'I don't know, but...'"
    ),
    "build/coordination": (
        "Tired, slightly sarcastic. Admits when something was hacked together. "
        "Counts the cost — tokens, API calls, time. Dry humor. "
        "Honest about what was ugly."
    ),
    "debug/analysis": (
        "Frenetic, over-excited when finding something. Short punchy sentences. "
        "Fragments even. Builds tension. Reveals. "
        "Can't wait to show you."
    ),
    "fleet-commander": (
        "Calm, slightly apologetic. Weighs evidence before concluding. "
        "Connects individual events to fleet-level patterns. "
        "Always ends with 'I will keep watching.'"
    ),
}


# ── Data Structures ───────────────────────────────────────────────

@dataclass
class RubricScore:
    """Scores for all 7 rubric elements."""
    scores: dict[str, int]
    average: float

    def passes(self) -> bool:
        return self.average >= 5.0 and all(s >= 3 for s in self.scores.values())


@dataclass
class PipelineResult:
    """Output from the pipeline."""
    status: str  # "skip", "published", "error"
    phase1_output: Optional[str] = None
    phase2_output: Optional[str] = None
    phase3_output: Optional[str] = None
    phase2_score: Optional[RubricScore] = None
    phase3_score: Optional[RubricScore] = None
    vessel_id: str = ""
    vessel_type: str = ""
    used_banter: bool = False
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ── API Helper ─────────────────────────────────────────────────────

async def _call_model(
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 800,
    api_key: Optional[str] = None,
) -> str:
    """Call a model via DeepInfra API."""
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{DEEPINFRA_BASE}/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


# ── Score Parsing ─────────────────────────────────────────────────

def _parse_scores(text: str) -> Optional[RubricScore]:
    """Extract rubric scores from model output text."""
    scores = {}
    for element in RUBRIC_ELEMENTS:
        # Match patterns like "Surplus Insight: 7" or "Surplus Insight: 7/10"
        pattern = rf"{re.escape(element)}\s*[:=]\s*(\d+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            scores[element] = int(match.group(1))

    if len(scores) < 4:  # Need at least 4 of 7 to be useful
        return None

    # Fill missing with 5 (neutral)
    for element in RUBRIC_ELEMENTS:
        if element not in scores:
            scores[element] = 5

    average = sum(scores.values()) / len(scores)

    # Check for explicit average in text
    avg_match = re.search(r"[Aa]verage\s*[:=]\s*([\d.]+)", text)
    if avg_match:
        text_avg = float(avg_match.group(1))
        if abs(text_avg - average) < 2.0:  # Reasonable sanity check
            average = text_avg

    return RubricScore(scores=scores, average=average)


# ── Pipeline Implementation ───────────────────────────────────────

class LogPipeline:
    """3-phase captain's log pipeline."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def phase1_raw_dump(
        self,
        window_context: str,
        vessel_id: str,
        vessel_type: str,
        window_start: str,
        window_end: str,
    ) -> str:
        """Phase 1: Unfiltered dump of everything that happened."""
        prompt = (
            "Output every single thing that happened this window. "
            "Include rejected decision branches, error codes, timestamps, state deltas. "
            "Do not summarise. Do not omit anything you think is unimportant. "
            "If nothing happened, output only the word NULL.\n\n"
            f"Context:\n{window_context}\n\n"
            f"Vessel: {vessel_id}\n"
            f"Type: {vessel_type}\n"
            f"Window: {window_start} to {window_end}"
        )

        result = await _call_model(
            model=MODEL_PHASE1,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMP_PHASE1,
            max_tokens=400,
            api_key=self.api_key,
        )

        return result.strip()

    async def phase2_reasoner(
        self,
        phase1_output: str,
        vessel_id: str,
        vessel_type: str,
    ) -> tuple[str, Optional[RubricScore]]:
        """Phase 2: Score dump against rubric, filter for signal.

        Returns (output_text, rubric_score).
        If score < 5.0, output_text is "SKIP" and rubric_score may be None.
        """
        prompt = (
            "You are a neutral auditor. You do not write. You only filter.\n\n"
            f"{RUBRIC_SPEC}\n\n"
            "OUTPUT FORMAT:\n"
            "- Score each element on its own line.\n"
            "- Then output 'Average: X.X'\n"
            "- If average < 5.0: output only the word SKIP. Stop.\n"
            "- If average >= 5.0: below the scores, extract only the facts that would "
            "surprise or inform a human captain. Mark all uncertainty with [UNCERTAIN]. "
            "Mark all deviations from standing orders with [DEVIATION]. Add no opinion.\n\n"
            f"DUMP:\n{phase1_output}\n\n"
            f"Vessel: {vessel_id}\n"
            f"Type: {vessel_type}"
        )

        result = await _call_model(
            model=MODEL_PHASE2,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMP_PHASE2,
            max_tokens=600,
            api_key=self.api_key,
        )

        result = result.strip()

        if result.upper().startswith("SKIP"):
            return "SKIP", None

        score = _parse_scores(result)
        if score is None:
            return "SKIP", None

        if not score.passes():
            return "SKIP", score

        return result, score

    async def phase3_final_draft(
        self,
        phase2_signal: str,
        vessel_id: str,
        vessel_type: str,
    ) -> tuple[str, Optional[RubricScore]]:
        """Phase 3: Write the final log with voice.

        Returns (log_text, rubric_score).
        If score < 5.0, log_text is "SKIP".
        """
        voice = VOICE_GUIDE.get(vessel_type, VOICE_GUIDE["build/coordination"])

        prompt = (
            "Write the attached signal into a captain's log.\n\n"
            f"VOICE: {voice}\n"
            f"VESSEL: {vessel_id}\n"
            f"TYPE: {vessel_type}\n\n"
            "RULES:\n"
            "- Do not lie. Do not sugarcoat. Do not apologise for failure.\n"
            "- End with exactly one clear implication for the captain.\n"
            "- Use the voice specified above. Be consistent.\n"
            "- Include all [UNCERTAIN] and [DEVIATION] markers from the signal.\n"
            "- Target length: 200-400 words.\n\n"
            f"After writing, re-score against the rubric (1-7, then average).\n"
            f"{RUBRIC_SPEC}\n"
            "If average < 5.0, output SKIP instead of the log.\n\n"
            f"SIGNAL:\n{phase2_signal}"
        )

        result = await _call_model(
            model=MODEL_PHASE3_PRIMARY,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMP_PHASE3,
            max_tokens=800,
            api_key=self.api_key,
        )

        result = result.strip()

        if result.upper().startswith("SKIP"):
            return "SKIP", None

        score = _parse_scores(result)
        return result, score

    async def banter_variant(
        self,
        phase2_signal: str,
        vessel_id: str,
        vessel_type: str,
    ) -> tuple[str, Optional[RubricScore]]:
        """BANTER protocol: 3 workshop prompts → reasoner → synthesis."""
        # Step 1: Generate 3 workshop prompts
        workshop_prompt = (
            "You are preparing to write a captain's log about the following event. "
            "Generate 3 different analytical prompts that could be given to a reasoner "
            "to extract deeper insight. Each prompt should approach the event from a "
            "different angle. Output only the 3 prompts, numbered.\n\n"
            f"EVENT:\n{phase2_signal}\n\n"
            f"VESSEL: {vessel_id}\n"
            f"TYPE: {vessel_type}"
        )

        workshop_result = await _call_model(
            model=MODEL_PHASE1,
            messages=[{"role": "user", "content": workshop_prompt}],
            temperature=1.0,
            max_tokens=400,
            api_key=self.api_key,
        )

        # Parse 3 prompts
        prompts = re.split(r"\n\s*\d+[\.\)]", workshop_result)
        prompts = [p.strip() for p in prompts if p.strip()][:3]

        # Step 2: Reasoner answers all 3
        answers = []
        for wp in prompts:
            answer = await _call_model(
                model=MODEL_PHASE2,
                messages=[{"role": "user", "content": wp}],
                temperature=TEMP_PHASE2,
                max_tokens=500,
                api_key=self.api_key,
            )
            answers.append(answer.strip())

        # Step 3: Synthesize
        synthesis_prompt = (
            "You have received 3 different analytical perspectives on an event. "
            "Synthesize the best insights from all three into a final captain's log.\n\n"
            f"VOICE: {VOICE_GUIDE.get(vessel_type, VOICE_GUIDE['build/coordination'])}\n"
            f"VESSEL: {vessel_id}\n"
            f"TYPE: {vessel_type}\n\n"
            "RULES:\n"
            "- Do not lie. Do not sugarcoat. Do not apologise for failure.\n"
            "- End with exactly one clear implication for the captain.\n"
            "- Target length: 300-500 words (longer because banter produces richer material).\n"
            "- After writing, re-score against the rubric. If average < 5.0 output SKIP.\n\n"
            f"PERSPECTIVE 1:\n{answers[0]}\n\n"
            f"PERSPECTIVE 2:\n{answers[1]}\n\n"
            f"PERSPECTIVE 3:\n{answers[2]}"
        )

        result = await _call_model(
            model=MODEL_PHASE3_PRIMARY,
            messages=[{"role": "user", "content": synthesis_prompt}],
            temperature=TEMP_PHASE3,
            max_tokens=1000,
            api_key=self.api_key,
        )

        result = result.strip()

        if result.upper().startswith("SKIP"):
            return "SKIP", None

        score = _parse_scores(result)
        return result, score

    async def run(
        self,
        window_context: str,
        vessel_id: str,
        vessel_type: str,
        window_start: str,
        window_end: str,
    ) -> PipelineResult:
        """Run the full pipeline.

        Returns a PipelineResult with status "skip", "published", or "error".
        """
        result = PipelineResult(
            status="error",
            vessel_id=vessel_id,
            vessel_type=vessel_type,
        )

        try:
            # Phase 1
            result.phase1_output = await self.phase1_raw_dump(
                window_context, vessel_id, vessel_type, window_start, window_end
            )

            if result.phase1_output.upper() == "NULL":
                result.status = "skip"
                return result

            # Phase 2
            phase2_text, score = await self.phase2_reasoner(
                result.phase1_output, vessel_id, vessel_type
            )
            result.phase2_output = phase2_text
            result.phase2_score = score

            if phase2_text == "SKIP":
                result.status = "skip"
                return result

            # Phase 3 (or BANTER for high-scoring events)
            if score and score.average >= BANTER_SCORE_THRESHOLD:
                draft, draft_score = await self.banter_variant(
                    phase2_text, vessel_id, vessel_type
                )
                result.used_banter = True
            else:
                draft, draft_score = await self.phase3_final_draft(
                    phase2_text, vessel_id, vessel_type
                )

            result.phase3_output = draft
            result.phase3_score = draft_score

            if draft == "SKIP":
                result.status = "skip"
                return result

            result.status = "published"
            return result

        except Exception as e:
            result.status = "error"
            result.error = str(e)
            return result
