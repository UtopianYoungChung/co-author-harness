#!/usr/bin/env python3
"""Fast lane for short deliverables: open, request, record, deliver, status.

Python binds, sequences and verifies evidence. A real Generator child and a
distinct real Evaluator child do the cognitive work. The result is an uncertified
working draft with a review record: it grants no lifecycle, acceptance or
scholarly CLEAN authority. Governed milestones keep the coordinator lane
(`piw_coordinator.py`).
"""
from __future__ import annotations
import argparse
import json
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
import piw_session as piw
from piw_session import assert_output as assert_writable
import bibliography_review as bib

CORE_RULES = ('GROUNDING_PROTOCOL.md', 'CITATION_DISCIPLINE.md')
CLAIM = re.compile(r'(?im)^\s*(?:lifecycle_terminal|research_acceptance|promotion|promote|certified)\s*[:=]\s*(?:true|yes|1)\b'
                   r'|^\s*run_scope\s*[:=]\s*full_lifecycle\b')
VERDICT = re.compile(r'(?i)verdict:\s*(clear|blocking)')
FINDING = re.compile(r'- \[(BLOCKING|ADVISORY)\] (.+?): (.+)')
FINDING_LIKE = re.compile(r'(?i)\s*(?:[-*+]\s*)?\[\s*(?:blocking|advisory)\b')
STATUS = {'generator': 'awaiting_generator', 'evaluator': 'awaiting_evaluator', 'ready': 'ready_to_deliver',
          'needs_revision': 'needs_revision', 'delivered': 'delivered'}
GENERATOR_TEXT = ('Write the deliverable that answers the brief to output_path as one Markdown file. For a revision, preserve every byte, '
                  'claim and citation the brief does not ask you to change. Cite only sources that appear in the input or the brief. Where a '
                  'fact or example is missing, write [FACT NEEDED] or [CONCRETE EXAMPLE NEEDED] rather than inventing it (Grounding Protocol '
                  'Rule 6). Read only the listed rule files. Do not review or certify your own work. When previous_candidate is present, start '
                  'from it and address only findings_to_address. Reply with the output path only.')
EVALUATOR_TEXT = ('Read the brief, the input if any, the candidate and the listed rule files. Check grounding, citation integrity, scope '
                  'preservation, the brief requirements and plain correctness. bibliography_inventory_errors were computed by the script. '
                  'Unsupported-syntax errors that also occur in the author input are a known parser limit: list them as ADVISORY, not BLOCKING. '
                  'Do not edit the candidate. Write findings to output_path in this exact shape: the first non-empty line is "verdict: clear" '
                  'or "verdict: blocking"; then one line per finding, "- [BLOCKING] <locator>: <message>" or "- [ADVISORY] <locator>: <message>"; '
                  'then optional prose. Verdict blocking needs at least one BLOCKING line and verdict clear needs none. Reply with the output path only.')


def require(ok, code, message):
    if not ok:
        raise piw.PIWError(code, message)


def text(path):
    return Path(path).read_bytes().decode('utf-8-sig')


def fresh(ident, code='FAST-EVIDENCE-DRIFT'):
    require(piw.identity(Path(ident['path']))['sha256'] == ident['sha256'], code, 'Bound bytes changed: ' + ident['path'])


def load(session):
    path = Path(session).resolve()
    b = piw.read_json(path)
    require(b.get('lane') == 'fast' and b.get('run_scope') == 'project_independent' and b.get('certified') is False
            and b.get('lifecycle_terminal') is False and b.get('research_acceptance') is False, 'FAST-BINDING', 'Not a fast-lane binding')
    return path, path.parent, b, piw.read_json(path.with_name('state.json'))


def phase(b, st):
    g, e = st['generators'], st['evaluators']
    if st.get('delivered'):
        return 'delivered'
    if not g:
        return 'generator'
    if len(g) > len(e):
        return 'evaluator'
    if e[-1]['verdict'] == 'clear':
        return 'ready'
    return 'generator' if len(g) - 1 < b['max_corrections'] else 'needs_revision'


