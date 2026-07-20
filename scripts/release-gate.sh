#!/usr/bin/env bash
# co-author-harness — release-gate.sh
#
# Pre-release pipeline for the co-author-harness plugin.
# Implements SK-22 Phase 0 (manifest self-probe) as a shell helper.
#
# What it does:
#   1. Resolves the plugin root (the directory containing .claude-plugin/plugin.json).
#   2. Computes the empirical distribution of plugin.json.description length
#      across every installed peer plugin under the current Cowork session's
#      /mnt/.remote-plugins/ (or the caller-supplied --peer-root).
#   3. Measures the current plugin's plugin.json.description against that distribution
#      and reports OK / WARN / BLOCKER.
#   4. Measures every skills/*/SKILL.md frontmatter description against a 500-char
#      safety margin and reports any overflow.
#   5. Runs scripts/skill-check.py for frontmatter, command-catalog, and registry parity checks.
#   6. Runs scripts/version-check.py for release-version consistency.
#   7. Runs scripts/catalog-check.py for README and registry parity checks.
#   8. Runs scripts/path-hygiene-check.py for maintainer-local path hygiene.
#   8a. [v0.15.0-pre] Runs scripts/snippet-check.py for packaging-time
#       include resolution and anti-duplication of extracted policy blocks.
#   8b. Runs scripts/output_economy_check.py; all behavioral fixtures execute
#       once through the authoritative registry.
#   9. [Retired at v0.7.0] Rule-digest build-and-verify. The tier-gated digest
#      exception (GROUNDING_PROTOCOL Rule 1, v0.6.0 and earlier) was retired in
#      v0.7.0 in favour of full-file reads at every rung. `scripts/
#      build_rule_digest.py` and `scripts/verify_rule_digest.py` are archived
#      under `legacy/` and no longer run at release time.
#  10. Runs syntax checks (py_compile) on Coupling E.2, graph-contract, Phase D,
#      milestone-feedback, lifecycle-renderer, and migration scripts. Includes
#      `paragraph_hash_map.py` (v0.8.0 P2.1c).
#  10a. [v0.8.0] Efficiency-config + chain-depth regression gate. Asserts
#       `.plugin-efficiency.json` is present at plugin root (landed at v0.8.0
#       Phase 1.1 per proposals/v0.8.0_upgrade_architecture.md §3.2). WARNs if
#       `input_tokens_per_second` still reads the 2000 placeholder — the v0.8.0
#       release-gate (§3.3 condition 4) blocks on placeholder when invoked with
#       --ship-intent; authoring runs ignore the placeholder. When the
#       plugin-calibrator CLI is available, runs `audit-package-speed` and
#       BLOCKs if `max_subagent_chain_depth` exceeds the config's
#       `thresholds.max_chain_depth` (default 15).
#  11. Builds the release .zip via the committed builder (scripts/build-plugin.py):
#      commit-bound bytes from a clean worktree re-exec, rendered includes,
#      embedded PROVENANCE.json, single population authority
#      (scripts/package_enumeration.py). The former worktree `zip -r` with
#      exclusion globs is retired -- it was a second, independent package
#      population and shipped unresolved include sentinels.
#  12. Inspects the in-archive plugin.json and reports its version and description length.
#  13. If an --outputs-dir is supplied, scans for stale deliverables under filenames
#      other than the current bundle name.
#
# Usage:
#   scripts/release-gate.sh                                           # probe-only, no build
#   scripts/release-gate.sh --build                                   # probe + build zip
#   scripts/release-gate.sh --build --outputs-dir /mnt/outputs        # full pipeline
#   scripts/release-gate.sh --peer-root /sessions/.../mnt/.remote-plugins/
#   scripts/release-gate.sh --ship-intent                             # block on any in-flight marker
#                                                                     # (efficiency placeholder, -wip version)
#
# Exit codes:
#   0 — CLEARED for release (no BLOCKER findings)
#   1 — BLOCKED (at least one BLOCKER finding)
#   2 — usage or environment error
#
# Known gaps (deferred to a future release, listed in CHANGELOG):
#   - tier-table sweep audit: would catch review_depth-vocabulary residue the same way
#     the wired retirement-sweep check catches run-full-review residue. Also deferred.
# Description length is measured empirically against installed peers; there is no
# hard-coded character target in this script.
#
# This script runs under bash 4+. It requires python3, PyYAML (python `yaml` module),
# zip, and unzip. No jq, no yq, no node.

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLUGIN_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
MANIFEST="$PLUGIN_ROOT/.claude-plugin/plugin.json"

BUILD=0
OUTPUTS_DIR=""
PEER_ROOT=""
SHIP_INTENT=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --build)        BUILD=1; shift ;;
        --outputs-dir)  OUTPUTS_DIR="$2"; shift 2 ;;
        --peer-root)    PEER_ROOT="$2"; shift 2 ;;
        --ship-intent)  SHIP_INTENT=1; shift ;;
        -h|--help)
            grep '^#' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *)  echo "Unknown flag: $1" >&2; exit 2 ;;
    esac
done

if [[ ! -f "$MANIFEST" ]]; then
    echo "ERROR: plugin.json not found at $MANIFEST" >&2
    exit 2
fi

# Auto-discover peer root if not supplied: walk up from the plugin root looking
# for a sibling .remote-plugins/ directory. This covers the Cowork session layout
# where plugins install under /sessions/<id>/mnt/.remote-plugins/plugin_<uuid>/.
if [[ -z "$PEER_ROOT" ]]; then
    PROBE="$PLUGIN_ROOT"
    while [[ "$PROBE" != "/" ]]; do
        if [[ -d "$PROBE/mnt/.remote-plugins" ]]; then
            PEER_ROOT="$PROBE/mnt/.remote-plugins"
            break
        fi
        PROBE="$( dirname "$PROBE" )"
    done
