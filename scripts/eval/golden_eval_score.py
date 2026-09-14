#!/usr/bin/env python3
"""Score located findings; regression evidence is not research acceptance.

python scripts/eval/golden_eval_score.py findings.json [--baseline score.json]

Findings need exact code families (M-n aliases C-8/M-n), severity, and a
one-based source line. Blinding removes comments but preserves newlines.
Unbaselined measurements exit 0 with gate_passed=false; --require-baseline
refuses them. Invalid inputs exit 2; comparable regressions exit 1.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
PLUGIN_ROOT = HERE.parents[2]
MANIFEST = PLUGIN_ROOT / 'scripts/fixtures/golden/manifest.json'
CODE = r'(?:C-[1-8](?:/(?:M-[1-7]|Check8-[A-J]))?|M-[1-7])'


def norm_code(code: str) -> str:
    if not isinstance(code, str):
        raise ValueError('finding code must be text')
    code = re.sub(r'^\[\s*(BLOCKER|MAJOR|MINOR)\s*[—–-]\s*', '', code.strip())
    code = code.rstrip(']').strip().replace('<->', '↔')
    if not re.fullmatch(CODE + r'(?:↔' + CODE + r')*', code):
        raise ValueError('invalid finding code: ' + repr(code))
    return '↔'.join('C-8/' + part if part.startswith('M-') else part
                    for part in code.split('↔'))


def family_match(expected: str, found: str) -> bool:
    return norm_code(expected) == norm_code(found)


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode('utf-8')).hexdigest()


def blind_text(text: str) -> str:
    """Remove answer-bearing comments, retaining source line coordinates."""
    text = re.sub(r'<!--.*?-->', lambda match: '\n' * match.group().count('\n'),
                  text, flags=re.DOTALL)
    return re.sub(r'\A# Golden fixture[^\r\n]*', '# Manuscript excerpt', text)


def score(findings_doc: dict, manifest: dict) -> dict:
    if not isinstance(findings_doc, dict):
        raise ValueError('findings must be a JSON object')
    fixture = findings_doc.get('fixture')
    fx = manifest['fixtures'].get(fixture)
    if fx is None:
        raise ValueError('unknown fixture: ' + repr(fixture))
    if not isinstance(findings_doc.get('pass'), str) or not findings_doc['pass'].strip():
        raise ValueError('pass must identify the actual evaluator/skill')
    findings = findings_doc.get('findings')
    if not isinstance(findings, list):
        raise ValueError('findings must be an explicit list')
    source = MANIFEST.parent / fixture
    if source.parent != MANIFEST.parent or not source.is_file():
        raise ValueError('fixture must be a local registered file')
    source_text = source.read_text(encoding='utf-8')
    lines = blind_text(source_text).splitlines()
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError('each finding must be an object')
        norm_code(finding.get('finding_code'))
        if finding.get('severity') not in ('BLOCKER', 'MAJOR', 'MINOR'):
            raise ValueError('finding severity is invalid')
        line = finding.get('line')
        if type(line) is not int or not 1 <= line <= len(lines) or not lines[line - 1].strip():
            raise ValueError('finding line must locate a nonempty blinded source line')
    evaluator = findings_doc.get('evaluator')
    if evaluator is not None and (not isinstance(evaluator, dict) or any(
            not isinstance(evaluator.get(k), str) or not evaluator[k].strip()
            for k in ('host', 'model', 'configuration'))):
        raise ValueError('evaluator needs host, model and configuration identities')
    out = {
        'schema': 'golden-eval-score/v2', 'fixture': fixture,
        'pass': findings_doc['pass'], 'role': fx['role'], 'evaluator': evaluator,
        'fixture_sha256': hashlib.sha256(source_text.encode('utf-8')).hexdigest(),
        'manifest_sha256': _digest({'fixture': fx, 'contract': manifest['findings_file_schema']}),
        'scorer_sha256': hashlib.sha256(HERE.read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
        'baseline_status': 'not_supplied', 'gate_passed': False,
        'judgment_quality_qualified': False, 'research_acceptance': False,
    }
    if fx['role'] == 'detection':
        unmatched = list(range(len(findings)))
        hits = {}
        for defect in fx['defects']:
            candidates = [i for i in unmatched if
                          family_match(defect['expected_code_family'], findings[i]['finding_code'])
                          and findings[i]['line'] == defect['line']]
            hits[defect['defect_id']] = bool(candidates)
            if candidates:
                unmatched.remove(candidates[0])
        out.update(per_defect=hits, recall=round(sum(hits.values()) / len(hits), 3),
                   extra_findings=len(unmatched))
    elif fx['role'] == 'false-positive-control':
        gated = manifest['findings_file_schema']['p2_gated_families']
        fps = [f for f in findings if any(family_match(g, f['finding_code']) for g in gated)]
        out.update(false_positives=len(fps), false_positive_codes=[f['finding_code'] for f in fps])
    else:
        raise ValueError('unknown fixture role')
    return out


def compare_baseline(result: dict, baseline: dict) -> bool:
    keys = ('schema', 'fixture', 'pass', 'role', 'evaluator', 'fixture_sha256',
            'manifest_sha256', 'scorer_sha256')
    if not isinstance(baseline, dict) or not result['evaluator'] or any(
            baseline.get(k) != result[k] for k in keys):
        raise ValueError('baseline fixture, evaluator or scoring bindings differ')
    metrics = ('recall', 'extra_findings') if result['role'] == 'detection' else ('false_positives',)
    for key in metrics:
        value = baseline.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('baseline metric is missing or invalid: ' + key)
        if key == 'recall' and value > 1:
            raise ValueError('baseline recall exceeds 1')
    regressed = any(result[k] < baseline[k] if k == 'recall' else result[k] > baseline[k]
                    for k in metrics)
    result.update(baseline_status='comparable', gate_passed=not regressed,
                  regression_status='regressed' if regressed else 'no_regression')
    return regressed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('findings', type=Path, nargs='?')
    ap.add_argument('--blind-fixture', choices=('golden_p2_theory.md', 'golden_p1_brief.md'))
    ap.add_argument('--baseline', type=Path)
    ap.add_argument('--require-baseline', action='store_true')
    args = ap.parse_args()
    try:
        if args.blind_fixture:
            if args.findings or args.baseline or args.require_baseline:
                raise ValueError('blinding and scoring are separate operations')
            print(blind_text((MANIFEST.parent / args.blind_fixture).read_text(encoding='utf-8')), end='')
            return 0
        if not args.findings:
            raise ValueError('supply findings or --blind-fixture')
        result = score(json.loads(args.findings.read_text(encoding='utf-8')),
                       json.loads(MANIFEST.read_text(encoding='utf-8')))
        if args.require_baseline and not args.baseline:
            raise ValueError('baseline is required for this gate')
        regressed = compare_baseline(result, json.loads(args.baseline.read_text(encoding='utf-8'))) if args.baseline else False
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 1 if regressed else 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'invalid', 'gate_passed': False, 'message': str(exc)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
