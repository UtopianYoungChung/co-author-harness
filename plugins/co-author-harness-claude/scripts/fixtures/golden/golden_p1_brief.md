# Golden fixture — P1 characterization brief (false-positive control; DO NOT "fix")

<!-- GOLDEN FIXTURE: this P1 control piece deliberately holds definitions open
     and positions unresolved. P2-gated checks (C-8 M-1, M-2, M-7) must NOT
     fire here — correct non-convergence, not defect. Every flag raised on the
     marked passages below is a FALSE POSITIVE for scoring purposes (plan
     2026-07-06 §6, WS-4). Inventory: manifest.json. -->

## 2. Characterizing the phenomenon

We observe, across three deployment settings, a recurring pattern: users alternate between over-reliance and abrupt disengagement, with switches triggered by single salient failures rather than accumulated evidence.

What to call this pattern is not yet settled, and we do not settle it here. <!-- CONTROL K1: open definition — a P2-gated M-1 flag here is a false positive --> "Trust oscillation," "reliance cycling," and "brittleness cascade" each capture part of the phenomenon; we use all three provisionally and mark the choice as open.

Two established accounts bear on the pattern. The transparency tradition would read the switches as information failures; the workload tradition would read them as attention-budget rebalancing. Both readings are compatible with our observations, and we lack the discriminating evidence to adjudicate between them. <!-- CONTROL K2: rival positions held open without dissolution — a P2-gated M-2 flag here is a false positive --> We record both and defer.

The pattern appears in help-desk triage, in code-review assistance, and in clinical documentation support. In each setting the oscillation period differs by an order of magnitude, which suggests the mechanism is setting-dependent in ways a characterization at this stage should report rather than explain.