fi

echo "============================================================"
echo "co-author-harness — release-gate"
echo "============================================================"
echo "Plugin root:  $PLUGIN_ROOT"
echo "Manifest:     $MANIFEST"
echo "Peer root:    ${PEER_ROOT:-<none found>}"
echo ""

# --- Phase 0.1: manifest self-probe ---------------------------------------

CURRENT_NAME=$( python3 -c "import json,sys; print(json.load(open(sys.argv[1], encoding='utf-8'))['name'])" "$MANIFEST" )
CURRENT_VERSION=$( python3 -c "import json,sys; print(json.load(open(sys.argv[1], encoding='utf-8'))['version'])" "$MANIFEST" )
CURRENT_DESC_LEN=$( python3 -c "import json,sys; print(len(json.load(open(sys.argv[1], encoding='utf-8')).get('description','')))" "$MANIFEST" )

echo "Current plugin:           $CURRENT_NAME @ $CURRENT_VERSION"
echo "Current description len:  $CURRENT_DESC_LEN chars"
echo ""

BLOCKERS=0
WARNINGS=0

if ! python3 -c "import yaml" >/dev/null 2>&1; then
    echo "[BLOCKER] python3 module 'yaml' (PyYAML) is not available."
    echo "          Install it before running the SKILL.md description-length checks."
    BLOCKERS=$((BLOCKERS + 1))
fi

