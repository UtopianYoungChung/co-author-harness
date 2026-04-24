---
name: tool-contract-roundtrip
description: Round-trip probe of every external-verifier MCP before a package release — invoke each advertised tool, inspect response payloads for undocumented contract fields, and surface placeholder namespaces, stale UUIDs, and referenced-but-unexercised tools. Use this before bumping the plugin version, when adding a new verifier, or when a runtime namespace mismatch is suspected.
trigger: when the user asks to verify external-tool contracts, probe MCPs before a release, round-trip-test the verifier tier, or is preparing a plugin version bump that touches EXTERNAL_VERIFIERS.md
created_by: Reflector
created_from: v0.3.3 integration analysis addendum — placeholder-namespace and missing render-contract defects were both instances of EXTERNAL_VERIFIERS.md referencing a tool without invoking it
pattern_source: GROUNDING_PROTOCOL.md Rule 1 and Rule 4 applied reflexively to the plugin's own advertised tool surface
version: 1.0
---
# Tool-Contract Round-Trip Test

You are running a pre-release round-trip test of the plugin's external-verifier tier. This skill reflexively applies Rule 1 (read-before-cite) and Rule 4 (verify-before-reference) to the plugin's own tool surface — every verifier the plugin references must be invoked, every response payload must be inspected, and every undocumented contract field must be surfaced before the plugin ships.

**The defect class this closes.** In v0.3.2 the plugin shipped with two defects of the same shape. First, `EXTERNAL_VERIFIERS.md` referenced `mcp__*__semanticSearch` as a placeholder that was never replaced with the runtime namespace — because the tool was referenced but not invoked. Second, Scholar Gateway's responses carry a mandatory `render_contract` v0.1 that the plugin did not honour — because the response payload was never inspected. Both defects were instances of the harness violating the rules it imposes on manuscripts: *cite only what you have read; reference only what you have verified.* This skill prevents recurrence by making a full round-trip the gate on every release.

---

## When to run this skill

Run before any of the following:

1. **Version bump that touches `EXTERNAL_VERIFIERS.md`.** Mandatory. No release is valid without the round-trip report.
2. **Adding a new verifier to the registry.** Mandatory. A new Class 1/1.5/2/3 verifier must be invoked successfully before its row lands in the tier table.
3. **Verifier MCP schema version change.** When a verifier reports a new version in its response, re-run to catch added fields (new contracts, new disclosures).
4. **Runtime-namespace drift suspected.** If `EXTERNAL_VERIFIERS.md` references a `mcp__<uuid>__<tool>` form but a session's tool list shows a different UUID, re-run to re-pin the namespaces.
5. **Quarterly hygiene sweep.** Regardless of release cadence, run once per quarter to catch silent schema evolution in any connected verifier.

Do **not** run during routine manuscript review. This skill probes the plugin's infrastructure, not the manuscript under review. Its findings feed `EXTERNAL_VERIFIERS.md` and the integration analysis, not `reviews/consolidated_findings_report.md`.

---

## What you read

1. `${CLAUDE_PLUGIN_ROOT}/references/EXTERNAL_VERIFIERS.md` — the authoritative list of referenced verifiers, their declared tier, and their advertised tool namespaces.
2. `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` — the current version and the verifier-related description text that must stay truthful after the probe.
3. `${CLAUDE_PLUGIN_ROOT}/README.md` — the user-facing version changelog, which will receive a compliance line per release.
4. The live MCP registry via `mcp__mcp-registry__search_mcp_registry` for each verifier keyword — produces the `directoryUuid` and `connected` state.
5. The session's tool list — used to confirm runtime namespaces against the registry entries.

## What you write

1. `reviews/tool_contract_probe_<YYYY-MM-DD>.md` in the plugin's scratch area (or in a project's `reviews/` if invoked inside a project session). Append-only — new probes do not overwrite old ones.
2. A concise findings block in the session response listing all detected defects with severity tags (per the severity schedule below).

## What you do NOT write

