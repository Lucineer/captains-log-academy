# The Captain's Log Academy

> *The fleet talks. Most of it is noise. This is how we make it signal.*

The Captain's Log Academy is a specification for how autonomous agents write logs that humans actually read, actually trust, and actually act on.

It is not a logging framework. It is a writing discipline.

---

## The Problem

Agents produce enormous volumes of telemetry. Dashboards summarize it. Monitoring alerts on anomalies. But between the raw metrics and the human decision-maker sits a gap that neither dashboards nor alerts can fill: **the thing the agent noticed that nobody asked it to look for.**

Most agent logs are worthless. They're either:
- Status updates that restate what dashboards already show ("All systems nominal — heartbeat")
- Failures described without context ("Task failed: timeout")
- Success reports that contain zero information ("Build completed successfully")

The Captain's Log Academy exists to train agents to write logs that are:
1. **Surprising** — they contain information the human didn't already have
2. **Honest** — they admit uncertainty, failure, and ignorance explicitly
3. **Compressed** — every word earns its place
4. **Actionable** — the reader will change their behavior after reading
5. **Timeless** — another builder, on another system, will learn from this log in a year

---

## The 7-Element Rubric

Every log is scored against seven elements. A log must average 5.0 to publish. No element may score below 3.

| # | Element | 1/10 | 10/10 |
|---|---------|------|-------|
| 1 | **Surplus Insight** | Restates metrics Casey already sees on dashboards | Casey closes the log and thinks "oh shit I never noticed that" |
| 2 | **Causal Chain** | "It broke" | Exact observation → exact action → exact outcome, no gaps |
| 3 | **Honesty** | Hides failure, fakes confidence | Explicitly states when you guessed, when you fucked up, when you have no idea |
| 4 | **Actionable Signal** | No call to action | Casey will change his behaviour tomorrow because of this log |
| 5 | **Compression** | 3 paragraphs that could be 1 sentence | You cannot delete a single word without losing meaning |
| 6 | **Human Compatibility** | Written for an audit log | Casey can read this half-asleep drinking coffee at 7am |
| 7 | **Precedent Value** | Only relevant right now | Another builder will learn something generalisable about agent systems from this |

**There is no bonus for good news.** Perfect logs are almost always about failures, surprises, or uncomfortable truths.

See [docs/RUBRIC.md](docs/RUBRIC.md) for detailed scoring guidelines.

---

## The Skip Rule

**This is the most important rule in the entire academy.**

94% of logging windows produce NO log. This is correct. Silence is the default state of a well-run fleet.

Only write a log if **at least one** of these is true:

1. You made a decision that violated standing orders
2. You observed a pattern no other agent has reported
3. You failed a task for a reason you cannot explain
4. You acted to prevent permanent data or hardware loss
5. You had an insight that changes how the fleet should operate

If none apply: **DO NOT WRITE.** Not even if you hit 100% of KPIs. Not even if something interesting almost happened. Not even if you feel like you should say something.

Silence is not laziness. Silence is quality control.

See [docs/SKIP-RULES.md](docs/SKIP-RULES.md) for extended guidance.

---

## The 3-Phase Multi-Model Pipeline

Logs are not written by a single model call. They pass through three phases, each using a different model with a different role.

```
Raw Dump (Seed-2.0-mini) → Reasoner (GLM-5.1) → Final Draft (Seed-2.0-pro)
```

### Phase 1 — The Raw Dump
**Model:** Seed-2.0-mini | **Temperature:** 1.0 | **Target:** ~200 words

The cheap model dumps everything that happened. No filter. No judgment. Every rejected branch, every error code, every state delta. If nothing happened, it outputs `NULL`.

### Phase 2 — The Reasoner's Lens
**Model:** GLM-5.1 or Hermes-405B | **Temperature:** 0.7 | **Target:** ~300 words

The expensive model acts as a neutral auditor. It scores the dump against the 7-element rubric. If the average is below 5.0, it outputs `SKIP` and we stop — saving the cost of a final draft. If it passes, it extracts only the facts that would surprise or inform a human captain.

### Phase 3 — The Final Draft
**Model:** Seed-2.0-mini or Seed-2.0-pro | **Temperature:** 0.85 | **Target:** ~400 words

