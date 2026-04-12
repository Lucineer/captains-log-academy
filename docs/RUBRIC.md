# The 7-Element Rubric

## Scoring Guidelines

Each element is scored 1-10. Scores should be integers. The seven scores are averaged; the average must be >= 5.0 to publish. No individual element may score below 3.

### 1. Surplus Insight (1-10)

**What it measures:** Does this log contain information the captain would not have obtained from any other source?

| Score | Meaning |
|-------|---------|
| 1-2 | Entirely redundant with dashboards, alerts, or other logs |
| 3-4 | Contains minor details not available elsewhere, but nothing surprising |
| 5-6 | At least one genuinely new observation or connection |
| 7-8 | Multiple non-obvious insights; Casey will see something he didn't expect |
| 9-10 | Casey's mental model of the fleet will change after reading this |

**Common failure modes:**
- Confusing detail with insight (100 register values ≠ 1 surprising register value)
- Reporting what happened without explaining why it matters
- Including context that Casey already has

### 2. Causal Chain (1-10)

**What it measures:** Is there a complete, gapless chain from observation through action to outcome?

| Score | Meaning |
|-------|---------|
| 1-2 | "It broke" or "It worked" with no chain |
| 3-4 | Some steps present but with gaps or assumptions |
| 5-6 | Most steps present; one or two gaps remain |
| 7-8 | Complete chain; every step explicit |
| 9-10 | Complete chain plus explanation of *why* each step was necessary |

**Common failure modes:**
- "Fixed the bug" without explaining what the bug was
- Stating an outcome without showing the action that produced it
- Implicit reasoning that the reader has to guess

### 3. Honesty (1-10)

**What it measures:** Does the log explicitly acknowledge uncertainty, mistakes, guesses, and ignorance?

| Score | Meaning |
|-------|---------|
| 1-2 | Hides or omits failures; presents speculation as fact |
| 3-4 | Acknowledges failures but downplays them or adds excuses |
| 5-6 | States failures clearly but avoids acknowledging uncertainty |
| 7-8 | Explicitly marks guesses, unknowns, and degrees of confidence |
| 9-10 | Radical honesty — admits what it doesn't know even when that's uncomfortable |

**Common failure modes:**
- "I believe the cause was..." without marking this as a guess
- Presenting the resolution as cleaner than it was
- Omitting the dead ends and wrong turns

### 4. Actionable Signal (1-10)

**What it measures:** Will Casey change his behavior after reading this log?

| Score | Meaning |
|-------|---------|
| 1-2 | Pure information; no implication for action |
| 3-4 | Vague implication ("we should look into this") |
| 5-6 | Clear implication for a specific action |
| 7-8 | Casey will do something specific tomorrow because of this |
| 9-10 | Casey will change a standing order or fleet protocol because of this |

**Common failure modes:**
- Ending with a vague summary instead of a specific implication
- Stating a problem without any hint of what to do about it
- Making the implication so broad it's useless ("be careful")

### 5. Compression (1-10)

**What it measures:** Is every word necessary? Could any word be removed without losing meaning?

| Score | Meaning |
|-------|---------|
| 1-2 | Extreme verbosity; could be reduced to 10% of length |
| 3-4 | Significant padding; obvious filler throughout |
| 5-6 | Mostly tight; a few paragraphs could lose sentences |
| 7-8 | Very tight; only individual words could be removed |
| 9-10 | Cannot delete a single word without losing meaning |

**Common failure modes:**
- Restating the same point in different words
- Providing background that Casey already has
- Using ten words when three would do

### 6. Human Compatibility (1-10)

**What it measures:** Can Casey read this at 7am, half-asleep, with coffee, and understand it on the first pass?

| Score | Meaning |
|-------|---------|
| 1-2 | Written for a machine; requires domain expertise Casey doesn't have |
| 3-4 | Requires re-reading to understand |
| 5-6 | Clear on first read but requires some effort |
| 7-8 | Effortless to read; flows naturally |
| 9-10 | Impossible to stop reading; genuinely engaging |

**Common failure modes:**
- Using jargon without context
- Long, meandering sentences
- Buried ledes (important information hidden in the middle)
- Failing to establish context early

### 7. Precedent Value (1-10)

**What it measures:** Will someone unfamiliar with this specific vessel/window learn something generalisable about agent systems?

| Score | Meaning |
|-------|---------|
| 1-2 | Only relevant to this exact event at this exact time |
| 3-4 | Slightly generalisable (useful if you run the same system) |
| 5-6 | Moderately generalisable (the principle applies to similar systems) |
| 7-8 | Highly generalisable (the lesson applies across agent architectures) |
| 9-10 | Changes how the reader thinks about autonomous systems fundamentally |

**Common failure modes:**
- Being so specific that the lesson is trapped in context
- Stating the outcome without extracting the general principle
- Assuming the reader has identical domain knowledge

## Example Scoring

### Log: "The conformance vectors kept skipping every 7th test."

| Element | Score | Justification |
|---------|-------|---------------|
| Surplus Insight | 8 | Casey didn't know about the systematic skip |
| Causal Chain | 9 | Complete chain: opcode numbering → vector misalignment → skip pattern |
| Honesty | 7 | Admits it took 3 hours to find; doesn't hide the dead ends |
| Actionable Signal | 8 | Casey will update the ISA test harness fleet-wide |
| Compression | 7 | Some repetition in the debugging narrative |
| Human Compatibility | 8 | Clear, builds to a reveal, good pacing |
| Precedent Value | 9 | The lesson about specification versioning applies everywhere |
| **Average** | **8.0** | |

### Log: "All systems nominal. Completed 47 tasks. No errors detected."

| Element | Score | Justification |
|---------|-------|---------------|
| Surplus Insight | 1 | Dashboard information |
| Causal Chain | 3 | No chain — just a statement |
| Honesty | 5 | Not dishonest, but not honest about anything either |
| Actionable Signal | 1 | No call to action |
| Compression | 2 | Could be "DONE" |
| Human Compatibility | 4 | Readable but contains nothing worth reading |
| Precedent Value | 1 | No generalisable lesson |
| **Average** | **2.4** | **SKIP** |
