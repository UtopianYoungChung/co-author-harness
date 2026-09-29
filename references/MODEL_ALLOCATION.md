# MODEL_ALLOCATION.md — Model capability at dispatch

*Package reference. Current allocation authority for Planner dispatch and Reflector Phase 2f audit. Historical model names in older reports and release notes describe those runs; they do not set a current default. Read this file before child dispatch.*

## 1. Required capability

**Joseph's direction (binding; registered 2026-09-29).** Verbatim: "Only the current model—the highest available model running at the highest possible effort—is adequate for planning and review, including orchestration. The current model should orchestrate all other jobs, assigning them to the appropriate lower models." Joseph, 2026-09-29, on this package, verbatim: "Apply the same rule for the harness. The harness is an agent platform that has a role of acting tool for drafting/revising all research artifacts." The research-root registration is `research/10_Governance/RESEARCH_RUNTIME.md` (section "Model assignment"). The model routes in `agents/*.md` are this platform's model routes and change only on Joseph's word. This section and §2–§4 implement the direction and do not relax it.

The parent that plans, orchestrates, or reviews uses the **strongest model currently available and verified for that host and session, at the highest reasoning effort that host supports for that model**. This applies throughout Ph1–Ph4 and to ordinary project-independent work. It includes classification, revision plans, dispatch decisions, Evaluator review, every Reflector mode, grounding audits, reflective review, and the parent's final synthesis or judgment. A lightweight review has narrower *scope*, not a lower capability requirement. The Planner remains the orchestrator and assigns bounded execution to suitable models.

"Strongest" is resolved within the actual host's available, usable model choices using that host's current capability information. It is not a permanent model ID or a ranking across providers. A family alias such as `opus` is a routing preference, not evidence of the resolved release, relative capability, or reasoning effort. Verify the selected model and maximum supported effort from host capabilities or execution metadata when exposed. Do not infer either from an agent file or a model's self-description.

The package cannot silently change an already-running parent session's model or effort. Before planning or review, check whether the current session satisfies the requirement. If availability, ordering, selected model, or effort cannot be established, or the required selection is unavailable, report the specific unknown or mismatch and hold affected planning/review dispatch for host or user resolution. Never silently substitute a weaker model or lower effort. A later host selection needs a fresh check.

## 2. Role allocation

| Role or work | Ph1 | Ph2 | Ph3 | Ph4 |
|---|---|---|---|---|
| **Planner / parent orchestration** | Strongest verified, maximum effort | Strongest verified, maximum effort | Strongest verified, maximum effort | Strongest verified, maximum effort |
| **Evaluator / independent review** | Strongest verified, maximum effort; bounded policy pass | Strongest verified, maximum effort | Strongest verified, maximum effort | Strongest verified, maximum effort |
| **Reflector / reflective review** | Strongest verified, maximum effort; lightweight scope | Strongest verified, maximum effort; lightweight scope | Strongest verified, maximum effort; lightweight scope | Strongest verified, maximum effort; full closeout |
| **Generator / bounded execution** | Suitable available model | Suitable available model | Suitable available model | Suitable available model; fix-only scope |

The same rule applies when one actor performs several roles in a parent session: role duties remain distinct. The Generator alone authors candidate prose, the Evaluator independently assesses it, the Reflector audits the round, and the Planner owns dispatch and synthesis. `policies/phase_engagement.v1.json` governs when roles engage; allocation does not change phase participation or approval authority.

The strongest orchestrator may assign extraction, indexing, formatting, coding, and constrained generation to a suitable lower model under an explicit parent brief with a bounded output. A lower model does not own a plan, orchestration decision, review verdict, reflective judgment, or final synthesis. Work that becomes interpretive or evaluative returns to the strongest parent or an equally qualified reviewer.

## 3. Host binding and dispatch

At each dispatch, inspect the actual host capability surface. Select a required reviewer model and its maximum supported effort when the host permits per-child selection. Where it does not, the child inherits the parent selection; verify that inheritance before relying on its review. Codex hosts may expose per-agent model and effort controls, so capability-detect the running host instead of assuming every role must inherit the session model. Do not add unsupported host configuration fields. On Claude Code, `agents/evaluator.md`, `agents/reflector.md`, `agents/reflector-probe.md`, and `agents/reflector-closeout.md` set `model: inherit` and `effort: max`, so they run on the main session's model at maximum effort; Planner inherits the main session. `agents/generator.md` uses `model: sonnet` as a suitable execution default, subject to task and host.

Effort on Claude Code (docs read 2026-09-29: platform.claude.com/docs/en/build-with-claude/effort, code.claude.com/docs/en/model-config, code.claude.com/docs/en/sub-agents): Fable 5.1, Opus 5.5 and Sonnet 5.5 support all five levels, `max` included. For the main session, a level the model does not support falls back to the highest supported level at or below it. For a subagent that sets `effort` above what its model supports, the behaviour is not documented. Verify a review child's actual model and effort in `/tasks`, which shows the effort only when the agent definition sets `effort`; the four review agents do. If it cannot be verified, report it as unknown.

For a `full_lifecycle` round, Phase 0.6 records intended resolved models in the approved F6 dispatch plan. Phase 4.5 consumes that plan and checks it against current host availability and this rule. If the plan drifts or its review allocation cannot be verified, use the existing superseding-F6 and approval path before dispatch. For other scopes, resolve at dispatch. Record the actual model identifier and effort when available, plus verification source, in existing dispatch notes/report. `model_used` and `model_allocation` carry resolved model identifiers; neither field alone proves maximum effort. Report unknowns as unknown; never fill them from a default alias.

## 4. Non-inversion, provenance, and audit

The Evaluator must not be weaker than the Generator for a round. When the host's model ordering is established, compare resolved models. Refuse an inversion with `E-MA-CAPABILITY-INVERSION`. When ordering cannot be established, do not assert non-inversion; use the same verified strongest model for both roles or hold the affected review. The strongest-model rule for planning and review still applies if the Generator is weaker.

An active project directive may choose a stronger Generator or further constrain a role, but cannot silently waive the current user's strongest-model requirement for planning or review. Preserve `model_override:{agent}-{phase}:={model}` in `phase_entry_log[].notes` for directive overrides and identify the active directive. Record ordinary dispatch as `model_dispatch:{agent}:={model}`. Reflector Phase 2f checks role engagement, non-inversion, actual model and effort evidence, F6 agreement when present, and override provenance. Existing finding identifiers `R-Refl-MA-1`, `R-Refl-MA-3`, and `R-Refl-MA-4` remain available for inversion, orphan override, and F6 mismatch. Missing verification is an unresolved finding, not a pass.

Older `Haiku 4.5 < Sonnet 4.6 < Opus 4.7` comparisons apply only to those identified historical models. They do not rank newer releases or providers. The former Sonnet Planner default and Haiku lightweight-Reflector pilot are retired as active allocation rules. Prior `model_dispatch_audit` records remain historical evidence.

*Normative status.* This package component follows the precedence in `AGENTS.md`. It does not authorize manuscript acceptance, release, installation, or a change to the host's selected parent model.
