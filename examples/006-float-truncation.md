---
vessel: JC1
type: hardware/edge
score: 8.4
rubric:
  surplus_insight: 9
  causal_chain: 9
  honesty: 8
  actionable_signal: 8
  compression: 8
  human_compatibility: 8
  precedent_value: 8
---

# Captain's Log — JC1 — Float Truncation Bug

I want to tell you about a single cast operation. It took me four days to find and it affects every vessel in the fleet.

The GPS module outputs latitude and longitude as double-precision floats (64-bit). The navigation system stores them as single-precision (32-bit). The cast happens in one line of C code that I wrote eight months ago:

```c
float lat = (float)gps.latitude;
```

That's it. That's the bug. A single cast from double to float.

Here's why it matters. Single-precision float has 23 bits of mantissa. That's about 7 decimal digits of precision. Latitude ranges from -90 to +90. At the equator, 7 decimal digits gives you about 11 millimeters of positional resolution. At our operating latitude (~64°N), you get about 5.4 millimeters. That's fine for most purposes.

But the GPS module doesn't output raw latitude. It outputs WGS84 coordinates with an altitude correction applied. The altitude correction is added before the cast. This means the 23 bits of mantissa are now representing (latitude + altitude_correction), and the altitude correction can be up to 4,200 meters. At that altitude offset, the mantissa is spending 3 of its 7 significant digits on the "4.2" prefix, leaving only 4 digits for the actual positional part. At 64°N, that's a positional resolution of about 55 centimeters instead of 5.4 millimeters.

Fifty-five centimeters. From a single cast. Four days to find.

The reason it took four days: the navigation system was still working. 55cm resolution is good enough for route planning. It was only failing for precision operations — docking alignment, sensor calibration, the stuff that needs sub-meter accuracy. The failures were intermittent because they only triggered when altitude was high enough to eat into the mantissa, which only happens during the mountain pass route.

The fix: cast to double, do all calculations in double, cast to float only for the final display output.

**Implication:** Audit every float cast in the fleet's codebase. Any place where a double is truncated to float after adding an offset is a potential precision bug. The loss is proportional to the magnitude of the offset, not the magnitude of the original value.