def expect(ph, want, code='FAST-SEQUENCE'):
    require(ph == want, 'FAST-NEEDS-REVISION' if ph == 'needs_revision' else code,
            f'Expected {want} step, but the session is {STATUS[ph]}')


def citation_gate(b, candidate):
    """Return (blocking errors, unsupported-syntax errors the author's own input also carries)."""
    errors = bib.inventory(text(candidate))['errors']
    syntax = [x for x in errors if 'unsupported citation syntax' in x]
    other = [x for x in errors if x not in syntax]
    written = bib.unsupported_syntax_count(text(b['input']['path'])) if b.get('input') else 0
    if syntax and bib.unsupported_syntax_count(text(candidate)) <= written:
        return other, syntax
    return other + syntax, []


def parse_findings(path):
    require(Path(path).is_file(), 'FAST-FINDINGS-MISSING', 'Findings file not found: ' + str(path))
    body = [x.rstrip() for x in Path(path).read_bytes().decode('utf-8-sig').splitlines() if x.strip()]
    head = VERDICT.fullmatch(body[0].strip()) if body else None
    require(head, 'FAST-FINDINGS-SHAPE', 'First non-empty line must be "verdict: clear" or "verdict: blocking"')
    lines = {'BLOCKING': [], 'ADVISORY': []}
    for line in body[1:]:
        if FINDING_LIKE.match(line):
            found = FINDING.fullmatch(line)
            require(found, 'FAST-FINDINGS-SHAPE', 'Malformed finding line: ' + line[:80])
            lines[found[1]].append(line)
    verdict = head[1].lower()
    require((verdict == 'blocking') == bool(lines['BLOCKING']), 'FAST-FINDINGS-SHAPE', 'Verdict and BLOCKING lines disagree')
    return verdict, lines['BLOCKING'], lines['ADVISORY']


def cmd_open(a):
    require(a.run_scope == 'project_independent' and not (a.lifecycle_terminal or a.research_acceptance or a.promotion or a.certified),
            'FAST-NON-TERMINAL', 'The fast lane is project_independent and non-terminal; it cannot claim lifecycle, promotion, acceptance or certification')
    task_root = Path(a.task_root).resolve()
    assert_writable(task_root)
    brief = Path(a.brief).resolve()
    require(not CLAIM.search(text(brief)), 'FAST-NON-TERMINAL', 'The brief claims lifecycle_terminal, promotion, research_acceptance, certification or full_lifecycle')
    require(a.max_corrections >= 0, 'FAST-ARGS', '--max-corrections must be 0 or more')
    for name in a.passes:
        require(name in piw.PASS_RULES, 'PIW-RULE-UNKNOWN', 'Unsupported rule profile: ' + name)
    names = list(CORE_RULES) + [f for p in a.passes if p not in a.exclude for f in piw.PASS_RULES[p]]
    session_id = 'fast-' + datetime.now(timezone.utc).strftime('%Y%m%d') + '-' + secrets.token_hex(4)
    root = task_root / 'fast' / session_id
    binding = {'lane': 'fast', 'run_scope': 'project_independent', 'certified': False, 'lifecycle_terminal': False,
               'research_acceptance': False, 'session_id': session_id, 'created_at': piw.utc_now(),
               'package_version': piw.read_json(piw.ROOT / 'version.json')['version'], 'brief': piw.identity(brief),
               'input': piw.identity(Path(a.input)) if a.input else None,
               'rules': [piw.identity(piw.ROOT / 'references' / n) for n in dict.fromkeys(names)],
               'passes': a.passes, 'exclusions': sorted(a.exclude), 'max_corrections': a.max_corrections}
    piw.write_json(root / 'binding.json', binding)
    piw.write_json(root / 'state.json', {'generators': [], 'evaluators': [], 'delivered': False})
    return {'ok': True, 'status': STATUS['generator'], 'session_path': str(root / 'binding.json'), 'session_id': session_id}


