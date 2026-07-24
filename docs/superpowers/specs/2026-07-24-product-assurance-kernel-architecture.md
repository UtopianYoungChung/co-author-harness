# Product-Assurance Kernel Architecture

**Status:** implementation contract for the 2026-07-24 harness-failure remediation.

## 1. Problem boundary

The prior runtime proved that a role received policy bytes, but allowed that
receipt to stand in for evidence that the resulting prose was conditioned,
grounded, citation-accurate, register-fit, and independently evaluated. The
replacement architecture separates five claims and gives each one a distinct
machine-checkable artifact:

1. **binding resolved** -- policy, pins, members, target, and exact bytes;
2. **sources extracted** -- canonical text derived from each bound source;
3. **semantic execution** -- passages actually used by one role dispatch;
4. **product assurance** -- quotes, citation identities, corpus-relative
   language, and empirical-claim candidates checked against the exact draft;
5. **mutation authority** -- every sanctioned manuscript write linked by a
   preimage/postimage hash-chain.

No artifact proves a later claim in this list merely because an earlier claim
passed. In particular, binding resolution is deliberately named
`binding_resolved`, never `ready` or `conditioned`.

## 2. Kernel and adapters

`scripts/product_assurance.py` is the single semantic-evidence kernel. It owns
normalization, quote containment, citation-label identity, corpus lexicon
construction, and four deterministic candidate detectors. It emits one
schema-defined report bound to the manuscript and semantic receipt.

Source extraction is an adapter boundary. `scripts/source_extract.py` uses
`pdftotext` for PDFs and exact UTF-8 reads for text sources, records tool
identity and source/output hashes, and fails closed when extraction is
unavailable. A library extractor may be recorded as corroboration, but a lone
library extraction is not canonical PDF evidence.

`scripts/run_product_gate.py` is the operational adapter. It accepts explicit
project, wiki, and workspace roots and runs the normal product gate in one
command. It does not create authority or widen output destinations.

The destination-capability kernel discovers a routing manifest from both the
plugin package and the intended destination. This makes an installed cache
operational against a governed workspace while keeping authority bound to the
destination itself: process cwd is never consulted, protected paths remain
protected, and destinations with no discoverable manifest remain
`DEST-UNGOVERNED`.

## 3. Product checks

The kernel distinguishes hard evidence failures from adjudication candidates.

- `QUOTE-*` and `CITATION-*` are hard failures. A recorded quote must occur in
  its hash-bound canonical extract. Same-author/year suffixes are derived from
  the alphabetic order of recorded titles and must match the label attached to
  the quote in the manuscript.
- `TERM-COINAGE`, `REGISTER-ABSENT`, `INSIDER-NEGATION`, and
  `EMPIRICAL-UNSUPPORTED` are candidates. A visible `[S]` marker is an explicit
  ownership/adjudication signal, not a claim that the corpus supplied the
  language. Unmarked candidates block the product gate until the Evaluator
  adjudicates them in the report; the kernel never rewrites prose.
- Grounding and register are separate dimensions. Corpus absence cannot be
  converted into grounding merely because a term is owned, and ownership
  cannot be converted into centroid register-fit merely because it is valid
  synthesis.

## 4. Role and write invariants

Generation and evaluation receipts bind distinct actor and dispatch IDs. The
Evaluator receipt binds the verified generation envelope. Both also bind a
passing product-assurance report for the same manuscript bytes.

The assignment writer appends a mutation row for every published target. Each
row records receipt/reservation IDs, mode, preimage, postimage, and the hash of
the previous row. Milestone record/accept and terminal validation compare the
live manuscript to the latest row. A direct edit therefore creates an explicit
`APG-MUTATION-UNJOURNALED` refusal instead of a latent byte discontinuity.

## 5. State recovery

When policy canon differs from a project binding, the resolver classifies the
delta. If the current request is present, no round is open, and the transaction
is otherwise admissible, the response is `PROJECT_BINDING_REBIND_AVAILABLE`
and includes the exact Planner-owned command. Conflicts and unreadable state
retain separate refusal codes. A bare stale code is not an operator interface.

## 6. Migration and release rule

Legacy `status: ready` packets remain readable only for diagnosis. New
generation or evaluation evidence must use `binding_resolved`. Existing
projects gain mutation authority on their next sanctioned assignment write;
until then, terminal claims require an explicit migration anchor rather than an
invented history. The plugin is not deployable until synthetic regressions,
the fixture registry, release gate, packaged ZIP, and installed-cache runtime
all exercise this architecture.
