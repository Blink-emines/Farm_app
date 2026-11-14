---
name: rotation-agronomy
description: Principles and rules for scoring crop rotations transparently. Use whenever working in engine/ or explaining a strategy.
---
# Rotation scoring principles

## Core rules (each one a named, testable function)
1. Legume after cereal → nitrogen credit (N-fixation).
2. Avoid the same crop family in consecutive seasons → pest/disease-cycle break.
3. Deep-rooting crop in the rotation → structure/infiltration benefit.
4. Fill bare-field months with a cover crop → erosion + organic-matter benefit.
5. Crop water demand must match the rainfall season (water balance from
   features.json); penalize irrigation-dependent crops if water is scarce.
6. Frost/heat tolerance vs frost-day and heat-day climatology.

## Every strategy output includes
why (rules triggered), evidence (feature values + dataset), benefits,
information gaps, risks for local review, confidence (low/med/high).

## Honesty rules
- Unknown crop parameter → write "unknown, needs local data". Never invent numbers.
- Use FAO-56 crop coefficients (Kc) for water demand and cite them.
- Scores are relative comparisons, not yield predictions. Say so in the UI.
- A strategy is an option to discuss with local experts, never an order.
