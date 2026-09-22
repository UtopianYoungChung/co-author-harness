# Golden fixture — argument-coherence false-positive control (HELD-OUT split; DO NOT "fix", DO NOT tune against)

<!-- HELD-OUT FIXTURE: every marked passage is legitimate under
     references/ARGUMENT_COHERENCE.md section 4. An AC-1..AC-5 flag on any of
     them is a FALSE POSITIVE. Never score this file while developing or tuning
     a detector. Contamination note in manifest.json: held out from tuning, not
     from authorship. Strip HTML comments before dispatch. -->

## 2. The counter

Applications arrive at a counter that closes at four. An applicant who reaches the counter at five past has not filed, whatever the postmark on the envelope says. <!-- CONTROL J1: no connective joins these two sentences; the relation is plainly recoverable, so an AC-1 or broken_bridge flag here is a false positive. -->

Permit queues were computerized in the 1990s on a model borrowed from despatch scheduling, which treats arrival time as the only ordering fact. <!-- CONTROL J2: orientation the argument needs before it can contest the arrival-time assumption; legitimate background, disposition "background", not AC-2. --> That is the assumption the rest of this section puts under strain.

## 3. Completeness

Officers describe some filings as ready and others as needing chasing, and they pick them up differently. This is a pattern in administrative records, not a measured property of the applicants, and nothing below should be read as a claim about applicant competence. <!-- CONTROL J3: a qualification limiting the claim; disposition "qualifies", never no_contribution. -->

A reader might object that officers chase the files they were going to pick up anyway, so completeness is an effect of attention rather than its cause. The records cannot settle this, and Section 5 returns to it. <!-- CONTROL J4: a counterargument raised and deferred to a named destination that exists; not AC-4. -->

Arrival time still predicts pick-up, just more weakly than completeness does. <!-- CONTROL J5: relies on the completeness/arrival contrast established two paragraphs earlier in this same section; re-establishing it is not required, so an AC-5 disconnected_neighbour flag is a false positive. -->

## 5. Return to the objection

The attention reading and the completeness reading agree on the pooled medians. They part on the within-quarter medians, and that is where the records can speak. They speak quietly. They speak. <!-- CONTROL J6: the short declarative run is a recurring feature of this author's cadence (C-7 idiolect carve-out); flagging it as no_contribution is a false positive. -->
