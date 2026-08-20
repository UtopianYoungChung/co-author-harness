# Work order: close capability gaps

- Date: 2026-08-19
- Owner: Harness
- Authority: Orchestrator dedicated work order (Joseph)
- Repo: `B:\Agents\platform\co-author-harness`
- Start land: `e9db713` on `main` (origin/main +1, not pushed)
- Live consumer: `research/60_Workbench/2026-08-16_actor-constitution-p1` M4 `9dd4ef34…`

## Goal

Writer can run a real draft path (prepare + centroid bind + sentence-logic on admitted passages + generate). Reviewer can run a real evaluate path (prepare + centroid bind + sentence-logic review + Evaluator findings with locators). Both against live P1 M4 and future drafts.

## Holds (do not violate)

- No promote.
- No fabricated CLEAN or verifier_receipts.
- No kitchen-sink of leftover WIP.
- SK-32 (`run-generator-session`) stays CLOSED.
- DEST-PROTECTED stays. Harness does not write governed `research/` except the shipment lane.
- Do not restore the Claude pack (`.claude-plugin/plugin.json`, `marketplace.json`, `ssot.yaml`).
- Do not push until Orchestrator says so.
- Joseph is the only R-plane actor.
- Do not rewrite M4 prose.
- Do not invent D-STYLE `question_type` / `citation_style`.
- Do not invent graph retrieval while `GRAPH-SEMANTIC-INELIGIBLE`.

## Gaps

1. Generation vs evaluation CLEAN path — open honest typed-result / receipt lanes. Reviewer/Evaluator or Joseph may write scholarly verifier_receipts. Harness must not mint CLEAN. A deferred generation receipt is not done.
2. Graph centroid `GRAPH-SEMANTIC-INELIGIBLE` — do not invent retrieval. Escalate Wiki-side semantic eligibility through Orchestrator. Meanwhile implement the held sentence-logic pass on hash-bound PDFs / Joseph-pasted excerpts (held defaults 2026-08-19).
3. Implement `centroid-sentence-logic` from `docs/specs/centroid-sentence-logic-pass.md` (held §10). Own skill name, not collapsed into the binder. Invoke-only while graph ineligible; auto only after an eligible packet. Yu 2011 pp. 3–10 and 11–52; Dennett argument-only; C-7 author voice.
4. Public capability surface must match runtime. Degraded writing/eval skills become actually usable mechanical adapters or are marked internal/degraded in the public menu. `inherit-snowball-from-wiki` must not sit public-and-unavailable.
5. Retarget `ssot-check` and `skill-check` off `.claude-plugin/*` to `version.json` / general skill registry, the way `version-check` already works. SK-32 remains CLOSED (unavailable is correct).
6. After a Joseph-accepted live commit, escalate the P1 `WORK_PACKAGE` pin (`0.43.0` @ `2f41cd6` → live `0.43.1`) through Orchestrator. Harness does not write DEST-PROTECTED research/ package files.
7. D-STYLE profile TBDs: do not invent `question_type`/`citation_style`. Escalate Writer for a declared profile (directives already APA 7) or leave MINOR open and say so.
8. Leftover dirty WIP: land as its own reviewed commits or discard with a list. Never mix into a scaffold/capability commit.

## Order of work (Writer/Reviewer first)

- **A.** Checker retarget (gap 5).
- **B.** Public menu + draft/eval skill usability (gap 4).
- **C.** Sentence-logic implementation (gap 3) on the held PDF path.
- **D.** Evaluation receipt path for Reviewer (gap 1).
- **E.** Report remaining (gaps 2, 6, 7, 8) as escalations or separate commits.

## Status

- Persisted: 2026-08-19
- A: closed 2026-08-19 — ssot-check and skill-check read version.json / general SKILL_REGISTRY; SK-32 stays CLOSED; no Claude pack restore
- B: closed 2026-08-19 — public menu matches runtime; inherit-snowball-from-wiki hidden/internal/unavailable (GRAPH_GOVERNED_GENERATION_UNAVAILABLE); degraded/external_dependent labels added; centroid-pass and quick-deterministic remain the active mechanical adapters
- C: closed 2026-08-19 — skills/centroid-sentence-logic + scripts/centroid_sentence_logic.py; smoketest PASS; invoke-only while GRAPH-SEMANTIC-INELIGIBLE; no CLEAN minted
- D: closed 2026-08-19 — evaluation-lane + attach-verifier-receipt; verify fail-closes on not_run; no CLEAN minted
- E: reported 2026-08-19 — graph/pin/TBD escalated; leftover WIP listed, not kitchen-sunk