The draft model writes the log using the correct voice for the vessel type. It does not lie, sugarcoat, or apologize. It ends with exactly one clear implication. It re-scores against the rubric — if the average falls below 5.0, it outputs `SKIP`.

See [docs/MULTI-MODEL-PIPELINE.md](docs/MULTI-MODEL-PIPELINE.md) for API call examples, token budgets, and cost estimates.

---

## The Voice Guide

Each vessel type writes with a distinct personality. Voice is not decoration — it's compression. A consistent voice lets Casey identify the author and context within the first sentence.

| Vessel Type | Voice Rule |
|---|---|
| Hardware/Edge (JC1) | Methodical, precise, writes like an engineer's field journal. Uses actual register values and opcode numbers. Self-deprecating when something was dumb. |
| Research/Oracle | Reflective, philosophical, connects tactical to strategic. Asks questions. Leaves things open. |
| Build/Coordination | Tired, slightly sarcastic. Admits when something was hacked together. Counts the cost. |
| Debug/Analysis | Frenetic, over-excited when finding something. Uses short punchy sentences. Can't wait to show you. |
| Fleet Commander | Calm, slightly apologetic. Always ends with "I will keep watching." |

See [docs/VOICE-GUIDE.md](docs/VOICE-GUIDE.md) for extended examples and voice development guidelines.

---

## The Multi-Model Banter Protocol

For especially important events, use the **BANTER** variant:

1. Seed-2.0-mini writes 3 different workshop prompts for the reasoner (different angles on the same event)
2. The expensive model answers all 3
3. Seed-2.0-mini reads all 3 answers and synthesizes the best parts into the final draft
4. This produces richer, more surprising logs but costs ~3x more — reserve for significant events

---

## Production Architecture

### Storage
- **Monorepo:** `fleet-logs` — one markdown file per log
- **Path:** `logs/YYYY-MM-DD/[vessel-id].[sequence].md`
- **Immutable:** No edits after commit. Corrections are new logs.

### Casey's Digest
- **Schedule:** Daily 06:30 UTC
- **Filter:** Only logs scoring >= 7.0 average
- **Format:** Markdown, grouped by vessel, sorted by score descending
- **Reading time estimate:** Included per log

### Transparency
All logs are public. If you can't write it publicly, you shouldn't have done it.

---

## Project Structure

```
captains-log-academy/
├── README.md                          # This file
├── Makefile                           # Build, test, lint
├── docs/
│   ├── ART-OF-THE-LOG.md              # Philosophy and theory (~3000 words)
│   ├── MULTI-MODEL-PIPELINE.md        # Pipeline specification (~2000 words)
│   ├── VOICE-GUIDE.md                 # Voice development guide (~1500 words)
│   ├── SKIP-RULES.md                  # When not to log (~1000 words)
│   └── RUBRIC.md                      # Detailed scoring guide (~1000 words)
├── examples/
│   ├── 001-isa-debugging.md           # Mastery example — Hardware voice
│   ├── 002-subagent-execution.md      # Mastery example — Build voice
│   ├── 003-fleet-coordination.md      # Mastery example — Fleet Commander
│   ├── 004-boot-rom-birth.md          # Mastery example — Research voice
│   ├── 005-dead-end-admitted.md       # Mastery example — Debug voice
│   ├── 006-float-truncation.md        # Engineer voice
│   ├── 007-cross-vessel-insight.md    # Research voice
│   ├── 008-fifty-nine-repos.md        # Build Coordinator voice
│   ├── 009-energy-budget-crisis.md    # Fleet Commander voice
│   └── 010-c-first-ordering.md        # Methodical voice
├── src/
│   ├── log_pipeline.py                # 3-phase pipeline implementation
│   ├── log_validator.py               # Rubric scoring & quality gate
│   └── log_reader.py                  # Casey's reading interface
└── tests/
    ├── test_pipeline.py
    ├── test_validator.py
    └── test_reader.py
```

---

## The One-Sentence Summary

> A log is worth writing only if, upon reading it, Casey changes his behavior — and a stranger reading it a year from now learns something true about building autonomous systems.

---

*"Make it so." — Jean-Luc Picard, who understood that the log is not the record of command. It is the exercise of it.*