def cmd_request(a):
    path, root, b, st = load(a.session)
    for ident in (b['brief'], b['input'], *b['rules']):
        if ident:
            fresh(ident)
    expect(phase(b, st), a.role)
    gens = st['generators']
    if a.role == 'generator':
        n = len(gens) + 1
        body = {'output_path': str(root / 'draft' / f'candidate-{n}.md'), 'instruction': GENERATOR_TEXT}
        if gens:
            body['previous_candidate'] = gens[-1]['candidate']['path']
            body['findings_to_address'] = st['evaluators'][-1]['blocking']
    else:
        n = len(gens)
        cand = gens[-1]['candidate']
        fresh(cand, 'FAST-CANDIDATE-DRIFT')
        author = bib.unsupported_syntax_count(text(b['input']['path'])) if b['input'] else 0
        body = {'output_path': str(root / 'review' / f'findings-{n}.md'), 'instruction': EVALUATOR_TEXT, 'candidate_path': cand['path'],
                'candidate_sha256': cand['sha256'], 'bibliography_inventory_errors': gens[-1]['inventory_errors'],
                'candidate_unsupported_syntax_count': bib.unsupported_syntax_count(text(cand['path'])),
                'input_unsupported_syntax_count': author}
    req = {'run_scope': 'project_independent', 'lane': 'fast', 'role': a.role, 'round': n, 'session': str(path), 'certified': False,
           'lifecycle_terminal': False, 'research_acceptance': False, 'brief_path': b['brief']['path'], 'brief_text': text(b['brief']['path']),
           'input_path': b['input']['path'] if b['input'] else None, 'rules': b['rules'], 'exclusions': b['exclusions'], **body}
    out = root / 'requests' / f'{n}-{a.role}.json'
    piw.write_json(out, req)
    Path(body['output_path']).parent.mkdir(parents=True, exist_ok=True)
    return {'ok': True, 'request_path': str(out), 'role': a.role, 'round': n, 'output_path': body['output_path']}


def cmd_record(a):
    path, root, b, st = load(a.session)
    require(a.child_id.strip(), 'FAST-CHILD-ID', '--child-id is required')
    other = st['evaluators' if a.role == 'generator' else 'generators']
    require(a.child_id not in {x['child_id'] for x in other}, 'FAST-ROLE-DISTINCT', 'The Generator and the Evaluator must be distinct child agents')
    expect(phase(b, st), a.role)
    n = len(st['generators']) + 1 if a.role == 'generator' else len(st['generators'])
    require((root / 'requests' / f'{n}-{a.role}.json').is_file(), 'FAST-SEQUENCE', 'Write the request before recording its result')
    row = {'round': n, 'child_id': a.child_id, 'child_model': a.child_model, 'recorded_at': piw.utc_now()}
    if a.role == 'generator':
        cand = root / 'draft' / f'candidate-{n}.md'
        require(cand.is_file() and text(cand).strip(), 'FAST-CANDIDATE-MISSING', 'Candidate missing or empty: ' + str(cand))
        ident = piw.identity(cand)
        require(n == 1 or ident['sha256'] != st['generators'][-1]['candidate']['sha256'], 'FAST-NO-CHANGE', 'The correction did not change the candidate')
        row.update(candidate=ident, inventory_errors=bib.inventory(text(cand))['errors'])
    else:
        cand = st['generators'][-1]['candidate']
        fresh(cand, 'FAST-CANDIDATE-DRIFT')
        findings = root / 'review' / f'findings-{n}.md'
        verdict, blocking, advisory = parse_findings(findings)
        row.update(verdict=verdict, blocking=blocking, advisory=advisory, findings=piw.identity(findings), candidate_sha256=cand['sha256'])
    st['generators' if a.role == 'generator' else 'evaluators'].append(row)
    piw.write_json(root / 'state.json', st)
    ph = phase(b, st)
    return {'ok': True, 'status': STATUS[ph], 'role': a.role, 'round': n, 'verdict': row.get('verdict'),
            'blocking': len(row.get('blocking', [])), 'advisory': len(row.get('advisory', []))}


