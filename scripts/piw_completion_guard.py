#!/usr/bin/env python3
"""Evidence-bound task completion and protected-destination/lifecycle refusal helpers.

None of the following establish PIW completion, terminal PASS, CLEAN, or accept:
  - binding packet emission
  - simulated roles
  - incomplete reviews
  - file presence of staging folders
  - readable legacy artifacts
  - overlay no-ops or findings alone
  - project_independent scope declaration alone
  - optional Writer apply presence/absence

PIW coordinators must refuse direct Workbench manuscript destination writes
(DEST-PROTECTED). Writer apply is a separate optional escalation, never PIW
completion (AT-9, AT-10).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import destination_capability as destination  # noqa: E402
import invocation_scope as invocation  # noqa: E402

try:
    import piw_session as piw_session  # noqa: E402
except ImportError:  # pragma: no cover
    piw_session = None  # type: ignore


FAKE_COMPLETION_SIGNALS = (
    "binding_packet",
    "simulated_role",
    "incomplete_review",
    "file_presence",
    "legacy_artifact",
    "overlay_noop",
    "overlay_finding",
    "scope_declaration",
    "writer_apply",
    "writer_apply_absent",
    "piw_receipt",
    "chat_apply",
)


def verify_completion(session_path: Path | str) -> dict[str, Any]:
    """Revalidate substantive role outputs, original host traces, order and bytes.

    Host JSONL integrity is trusted, not authenticated by self-written receipts.
    This grants task completion only; it cannot grant research/lifecycle authority.
    """
    import piw_coordinator as coordinator
    import piw_session as piw
    try:
        contract, root, log, state = coordinator.replay(session_path)
        if state['stage'] != 'ready_to_deliver':
            code = 'PIW-NEEDS-REVISION' if state['stage'] == 'needs_revision' else 'PIW-INCOMPLETE'
            raise piw.PIWError(code, 'Required role work remains: ' + state['stage'])
        delivery_path = root / 'binding/delivery.json'
        if not delivery_path.is_file():
            raise piw.PIWError('PIW-DELIVERY-MISSING', 'Exact reviewed bytes have not been delivered')
        delivery = piw.read_json(delivery_path)
        if delivery.get('run_id') != contract['run_id'] or delivery.get('candidate') != state['candidate']:
            raise piw.PIWError('PIW-DELIVERY-MISMATCH', 'Delivery is not this run final candidate')
        coordinator._fresh(delivery['artifact'], 'PIW-FINAL-BYTES-STALE')
        if any(delivery['artifact'][k] != state['candidate'][k] for k in ('sha256', 'bytes')):
            raise piw.PIWError('PIW-FINAL-BYTES-STALE', 'Delivered bytes differ from the independently reviewed candidate')
        role_events = [x for x in log['events'] if x['kind'] == 'role']
        results = [(x, piw.read_json(x['result']['path'])) for x in role_events]
        reviews = [(e, r) for e, r in results if r['phase'] == 'evaluation']
        reflections = [(e, r) for e, r in results if r['phase'] == 'reflection']
        generations = [(e, r) for e, r in results if r['role'] == 'generator']
        if not reviews or not reflections or not generations:
            raise piw.PIWError('PIW-REQUIRED-EVIDENCE-MISSING', 'Generation, independent final evaluation and reflection are required')
        for _, result in (reviews[-1], reflections[-1]):
            if result['target'] != state['candidate']:
                raise piw.PIWError('PIW-FINAL-REVIEW-STALE', 'Final review/reflection did not inspect delivered bytes')
        if state['unresolved_findings']:
            raise piw.PIWError('PIW-NEEDS-REVISION', 'Unresolved blocking findings remain')
        return {'ok': True, 'status': 'task_complete', 'code': 'PIW-TASK-COMPLETE', 'task_complete': True,
                'completion': True, 'piw_work_id': contract['run_id'], 'run_id': contract['run_id'],
                'artifact_sha256': delivery['artifact']['sha256'], 'artifact_bytes': delivery['artifact']['bytes'],
                'artifact': delivery['artifact'], 'input': contract['input'], 'requested_scope': contract['requested_scope'],
                'proposal_only': contract['proposal_only'], 'profile': contract.get('profile'), 'project_context': contract.get('project_context'), 'venue': contract.get('venue'), 'rules': contract['rules'], 'applied_passes': contract['passes'],
                'exclusions': contract['exclusions'], 'source_excerpts': contract['source_excerpts'],
                'generator_execution_id': state['generator_execution_id'], 'evaluator_execution_id': reviews[-1][1]['agent_execution_id'],
                'reflection_execution_id': reflections[-1][1]['agent_execution_id'],
                'evidence': role_events, 'evaluation': reviews[-1][0]['result'], 'reflection': reflections[-1][0]['result'],
                'checks': reviews[-1][1]['checks'], 'unresolved_blocking_findings': [], 'limitations': state['limitations'],
                'bibliography_status': ('not_assessed_prose_only' if contract.get('review_scope') == 'prose_only' else
                                        'assessed' if any(x['id'] == 'bibliography' and x['status'] == 'pass' for x in reviews[-1][1]['checks']) else 'not_applicable'),
                'change_summary': generations[-1][1]['summary'], 'correction_cycles': state['corrections'],
                'lifecycle_terminal': False, 'research_acceptance': False, 'terminal': False, 'clean': False,
                'trust_boundary': contract['host']['trust_boundary']}
    except (piw.PIWError, OSError, ValueError, KeyError, TypeError) as exc:
        return {'ok': False, 'status': 'needs_revision' if getattr(exc, 'code', '') == 'PIW-NEEDS-REVISION' else 'incomplete',
                'code': getattr(exc, 'code', 'PIW-REQUIRED-EVIDENCE-MISSING'), 'message': str(exc), 'task_complete': False,
                'completion': False, 'lifecycle_terminal': False, 'research_acceptance': False, 'terminal': False}


def evaluate_completion_claim(claim: dict[str, Any] | str | None) -> dict[str, Any]:
    if isinstance(claim, str):
        claim = {'signal': claim}
    claim = claim or {}
    if any(claim.get(x) for x in ('terminal', 'terminal_claim', 'lifecycle_terminal', 'promotion', 'research_acceptance')):
        return refuse_terminal_from_piw(claim)
    if claim.get('clean'):
        return refuse_clean_mint()
    signal = str(claim.get('signal') or claim.get('kind') or claim.get('type') or '').lower()
    if signal in FAKE_COMPLETION_SIGNALS or any(claim.get(x) is True for x in FAKE_COMPLETION_SIGNALS):
        return {'ok': False, 'code': 'PIW-FAKE-COMPLETION', 'completion': False, 'task_complete': False,
                'message': 'Flags, file presence and role labels do not establish performed cognitive work'}
    if claim.get('piw_session'):
        return verify_completion(claim['piw_session'])
    return {'ok': False, 'code': 'PIW-FAKE-COMPLETION' if any(claim.get(x) for x in ('completion', 'complete', 'task_complete')) else 'PIW-INCOMPLETE',
            'completion': False, 'task_complete': False, 'message': 'Supply a session with independently inspectable completed evidence'}


def refuse_clean_mint(actor: str = "coordinator") -> dict[str, Any]:
    return {
        "ok": False,
        "clean": False,
        "code": "PIW-CLEAN-FORBIDDEN",
        "message": f"{actor} may not mint scholarly CLEAN under project_independent",
    }


def refuse_terminal_from_piw(evidence: Any = None) -> dict[str, Any]:
    return {
        "ok": False,
        "terminal": False,
        "code": invocation.FRC_PIW_NON_TERMINAL,
        "message": (
            "PIW receipts / staging evidence cannot satisfy full_run_contract_check "
            "terminal / 15-gate claims"
        ),
        "evidence_type": type(evidence).__name__ if evidence is not None else None,
    }


def is_workbench_manuscript_path(path: os.PathLike | str) -> bool:
    """Heuristic: research/60_Workbench/<id>/manuscript/... under a governed root."""
    try:
        parts = Path(os.path.realpath(os.fspath(path))).parts
    except OSError:
        parts = Path(os.fspath(path)).parts
    lowered = [p.casefold() for p in parts]
    for i in range(len(lowered) - 2):
        if (
            lowered[i] == "research"
            and lowered[i + 1] == "60_workbench"
            and "manuscript" in lowered[i + 2 :]
        ):
            return True
    return False


def refuse_workbench_manuscript_write(destination_path: os.PathLike | str, *, purpose: str = 'PIW coordinator write') -> dict[str, Any]:
    import piw_session as piw
    try:
        kind = piw.assert_output(Path(destination_path))
        return {'ok': True, 'code': 'OK', 'kind': kind, 'destination': str(destination_path), 'completion': False}
    except piw.PIWError as exc:
        return {'ok': False, 'code': exc.code, 'message': str(exc), 'destination': str(destination_path), 'completion': False}


def writer_apply_is_not_completion(apply_receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    """AT-10: optional Writer apply is a separate transaction, never PIW completion."""
    return {
        "ok": True,
        "piw_completion": False,
        "terminal": False,
        "code": "PIW-WRITER-APPLY-SEPARATE",
        "message": (
            "Writer apply (present or absent) is not PIW completion and does not "
            "convert PIW into full_lifecycle terminal evidence"
        ),
        "apply_present": bool(apply_receipt),
    }


def guard_session_claims(session: dict[str, Any]) -> dict[str, Any]:
    """Binding / session object alone never completes."""
    return evaluate_completion_claim({
        "signal": "binding_packet",
        "scope": session.get("scope"),
        "piw_work_id": session.get("piw_work_id") or session.get("work_id"),
    })


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check-claim", help="evaluate a fake-completion claim JSON")
    c.add_argument("--claim-json", required=True, help="JSON object or path to JSON file")

    d = sub.add_parser("refuse-dest", help="DEST-PROTECTED check for a write destination")
    d.add_argument("--destination", required=True)

    t = sub.add_parser("refuse-terminal", help="refuse PIW-as-terminal")
    t.add_argument("--note", default="")

    wri = sub.add_parser("writer-apply", help="confirm writer apply is not PIW completion")
    wri.add_argument("--apply-json", default=None)

    verify = sub.add_parser('verify', help='Revalidate exact delivered bytes and actual host role evidence')
    verify.add_argument('--piw-session', required=True)

    args = ap.parse_args(argv)

    if args.cmd == 'verify':
        result = verify_completion(args.piw_session)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0 if result.get('task_complete') else 4

    if args.cmd == "check-claim":
        raw = args.claim_json
        path = Path(raw) if not raw.lstrip().startswith("{") else None
        if path is not None and path.is_file():
            claim = json.loads(path.read_text(encoding="utf-8"))
        else:
            claim = json.loads(raw)
        result = evaluate_completion_claim(claim)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("ok") and result.get("completion") else 4

    if args.cmd == "refuse-dest":
        result = refuse_workbench_manuscript_write(args.destination)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("ok") else 4

    if args.cmd == "refuse-terminal":
        result = refuse_terminal_from_piw(args.note)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 4

    if args.cmd == "writer-apply":
        apply_receipt = None
        if args.apply_json:
            p = Path(args.apply_json)
            apply_receipt = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else json.loads(args.apply_json)
        result = writer_apply_is_not_completion(apply_receipt)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        # ok True but piw_completion False -- exit 0 for the separation assertion
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
