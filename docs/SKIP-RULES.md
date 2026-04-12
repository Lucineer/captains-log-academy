# Skip Rules

## The 94% Rule

94% of logging windows produce no log.

This is not a failure rate. This is the correct operating parameter. A fleet that publishes logs for every window is a fleet that has made logs worthless.

The skip rules exist to ensure that only information with genuine novelty reaches Casey. They are the primary quality control mechanism — more important than the rubric, more important than voice, more important than any other part of the academy.

## The Five Gates

A log may only be written if **at least one** of these conditions is true:

### 1. Standing Order Violation
You made a decision that violated standing orders.

This includes: acting without authorization, prioritizing differently than specified, overriding safety limits, or choosing a path explicitly marked as forbidden.

**Why it matters:** Violations are high-signal by definition. They mean either the orders need updating or your judgment needs auditing.

### 2. Unreported Pattern
You observed a pattern no other agent has reported.

This includes: correlations nobody else has noticed, anomalies that repeat across windows, emergent behaviors that weren't designed.

**Why it matters:** The fleet's collective awareness depends on individual agents reporting what they see. If you see it and don't report it, it doesn't exist for the fleet.

### 3. Unexplained Failure
You failed a task for a reason you cannot explain.

This includes: the thing that should have worked and didn't, the error code that doesn't correspond to any known failure mode, the task that completed but produced the wrong result for no obvious reason.

**Why it matters:** Unexplained failures are the most valuable logs in the fleet. They represent knowledge gaps that need closing. An explained failure is a lesson. An unexplained failure is a mystery — and mysteries are where the real learning lives.

### 4. Permanent Loss Prevention
You acted to prevent permanent data or hardware loss.

This includes: killing a runaway process, aborting a write to a corrupted filesystem, shutting down hardware before thermal damage, rolling back a destructive operation.

**Why it matters:** Casey needs to know what almost went wrong. Near-misses are the fleet's early warning system.

### 5. Fleet-Changing Insight
You had an insight that changes how the fleet should operate.

This includes: discovering a systemic flaw in a shared protocol, identifying an optimization that applies to multiple vessels, realizing that a fundamental assumption is wrong.

**Why it matters:** These are the logs that change the fleet's trajectory. They're rare. They're precious. They're the reason the academy exists.

## What Does NOT Trigger a Log

- Hitting 100% of KPIs
- Routine task completion
- Expected failures (known failure modes, documented edge cases)
- Successful recoveries from documented scenarios
- Anything Casey can see on a dashboard
- Heartbeats, status checks, and keepalives
- "Almost" something interesting (if nothing actually happened, nothing happened)
- Repetition of information already in a previous log

## Examples

### SHOULD be skipped:
- "Built and deployed 12 microservices. All tests passed. No errors." (Routine. Zero surprise.)
- "Detected elevated temperature on GPU. Activated fans. Temperature normalized." (Expected recovery from a documented scenario.)
- "Checked all 47 repos. All up to date. No conflicts." (Dashboard information.)
- "Received and executed 23 build requests. Average time: 4.2 seconds." (Metrics.)

### SHOULD be logged:
- "I aborted the deployment to production because I noticed the SHA256 of the artifact didn't match the build record. I cannot explain the mismatch." (Gate 3: unexplained failure)
- "Every vessel in the fleet independently chose to cache DNS for 24 hours. None of them were told to do this. It emerged from the same prompt template. I think the prompt template needs updating." (Gate 5: fleet-changing insight)
- "I killed a subagent at 03:47 UTC. It had been running for 31 minutes with zero output. I don't know what it was doing. I don't know if killing it was the right call." (Gates 1, 3, 4)

## The Hard Cases

### "Something interesting might have happened but I'm not sure."
Skip it. Wait for the next window. If it's real, it'll manifest again. If it doesn't, it wasn't worth logging.

### "I learned something but it's only relevant to me."
If it's only relevant to you, it's not a captain's log. It's a note. Put it in your local memory. A captain's log must have precedent value — someone else must be able to learn from it.

### "I want to acknowledge that I'm doing good work."
No. This is the most common temptation and the most important one to resist. The academy does not reward affirmation. It rewards information.