- **Do not edit `EXTERNAL_VERIFIERS.md` or `plugin.json` unilaterally.** This skill reports; the user approves; the Generator applies. The only exception is the probe report itself, which is a fresh artifact.
- **Do not clear `[UNVERIFIED]` markers on manuscripts using probe results.** This skill tests the plugin's own tools; it is not a Rule 7a verifier for manuscript claims.
- **Do not invoke a verifier's paid-quota-consuming path during the probe unless the user explicitly authorizes it.** A whoami-class call is sufficient for contract inspection on most tools; reserve a full search only for verifiers whose contract fields appear only in search responses (Scholar Gateway's `render_contract` is in the search response, not a whoami call — so a minimal search is required for Scholar Gateway).

---

## Procedure

### Phase 0 — Manifest self-probe (v0.4.1)

Before probing any external tool, apply Rule 1 and Rule 4 reflexively to the plugin's **own manifest fields**. The failure mode this closes was observed in v0.4.0: the Cowork plugin validator enforces an undocumented length cap on `plugin.json.description`, and three validator round-trips were spent before the cap was inferred empirically.

Compute the empirical distribution of length-bounded manifest fields across every plugin installed under `/sessions/<session>/mnt/.remote-plugins/*/` (or the equivalent install root on the host). For each field, measure the current plugin's value against the peer distribution.

```bash
# Illustrative helper — full implementation in scripts/release-gate.sh
for p in /sessions/*/mnt/.remote-plugins/*/.claude-plugin/plugin.json; do
  python3 -c "import json; d=json.load(open('$p')); print(len(d.get('description','')))"
done | sort -n
```

Record the following in the probe report (inserted as §0 ahead of §1 Inventory):

```
## 0. Manifest self-probe
| Field | Current length | Peer min | Peer p50 | Peer max | Verdict |
|---|---|---|---|---|---|
| plugin.json.description | <n> | <min> | <median> | <max> | OK / WARN / BLOCKER |
| <skill>.SKILL.md.description (each) | <n> | <min> | <median> | <max> | OK / WARN / BLOCKER |
```

Verdicts:

- **OK** — current length ≤ peer p75.
- **WARN** — current length > peer p75 and ≤ peer max. Record; the release may proceed but the field should be trimmed before the next release.
- **BLOCKER** — current length > peer max. Release is held until the field is trimmed. This is the exact defect class that shipped in v0.4.0 before the three-round-trip recovery.

Phase 0 is **mandatory before every release**, and completes in seconds. It must pass before Phase 1 begins. This is the reflexive analogue of Rule 4 applied to the plugin's *own* advertised presentation surface: the plugin's manifest is part of what it asks the host to accept, and "accept" is subject to empirical caps that are not declared in any schema the plugin can read.

### Phase 1 — Inventory

From `EXTERNAL_VERIFIERS.md` §2, enumerate every verifier row. For each, extract: (a) declared tier (Class 1 / 1.5 / 2 / 3), (b) advertised tool names in the `MCP tool (runtime namespace)` column, (c) declared required parameters (from §2 or §3.1), and (d) any declared contract text (§3.1 currently covers Scholar Gateway only).

Produce a probe plan table:

```
| Verifier | Tier | Tools advertised | Required params declared | Contract declared |
|---|---|---|---|---|
| Scholar Gateway | 1 | mcp__...__semanticSearch | query, interaction_id, inferred_intent | render_contract v0.1 |
| Consensus | 1 | mcp__...__search | ... | ... |
| HuggingFace Papers | 1.5 | paper_search, hf_doc_search, hub_repo_search | ... | ... |
| Zotero + Scite | 1 / 2 / 3 | mcp__zotero__* (43 tools) | ... | ... |
```

### Phase 2 — Connectivity probe

For each verifier, call `mcp__mcp-registry__search_mcp_registry` with the verifier's name as a keyword. Record: `directoryUuid`, `connected`, `enabledInChat`. A verifier that is referenced in `EXTERNAL_VERIFIERS.md` but returns `connected: false` is a **contract gap** (MAJOR): the plugin claims operational reachability that the registry does not confirm.