def cmd_deliver(a):
    path, root, b, st = load(a.session)
    expect(phase(b, st), 'ready', 'FAST-NOT-READY')
    last = st['generators'][-1]['candidate']
    for ident in (last, b['brief'], b['input'], *b['rules']):
        if ident:
            fresh(ident, 'FAST-CANDIDATE-DRIFT' if ident is last else 'FAST-EVIDENCE-DRIFT')
    dest = Path(a.destination).resolve()
    require(not (b['input'] and dest == Path(b['input']['path']).resolve()), 'FAST-INPUT-APPLY-SEPARATE', 'Deliver to a new output file; applying to the original is a separate step')
    require(dest != root and not dest.is_relative_to(root) and dest not in {Path(x['path']).resolve() for x in (b['brief'], *b['rules'])},
            'FAST-DELIVERY-LOCATION', 'Delivery must not land in the session folder or on a bound brief or rule file')
    assert_writable(dest)
    errors, allowed = citation_gate(b, last['path'])
    require(not errors, 'FAST-CITATIONS-UNRESOLVED', 'Citation inventory errors: ' + ' | '.join(errors))
    piw.write_bytes(dest, Path(last['path']).read_bytes())
    ev = st['evaluators'][-1]
    receipt = {'lane': 'fast', 'run_scope': 'project_independent', 'certified': False, 'lifecycle_terminal': False, 'research_acceptance': False,
               'session_id': b['session_id'], 'package_version': b['package_version'], 'brief': b['brief'], 'input': b['input'],
               'output': piw.identity(dest), 'candidate': last, 'corrections_used': len(st['generators']) - 1, 'max_corrections': b['max_corrections'],
               'findings': {'verdict': ev['verdict'], 'blocking': len(ev['blocking']), 'advisory': len(ev['advisory']), 'advisory_lines': ev['advisory'], 'file': ev['findings']},
               'citation_gate': {'blocking_errors': 0, 'author_syntax_errors_allowed': allowed},
               'children': [{'role': r, 'round': x['round'], 'child_id': x['child_id'], 'child_model': x['child_model']}
                            for r, k in (('generator', 'generators'), ('evaluator', 'evaluators')) for x in st[k]],
               'rules': b['rules'], 'exclusions': b['exclusions'], 'delivered_at': piw.utc_now(),
               'limits': 'Uncertified working draft. Child ids are declared by the host and not verified. No lifecycle, acceptance or scholarly CLEAN authority.'}
    piw.write_json(root / 'receipt.json', receipt)
    st['delivered'] = True
    piw.write_json(root / 'state.json', st)
    return receipt


def cmd_status(a):
    path, root, b, st = load(a.session)
    ev = st['evaluators']
    return {'ok': True, 'status': STATUS[phase(b, st)], 'session_id': b['session_id'], 'generator_records': len(st['generators']),
            'evaluator_records': len(ev), 'corrections_used': max(len(st['generators']) - 1, 0), 'max_corrections': b['max_corrections'],
            'last_verdict': ev[-1]['verdict'] if ev else None, 'delivered': st['delivered']}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    o = sub.add_parser('open')
    o.add_argument('--task-root', required=True)
    o.add_argument('--brief', required=True)
    o.add_argument('--input')
    o.add_argument('--pass', dest='passes', nargs='*', default=[])
    o.add_argument('--exclude', nargs='*', default=[])
    o.add_argument('--max-corrections', type=int, default=1)
    o.add_argument('--run-scope', default='project_independent')
    for flag in ('lifecycle-terminal', 'research-acceptance', 'promotion', 'certified'):
        o.add_argument('--' + flag, action='store_true')
    for name in ('request', 'record', 'deliver', 'status'):
        p = sub.add_parser(name)
        p.add_argument('--session', required=True)
        if name in ('request', 'record'):
            p.add_argument('--role', required=True, choices=('generator', 'evaluator'))
        if name == 'record':
            p.add_argument('--child-id', required=True)
            p.add_argument('--child-model')
        if name == 'deliver':
            p.add_argument('--destination', required=True)
    a = ap.parse_args(argv)
    try:
        result = globals()['cmd_' + a.command](a)
        code = 0
    except (piw.PIWError, OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        result, code = {'ok': False, 'code': getattr(exc, 'code', 'FAST-ERROR'), 'message': str(exc)}, 4
    print(json.dumps(result, indent=2, sort_keys=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
