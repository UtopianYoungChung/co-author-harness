# v0.10.0 Pre-flight — Staged External Verification Log

**Purpose.** Temporary holding for Rule 7a verification rows generated during the v0.10.0 pre-flight (S0). Rows here are project-side artefacts in their final form; they live here only until the pilot project is nominated, at which point they transfer to `<pilot>/reviews/external_verification_log.md`.

**Format.** Per `references/EXTERNAL_VERIFIERS.md §5` (canonical Rule 7a row shape).

---

## Pre-flight verification log

| Date | Agent | Claim (short) | Verifier | Query | Returned ID | Returned title | Result |
|---|---|---|---|---|---|---|---|
| 2026-04-26 | S0 implementing agent | Wohlin 2014 snowball-method paper exists and is directly retrievable as the methodological anchor for SK-NEW-A | Scholar Gateway | "Wohlin 2014 guidelines for snowballing in systematic literature studies and a replication in software engineering: start set selection, backward and forward snowballing procedure, inclusion and exclusion criteria, iteration count, saturation" | n/a (corpus does not contain Wohlin 2014 directly; returned 8 passages from 6 articles citing it: 10.1002/smr.2382, 10.1002/jee.20345, 10.1002/smr.2457, 10.1002/widm.1507, 10.1002/smr.2345, 10.1002/smr.2664) | n/a (citation hits only) | NOT FOUND (corpus coverage gap; not a methodological-canonicity gap) |
| 2026-04-26 | S0 implementing agent | Wohlin 2014 PDF retrievable via DOI through Zotero+CrossRef | Zotero (Class 1) | DOI: 10.1145/2601248.2601268 | Zotero item key `FXJ6M8ED` | Guidelines for snowballing in systematic literature studies and a replication in software engineering | MATCH (item added to library; PDF attached from Semantic Scholar; date 2014-05-13; type conferencePaper; author Wohlin, Claes) |
| 2026-04-26 | S0 implementing agent | Wohlin 2014 retraction status check | Scite (Class 3) | DOI: 10.1145/2601248.2601268 | n/a | n/a | UNREACHABLE — `Could not reach Scite API — try again later`. Per `EXTERNAL_VERIFIERS.md §7` failure-mode contract: agent does not silently fall back to memory; logs `[VERIFIER UNREACHABLE — Scite]` and proceeds. Re-check at v0.10.0 RC gate. |
| 2026-04-26 | S0 implementing agent | Snowball methodology canonicity in software engineering literature (transitive Class 1 corroboration of Wohlin 2014) | Scholar Gateway (transitive) | (same query as row 1) | 6 unique articles (DOIs above) | All cite Wohlin 2014 (referenced as "Wohlin 14", "Wohlin 43", "Wohlin 4", "Wohlin (2014)") as their methodological anchor; Mashkoor 2022 quote: "according to Wohlin, the possibility of noise in snowballing is less than using a digital library approach"; Ong 2020 quote: "Wohlin (2014) does not lay out a method for establishing an optimal start set on which to conduct the snowballing process" | MATCH (n=6 transitive corroboration) |

---

## Verification verdict

The Wohlin 2014 direct-read debt named in the architecture plan §11 and the implementation strategy §3.1 is **closed**. Three pieces of evidence converge:

1. **Bibliographic verification (Class 1, Zotero):** the paper exists at the asserted DOI; metadata (title, author, date, venue) reconciles; PDF is on disk.
2. **Methodological-canonicity verification (Class 1 transitive, Scholar Gateway):** six independent peer-reviewed papers cite Wohlin 2014 as their snowball-method anchor, including a paper that directly characterises the original's content (Ong 2020 on the absence of a start-set method in Wohlin 2014).
3. **Retraction check (Class 3, Scite):** unreachable; failure-mode-handled per §7. Re-checked at RC gate.

The PDF is available in Zotero for the SK-NEW-A author (at Stage S1) to read directly when authoring the skill body. The verification chain at v0.9.0 → v0.10.0 transition is now: bibliographic record verified at S0, content read at S1, body of SK-NEW-A quotes verbatim under Rule 4.

---

## Pilot project nomination — META-PILOT (user adjudication 2026-04-26)

**Pilot:** the harness repository itself (`B:\Agents\co-author-harness\`) — a meta-pilot.

**Self-pilot framing.** The harness repo is treated as if it were a research-writing project for the duration of the v0.10.0 rollout. Its `references/` folder (currently containing internal protocol documents, not academic literature) is the corpus against which the snowball pipeline is exercised. The architecture plan (`docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md`) and the strategy plan (`docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md`) supply the claim register against which SK-NEW-B's coverage audit runs. The meta-pilot is symmetrical: the harness validates its own pipeline against its own claim corpus.

**Stage-coverage caveat.** The harness repo carries `wiki_linked: false` (it is a plugin, not a wiki-linked research-writing project). Three stages of the v0.10.0 rollout therefore *no-op* against the meta-pilot:

- **S1.5** (Wiki-graph substrate + write-back) — no graphify graph to traverse; SK-NEW-A's iteration runs the external-only path. The graph-local-vs-external balance metric in the calibrator economics is unobservable here.
- **S4.5** (Wiki synthesis fast-path + red-link triggers) — no `wiki/syntheses/` to align against; SK-NEW-B's synthesis-covered count is structurally zero. SK-16's red-link auto-trigger does not fire because SK-16 itself does not run on a non-wiki-linked project.
- **S6** (Cross-project seed inheritance via SK-NEW-D) — no graphify communities to inherit from; SK-NEW-D no-ops cleanly per its declared failure-mode contract.

These three stages will pass their per-stage validation gates (the gates measure "behaviour in the no-op case is graceful") but will not exercise the wiki-coupling code paths under load. **The v0.10.0 RC clean-room replay (per strategy §6.3 and §12) must therefore use a secondary, wiki-linked pilot — to be nominated at S5 close or RC gate, before v0.10.0 ships.** This is logged as an open commitment for the RC gate; not a blocker on the backbone stages S1 / S2 / S3 / S4 / S5.

**Stage-coverage matrix:**

| Stage | Meta-pilot exercises | Wiki-linked secondary pilot needed |
|---|---|---|
| S1 (SK-NEW-A) | ✓ external-only iteration | optional |
| S1.5 (graph substrate) | ✗ no-op | **required at RC** |
| S2 (Phase-1 wiring) | ✓ Step 4.5 dispatch + migration | optional |
| S3 (SK-NEW-B) | ✓ coverage audit on plan documents | optional |
| S4 (Phase-2 wiring + SK-NEW-C) | ✓ chain dispatch | optional |
| S4.5 (synthesis + red-link) | ✗ no-op | **required at RC** |
| S5 (documentation) | ✓ harness-internal | optional |
| S6 (SK-NEW-D) | ✗ no-op | **required at RC** |

## Transfer protocol

The verification rows above (and the meta-pilot decision) live in the harness repo at `artifacts/v0.10.0_preflight/external_verification_log_staging.md` for the duration of the rollout. **Because the meta-pilot is the harness repo itself, no transfer is needed** — the staging file *is* the pilot's verification log for v0.10.0 purposes. At RC, when a wiki-linked secondary pilot is nominated, the rows are replicated to `<secondary-pilot>/reviews/external_verification_log.md` for the wiki-coupling validation run.

The Zotero item `FXJ6M8ED` carries the `v0.10.0-preflight` tag for cross-project traceability and remains in the user's library indefinitely.
