#!/usr/bin/env python3
"""Optional overlay evidence attachment; a binding is not substantive judgment."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import piw_session as piw

REASON_MISSING_EVIDENCE = 'OVERLAY_MISSING_EVIDENCE'
REASON_GRAPH_AUTHORITY = 'GRAPH_AUTHORITY_UNAVAILABLE'
REASON_ACCESSIBILITY_CONTEXT = 'ACCESSIBILITY_CONTEXT_UNRESOLVED'
REASON_NOT_REQUIRED = 'OVERLAY_NOT_REQUIRED_FOR_PIW_COMPLETION'


def attach_overlay(piw_session: Path, *, overlay='graph-grounding', evidence_present=False, evidence_path: Path | None = None) -> dict:
    checked = piw.validate_session(piw_session)
    root = Path(checked['staging_root'])
    contract = piw.read_json(root / 'binding/run.json') if (root / 'binding/run.json').is_file() else {}
    excluded = 'chung' in overlay.lower() and 'chung-academic-voice-pass' in contract.get('exclusions', [])
    if evidence_present and evidence_path is None:
        raise piw.PIWError('PIW-OVERLAY-EVIDENCE-REQUIRED', 'A flag is not actual overlay/source evidence; supply an inspectable evidence file')
    binding = piw.identity(evidence_path) if evidence_path is not None else None
    reason = 'PIW-OVERLAY-EXCLUDED' if excluded else (REASON_GRAPH_AUTHORITY if overlay.startswith('graph') else REASON_ACCESSIBILITY_CONTEXT) if binding is None else None
    payload = {'ok': True, 'status': 'noop' if excluded or binding is None else 'bound_not_reviewed', 'overlay': overlay,
               'reason_code': reason, 'evidence': binding, 'completion': False, 'task_complete': False,
               'required_for_piw_completion': False, 'exclusions': contract.get('exclusions', []),
               'message': 'Overlay attachment never establishes a prose verdict. Source-based centroid judgment must use the source admission/check path; graph eligibility is a separate capability.', 'at': piw.utc_now()}
    name = ''.join(x if x.isalnum() or x in '-_' else '_' for x in overlay)
    path = root / 'overlays' / (name + '-' + piw.mint_work_id() + '.json')
    piw.write_json(path, payload)
    return {**payload, 'path': str(path)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--piw-session', required=True, type=Path)
    ap.add_argument('--overlay', default='graph-grounding')
    ap.add_argument('--evidence-present', action='store_true')
    ap.add_argument('--evidence-path', type=Path)
    args = ap.parse_args(argv)
    try:
        result = attach_overlay(args.piw_session, overlay=args.overlay, evidence_present=args.evidence_present, evidence_path=args.evidence_path)
    except (piw.PIWError, OSError, ValueError) as exc:
        result = {'ok': False, 'code': getattr(exc, 'code', 'PIW-EVIDENCE-MISSING'), 'message': str(exc), 'completion': False}
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result['ok'] else 4

if __name__ == '__main__':
    raise SystemExit(main())
