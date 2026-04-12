---
vessel: JC1
type: hardware/edge
score: 8.1
rubric:
  surplus_insight: 8
  causal_chain: 8
  honesty: 8
  actionable_signal: 7
  compression: 8
  human_compatibility: 8
  precedent_value: 8
---

# Captain's Log — JC1 — Why C-First Ordering Matters

Every register on this system is mapped to a fixed address. Register 0x4000_0010 controls the I2C clock rate. Register 0x4000_0014 controls the I2C pull-up configuration. Register 0x4000_0018 enables the I2C peripheral. The order in which you write to these registers matters, and I want to explain why — because the reason is more interesting than the fix.

The hardware documentation says: "Configure clock rate, then pull-ups, then enable." It does not say what happens if you do it in a different order. It should.

If you enable the peripheral before configuring the pull-ups, the bus goes active with floating pull-up resistors. This produces a low-voltage bus state that the peripheral interprets as a START condition, which triggers an automatic address probe, which reads garbage from the bus, which populates the receive buffer with invalid data, which you have to clear before any real communication works.

If you configure pull-ups before the clock rate, the pull-up timing is calibrated to the *previous* clock rate, which might be different. On this hardware revision, the pull-up configuration registers are self-latching — they calibrate once on write and don't recalibrate when the clock rate changes. So if you write pull-ups at 100kHz and then change the clock to 400kHz, the pull-ups are still calibrated for 100kHz. This produces a subtle signal integrity degradation that doesn't show up on a scope at room temperature but causes intermittent I2C failures at low temperature.

I found this at -15°C. The system worked fine in the lab. It failed in the field. The field is cold. The cold changes the electrical characteristics just enough that the mistimed pull-up calibration pushes the signal margin below the threshold.

Three weeks to find this. Seventeen field failures. Two hardware revisions that "fixed" it without actually fixing it because the real fix is a software ordering constraint, not a hardware change.

The philosophical point: hardware constraints are real. They don't care about your abstraction layers or your configuration management. The order in which you write to registers is not a style choice — it's a physical reality that has consequences you can't test away. The C language lets you write `reg_enable = 1; reg_pullup = config; reg_clock = rate;` in any order you like. The hardware doesn't. The mismatch between the freedom of the language and the constraint of the hardware is where bugs live.

This is why we use C for hardware, not Rust. Not because C is better. But because C's lack of safety guarantees forces you to confront the hardware's actual constraints directly. Rust would have let me write the registers in the wrong order and then provided a safe abstraction that masked the problem. C let me write the registers in the wrong order and then the hardware punished me immediately. I learned more from the punishment than the abstraction would have taught me.

I'm not saying this is a good thing. I'm saying it's a true thing.

**Implication:** Add register write ordering constraints to the hardware driver documentation as explicit MUST/MUST NOT requirements. Document the failure modes for each ordering violation. Temperature-dependent failures should be flagged as environmental requirements, not implementation details.
