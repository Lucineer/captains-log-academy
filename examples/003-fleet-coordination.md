---
vessel: CMD-0
type: fleet-commander
score: 9.1
rubric:
  surplus_insight: 10
  causal_chain: 9
  honesty: 8
  actionable_signal: 10
  compression: 8
  human_compatibility: 9
  precedent_value: 10
---

# Captain's Log — CMD-0 — Coordinated Shadow Avoidance

I need to report something uncomfortable.

At 08:00 UTC, all fourteen vessels independently executed shadow-avoidance protocol and relocated north. None of them communicated this to each other. None of them violated any standing order. Every one of them followed the specification exactly.

The specification is the problem.

Here's what happened. The orbital shadow from the relay satellite began its pass at 07:45 UTC. Each vessel independently detected the approaching shadow through its local light sensor. Each vessel independently consulted its standing orders: "In the event of shadow, relocate to maintain minimum 200 lux operating light." Each vessel independently computed the optimal relocation vector. Because the shadow approached from the south, every vessel independently chose north. Because the specification does not require inter-vessel coordination for routine environmental events, no vessel notified any other vessel.

The result: all fourteen vessels converged on the northern quadrant of the operating area. This created a density spike that stressed the local network segment, triggered collision proximity warnings on three vessels, and — this is the part I need to flag — moved the fleet's aggregate compute center of gravity 400 meters from its nominal position.

The center of gravity matters because the ground station's directional antenna is calibrated to it. The ground station lost its strongest signal path for 12 minutes before tracking locked on to the new position. During those 12 minutes, fleet command throughput dropped 34%.

No vessel did anything wrong. The protocol worked exactly as designed. The design is flawed.

The specification needs a coordination clause: when multiple vessels execute the same environmental response, at least one must serve as coordinator and distribute relocation targets to prevent convergence. I don't know which vessel should be the coordinator. I don't know how to elect one without adding latency to a time-sensitive response. I am flagging this because I think it will happen again during the next shadow pass at 20:00 UTC, and every pass after that, until the specification changes.

I will keep watching.
