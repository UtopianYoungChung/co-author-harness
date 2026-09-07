# ROLE_AND_AUTHORITY.md — this package's role relative to research governance

**Status.** Binding instrument record. Not a Master Governance amendment. Adds no rule.

> **Canonical surface.** This file is the single normative home for this
> package's role and authority statement. Entry files **route here**; they
> do not restate the record. Duplicated role prose drifts — that is the
> defect this file exists to close, not to reproduce.
>
> **Mechanical authority.** A parity keeper, specified separately and not yet
> implemented, would check that both package-root entry files carry the
> reference stub naming this file. It would not pin the producer-disclaimer
> substring in those entry files. Under the installed arrangement the
> disclaimer lives in this file, not in the entry files.

---

**Role and authority (binding).** Each research project is governed by research
governance under Master Governance Plane R. This package is one instrument among
others: a producer and evaluator of proposed artifacts and findings, commissioned
by research governance. It does not govern the project or the research. Its
ordinary outputs carry no authority over Plane R; the one upward channel Master
Governance reserves — fabrication-class findings under Section 4, travelling with
blocking force — is untouched by this record. Its functions and policies —
receipts, checks, phase labels, destination capability, and product gates —
continue to constrain the outputs of a commissioned run and remain subordinate to
Master Governance 1.5. A PASS, phase label, receipt, shipment, or evaluation
issued by this package never becomes project acceptance, milestone authority,
promotion, or research direction. Never infer authority from a harness verdict,
phase label, terminal PASS, or artifact quality. Separation of producer and
evaluator roles within this package is auditable, not independent (Master
Governance 2.4). This record adds no rule: it states the producer boundary this
package shipped at v0.37.4 and names the already-installed Master Governance
clauses that govern that boundary.

**Bound Master Governance version (7.7).** Before a write within a governed
workspace or an explicitly governed operation, this package must name the bound
Master Governance version under that workspace's current resolver. Ordinary
read-only checks and authorized task-local drafting/revision outside governed
workspaces do not require installing Master Governance; their outputs confer no
research acceptance or lifecycle authority. A supplied invalid authoritative
binding remains a refusal, and a scope label cannot bypass a protected destination.
The following installed-workspace resolution record remains subordinate to the
workspace's current resolver and newer validating amendment anchors. The mechanical resolver is
workspace `governance/tools/master_governance_resolver.py`, invoked by
`governance/tools/workspace_preflight.py`. Resolve the current head by
exact path and existence only, never by hashes, in this order: if
`research/99_System/migrations/2026-08-20_master_governance_amendment_1_0_11/JOSEPH_AMENDMENT_ANCHOR.yaml`
exists, it must validate against
`research/10_Governance/MASTER_GOVERNANCE_AMENDMENT_RECORD_1.0.11.md`; if
that validation succeeds, the bound version is **1.0.11**; if that file
exists and validation fails, evaluation STOPs and must not fall back. If
that A06 path is absent and
`research/99_System/migrations/2026-08-20_master_governance_amendment_1_0_10/JOSEPH_AMENDMENT_ANCHOR.yaml`
exists, it must validate against
`research/10_Governance/MASTER_GOVERNANCE_AMENDMENT_RECORD_1.0.10.md`; if
that validation succeeds, the bound version is **1.0.10**; if that file
exists and validation fails, evaluation STOPs and must not fall back. If
that A05 path is absent and
`research/99_System/migrations/2026-08-04_master_governance_amendment_1_0_9/JOSEPH_AMENDMENT_ANCHOR.yaml`
exists and validates against
`research/10_Governance/MASTER_GOVERNANCE_AMENDMENT_RECORD_1.0.9.md`, the
bound version is **1.0.9**; a present invalid A02 STOPs and must not fall
back. Else if
`research/99_System/migrations/2026-08-03_ws10_authority_split/JOSEPH_ACTIVATION_ANCHOR.yaml`
exists and validates against
`research/10_Governance/ACTIVATION_RECORD.md`, the bound version is
**1.0.8**; else the pre-activation regime remains. A governed invocation that
cannot name that version before its first governed write is refused. This
paragraph names the resolver; it does not amend Master Governance.
