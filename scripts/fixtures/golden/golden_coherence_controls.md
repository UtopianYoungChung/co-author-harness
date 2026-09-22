# Golden fixture — argument-coherence false-positive control (development split; DO NOT "fix")

<!-- GOLDEN FIXTURE: every marked passage below is legitimate under
     references/ARGUMENT_COHERENCE.md section 4. An AC-1..AC-5 flag on any of
     them is a FALSE POSITIVE for scoring purposes. These are the passages a
     reviewer over-applying the obligation will reach for: an unmarked
     transition, honest background, a qualification, a counterargument, a
     relation established earlier in the section, and the author's own
     cadence. Inventory: manifest.json. Strip HTML comments before dispatch. -->

## 2. Setting

Triage work is bounded by the shift, not by the queue. A reviewer who leaves an alert unopened at the end of a shift hands it to someone who did not see it arrive. <!-- CONTROL K1: no connective joins these two sentences; the relation is plainly recoverable, and an AC-1 or broken_bridge flag here is a false positive. -->

Maintenance alerting systems emerged from process-control telemetry in the 1980s and inherited its assumption that severity is an intrinsic property of an event. <!-- CONTROL K2: orientation the argument needs before it can contest the severity assumption; legitimate background, disposition "background", not AC-2. --> That assumption is what the rest of this section questions.

## 3. Confidence

Reviewers describe some sensors as trustworthy and others as noisy, and they escalate differently across the two. This is an association in free-text notes, not a measured property of the sensors themselves, and nothing below should be read as a claim about sensor accuracy. <!-- CONTROL K3: a qualification that limits the claim; disposition "qualifies", never AC-2 or no_contribution. -->

A reader might object that confidence talk is a post-hoc rationalization of a decision already made on other grounds. The objection is not answered by the corpus, and we return to it in Section 5. <!-- CONTROL K4: a counterargument raised and deferred with a named destination; legitimate, not AC-4 promise_without_payoff, because Section 5 carries it. -->

The severity band still predicts escalation, just more weakly than confidence does. <!-- CONTROL K5: relies on the severity/confidence contrast established two paragraphs earlier in this same section; re-establishing it is not required, and an AC-5 disconnected_neighbour flag here is a false positive. -->

## 5. Return to the objection

The post-hoc reading and the confidence reading make the same prediction for the pooled rates. They diverge on the within-band rates, and the within-band gap is where the corpus can speak. It speaks weakly. It speaks. <!-- CONTROL K6: the short declarative run is a recurring feature of this author's cadence (C-7 idiolect carve-out); flagging it as no_contribution is a false positive. -->
