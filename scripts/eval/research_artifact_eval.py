"""Prepare blinded tasks and validate separately adjudicated artifact measurements."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import piw_session as piw

ROOT = Path(__file__).resolve().parents[1] / 'fixtures/research_artifacts'
MANIFEST = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))


def require(condition, message):
    if not condition: raise ValueError(message)


def case_spec(case):
    found = [c for c in MANIFEST['cases'] if c['id'] == case]
    require(len(found) == 1, 'Unknown benchmark case')
    return found[0]


def prepare(case):
    spec = case_spec(case)
    names = [MANIFEST['source_file']] + ([spec['input_file']] if spec.get('input_file') else [])
    inputs = []
    for name in names:
        data = (ROOT / name).read_bytes()
        inputs.append({'name': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'text': data.decode('utf-8')})
    packet = {k: spec[k] for k in ('id', 'artifact', 'brief', 'editable_section') if k in spec}
    packet.update(inputs=inputs, evidence_kind=MANIFEST['evidence_kind'])
    return {'packet': packet, 'packet_sha256': piw.digest(piw.json_bytes(packet)), 'quality_qualified': False}


def score(submission, review=None, expected_sha256=None, review_bytes=None):
    spec = case_spec(submission['case'])
    require(submission['packet_sha256'] == prepare(spec['id'])['packet_sha256'], 'Task packet changed')
    artifact = submission['artifact']
    actual = piw.identity(Path(artifact['path']))
    require(actual['bytes'] > 0 and all(actual[k] == artifact[k] for k in ('sha256', 'bytes')), 'Artifact differs from submitted bytes')
    require(submission.get('execution_kind') in ('live_host', 'synthetic_fixture'), 'Declare live_host or synthetic_fixture evidence')
    require(all(isinstance(submission.get('host', {}).get(k), str) and submission['host'][k].strip() for k in ('adapter', 'model', 'configuration')), 'Bind host and evaluator configuration')
    result = {'schema_version': 'research-artifact-score/v1', 'case': spec['id'], 'packet_sha256': submission['packet_sha256'],
              'rubric_sha256': piw.digest(piw.json_bytes(MANIFEST)), 'artifact': actual, 'host': submission['host'],
              'execution_kind': submission['execution_kind'], 'adjudication_status': 'not_supplied',
              'case_thresholds_passed': False, 'quality_qualified': False, 'host_qualified': False, 'research_acceptance': False}
    if review is None: return result
    raw = review_bytes if review_bytes is not None else piw.json_bytes(review)
    require(json.loads(raw) == review and piw.digest(raw) == expected_sha256, 'Adjudication bytes differ from the separately retained digest')
    require(review['case'] == spec['id'] and review['artifact_sha256'] == actual['sha256'], 'Adjudication targets another case or artifact')
    require(review.get('reviewer', {}).get('kind') == 'human' and bool(review['reviewer'].get('identity')), 'A human reference assessment is required')
    scores = review['scores']
    require(set(scores) == set(MANIFEST['dimensions']), 'Assess every required dimension exactly once')
    for item in scores.values():
        require(type(item.get('value')) is int and 0 <= item['value'] <= 4 and len(item.get('rationale', '').strip()) >= 20
                and isinstance(item.get('locators'), list) and item['locators'] and all(isinstance(x, str) and x.strip() for x in item['locators']),
                'Each score needs a 0..4 integer, substantive reason and artifact locators')
    failures = review['critical_failures']
    require(isinstance(failures, list) and all(x in MANIFEST['critical_failures'] for x in failures), 'Unknown critical failure')
    thresholds = not failures and all(x['value'] >= MANIFEST['minimum_per_dimension'] for x in scores.values())
    result.update(adjudication_status='supplied_declared_human', adjudication_sha256=piw.digest(raw), scores=scores,
                  critical_failures=failures, case_thresholds_passed=thresholds and submission['execution_kind'] == 'live_host',
                  trust_boundary='Caller must independently know the adjudicator and establish native execution; labels and hashes are not authentication.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    task = sub.add_parser('prepare'); task.add_argument('--case', required=True)
    scored = sub.add_parser('score'); scored.add_argument('--submission', type=Path, required=True)
    scored.add_argument('--adjudication', type=Path); scored.add_argument('--adjudication-sha256')
    args = parser.parse_args()
    try:
        if args.command == 'prepare': result = prepare(args.case)
        else:
            require(bool(args.adjudication) == bool(args.adjudication_sha256), 'Supply both the adjudication file and its retained digest')
            raw = args.adjudication.read_bytes() if args.adjudication else None
            result = score(json.loads(args.submission.read_bytes()), json.loads(raw) if raw is not None else None, args.adjudication_sha256, raw)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'ok': False, 'code': 'RESEARCH-EVAL-INVALID', 'message': str(exc), 'quality_qualified': False}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__': raise SystemExit(main())