if [[ -n "$PEER_ROOT" && -d "$PEER_ROOT" ]]; then
    # Compute peer distribution, excluding the current plugin by name.
    readarray -t PEER_LENS < <(
        for p in "$PEER_ROOT"/*/.claude-plugin/plugin.json; do
            [[ -f "$p" ]] || continue
            python3 -c "
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
if d.get('name') != '$CURRENT_NAME':
    print(len(d.get('description','')))
" "$p" 2>/dev/null
        done
    )

    if [[ ${#PEER_LENS[@]} -gt 0 ]]; then
        PEER_MIN=$( printf '%s\n' "${PEER_LENS[@]}" | sort -n | head -1 )
        PEER_MAX=$( printf '%s\n' "${PEER_LENS[@]}" | sort -n | tail -1 )
        PEER_P75=$( python3 -c "
import sys
vs = sorted([int(x) for x in sys.argv[1:]])
import math
p75 = vs[max(0, math.ceil(0.75 * len(vs)) - 1)]
print(p75)
" "${PEER_LENS[@]}" )

        echo "Peer distribution (N=${#PEER_LENS[@]}): min=$PEER_MIN  p75=$PEER_P75  max=$PEER_MAX"

        if   (( CURRENT_DESC_LEN > PEER_MAX )); then
            echo "  [BLOCKER] plugin.json.description ($CURRENT_DESC_LEN) > peer max ($PEER_MAX)"
            echo "            The Cowork validator has historically rejected payloads above peer max."
            BLOCKERS=$((BLOCKERS + 1))
        elif (( CURRENT_DESC_LEN > PEER_P75 )); then
            echo "  [WARN]    plugin.json.description ($CURRENT_DESC_LEN) > peer p75 ($PEER_P75)"
            WARNINGS=$((WARNINGS + 1))
        else
            echo "  [OK]      plugin.json.description ($CURRENT_DESC_LEN) <= peer p75 ($PEER_P75)"
        fi
    else
        echo "Peer distribution: 0 peers found under $PEER_ROOT — skipping empirical check."
    fi
else
    echo "Peer distribution: no peer root available — skipping empirical check."
fi

echo ""

# --- Phase 0.2: SKILL.md description lengths ------------------------------

if python3 -c "import yaml" >/dev/null 2>&1; then
    echo "SKILL.md description lengths (safety margin: 500 chars)"
    for skill_md in "$PLUGIN_ROOT"/skills/*/SKILL.md; do
        [[ -f "$skill_md" ]] || continue
        skill_name=$( basename "$( dirname "$skill_md" )" )
        desc_len=$( python3 -c "
import re, sys, yaml
t = open(sys.argv[1], encoding='utf-8').read()
m = re.search(r'^---\n(.*?)\n---', t, re.S)
try:
    fm = yaml.safe_load(m.group(1)) if m else {}
    print(len(fm.get('description','')))
except Exception:
    print(0)
" "$skill_md" 2>/dev/null || echo 0 )
        if (( desc_len > 500 )); then
            printf "  [WARN] %-30s %5d chars (exceeds 500-char safety margin)\n" "$skill_name" "$desc_len"
            WARNINGS=$((WARNINGS + 1))
        else
            printf "  [OK]   %-30s %5d chars\n" "$skill_name" "$desc_len"
        fi
    done
    echo ""
else
    echo "SKILL.md description lengths: skipped (PyYAML missing)"
    echo ""
fi

# --- Phase 0.3: skill integrity checks -------------------------------------

if [[ -f "$PLUGIN_ROOT/scripts/skill-check.py" ]]; then
    echo "Skill integrity checks (frontmatter + command/registry parity)"
    if ! python3 "$PLUGIN_ROOT/scripts/skill-check.py" --plugin-root "$PLUGIN_ROOT"; then
        echo "  [BLOCKER] scripts/skill-check.py reported blocking issues"
        BLOCKERS=$((BLOCKERS + 1))
    else
        echo "  [OK]      scripts/skill-check.py passed"
    fi
    echo ""
else
    echo "Skill integrity checks: script missing (scripts/skill-check.py)"
    echo "  [BLOCKER] cannot run skill integrity checks"
    BLOCKERS=$((BLOCKERS + 1))
    echo ""
fi

# --- Phase 0.4: version consistency checks --------------------------------

if [[ -f "$PLUGIN_ROOT/scripts/version-check.py" ]]; then
    echo "Version consistency checks (manifest/README/CHANGELOG)"
    if ! python3 "$PLUGIN_ROOT/scripts/version-check.py" --plugin-root "$PLUGIN_ROOT"; then
        echo "  [BLOCKER] scripts/version-check.py reported blocking issues"
        BLOCKERS=$((BLOCKERS + 1))
    else
        echo "  [OK]      scripts/version-check.py passed"
    fi
    echo ""
else
    echo "Version consistency checks: script missing (scripts/version-check.py)"
    echo "  [BLOCKER] cannot run version consistency checks"
    BLOCKERS=$((BLOCKERS + 1))
    echo ""
fi

# --- Phase 0.45: distribution-rights checks -------------------------------

if [[ -f "$PLUGIN_ROOT/scripts/distribution-rights-check.py" ]]; then
    echo "Distribution-rights checks (current tree + future artifacts)"
    if ! python3 "$PLUGIN_ROOT/scripts/distribution-rights-check.py" --plugin-root "$PLUGIN_ROOT"; then
        echo "  [BLOCKER] scripts/distribution-rights-check.py reported blocking issues"
        BLOCKERS=$((BLOCKERS + 1))
    else
        echo "  [OK]      scripts/distribution-rights-check.py passed"
    fi
    echo ""
else
    echo "Distribution-rights checks: script missing (scripts/distribution-rights-check.py)"
    echo "  [BLOCKER] cannot run distribution-rights checks"
    BLOCKERS=$((BLOCKERS + 1))
    echo ""
fi

# --- Phase 0.5: catalog parity checks -------------------------------------

if [[ -f "$PLUGIN_ROOT/scripts/catalog-check.py" ]]; then
    echo "Catalog parity checks (README/commands/registry)"
    if ! python3 "$PLUGIN_ROOT/scripts/catalog-check.py" --plugin-root "$PLUGIN_ROOT"; then
        echo "  [BLOCKER] scripts/catalog-check.py reported blocking issues"
        BLOCKERS=$((BLOCKERS + 1))
    else
        echo "  [OK]      scripts/catalog-check.py passed"
    fi
    echo ""
else
    echo "Catalog parity checks: script missing (scripts/catalog-check.py)"
    echo "  [BLOCKER] cannot run catalog parity checks"
    BLOCKERS=$((BLOCKERS + 1))
    echo ""
fi

# --- Phase 0.6: path hygiene checks ---------------------------------------

if [[ -f "$PLUGIN_ROOT/scripts/path-hygiene-check.py" ]]; then
    echo "Path hygiene checks (maintainer-local absolute paths)"
    if ! python3 "$PLUGIN_ROOT/scripts/path-hygiene-check.py" --plugin-root "$PLUGIN_ROOT"; then
        echo "  [BLOCKER] scripts/path-hygiene-check.py reported blocking issues"
        BLOCKERS=$((BLOCKERS + 1))
    else
        echo "  [OK]      scripts/path-hygiene-check.py passed"
    fi
    echo ""
else
    echo "Path hygiene checks: script missing (scripts/path-hygiene-check.py)"
    echo "  [BLOCKER] cannot run path hygiene checks"
    BLOCKERS=$((BLOCKERS + 1))
    echo ""
fi

# --- Phase 0.55: registry checks (2026-07-06 improvement plan WS-2/WS-3) ---

for REG_CHECK in version-planes-check.py commitment-interactions-check.py retirement-sweep-check.py; do
    if [[ -f "$PLUGIN_ROOT/scripts/$REG_CHECK" ]]; then
        echo "Registry check ($REG_CHECK)"
        if ! python3 "$PLUGIN_ROOT/scripts/$REG_CHECK"; then
            echo "  [BLOCKER] scripts/$REG_CHECK reported blocking issues"
            BLOCKERS=$((BLOCKERS + 1))
        else
            echo "  [OK]      scripts/$REG_CHECK passed"
        fi
        echo ""
    else
        echo "Registry check: script missing (scripts/$REG_CHECK)"
        echo "  [BLOCKER] cannot run $REG_CHECK"
        BLOCKERS=$((BLOCKERS + 1))
        echo ""
    fi
done

# --- Phase 0.56: authoritative fixture infrastructure + corpus -------------

echo "Fixture infrastructure preflight"
if ! python3 "$PLUGIN_ROOT/scripts/analysis/fixture_infrastructure_check.py"; then
    echo "  [BLOCKER] fixture infrastructure preflight failed"
    BLOCKERS=$((BLOCKERS + 1))
else
    echo "  [OK]      fixture infrastructure preflight passed"
fi
echo ""

echo "Authoritative fixture registry"
if ! python3 "$PLUGIN_ROOT/scripts/analysis/fixture_runner.py" --no-write; then
    echo "  [BLOCKER] authoritative fixture registry failed"
    BLOCKERS=$((BLOCKERS + 1))
else
    echo "  [OK]      authoritative fixture registry passed"
fi
echo ""

MILESTONE_COMPILE_TARGETS=(
    assignment_process_gate.py
    assignment_dispatch_preflight.py
    assignment_receipt_transaction.py
    assignment_milestone_transaction.py
    assignment_milestone_checkpoint.py
    assignment_writer_commit.py
    assignment_receipt_invalidate.py
    assignment_receipt_recover.py
    milestone_framework_validate.py
    render_lifecycle_state.py
    migrate_legacy_milestones.py
)
MILESTONE_COMPILE_READY=1
for COMPILE_TARGET in "${MILESTONE_COMPILE_TARGETS[@]}"; do
    if [[ ! -f "$PLUGIN_ROOT/scripts/$COMPILE_TARGET" ]]; then
        echo "Milestone-feedback framework: compile target missing (scripts/$COMPILE_TARGET)"
        echo "  [BLOCKER] cannot compile scripts/$COMPILE_TARGET"
        BLOCKERS=$((BLOCKERS + 1))
        MILESTONE_COMPILE_READY=0
    fi
done

if (( MILESTONE_COMPILE_READY == 1 )); then
    echo "Milestone-feedback framework syntax check"
    if ! python3 -m py_compile \
        "$PLUGIN_ROOT/scripts/assignment_process_gate.py" \
        "$PLUGIN_ROOT/scripts/assignment_dispatch_preflight.py" \
        "$PLUGIN_ROOT/scripts/assignment_receipt_transaction.py" \
        "$PLUGIN_ROOT/scripts/assignment_milestone_transaction.py" \
        "$PLUGIN_ROOT/scripts/assignment_milestone_checkpoint.py" \
        "$PLUGIN_ROOT/scripts/assignment_writer_commit.py" \
        "$PLUGIN_ROOT/scripts/assignment_receipt_invalidate.py" \
        "$PLUGIN_ROOT/scripts/assignment_receipt_recover.py" \
        "$PLUGIN_ROOT/scripts/milestone_framework_validate.py" \
        "$PLUGIN_ROOT/scripts/render_lifecycle_state.py" \
        "$PLUGIN_ROOT/scripts/migrate_legacy_milestones.py"; then
        echo "  [BLOCKER] milestone-feedback framework syntax check failed"
        BLOCKERS=$((BLOCKERS + 1))
    else
        echo "  [OK]      milestone-feedback framework syntax check passed"
    fi
    echo ""
fi

# --- Phase 0.60: snippet include guard (v0.15.0-pre) ----------------------

if [[ -f "$PLUGIN_ROOT/scripts/snippet-check.py" ]]; then
    echo "Snippet include guard (resolve includes + anti-duplication)"
    if ! python3 "$PLUGIN_ROOT/scripts/snippet-check.py"; then
        echo "  [BLOCKER] scripts/snippet-check.py reported blocking issues"
        BLOCKERS=$((BLOCKERS + 1))
    else
        echo "  [OK]      scripts/snippet-check.py passed"
    fi
    echo ""
else
    echo "Snippet include guard: script missing (scripts/snippet-check.py)"
    echo "  [BLOCKER] cannot run snippet include guard"
    BLOCKERS=$((BLOCKERS + 1))
    echo ""
fi

# --- Phase 0.60d: GROUNDING_PROTOCOL stable anchors (v0.15.0-pre) ---------

if [[ -f "$PLUGIN_ROOT/scripts/grounding_anchors_check.py" ]]; then
    echo "GROUNDING_PROTOCOL stable anchors (scripts/grounding_anchors_check.py)"
    if ! python3 "$PLUGIN_ROOT/scripts/grounding_anchors_check.py"; then
        echo "  [BLOCKER] grounding_anchors_check.py reported missing or misplaced anchors"
        BLOCKERS=$((BLOCKERS + 1))
    else
        echo "  [OK]      grounding_anchors_check.py passed"
    fi
    echo ""
else
    echo "GROUNDING_PROTOCOL stable anchors: script missing (scripts/grounding_anchors_check.py)"
    echo "  [BLOCKER] cannot run grounding_anchors_check"
    BLOCKERS=$((BLOCKERS + 1))
    echo ""
fi

# Live-tree citation audit. Inviolable severity — any unresolved
# [GP §N] / GROUNDING_PROTOCOL.md §Rule N citation in references/, agents/,
# or skills/ fails closed. The smoketest above proves the auditor itself
# works; this block runs it against the actual harness package.
if [[ -f "$PLUGIN_ROOT/scripts/audit/audit_citations.py" ]]; then
    echo "Live citation audit (references/, agents/, skills/, commands/)"
    LIVE_AUDIT_FAILED=0
    for target in references agents skills commands; do
        if [[ -d "$PLUGIN_ROOT/$target" ]]; then
            if ! python3 "$PLUGIN_ROOT/scripts/audit/audit_citations.py" \
                    "$PLUGIN_ROOT/$target" --quiet; then
                echo "  [BLOCKER] unresolved GROUNDING_PROTOCOL citations in $target/"
                LIVE_AUDIT_FAILED=1
            fi
        fi
    done
    if [[ $LIVE_AUDIT_FAILED -eq 0 ]]; then
        echo "  [OK]      all canonical GP citations resolve against gp-N anchors"
    else
        BLOCKERS=$((BLOCKERS + 1))
    fi
    echo ""
fi

# --- Phase 0.60d3: MANIFEST.md link + CLAUDE.md preservation (v0.15.0-pre PR-4b) ---

if [[ -f "$PLUGIN_ROOT/scripts/manifest_links_check.py" ]]; then
    echo "MANIFEST.md link + CLAUDE.md preservation (scripts/manifest_links_check.py)"
    if ! python3 "$PLUGIN_ROOT/scripts/manifest_links_check.py"; then
        echo "  [BLOCKER] manifest_links_check failed"
        BLOCKERS=$((BLOCKERS + 1))
    else
        echo "  [OK]      manifest_links_check passed"
    fi
    echo ""
else
    echo "MANIFEST.md link check: script missing"
    echo "  [BLOCKER] cannot run manifest_links_check"
    BLOCKERS=$((BLOCKERS + 1))
    echo ""
fi

# Token-budget measurement is WARN-ONLY at PR-4d per the v0.15.0
# architecture (measurement-first; the Reflector split + later slims
# will pull breaching files under the threshold). Breaches do NOT
# increment BLOCKERS. The script always exits 0 in normal mode; we
# treat any non-zero exit as an environment issue (tiktoken missing).
if [[ -f "$PLUGIN_ROOT/scripts/token_budget_check.py" ]]; then
    echo "Token-budget measurement (warn-only; PR-4d)"
    TOKEN_BUDGET_REPORT="$PLUGIN_ROOT/reviews/token_budget_report.json"
    if ! python3 "$PLUGIN_ROOT/scripts/token_budget_check.py" --quiet \
            --out "$TOKEN_BUDGET_REPORT"; then
        echo "  [WARN]    token-budget script could not run (tiktoken missing?)"
        WARNINGS=$((WARNINGS + 1))
    else
        BREACH_COUNT=$(python3 - "$TOKEN_BUDGET_REPORT" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("unknown")
else:
    print(len(data.get("breaches", [])))
PY
)
        if [[ "$BREACH_COUNT" == "0" ]]; then
            echo "  [OK]      token-budget measurement complete; no breaches"
        else
            echo "  [WARN]    token-budget measurement found $BREACH_COUNT budget breach(es)"
            WARNINGS=$((WARNINGS + 1))
        fi
        echo "            report: reviews/token_budget_report.json"
    fi
    echo ""
fi

# --- Phase 0.61: output economy guard + smoketest (v0.14.0) ---------------

if [[ -f "$PLUGIN_ROOT/scripts/output_economy_check.py" ]]; then
    echo "Output economy static guard (phase skills + agent contracts)"
    if ! python3 "$PLUGIN_ROOT/scripts/output_economy_check.py"; then
        echo "  [BLOCKER] scripts/output_economy_check.py reported blocking issues"
        BLOCKERS=$((BLOCKERS + 1))
    else
        echo "  [OK]      scripts/output_economy_check.py passed"
    fi
    echo ""
else
    echo "Output economy check: script missing (scripts/output_economy_check.py)"
    echo "  [BLOCKER] cannot run output economy check"
    BLOCKERS=$((BLOCKERS + 1))
    echo ""
fi

# --- Phase 0.62: manifest coherence checks (v0.11.0 c8) -------------------

if [[ -f "$PLUGIN_ROOT/scripts/manifest-coherence-check.py" ]]; then
    echo "Manifest coherence checks (description / keywords / parity)"
    if ! python3 "$PLUGIN_ROOT/scripts/manifest-coherence-check.py" --plugin-root "$PLUGIN_ROOT"; then
        echo "  [BLOCKER] scripts/manifest-coherence-check.py reported blocking issues"
        BLOCKERS=$((BLOCKERS + 1))
    else
        echo "  [OK]      scripts/manifest-coherence-check.py passed"
    fi
    echo ""
else
    echo "Manifest coherence checks: script missing (scripts/manifest-coherence-check.py)"
    echo "  [BLOCKER] cannot run manifest coherence checks"
    BLOCKERS=$((BLOCKERS + 1))
    echo ""
fi

# --- Phase 0.63: SSOT registry check (v0.11.0 c9) -------------------------

if [[ -f "$PLUGIN_ROOT/scripts/ssot-check.py" ]]; then
    echo "SSOT registry checks (.claude-plugin/ssot.yaml fact-consumer parity)"
    if ! python3 "$PLUGIN_ROOT/scripts/ssot-check.py" --plugin-root "$PLUGIN_ROOT"; then
        echo "  [BLOCKER] scripts/ssot-check.py reported blocking issues"
        BLOCKERS=$((BLOCKERS + 1))
    else
        echo "  [OK]      scripts/ssot-check.py passed"
    fi
    echo ""
else
    echo "SSOT registry checks: script missing (scripts/ssot-check.py)"
    echo "  [BLOCKER] cannot run SSOT registry checks"
    BLOCKERS=$((BLOCKERS + 1))
    echo ""
fi

# --- Phase 0.65: [Retired at v0.7.0] Rule-digest build-and-verify ---------
#
# The tier-gated digest exception in GROUNDING_PROTOCOL Rule 1 (v0.6.0 and
# earlier) was retired at v0.7.0 in favour of full-file reads at every rung.
# `scripts/build_rule_digest.py` and `scripts/verify_rule_digest.py` are
# archived under `legacy/`. This phase is preserved as a numbered placeholder
# to keep the phase-number contract stable across release-gate invocations.
echo "Rule digest build-and-verify — retired at v0.7.0 (no-op placeholder)"
echo "  [SKIP]    digest exception retired; full-file reads are universal at v0.7.0+"
echo ""

# --- Phase 0.695: superseded migration script smoketests retired at v0.11.0 -
#
# The v0.8.0 P2.1d migrate_convergence_journal_v075.py determinism gate is
# retired alongside the script itself in c5. The v0.10.0->v0.11.0 migration
# (scripts/migrate_v0100_to_v0110_drop_sd_sr.py) carries its own idempotence
# verification inline in its module docstring; the v0.9.0->v0.10.0 migration
# (migrate_v090_to_v100_snowball_fields.py) is gate-checked via py_compile in
# Phase 0.7 below.

# --- Phase 0.7: Coupling automation and Phase D script syntax checks -------
#
# Note on scope: this phase is a syntax-only gate (py_compile). The coupling
# automation scripts (coupling_readiness_check.py, coupling_health_report.py,
# the three sk20_*.py scripts) are invoked by the Evaluator at runtime against
# live project state — wiki paths, graphify output, review directories — and
# cannot be meaningfully executed against an empty plugin tree at release time.
# Full-invocation coverage lives in the round-level regression harness the
# Reflector runs per-project, not in this release gate. This phase's guarantee
# is therefore narrower than the structural checks above: "no script has a
# syntax error that would crash on import," not "every script succeeds at
# runtime."

echo "Coupling + Phase D/F script syntax checks (py_compile)"
for pyf in \
    "$PLUGIN_ROOT/scripts/graphify_contract.py" \
    "$PLUGIN_ROOT/scripts/coupling_readiness_check.py" \
    "$PLUGIN_ROOT/scripts/sk20_preflight_gate.py" \
    "$PLUGIN_ROOT/scripts/sk20_overlay_run.py" \
    "$PLUGIN_ROOT/scripts/sk20_autonomous_loop.py" \
    "$PLUGIN_ROOT/scripts/coupling_health_report.py" \
    "$PLUGIN_ROOT/scripts/install_preflight_assets.py" \
    "$PLUGIN_ROOT/scripts/gate_threshold_tuner.py" \
    "$PLUGIN_ROOT/scripts/migrate_v090_to_v100_snowball_fields.py" \
    "$PLUGIN_ROOT/scripts/migrate_v0100_to_v0110_drop_sd_sr.py" \
    "$PLUGIN_ROOT/scripts/pre_phase_advance_check.py" \
    "$PLUGIN_ROOT/scripts/phase_state_validate.py" \
    "$PLUGIN_ROOT/scripts/artefact_frontmatter_validate.py" \
    "$PLUGIN_ROOT/scripts/paragraph_hash_map.py" \
    "$PLUGIN_ROOT/scripts/check8_g_prefilter.py" \
    "$PLUGIN_ROOT/scripts/provenance_prewrite_check.py" \
    "$PLUGIN_ROOT/scripts/plugin_calibrator_audit.py"
do
    if [[ -f "$pyf" ]]; then
        if python3 -m py_compile "$pyf"; then
            echo "  [OK]      $( basename "$pyf" )"
        else
            echo "  [BLOCKER] $( basename "$pyf" ) failed python syntax check"
            BLOCKERS=$((BLOCKERS + 1))
        fi
    else
        echo "  [WARN]    missing optional script: $( basename "$pyf" )"
        WARNINGS=$((WARNINGS + 1))
    fi
done
echo ""

# --- Phase 0.8: efficiency-config + chain-depth regression gate (v0.8.0) ---
#
# Landed at v0.8.0 Phase 1.1 (α Tier A) per
# proposals/v0.8.0_upgrade_architecture.md §3.2. Enforces two conditions:
#
#   (a) `.plugin-efficiency.json` is present at plugin root. This is the
#       authoritative pin of model rates, thresholds, and role overrides that
#       the calibrator reads for cost and speed estimates. Its absence is the
#       `efficiency_config_missing` MINOR the v0.7.4.1 audit flagged; at v0.8.0
#       it is a BLOCKER.
#   (b) When the plugin-calibrator CLI is reachable, `audit-package-speed`
#       reports `max_subagent_chain_depth` within the config's
#       `thresholds.max_chain_depth` ceiling (default 15). The ceiling is
#       matched against the alias-removal floor — v0.7.4.1 measured 19 hops on
#       the dual-surface `run-tier-*` / `run-phase-*` graph; v0.8.0 Phase 1.2
#       removed the deprecated aliases, dropping the measured depth into the
#       12–15 band.
#
# Placeholder discipline: if `input_tokens_per_second` reads 2000 (the
# hand-authored draft placeholder per proposals/drafts/v0.7.6_hand_authored
# _route/README.md §Honesty notes), the gate emits a WARN on authoring runs
# and a BLOCKER on ship-intent runs (invoke with --ship-intent). The v0.8.0
# release-gate §3.3 condition 4 refuses to pass until a measured-throughput
# figure replaces the placeholder; no wall-clock or per-round cost figure may
# be quoted externally before this amendment lands (decision D-3 closed
# 2026-04-22).
#
# Calibrator discovery order (first match wins):
#   1. $PLUGIN_CALIBRATOR_BIN — explicit opt-in path.
#   2. `plugin-calibrator` on PATH.
#   3. $PEER_ROOT/*/scripts/plugin_quality_check.py — sibling-plugin layout.
# On no-match, the chain-depth regression gate WARN-skips with an explicit
# message; absence is not a BLOCKER because the calibrator may not ship on
# every release host.

echo "Efficiency-config + chain-depth regression gate (v0.8.0)"
EFFICIENCY_CONFIG="$PLUGIN_ROOT/.plugin-efficiency.json"

if [[ ! -f "$EFFICIENCY_CONFIG" ]]; then
    echo "  [BLOCKER] .plugin-efficiency.json missing at plugin root"
    echo "            Clears v0.7.4.1 audit 'efficiency_config_missing' MINOR; required at v0.8.0."
    BLOCKERS=$((BLOCKERS + 1))
else
    echo "  [OK]      .plugin-efficiency.json present"

    TOKS_PER_SEC=$( python3 -c "
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
print(d.get('input_tokens_per_second', 'missing'))
" "$EFFICIENCY_CONFIG" 2>/dev/null )

    if [[ "$TOKS_PER_SEC" == "2000" ]]; then
        if (( SHIP_INTENT == 1 )); then
            echo "  [BLOCKER] input_tokens_per_second == 2000 (hand-authored draft placeholder)"
            echo "            Decision D-3 binds: measured throughput must replace the placeholder"
            echo "            before the release-gate passes under --ship-intent."
            BLOCKERS=$((BLOCKERS + 1))
        else
            echo "  [WARN]    input_tokens_per_second == 2000 (placeholder; authoring-phase tolerated)"
            echo "            Replace with measured throughput before --ship-intent or external quote."
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        echo "  [OK]      input_tokens_per_second == $TOKS_PER_SEC (measured or custom)"
    fi

    MAX_CHAIN=$( python3 -c "
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
print(d.get('thresholds', {}).get('max_chain_depth', 15))
" "$EFFICIENCY_CONFIG" 2>/dev/null )

    CALIBRATOR_BIN=""
    if [[ -n "${PLUGIN_CALIBRATOR_BIN:-}" && -x "${PLUGIN_CALIBRATOR_BIN}" ]]; then
        CALIBRATOR_BIN="$PLUGIN_CALIBRATOR_BIN"
    elif command -v plugin-calibrator >/dev/null 2>&1; then
        CALIBRATOR_BIN="plugin-calibrator"
    elif [[ -f "$PLUGIN_ROOT/scripts/plugin_calibrator_audit.py" ]]; then
        CALIBRATOR_BIN="python3 $PLUGIN_ROOT/scripts/plugin_calibrator_audit.py"
    elif [[ -n "$PEER_ROOT" && -d "$PEER_ROOT" ]]; then
        for cand in "$PEER_ROOT"/*/scripts/plugin_quality_check.py; do
            [[ -f "$cand" ]] || continue
            CALIBRATOR_BIN="python3 $cand"
            break
        done
    fi

    if [[ -z "$CALIBRATOR_BIN" ]]; then
        echo "  [WARN]    chain-depth regression gate skipped: calibrator CLI not found"
        echo "            (set PLUGIN_CALIBRATOR_BIN, or install plugin-calibrator on PATH)"
        WARNINGS=$((WARNINGS + 1))
    else
        echo "  [INFO]    running audit-package-speed via: $CALIBRATOR_BIN"
        set +e
        SPEED_JSON=$( $CALIBRATOR_BIN audit-package-speed --target-root "$PLUGIN_ROOT" --json 2>/dev/null )
        RC=$?
        set -e
        if [[ "$RC" -ne 0 || -z "$SPEED_JSON" ]]; then
            echo "  [WARN]    audit-package-speed invocation failed (rc=$RC); gate not evaluated"
            WARNINGS=$((WARNINGS + 1))
        else
            MEASURED_DEPTH=$( python3 -c "
import json, sys
d = json.loads(sys.argv[1])
print(d.get('max_subagent_chain_depth', 'missing'))
" "$SPEED_JSON" 2>/dev/null )
            if [[ "$MEASURED_DEPTH" == "missing" || "$MEASURED_DEPTH" == "" ]]; then
                echo "  [WARN]    audit-package-speed did not report max_subagent_chain_depth"
                WARNINGS=$((WARNINGS + 1))
            elif (( MEASURED_DEPTH > MAX_CHAIN )); then
                echo "  [BLOCKER] max_subagent_chain_depth=$MEASURED_DEPTH exceeds ceiling $MAX_CHAIN"
                echo "            Either raise the ceiling in .plugin-efficiency.json after"
                echo "            architectural review, or resolve the chain-depth regression."
                BLOCKERS=$((BLOCKERS + 1))
            else
                echo "  [OK]      max_subagent_chain_depth=$MEASURED_DEPTH <= ceiling $MAX_CHAIN"
            fi
        fi
    fi
fi
echo ""

# --- Phase 1: build the bundle --------------------------------------------

BUNDLE_PATH=""
if (( BUILD == 1 )); then
    # NAME AND VERSION COME FROM COMMITTED HEAD, not the worktree. The bundle
    # packages HEAD bytes, so a worktree-derived filename could disagree with
    # the embedded manifest (verified: dirty v0.30.0 bump -> v0.30.0-named
    # zip carrying a v0.29.0 manifest). One source for both.
    HEAD_MANIFEST_JSON=$( git -C "$PLUGIN_ROOT" show HEAD:.claude-plugin/plugin.json 2>/dev/null ) || {
        echo "  [BLOCKER] cannot read HEAD:.claude-plugin/plugin.json"
        BLOCKERS=$((BLOCKERS + 1))
        HEAD_MANIFEST_JSON=""
    }
    HEAD_NAME=$( printf '%s' "$HEAD_MANIFEST_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('name',''))" 2>/dev/null || true )
    HEAD_VERSION=$( printf '%s' "$HEAD_MANIFEST_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('version',''))" 2>/dev/null || true )
    BUNDLE_NAME="${HEAD_NAME:-$CURRENT_NAME}-v${HEAD_VERSION:-$CURRENT_VERSION}.zip"
    BUNDLE_PATH="/tmp/$BUNDLE_NAME"

    # ONE POPULATION AUTHORITY. This phase used to run its own `zip -r` over
    # the WORKTREE with exclusion globs -- a second, independent package
    # population (worktree bytes, raw include sentinels) beside
    # scripts/package_enumeration.py (HEAD bytes, rendered includes). Two
    # rules over one repo meant "drift impossible by construction" was FALSE,
    # and the release zip shipped UNRESOLVED include sentinels that Phase
    # 0.60's snippet guard had only verified resolvABLE, never resolved.
    #
    # The committed builder is now the only bundle producer: commit-bound
    # bytes via clean-worktree re-exec, rendered includes, embedded
    # PROVENANCE.json with its own readback. Consequence, intended: a DIRTY
    # manifest now blocks below (the bundle carries HEAD's manifest, the
    # source comparison reads the worktree) -- a release must be a commit.
    echo "Building bundle via the committed builder: $BUNDLE_PATH"
    rm -f "$BUNDLE_PATH"
    set +e
    ( cd "$PLUGIN_ROOT" && python3 scripts/build-plugin.py )
    BUILD_RC=$?
    set -e
    PLUGIN_ARTIFACT="$PLUGIN_ROOT/.claude-plugin/${HEAD_NAME:-$CURRENT_NAME}.plugin"
    if (( BUILD_RC != 0 )); then
        echo "  [BLOCKER] build-plugin.py exited $BUILD_RC (contract: 5 provenance"
        echo "            readback failed, 6 child produced no bundle, 7 worktree"
        echo "            cleanup VOID -- see scripts/build-plugin.py docstring)"
        BLOCKERS=$((BLOCKERS + 1))
        BUNDLE_PATH=""
    elif [[ ! -f "$PLUGIN_ARTIFACT" ]]; then
        echo "  [BLOCKER] builder exited 0 but no artifact at $PLUGIN_ARTIFACT"
        BLOCKERS=$((BLOCKERS + 1))
        BUNDLE_PATH=""
    else
        cp "$PLUGIN_ARTIFACT" "$BUNDLE_PATH"
        echo "  Built: $( ls -la "$BUNDLE_PATH" | awk '{print $5" bytes"}' )"

        # EXACT-DIGEST manifest reconciliation, two independent claims:
        #
        # (1) archive manifest == HEAD manifest -- via the shared verifier
        #     (scripts/release_manifest_check.py). The old check compared
        #     version + description LENGTH against the WORKTREE, so a
        #     same-length description mutation or a keyword-only change
        #     passed, and a dirty version bump named the zip wrongly.
        # (2) worktree manifest == HEAD manifest -- a dirty manifest blocks:
        #     a release must be a commit.
        if python3 "$PLUGIN_ROOT/scripts/release_manifest_check.py" "$BUNDLE_PATH" --repo "$PLUGIN_ROOT"; then
            echo "  [OK]      archive manifest == committed HEAD manifest (digest-exact)"
        else
            echo "  [BLOCKER] archive manifest does not match committed HEAD manifest"
            BLOCKERS=$((BLOCKERS + 1))
        fi
        # Git is the authority on "modified" (raw byte hashes false-block
        # under CRLF normalization); porcelain output empty == committed.
        MANIFEST_DIRTY=$( git -C "$PLUGIN_ROOT" status --porcelain -- .claude-plugin/plugin.json 2>/dev/null || echo "STATUS-FAILED" )
        if [[ -z "$MANIFEST_DIRTY" ]]; then
            echo "  [OK]      worktree manifest is committed (no dirty manifest)"
        else
            echo "  [BLOCKER] worktree manifest differs from HEAD: a release must be a commit ($MANIFEST_DIRTY)"
            BLOCKERS=$((BLOCKERS + 1))
        fi

        NESTED_ARCHIVES=$( unzip -Z1 "$BUNDLE_PATH" | grep -Ec '\.(plugin|zip)$' || true )
        LOCAL_CLAUDE_STATE=$( unzip -Z1 "$BUNDLE_PATH" | grep -Ec '(^|/)\.claude/' || true )
        if [[ "$NESTED_ARCHIVES" -eq 0 && "$LOCAL_CLAUDE_STATE" -eq 0 ]]; then
            echo "  [OK]      bundle excludes nested archives and local .claude state"
        else
            echo "  [BLOCKER] bundle contains nested archives=$NESTED_ARCHIVES local_claude_state=$LOCAL_CLAUDE_STATE"
            BLOCKERS=$((BLOCKERS + 1))
        fi

        # Independent artifact check: the embedded provenance must name the
        # repo's CURRENT HEAD. The builder's own readback ran inside the
        # build; this one interrogates the finished RELEASE COPY -- verify
        # the artifact, not the process that claims to have made it.
        PROV_COMMIT=$( unzip -p "$BUNDLE_PATH" PROVENANCE.json \
            | python3 -c "import json,sys; print(json.load(sys.stdin).get('commit',''))" 2>/dev/null || true )
        HEAD_SHA=$( git -C "$PLUGIN_ROOT" rev-parse HEAD 2>/dev/null || true )
        if [[ -n "$PROV_COMMIT" && -n "$HEAD_SHA" && "$PROV_COMMIT" == "$HEAD_SHA" ]]; then
            echo "  [OK]      PROVENANCE.json commit matches HEAD (${HEAD_SHA:0:12})"
        else
            echo "  [BLOCKER] PROVENANCE.json commit '${PROV_COMMIT:0:12}' != HEAD '${HEAD_SHA:0:12}'"
            BLOCKERS=$((BLOCKERS + 1))
        fi
    fi
    echo ""
fi

# --- Phase 2: outputs-dir staleness check ---------------------------------

if [[ -n "$OUTPUTS_DIR" && -d "$OUTPUTS_DIR" ]]; then
    echo "Outputs directory staleness check: $OUTPUTS_DIR"
    # Any plugin-related file not matching the current bundle name is a candidate stale file.
    STALE_FOUND=0
    for f in "$OUTPUTS_DIR"/${CURRENT_NAME}*.plugin "$OUTPUTS_DIR"/${CURRENT_NAME}*.zip; do
        [[ -f "$f" ]] || continue
        fname=$( basename "$f" )
        if [[ -n "$BUNDLE_PATH" && "$fname" != "$( basename "$BUNDLE_PATH" )" ]]; then
            echo "  [WARN]    stale: $f"
            echo "            Consider: mcp__cowork__allow_cowork_file_delete (rm is blocked in /mnt/outputs/)"
            STALE_FOUND=1
            WARNINGS=$((WARNINGS + 1))
        fi
    done
    if (( STALE_FOUND == 0 )); then
        echo "  [OK]      no stale deliverables under superseded names"
    fi
    echo ""
fi

# --- Verdict ---------------------------------------------------------------

echo "============================================================"
if (( BLOCKERS > 0 )); then
    echo "VERDICT: BLOCKED — $BLOCKERS blocker(s), $WARNINGS warning(s)"
    exit 1
elif (( WARNINGS > 0 )); then
    echo "VERDICT: CLEARED-WITH-WARNINGS — 0 blockers, $WARNINGS warning(s)"
    exit 0
else
    echo "VERDICT: CLEARED — 0 blockers, 0 warnings"
    exit 0
fi
