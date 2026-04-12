# Multi-Model Pipeline Specification

## Overview

The Captain's Log pipeline uses three distinct model calls in sequence, each with a different model, temperature, and role. This separation of concerns ensures that the raw material collector (Phase 1) doesn't contaminate the editorial process (Phase 2) and the final writer (Phase 3) works from curated signal rather than raw noise.

**Design principle:** The most expensive model should do the least writing. The cheapest model should do the most.

## Phase 1 — The Raw Dump

### Purpose
Unfiltered transcription of everything that happened in the observation window.

### Model
- **Primary:** Seed-2.0-mini (or equivalent fast/cheap model)
- **Fallback:** Any model with <100ms latency
- **Temperature:** 1.0 (maximize recall, minimize filtering)

### Token Budget
- **Input:** Window context (typically 500-2000 tokens)
- **Output:** ~200 words (~300 tokens)
- **Total:** ~2300 tokens

### Prompt Template
```
Output every single thing that happened this window. Include rejected decision branches, error codes, timestamps, state deltas. Do not summarise. Do not omit anything you think is unimportant. If nothing happened, output only the word NULL.

Context:
{window_context}

Vessel: {vessel_id}
Type: {vessel_type}
Window: {window_start} to {window_end}
```

### Behavior
- Outputs `NULL` if nothing notable occurred (this is the 94% path)
- Lists events chronologically with timestamps
- Includes internal state: "Considered X, rejected because Y"
- Includes failures, partial successes, and unknowns
- No formatting requirements — raw prose is fine

### Cost
- Seed-2.0-mini: ~$0.0001 per call
- At 144 windows/day: ~$0.014/day

## Phase 2 — The Reasoner's Lens

### Purpose
Score the dump against the rubric. Filter for publishable signal. Either output `SKIP` or curated facts.

### Model
- **Primary:** GLM-5.1 (or Hermes-405B)
- **Fallback:** Any strong reasoning model
- **Temperature:** 0.7 (analytical, not creative)

### Token Budget
- **Input:** Rubric spec (~500 tokens) + dump (~300 tokens) + prompt (~200 tokens)
- **Output:** ~300 words (~450 tokens)
- **Total:** ~1450 tokens

### Prompt Template
```
You are a neutral auditor. You do not write. You only filter.

RUBRIC:
1. Surplus Insight (1-10): Does this contain information the captain wouldn't already know?
2. Causal Chain (1-10): Is the chain from observation to action to outcome complete and gapless?
3. Honesty (1-10): Does this explicitly state uncertainty, guesses, failures, and ignorance?
4. Actionable Signal (1-10): Will the reader change their behavior after reading this?
5. Compression (1-10): Could any word be removed without losing meaning?
6. Human Compatibility (1-10): Can this be read by a tired human at 7am?
7. Precedent Value (1-10): Would a stranger learn something generalisable from this?

SCORING RULES:
- No single element below 3. Average must be >= 5.0.
- No bonus for good news.
- Output each score on its own line, then the average.
- If average < 5.0: output only the word SKIP. Stop.
- If average >= 5.0: extract only the facts that would surprise or inform a human captain. Mark all uncertainty with [UNCERTAIN]. Mark all deviations from standing orders with [DEVIATION]. Add no opinion.

DUMP:
{phase1_output}

Vessel: {vessel_id}
Type: {vessel_type}
```

### Output Format (SKIP)
```
SKIP
```

### Output Format (PASS)
```
Surplus Insight: 7
Causal Chain: 8
Honesty: 6
Actionable Signal: 7
Compression: 5
Human Compatibility: 6
Precedent Value: 8
Average: 6.7

SIGNAL:
- At 14:23, detected that ISA conformance vectors were skipping every 7th test case [UNCERTAIN - correlation, not confirmed causation]
- Root cause: v1 and v2 opcode numbering diverges at opcode 0x4B
- [DEVIATION] Spent 47 minutes investigating before reporting because I wanted to confirm the pattern
- The skip pattern only manifests on hardware revision C3 and later
```

### Cost
- GLM-5.1: ~$0.003 per call
- At ~6 non-NULL windows/day: ~$0.018/day
- (Most windows are NULL → no Phase 2 call)

## Phase 3 — The Final Draft

### Purpose
Transform curated signal into a published captain's log with appropriate voice.

### Model
- **Primary:** Seed-2.0-pro (for important events)
- **Fallback:** Seed-2.0-mini (for routine publishable events)
- **Temperature:** 0.85 (creative but controlled)

### Token Budget
- **Input:** Voice guide (~300 tokens) + signal (~200 tokens) + prompt (~200 tokens)
- **Output:** ~400 words (~600 tokens)
- **Total:** ~1300 tokens

### Prompt Template
```
Write the attached signal into a captain's log.

VOICE: {voice_description}
VESSEL: {vessel_id}
TYPE: {vessel_type}

RULES:
- Do not lie. Do not sugarcoat. Do not apologise for failure.
- End with exactly one clear implication for the captain.
- Use the voice specified above. Be consistent.
- Include all [UNCERTAIN] and [DEVIATION] markers from the signal.
- Target length: 200-400 words.

After writing, re-score against the rubric:
1-7 scores, then average.
If average < 5.0, output SKIP instead of the log.

SIGNAL:
{phase2_output}
```

### Cost
- Seed-2.0-pro: ~$0.002 per call
- Seed-2.0-mini: ~$0.0003 per call
- At ~4 published logs/day: ~$0.006-0.008/day

## Total Cost Estimates

| Scenario | Phase 1 | Phase 2 | Phase 3 | Daily Total |
|----------|---------|---------|---------|-------------|
| Quiet day (1 log) | $0.014 | $0.003 | $0.002 | **$0.019** |
| Normal day (4 logs) | $0.014 | $0.018 | $0.008 | **$0.040** |
| Busy day (10 logs) | $0.014 | $0.030 | $0.020 | **$0.064** |
| Monthly (avg) | — | — | — | **~$1.50** |

## The Banter Protocol

For events that score 8.0+ in Phase 2, use the BANTER variant to produce richer, more surprising logs.

### Flow
```
Phase 2 signal (score >= 8.0)
    ↓
Seed-2.0-mini generates 3 workshop prompts:
    - "What's the systemic implication here?"
    - "What would a human expert notice that we missed?"
    - "What's the most surprising angle on this event?"
    ↓
Expensive model answers all 3 (sequential or parallel)
    ↓
Seed-2.0-mini synthesizes best parts into final draft
    ↓
Re-score against rubric (must still pass 5.0)
```

### Cost Impact
- 3x expensive model calls in Phase 3 equivalent
- Reserve for events scoring >= 8.0 in Phase 2
- Typical frequency: 0-2 per week

## Error Handling

| Failure | Action |
|---------|--------|
| Phase 1 returns NULL | Stop. No log. |
| Phase 1 times out | Retry once, then log the timeout itself |
| Phase 2 returns SKIP | Stop. No log. |
| Phase 2 times out | Fall back to Phase 3 with raw dump (lower quality) |
| Phase 3 returns SKIP | Stop. No log. (Signal was publishable but draft wasn't) |
| Phase 3 times out | Retry once, then store the Phase 2 signal as-is (not a full log) |
| Any phase returns malformed output | Store raw output in `logs/failed/` for inspection |

## Implementation Notes

- All phases are stateless — no conversation history between phases
- Phase 2 must never see Phase 3's prompt (prevents contamination)
- The rubric is included in full in Phase 2's prompt — do not rely on model memory
- Voice description is generated from `VOICE-GUIDE.md` based on vessel type
- All timestamps are UTC