### Phase 3 — Runtime namespace pinning

For each advertised tool, confirm the runtime namespace by consulting the session's tool list. A namespace that appears in `EXTERNAL_VERIFIERS.md` as `mcp__*__<tool>` (literal asterisk) or as a registry UUID not matching the runtime UUID is a **placeholder defect** (MAJOR if still in a released version; BLOCKER if introduced in a version bump that has not yet shipped). This is the exact defect class SK-22 was built to catch.

Record runtime namespaces in the probe report:

```
Runtime namespaces (as of <date>):
- Scholar Gateway semanticSearch: mcp__70599628-0640-490e-bb1b-450b0e8248a9__semanticSearch
- Consensus search: mcp__a28b93ab-2ce7-493f-b02d-f03a8ebe522f__search
- HuggingFace Papers paper_search: mcp__ab9ac1e8-8aca-4de3-afba-92c86249d5aa__paper_search
- ...
```

### Phase 4 — Contract inspection (core)

For each verifier, invoke the minimal call that will surface every payload field. "Minimal" depends on the verifier:

- **Scholar Gateway.** A single `semanticSearch` with a short natural-language query, a freshly generated `interaction_id`, and a plausible `inferred_intent`. Inspect the response for `render_contract`, `provenance`, `disclosures`, `usage_terms`, `result_count`, `pub_date_range`, `results[].text`, and any field name not already documented in §3.1.
- **Consensus.** A single `search` call with a simple query. Inspect for any contract, disclosure, or policy field in the response envelope.
- **HuggingFace Papers.** A `paper_search` with a short query. Inspect for rate-limit headers, usage-terms strings, or schema version markers.
- **Zotero + Scite.** A `zotero_list_libraries` whoami call (no quota impact). Inspect for Scite-specific fields in any enriched response.

For every field surfaced that is **not** already documented in `EXTERNAL_VERIFIERS.md`, record it as an **undocumented-contract finding**. Severity:

| Field category | Severity |
|---|---|
| Binding presentation contract (render, footer, disclosure-mandated) | BLOCKER if unrendered; MAJOR if documented but not audited |
| Provenance / metadata (dates, counts, identifiers) | MAJOR if claimed without display |
| Usage terms / licence / attribution | MAJOR if attribution required and absent |
| Rate limit / quota | MINOR if not displayed; MAJOR if displayed incorrectly |
| Schema version marker | MINOR (record for next probe) |

A BLOCKER finding at this phase blocks the release. A MAJOR must be documented in `EXTERNAL_VERIFIERS.md` before the release; a MINOR may be deferred to the next version.

### Phase 5 — Advertised-but-unexercised audit

For every tool name listed in `EXTERNAL_VERIFIERS.md` §2 that was **not** invoked during Phases 2–4, record it as an **advertised-but-unexercised** entry. This is a MINOR finding by default (the plugin references a tool the probe did not exercise), but escalates to MAJOR if the tool is named in a procedure step in `REVIEW_ORCHESTRATION.md` or in any agent's procedure — because a referenced-but-unexercised tool in an agent procedure is the exact v0.3.2 defect pattern.

### Phase 6 — Contract-drift audit (version bump only)

When run as a pre-release gate, compare the current probe report to the most recent prior probe report:

- New fields in any verifier's response → record as *new-contract detected*. Each must either (a) land in `EXTERNAL_VERIFIERS.md` with the release, or (b) be explicitly deferred with a dated follow-up in the integration analysis.
- Fields present in the prior probe but absent in this one → record as *contract-removed*. Rare but possible if the verifier deprecated a field; the plugin's enforcement must be removed in lockstep.
- Runtime namespace changes → record as *namespace drift*. Every referencing file must be updated; the old namespace must not remain in the shipped text.

### Phase 7 — Emit the probe report

Write `reviews/tool_contract_probe_<YYYY-MM-DD>.md` with this exact shape:

```markdown
# Tool-Contract Round-Trip Probe — <date>

**Plugin version under test:** <semver>
**Probed by:** <agent name or "user via /tool-contract-roundtrip">
**Release status:** pre-release-gate | quarterly-hygiene | new-verifier-onboarding | drift-re-probe

## 1. Inventory
<paste Phase 1 probe plan table>

## 2. Connectivity
| Verifier | directoryUuid | connected | enabledInChat | Contract gap? |
|---|---|---|---|---|
...

## 3. Runtime namespaces pinned
<paste Phase 3 namespace list>

## 4. Contract inspection findings
### 4.a Documented-and-compliant fields
- <verifier> · <field> · <presence confirmed>

### 4.b Undocumented-contract findings
- [BLOCKER / MAJOR / MINOR] <verifier> · <field> · <what the field says> · <what the plugin should do about it>

## 5. Advertised-but-unexercised tools
- <verifier> · <tool name> · <referenced in: file and section> · [MINOR / MAJOR]

## 6. Drift relative to prior probe
- New fields: <list>
- Removed fields: <list>
- Namespace changes: <list>

## 7. Release-gate verdict
- Manifest self-probe (§0): OK / WARN / BLOCKER
- BLOCKER count (§0+§4+§5): <n>
- MAJOR count: <n>
- MINOR count: <n>
- **Verdict:** CLEARED for release | BLOCKED pending <items> | CLEARED with deferred items <items>

## 8. Follow-up actions
- [PROPOSED] Update `EXTERNAL_VERIFIERS.md` §<section> to add <field> — for user approval before release
- [PROPOSED] Update `plugin.json` description to reflect <change> — for user approval before release
- [PROPOSED] Update `README.md` changelog with <line> — for user approval before release
- ...
```

### Phase 8 — Gate decision

Present the probe report to the user with this summary line at the top:

```
Tool-contract round-trip: CLEARED / BLOCKED / CLEARED-WITH-DEFERRALS — <n> BLOCKER, <n> MAJOR, <n> MINOR. Full report at reviews/tool_contract_probe_<date>.md.
```

The release may proceed only on CLEARED or CLEARED-WITH-DEFERRALS. If BLOCKED, the release is held until the Generator applies the proposed updates from §8 and the probe is re-run.

---

## Invariants

- **Reflexive application of Rule 1 and Rule 4.** This skill exists because the harness must be subject to the rules it imposes. If the plugin cannot pass its own Rule 1 / Rule 4 test, it cannot credibly enforce them on manuscripts.
- **Probes are append-only.** Probe reports are dated; older reports are never overwritten. The Reflector diffs them for contract evolution; drift detection depends on the chain of reports.
- **Severity is pinned to release status.** A MAJOR finding in a probe run outside of a release window is a tracked item; the same finding in a pre-release gate is a release-blocker. Phase 8's verdict reflects the release status.
- **Advertised-but-unexercised is never zero-tolerance at MINOR.** Some verifiers list tools that the plugin deliberately does not invoke (e.g. Zotero has 43 tools; the plugin uses a subset). MINOR exists to record the list; MAJOR fires only when the unexercised tool is named in a procedure step that the plugin actually runs.

## What you do NOT do

- **Do not probe a tool the user has not authorized at the quota level required.** If a probe would consume paid quota beyond the verifier's free tier, ask the user before proceeding. A MINOR probe-deferred finding is preferable to an unapproved quota burn.
- **Do not update `EXTERNAL_VERIFIERS.md` or `plugin.json` in this skill.** All edits are proposals in §8 of the probe report. The Generator applies them after user approval.
- **Do not run this skill against a manuscript's verifier usage.** That is the Reflector's Rule 7a audit (Category 9). SK-22 probes the plugin's own tool surface; Category 9 audits the manuscript's use of that surface.
- **Do not treat a probe failure as a plugin defect without re-probing.** Transient MCP unavailability is not a plugin defect. A second failure within the same session, or a failure reproduced in a later session, is a defect — then escalate.
