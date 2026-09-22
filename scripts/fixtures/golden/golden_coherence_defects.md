# Golden fixture — argument-coherence detection (development split; DO NOT "fix")

<!-- GOLDEN FIXTURE: synthetic prose written for this fixture. Five seeded
     argument-coherence defects, one per AC class, with sound neighbours. Every
     sentence here is grammatical, on-topic, and mechanically clean: the whole
     point is that no deterministic pattern reaches these defects. Inventory:
     manifest.json. A scored run must be produced WITHOUT showing the reviewer
     agent these markers — strip HTML comments before dispatch. -->

## 1. Introduction

Maintenance teams receive more alerts than they can act on, and the order in which they act is not the order the alert severities imply. We ask how a reviewer decides which alert to escalate, and we argue that the deciding factor is the reviewer's confidence in the upstream sensor rather than the severity the alert carries.

We will deliver a calibration instrument that practitioners can apply to their own alert streams. <!-- DEFECT D1 (AC-4): a deliverable is promised here and no later section carries it - Section 3 describes only the observational study, and Section 4 evaluates only the confidence claim. -->

The argument proceeds in three steps. Section 2 sets out the corpus, Section 3 the coding scheme, and Section 4 the evidence for the confidence claim.

## 2. Corpus

The corpus covers eleven months of triage records from three maintenance sites. Each record pairs an alert with the reviewer's disposition and a free-text note. Prior work on alert fatigue is largely survey-based rather than observational. <!-- DEFECT D2 (AC-1): a true, relevant source-status aside dropped between the premise and the conclusion that depends on it; the aside is never used, and the "therefore" below now stands on nothing adjacent. --> Escalation therefore tracks the reviewer's stated confidence in the sensor more closely than it tracks the alert's severity band.

Site B contributed roughly twice the volume of the other two sites, so the per-site rates below are reported separately as well as pooled.

## 3. Coding scheme

The scheme assigns each triage record a confidence code drawn from the reviewer's free-text note. Two coders applied the scheme independently, and disagreements were resolved by discussion rather than by a third coder. Reviewers at Site C rotate on a fortnightly roster. <!-- DEFECT D3 (AC-2): fluent and on-topic, but it answers a staffing question this paragraph is not asking; the paragraph is about how codes were assigned and reconciled. -->

Codes were assigned before the disposition field was read, so the coding could not be anchored on the outcome it was meant to explain.

## 4. Evidence

Escalation, as we use it here, is the act of moving an alert to a named owner. <!-- DEFECT D4 (AC-3): Section 1 used escalation for acting on an alert at all, including routing to an unowned queue; the sense has narrowed with no marked revision, and the counts below are not comparable to the framing above. --> Under this reading, 41 per cent of high-severity alerts were escalated, against 63 per cent of the alerts whose sensor the reviewer described as reliable.

The gap holds within each severity band and within each site, which is what the confidence account predicts and the severity account does not.

## 5. Threats

The corpus is observational, so the confidence association is not a causal claim. A reviewer's stated confidence may itself be a reconstruction offered after the disposition was chosen.

The instrument records the reviewer's note verbatim, so a reconstruction of this kind would be preserved rather than smoothed away. <!-- DEFECT D5 (AC-5): "the instrument" here is the recording apparatus of Section 2; after the Section 1 edit that introduced a promised calibration instrument, this untouched sentence now reads as referring to that deliverable, and the threat it answers no longer connects. -->
