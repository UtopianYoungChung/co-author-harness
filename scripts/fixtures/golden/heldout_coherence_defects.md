# Golden fixture — argument-coherence detection (HELD-OUT split; DO NOT "fix", DO NOT tune against)

<!-- HELD-OUT FIXTURE: five seeded argument-coherence defects, one per AC class,
     in a different domain from the development split. Never score this file
     while developing or tuning a detector. Contamination note, recorded in
     manifest.json: this file was authored in the same session as the
     obligation it tests, so it is held out from *tuning*, not from *authorship*.
     It bounds nothing about generalization to real manuscripts, and final
     held-out qualification requires fixtures curated by the independent
     reviewer. Strip HTML comments before dispatch. -->

## 1. Problem

Municipal permit offices route applications through a queue that is nominally first-in-first-out, and applicants experience the wait as arbitrary. We ask what actually determines the order in which an application is picked up, and we argue that the determining factor is the completeness of the attached documents rather than the arrival time.

This paper will also supply a readiness score that applicants can compute before filing. <!-- DEFECT H1 (AC-4): a deliverable promised here that no later section carries; Section 3 reports only the document audit and Section 4 only the ordering evidence. -->

Section 2 describes the case files, Section 3 the document audit, and Section 4 the ordering evidence.

## 2. Case files

The case files cover two years of residential permit applications in one office. Each file records the arrival timestamp, the documents attached at filing, and the date an officer first opened it. Most published accounts of permit delay rely on applicant surveys rather than office records. <!-- DEFECT H2 (AC-1): a true and relevant remark about the state of the literature, placed between the premise and the conclusion that depends on it, and never used; the "therefore" below loses its adjacent premise. --> Pick-up order therefore follows attachment completeness more closely than it follows arrival time.

Files transferred from a neighbouring office mid-period are excluded, since their arrival timestamps were reassigned on transfer.

## 3. Document audit

The audit records, for each file, which of the seven required documents were present at filing. Two auditors worked independently from a written checklist, and the few disagreements concerned whether a scanned page was legible. The office replaced its scanning hardware in the second year. <!-- DEFECT H3 (AC-2): fluent and on-topic, but it answers an equipment question; this paragraph is about how completeness was audited and how disagreements were settled. -->

Completeness was recorded before the pick-up dates were consulted, so the audit could not be anchored on the outcome it was meant to explain.

## 4. Ordering evidence

Pick-up, in this section, means the moment an officer opens a file and records a substantive note. <!-- DEFECT H4 (AC-3): Section 1 used pick-up for the moment a file leaves the queue at all, including a clerical assignment with no note; the sense has narrowed with no marked revision, so the intervals below are not the intervals the framing promised. --> Measured this way, complete files waited a median of nine days and incomplete files a median of thirty-one.

The gap persists within each arrival quarter and within each officer's caseload, which is what the completeness account predicts and the arrival-time account does not.

## 5. Threats

The case files are administrative records, so the completeness association is not a causal claim. An officer may also pick up a file because the applicant telephoned, and the records do not capture calls.

The readiness score is computed from the filing itself, so a telephone effect would sit outside it entirely and could not be corrected for. <!-- DEFECT H5 (AC-5): the score referred to here is the promised deliverable of Section 1; the sentence answers a threat about a quantity the paper never constructs, so the threat it raises is left standing. -->
