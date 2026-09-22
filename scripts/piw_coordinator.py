#!/usr/bin/env python3
"""Host-driven drafting/revision state machine: start, next, plan, ingest, deliver.

`next` returns a role request. The calling host invokes its actual native child
and waits; this Python process never pretends to dispatch cognitive execution.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
import piw_session as piw
from piw_session import assert_output as assert_writable
import piw_native_host as native
import bibliography_review as bibliography
import coherence_review as coherence
import coherence_prefilter

require = native.require
PROFILES = {'draft': 'Produce a new deliverable from the bound brief and supplied sources.', 'refine': 'Improve requested wording and local clarity while preserving argument, terminology and citations.', 'structural': 'Revise organization only within the explicitly authorized scope; preserve claims and sources.', 'deep': 'Make the explicitly requested substantive revision; do not infer authority to alter unrelated material.', 'stability': 'Check whether the requested material needs any change; explained no-change is valid after all required roles.'}


def _paths(session_path):
    checked = piw.validate_session(session_path)
    return checked['session'], Path(checked['staging_root'])


def _read_bytes(path):
    return Path(path).read_bytes()


def _fresh(binding: dict, code='PIW-EVIDENCE-DRIFT', read_bytes=None):
    data = (read_bytes or _read_bytes)(binding['path'])
    actual = {'path': binding['path'], 'sha256': piw.digest(data), 'bytes': len(data)}
    require(all(actual[k] == binding[k] for k in ('sha256', 'bytes')), code, 'Bound bytes changed: ' + binding['path'])
    return actual


def _scope(original: bytes, requested: dict) -> dict:
    if requested.get('section'):
        content_start = 3 if original.startswith(b'\xef\xbb\xbf') else 0
        matches = list(re.finditer(rb'(?m)^(#{1,6})[ \t]+([^\r\n]+)\r?\n', original[content_start:]))
        hits = [m for m in matches if m.group(2).decode('utf-8', errors='strict').strip() == requested['section']]
        require(len(hits) == 1, 'PIW-SCOPE-INVALID', 'Requested section must match exactly one heading')
        selected = hits[0]
        end = next((content_start + m.start() for m in matches if m.start() > selected.start() and len(m.group(1)) <= len(selected.group(1))), len(original))
        start = content_start + selected.start()
    else:
        start, end = 0, len(original)
    return {**requested, 'start_byte': start, 'end_byte': end,
            'prefix_sha256': piw.digest(original[:start]), 'suffix_sha256': piw.digest(original[end:])}


def _preserved(contract, candidate, read_bytes=None):
    if not contract.get('input'):
        return
    reader = read_bytes or _read_bytes
    original = reader(contract['input_snapshot']['path'])
    final = reader(candidate['path'])
    scope = contract['requested_scope']
    prefix, suffix = original[:scope['start_byte']], original[scope['end_byte']:]
    require(len(final) >= len(prefix) + len(suffix) and final.startswith(prefix) and final.endswith(suffix),
            'PIW-SCOPE-DRIFT', 'Unrequested manuscript bytes changed')


def _scope_region(contract, data: bytes) -> str:
    """Text of the requested scope inside `data`.

    `_preserved` guarantees an unchanged prefix/suffix, so the in-scope region of
    any candidate is the same byte window measured from both ends. A fresh draft
    has no input and its whole body is in scope.
    """
    scope = contract.get('requested_scope') or {}
    snapshot = contract.get('input_snapshot')
    if not snapshot or 'start_byte' not in scope:
        return data.decode('utf-8-sig')
    tail = snapshot['bytes'] - scope['end_byte']
    end = len(data) - tail
    return data[scope['start_byte']:end].decode('utf-8-sig') if 0 <= scope['start_byte'] <= end else data.decode('utf-8-sig')


def coherence_scope(contract, target, stage, read_bytes=None):
    """In-scope candidate text and the units this stage must cover.

    The AC-5 baseline is the author's original bytes, not the previous
    correction: a unit the harness disturbed three cycles ago is still a unit
    whose neighbours can be disconnected now.
    """
    reader = read_bytes or _read_bytes
    candidate = _scope_region(contract, reader(target['path']))
    if stage == 'diagnosis' or not contract.get('input_snapshot'):
        return candidate, None
    original = _scope_region(contract, reader(contract['input_snapshot']['path']))
    return candidate, coherence_prefilter.changed_unit_ids(original, candidate)


def start(session_path: Path, request: dict) -> dict:
    session, root = _paths(session_path)
    require(not (root / 'binding/run.json').exists(), 'PIW-RUN-EXISTS', 'Start a new session for another run')
    require(isinstance(request.get('brief'), str) and len(request['brief'].strip()) >= 10,
            'PIW-BRIEF-REQUIRED', 'Bind the actual user request and constraints')
    require(not any(request.get(x) for x in ('lifecycle_terminal', 'promotion', 'research_acceptance', 'full_lifecycle')), 'FRC-PIW-NON-TERMINAL', 'Explicit lifecycle operations must retain their governed route')
    project_context = piw.validate_authoritative_binding(Path(request['authoritative_binding'])) if request.get('authoritative_binding') else None
    profile = request.get('profile', 'refine' if session.get('mss_pin') else 'draft')
    require(profile in PROFILES, 'PIW-PROFILE-INVALID', 'Unknown draft/revision profile')
    review_scope = request.get('review_scope', 'substantive')
    require(review_scope in ('substantive', 'prose_only'), 'PIW-SCOPE-REQUIRED', 'Review scope must be substantive or prose_only')
    host = native.bind_host(request.get('host', {}), root)
    exclusions = sorted(set('chung-academic-voice-pass' if 'chung' in str(x).lower() else x for x in request.get('exclusions', [])))
    passes = request.get('passes', ['grammar-mechanics-pass', 'sentence-level-pass'])
    applied = [x for x in passes if x not in exclusions]
    checks = request.get('required_checks', [{'id': 'brief_and_scope', 'required': True}, {'id': 'grammar', 'required': True}, {'id': 'grounding', 'required': True, 'source_required': bool(request.get('source_excerpts'))}])
    checks = [{'id': x, 'required': True} if isinstance(x, str) else x for x in checks]
    require(checks and len({x['id'] for x in checks}) == len(checks), 'PIW-CHECKS-INVALID', 'Bind unique substantive checks')
    require(all(x.get('verification_level', 'attribution') in ('attribution', 'bibliographic') for x in checks),
            'PIW-CHECKS-INVALID', 'Source verification level must be attribution or bibliographic')
    requested_scope = request.get('requested_scope', {'description': 'whole deliverable'})
    require(isinstance(requested_scope, dict) and requested_scope.get('description'), 'PIW-SCOPE-REQUIRED', 'Bind an explicit scope description')
    original = (root / 'binding/original.bin').read_bytes() if session.get('mss_pin') else None
    if original is not None:
        requested_scope = _scope(original, requested_scope)
    limit = request.get('max_corrections', 3)
    require(isinstance(limit, int) and 0 <= limit <= 20, 'PIW-CORRECTION-LIMIT', 'Correction limit must be 0..20')
    sources = []
    for item in request.get('source_excerpts', []):
        require(item.get('locator') and item.get('source_id'), 'PIW-SOURCE-LOCATOR', 'Source excerpts require source identity and locator')
        bound = piw.identity(Path(item['path']))
        if item.get('sha256'):
            require(item['sha256'] == bound['sha256'], 'PIW-SOURCE-DRIFT', 'Supplied source hash differs from actual excerpt')
        sources.append({**item, **bound})
    require(len({x['source_id'] for x in sources}) == len(sources), 'PIW-SOURCE-LOCATOR', 'Bind a unique source ID for each excerpt')
    contract = {'schema_version': '2.0.0', 'run_id': session['piw_work_id'], 'created_at': piw.utc_now(), 'session': piw.identity(root / 'binding/piw_session.json'),
                'brief': request['brief'], 'profile': profile, 'profile_definition': PROFILES[profile], 'project_context': project_context, 'requested_scope': requested_scope, 'input': session.get('mss_pin'),
                'input_snapshot': piw.identity(root / 'binding/original.bin') if original is not None else None,
                'proposal_only': bool(request.get('proposal_only', False)), 'passes': applied, 'exclusions': exclusions,
                'rules': piw.rule_bindings(applied, exclusions), 'package_version': piw.read_json(piw.ROOT / 'version.json'),
                'required_checks': checks, 'max_corrections': limit, 'source_excerpts': sources, 'review_scope': review_scope,
                'host': host, 'output_authority': 'task-local deliverable; input apply is separate',
                'lifecycle_terminal': False, 'research_acceptance': False}
    if request.get('venue_path'):
        contract['venue'] = piw.identity(Path(request['venue_path']))
    piw.write_json(root / 'binding/run.json', contract)
    piw.write_json(root / 'logs/state.json', {'events': [], 'pending': None})
    return next_step(session_path)


def _contract(session_path):
    session, root = _paths(session_path)
    path = root / 'binding/run.json'
    contract = piw.read_json(path)
    require(contract['run_id'] == session['piw_work_id'], 'PIW-WRONG-RUN', 'Run and session identities differ')
    for item in [contract['session'], *contract['rules'], *contract['source_excerpts']]:
        _fresh(item)
    if contract.get('venue'):
        _fresh(contract['venue'])
    if contract.get('project_context'):
        _fresh(contract['project_context']['contract'])
        _fresh(contract['project_context']['assignment_source'])
        piw.validate_authoritative_binding(Path(contract['project_context']['contract']['path']))
    return contract, root, piw.identity(path)


def initial_state(contract):
    return {'stage': 'diagnosis' if contract['input'] else 'plan', 'candidate': contract.get('input_snapshot'), 'corrections': 0, 'unresolved_findings': [], 'limitations': [], 'executions': {}, 'last_findings': [], 'generator_execution_id': None}


def effective_checks(contract, target=None, read_bytes=None):
    checks = list(contract['required_checks'])
    # Argument coherence is not optional and not caller-suppressible: prose this
    # package drafts or revises is reviewed for whether it advances its argument
    # (references/ARGUMENT_COHERENCE.md section 8). A narrower required_checks list, a
    # prose_only scope, or an exclusion cannot remove it.
    checks = [x for x in checks if x['id'] != 'argument_coherence']
    checks.append({'id': 'argument_coherence', 'required': True})
    if contract.get('review_scope', 'substantive') != 'prose_only' and target:
        text = (read_bytes or _read_bytes)(target['path']).decode('utf-8-sig')
        if bibliography.has_sources(text):
            checks = [x for x in checks if x['id'] != 'bibliography']
            checks.append({'id': 'bibliography', 'required': True})
    return checks


def validate_result(contract, request, result, state, read_bytes=None):
    reader = read_bytes or _read_bytes
    expected_role = {'diagnosis': 'evaluator', 'generation': 'generator', 'evaluation': 'evaluator', 'reflection': 'reflector'}.get(state['stage'])
    require(expected_role is not None and request.get('role') == expected_role and request.get('phase') == state['stage'], 'PIW-ROLE-SEQUENCE', 'Role must match the actual diagnosis/plan/generation/evaluation/reflection stage')
    for key in ('run_id', 'step_id', 'role', 'phase'):
        require(result.get(key) == request.get(key), 'PIW-WRONG-RUN-OR-STEP', 'Result mismatches bound ' + key)
    require(result.get('request_sha256') == piw.digest(piw.json_bytes(request)), 'PIW-REQUEST-DRIFT', 'Result does not bind the exact dispatched request')
    require(result.get('outcome') == 'completed', 'PIW-EXECUTION-FAILED', 'Native role outcome: ' + str(result.get('outcome')))
    require(isinstance(result.get('summary'), str) and len(result['summary'].strip()) >= 30, 'PIW-SUBSTANTIVE-EVIDENCE-MISSING', 'Explain actual work and conclusions')
    require(result.get('exclusions') == contract['exclusions'] and result.get('applied_passes') == contract['passes'],
            'PIW-EXCLUSION-DRIFT', 'Applied rules or exclusions differ from the user-bound fire table')
    require(result.get('rule_reads') == contract['rules'], 'PIW-RULE-EVIDENCE-MISSING', 'Record the exact rule identities actually read, separately from activation')
    require(result.get('target') == request.get('target'), 'PIW-TARGET-MISMATCH', 'Result must inspect the bound target bytes')
    execution = result.get('agent_execution_id')
    require(bool(execution), 'PIW-HOST-IDENTITY', 'Missing actual host child execution ID')
    roles = state['executions']
    require(all(role == request['role'] or execution not in ids for role, ids in roles.items()),
            'PIW-ROLE-IMPERSONATION', 'Generator, Evaluator and Reflector must have distinct host contexts')
    require(execution != contract['host']['parent_execution_id'], 'PIW-ROLE-IMPERSONATION', 'Caller cannot impersonate a child')
    if request['role'] == 'generator':
        artifact = result.get('artifact')
        require(isinstance(artifact, dict), 'PIW-ARTIFACT-MISSING', 'Generator must bind substantive authored bytes')
        _fresh(artifact, 'PIW-ARTIFACT-DRIFT', read_bytes)
        root = native.trace_path(contract['session']['path'], read_bytes is not None).parent.parent
        require(native.trace_path(artifact['path'], read_bytes is not None).is_relative_to(root / 'draft'), 'PIW-ARTIFACT-LOCATION', 'Generator writes a new candidate in this run draft directory')
        require(artifact['bytes'] > 0 and len(reader(artifact['path']).decode('utf-8-sig').split()) >= 3,
                'PIW-SUBSTANTIVE-EVIDENCE-MISSING', 'Generator artifact is empty')
        _preserved(contract, artifact, read_bytes)
        expected = {x['id'] for x in state['last_findings'] if x.get('blocking')}
        require(expected.issubset(set(result.get('addressed_findings', []))), 'PIW-CORRECTION-UNBOUND', 'Correction must address the actual blocking finding IDs')
        return
    checks = result.get('checks', [])
    require(isinstance(checks, list) and len({x.get('id') for x in checks}) == len(checks), 'PIW-CHECK-EVIDENCE-MISSING', 'Supply distinct performed checks')
    by_id = {x.get('id'): x for x in checks}
    for required_check in effective_checks(contract, request.get('target'), read_bytes):
        item = by_id.get(required_check['id'])
        require(bool(item) and item.get('status') in ('pass', 'fail', 'not_applicable', 'unavailable') and len(item.get('rationale', '').strip()) >= 20 and bool(item.get('locators')),
                'PIW-CHECK-EVIDENCE-MISSING', 'Check needs applicability, result, actual reason and locators: ' + required_check['id'])
        if required_check.get('source_required') and not contract['source_excerpts']:
            require(item['status'] in (('unavailable',) if required_check.get('required', True) else ('unavailable', 'not_applicable')), 'PIW-SOURCE-EVIDENCE-MISSING', 'Source-dependent check cannot pass without bound excerpts')
        if required_check.get('source_required') and item['status'] == 'pass' and required_check.get('verification_level', 'attribution') == 'attribution':
            support = item.get('source_support')
            require(isinstance(support, list) and bool(support), 'PIW-SOURCE-EVIDENCE-MISSING', 'An attribution pass requires a supporting passage and claim locator')
            sources = {x['source_id']: x for x in contract['source_excerpts']}
            target_text = ' '.join(reader(request['target']['path']).decode('utf-8-sig').split())
            for row in support:
                require(isinstance(row, dict), 'PIW-SOURCE-EVIDENCE-MISSING', 'Source support must identify a passage and claim')
                source = sources.get(row.get('source_id'))
                require(source and row.get('source_locator') == source['locator'] and row.get('status') == 'supported',
                        'PIW-SOURCE-EVIDENCE-MISSING', 'Attribution pass requires supported status and the bound passage locator')
                quote, claim = row.get('quote'), row.get('claim')
                require(isinstance(quote, str) and quote.strip() and isinstance(claim, str) and claim.strip(),
                        'PIW-SOURCE-EVIDENCE-MISSING', 'Quote the source passage and the actual target claim')
                source_text = ' '.join(reader(source['path']).decode('utf-8-sig').split())
                require(' '.join(quote.split()) in source_text and ' '.join(claim.split()) in target_text,
                        'PIW-SOURCE-EVIDENCE-MISSING', 'Quoted passage or claim does not occur in the bound bytes')
    bibliography_check = by_id.get('bibliography')
    if contract.get('review_scope') == 'prose_only':
        require(not bibliography_check or bibliography_check['status'] in ('not_applicable', 'unavailable'),
                'BIBLIOGRAPHY-SCOPE', 'A prose-only pass cannot approve the bibliography')
        require(not result.get('bibliography_review'), 'BIBLIOGRAPHY-SCOPE', 'Prose-only work must report bibliography not assessed')
    elif bibliography_check:
        require(bibliography_check['status'] in ('pass', 'fail', 'unavailable'),
                'BIBLIOGRAPHY-UNASSESSED', 'A cited manuscript cannot mark its bibliography not applicable')
        if bibliography_check['status'] == 'pass' or result.get('bibliography_review'):
            try:
                bibliography.validate(reader(request['target']['path']).decode('utf-8-sig'),
                                      result.get('bibliography_review'), contract['source_excerpts'], reader,
                                      require_clear=bibliography_check['status'] == 'pass')
            except bibliography.ReviewError as exc:
                raise piw.PIWError(exc.code, str(exc)) from exc
    coherence_check = by_id.get('argument_coherence')
    require(bool(coherence_check), 'COHERENCE-REVIEW-MISSING',
            'Substantive prose review requires the argument_coherence check')
    require(coherence_check['status'] in ('pass', 'fail'), 'COHERENCE-REVIEW-MISSING',
            'Argument coherence is judged on the actual bytes; it is never not_applicable '
            'or unavailable while there is prose to review')
    candidate_scope, changed_units = coherence_scope(contract, request['target'], state['stage'], read_bytes)
    try:
        coherence_summary = coherence.validate(
            candidate_scope, result.get('coherence_review'), changed_unit_ids=changed_units,
            require_clear=coherence_check['status'] == 'pass')
    except coherence.ReviewError as exc:
        raise piw.PIWError(exc.code, str(exc)) from exc
    if coherence_check['status'] == 'fail':
        require(coherence_summary['blocking_finding_ids'], 'COHERENCE-OUTCOME-INVALID',
                'A failed argument_coherence check must name the blocking coherence findings')
        require(all(any(f['id'] == finding_id for f in result.get('findings', []))
                    for finding_id in coherence_summary['blocking_finding_ids']),
                'COHERENCE-FINDING-UNBOUND',
                'Blocking coherence findings must also appear in the result findings list')
    findings = result.get('findings')
    require(isinstance(findings, list), 'PIW-FINDINGS-MISSING', 'Return findings or explained no-defect checks')
    require(all(isinstance(f.get('blocking'), bool) and f.get('id') and f.get('locator') and len(f.get('message', '').strip()) >= 15 for f in findings), 'PIW-FINDINGS-MISSING', 'Findings need IDs, locators, reasons and blocking disposition')


def advance(contract, state, role, result):
    if role == 'planner':
        state['stage'] = 'generation'
        return
    state['executions'].setdefault(role, []).append(result['agent_execution_id'])
    if role == 'generator':
        state['candidate'] = result['artifact']
        state['generator_execution_id'] = result['agent_execution_id']
        state['stage'] = 'evaluation'
        return
    blockers = [x for x in result['findings'] if x['blocking']]
    required = {x['id'] for x in contract['required_checks'] if x.get('required', True)}
    required.add('argument_coherence')
    if contract.get('review_scope', 'substantive') != 'prose_only':
        required.add('bibliography')
    for check in result['checks']:
        if check['id'] in required and check['status'] in ('fail', 'unavailable'):
            blockers.append({'id': check['id'], 'blocking': True, 'locator': ', '.join(check['locators']), 'message': check['rationale']})
        if check['status'] == 'unavailable' and check['id'] not in required:
            state['limitations'].append(check)
    state['last_findings'] = blockers
    if state['stage'] == 'diagnosis':
        state['stage'] = 'plan'
    elif blockers:
        state['unresolved_findings'] = blockers
        if state['corrections'] >= contract['max_corrections']:
            state['stage'] = 'needs_revision'
        else:
            state['corrections'] += 1
            state['stage'] = 'generation'
    else:
        state['unresolved_findings'] = []
        state['stage'] = 'reflection' if role == 'evaluator' else 'ready_to_deliver'


def replay(session_path):
    contract, root, contract_binding = _contract(session_path)
    log = piw.read_json(root / 'logs/state.json')
    state = replay_records(contract, contract_binding, log)
    return contract, root, log, state


def replay_records(contract, contract_binding, log, read_bytes=None, read_rows=None):
    """Shared state validation; archived readers never resolve live source paths."""
    reader = read_bytes or _read_bytes
    state = initial_state(contract)
    for index, event in enumerate(log['events']):
        _fresh(event['result'], read_bytes=read_bytes)
        result = json.loads(reader(event['result']['path']))
        if event['kind'] == 'plan':
            require(state['stage'] == 'plan', 'PIW-SEQUENCE', 'Revision diagnosis must precede planning')
            require(result.get('run_id') == contract['run_id'] and result.get('contract_sha256') == contract_binding['sha256'] and len(result.get('summary', '')) >= 30 and bool(result.get('steps')), 'PIW-PLAN-MISSING', 'Planner must map user request and diagnosis into bounded concrete steps')
            expected_diagnosis = log['events'][index - 1]['result']['sha256'] if contract['input'] else None
            require(result.get('diagnosis_sha256') == expected_diagnosis, 'PIW-PLAN-DIAGNOSIS', 'Revision plan must bind the actual independent diagnosis')
            advance(contract, state, 'planner', result)
            continue
        _fresh(event['request'], read_bytes=read_bytes)
        request = json.loads(reader(event['request']['path']))
        require(request['phase'] == state['stage'] and request['contract_sha256'] == contract_binding['sha256'] and request['sequence'] == index,
                'PIW-SEQUENCE', 'Evidence is out of order or bound to another contract')
        target = contract['input_snapshot'] if state['stage'] == 'diagnosis' else state['candidate']
        require(request.get('target') == target, 'PIW-TARGET-MISMATCH', 'Request points at stale or unrelated bytes')
        validate_result(contract, request, result, state, read_bytes)
        native.verify_execution(contract['host'], event['host'], request, result, event['host']['pins'], read_rows)
        advance(contract, state, request['role'], result)
    return state


def next_step(session_path):
    contract, root, log, state = replay(session_path)
    stage = state['stage']
    if stage in ('plan', 'ready_to_deliver', 'needs_revision'):
        return {'ok': stage != 'needs_revision', 'status': stage, 'run_id': contract['run_id'], 'state': state,
                'contract': piw.identity(root / 'binding/run.json'), 'diagnosis': log['events'][-1]['result'] if stage == 'plan' and log['events'] else None, 'task_complete': False}
    if log.get('pending'):
        _fresh(log['pending'])
        pending = piw.read_json(log['pending']['path'])
    else:
        role = {'generation': 'generator', 'diagnosis': 'evaluator', 'evaluation': 'evaluator', 'reflection': 'reflector'}[stage]
        pending = {'run_id': contract['run_id'], 'step_id': piw.mint_work_id(), 'sequence': len(log['events']), 'created_at': piw.utc_now(),
                   'role': role, 'phase': stage, 'run_scope': 'project_independent', 'contract_sha256': piw.identity(root / 'binding/run.json')['sha256'],
                   'contract_path': str(root / 'binding/run.json'), 'target': contract['input_snapshot'] if stage == 'diagnosis' else state['candidate'],
                   'brief': contract['brief'], 'profile': contract.get('profile', 'refine' if contract['input'] else 'draft'), 'profile_definition': contract.get('profile_definition'), 'venue': contract.get('venue'), 'project_context': contract.get('project_context'), 'requested_scope': contract['requested_scope'], 'rules': contract['rules'], 'applied_passes': contract['passes'],
                   'exclusions': contract['exclusions'], 'required_checks': effective_checks(contract, contract['input_snapshot'] if stage == 'diagnosis' else state['candidate']), 'source_excerpts': contract['source_excerpts'],
                   'review_scope': contract.get('review_scope', 'substantive'),
                   'findings_to_address': state['last_findings'], 'evidence_so_far': log['events'], 'output_directory': str(root / 'draft'),
                   'role_prompt': piw.identity(piw.ROOT / 'agents' / f'{role}.md'),
                   'skill_bodies': [piw.identity(piw.ROOT / 'skills' / name / 'SKILL.md') for name in contract['passes']],
                   'package_root': str(piw.ROOT),
                   'instruction': 'Perform the real assigned role in a distinct native context. Read role_prompt and skill_bodies from package_root on any host, then actual input and rule files, including the bound venue/project context when supplied; venue/advisor instructions refine packaged defaults under the user request. Respect the scope and exclusions in every check and correction. Final response must be only result JSON. Include run_id, step_id, role, phase, request_sha256 (hash of this exact request file), agent_execution_id (actual host session UUID), outcome completed, target copied exactly, summary explaining actual work, rule_reads copied from rules after actual reads, applied_passes and exclusions copied exactly. Generator additionally returns artifact={path,sha256,bytes} and addressed_findings IDs, writes a NEW candidate path each cycle; Evaluator/Reflector return checks=[{id,status,rationale,locators:[...]}] for every required check and findings=[{id,blocking,message,locator}]. Empty findings require substantive checks explaining why. Required unavailable checks cannot pass. Reflector inspects diagnosis/plan/generation/evaluation and final bytes; new material issues reopen correction. No scholarly CLEAN, acceptance or lifecycle authority.'}
        pending['source_support_instruction'] = 'For each source_required attribution check marked pass, include nonempty source_support=[{source_id,source_locator,quote,claim,status:"supported"}]. Quote actual source and target bytes, use the bound source locator, and explain support including qualifications. Bibliographic resolution alone cannot clear attribution; contested or missing support must fail or remain unavailable.'
        pending['bibliography_instruction'] = 'Read references/CITATION_DISCIPLINE.md. Substantive cited drafts require a bibliography check and bibliography_review in the result. Use scripts/bibliography_review.py inventory(target_text) to enumerate references, citation uses and non_citations; copy the exact non_citations classifications into the assessment, then inspect all claims in each cited paragraph and supply judgments; inventory output is not approval. Bind sources, actually inspected materials, all source_support use IDs, role, authority, directness, currency, discovery/challenging evidence and dispositions. A supported example cannot clear other uses. New references/claims/roles reopen affected judgments; pure numbering changes may reuse identical coverage. Prose-only work must state bibliography not assessed. Unresolved evidence blocks dependent claims, while independent planning/drafting may continue.'
        if pending['target']:
            scope_text, changed_units = coherence_scope(contract, pending['target'], stage)
            needed, changed_ids, neighbour_ids = coherence.required_units(scope_text, changed_units)
            pending['coherence_scope'] = {
                'coverage_denominator': len(coherence_prefilter.units_for(scope_text)),
                'required_unit_ids': needed, 'changed_unit_ids': changed_ids,
                'neighbour_unit_ids': neighbour_ids,
                'units': coherence_prefilter.units_for(scope_text),
                'baseline': 'original author bytes' if contract.get('input_snapshot') else 'new draft'}
        else:
            # First generation of a new draft: no candidate exists yet, so the
            # coverage denominator is not computable. The obligation still binds
            # the Evaluator that reads what this Generator writes.
            pending['coherence_scope'] = {'status': 'not_computable_before_first_candidate'}
        pending['coherence_instruction'] = (
            'Read references/ARGUMENT_COHERENCE.md in full and execute its obligation on the '
            'target bytes. Return coherence_review={candidate_sha256, scope:{covered_unit_ids, '
            'changed_unit_ids, neighbours_reviewed}, units:[{unit_id, sha256, purpose, '
            'sentences:[{text, contribution, finding_id}]}], commitment_occurrences, findings, '
            'out_of_scope_observations, outcome}. candidate_sha256 is the sha256 of the requested '
            'scope region of the target, and unit ids/hashes come from '
            '`python scripts/coherence_prefilter.py <target> --json`; that pre-filter reaches no '
            'verdict and clears nothing. Cover every required unit: the changed units and their '
            'immediate neighbours, because a sound edit can disconnect an untouched neighbour. '
            'Determine each paragraph purpose from the actual text, not from a role label. The '
            'sentence texts you report must partition the unit exactly. Quote only passages that '
            'occur in the bytes. Do not flag implicit transitions the reader can recover, '
            'legitimate background, qualifications, counterarguments, connections established '
            'earlier in the section, or authorial voice, and never impose a paragraph formula or '
            'mandatory signposting. If explaining a defect or its remedy requires a premise the '
            'author never stated, report the relationship as unrecoverable instead. Source '
            'support and argument coherence are separate verdicts: a valid citation does not '
            'clear irrelevant placement and a coherent bridge does not clear an unsupported '
            'claim. Defects outside the write scope are findings only; they confer no write '
            'authority. Outcome is review_complete, changes_required or review_incomplete.')
        path = root / 'logs' / f'{len(log["events"]):03d}-{stage}-request.json'
        piw.write_json(path, pending)
        log['pending'] = piw.identity(path)
        piw.write_json(root / 'logs/state.json', log)
    return {'ok': True, 'status': 'awaiting_native_child', 'request_path': log['pending']['path'], 'request_sha256': log['pending']['sha256'], 'request': pending, 'task_complete': False}


def record_plan(session_path, plan):
    contract, root, log, state = replay(session_path)
    require(state['stage'] == 'plan', 'PIW-SEQUENCE', 'Plan is accepted only after required independent diagnosis')
    plan = {**plan, 'profile': contract.get('profile'), 'applied_passes': contract['passes'], 'exclusions': contract['exclusions'], 'run_id': contract['run_id'], 'contract_sha256': piw.identity(root / 'binding/run.json')['sha256'],
            'diagnosis_sha256': log['events'][-1]['result']['sha256'] if contract['input'] else None}
    require(len(plan.get('summary', '')) >= 30 and bool(plan.get('steps')), 'PIW-PLAN-MISSING', 'Provide substantive scope-preserving plan and concrete steps')
    path = root / 'plan/planner.json'
    piw.write_json(path, plan)
    log['events'].append({'kind': 'plan', 'result': piw.identity(path)})
    piw.write_json(root / 'logs/state.json', log)
    return next_step(session_path)


def ingest(session_path, result, evidence):
    contract, root, log, state = replay(session_path)
    require(bool(log.get('pending')), 'PIW-NO-PENDING-REQUEST', 'Run next before native dispatch')
    _fresh(log['pending'])
    request = piw.read_json(log['pending']['path'])
    validate_result(contract, request, result, state)
    host = native.verify_execution(contract['host'], evidence, request, result)
    path = root / {'generator': 'draft', 'evaluator': 'evaluate', 'reflector': 'reflect'}[request['role']] / f'{len(log["events"]):03d}-{request["phase"]}-result.json'
    piw.write_json(path, result)
    log['events'].append({'kind': 'role', 'request': log['pending'], 'result': piw.identity(path), 'host': host})
    log['pending'] = None
    piw.write_json(root / 'logs/state.json', log)
    return next_step(session_path)


def deliver(session_path, destination):
    contract, root, log, state = replay(session_path)
    require(state['stage'] == 'ready_to_deliver', 'PIW-INCOMPLETE' if state['stage'] != 'needs_revision' else 'PIW-NEEDS-REVISION', 'Required role work has not completed acceptably')
    destination = Path(destination).resolve()
    assert_writable(destination)
    require(not contract['input'] or destination != Path(contract['input']['path']).resolve(), 'PIW-INPUT-APPLY-SEPARATE', 'Deliver to an authorized output artifact; original manuscript application is separate')
    reserved = [root / name for name in piw.STAGING_SUBDIRS]
    reserved.append(Path(contract['host']['logs_root']).resolve())
    bound_files = [contract['session'], *contract['rules'], *contract['source_excerpts']]
    bound_files.extend(x for x in (contract.get('input_snapshot'), contract.get('venue')) if x)
    if contract.get('project_context'):
        bound_files.extend([contract['project_context']['contract'], contract['project_context']['assignment_source']])
    protected_files = {Path(x['path']).resolve() for x in bound_files} | {root / 'completion.json', root / 'evaluation.json'}
    require(destination not in protected_files and not any(destination.is_relative_to(path) for path in reserved), 'PIW-DELIVERY-LOCATION', 'Delivery must not overwrite bound inputs, sources, rules, original host logs or runtime evidence')
    data = Path(state['candidate']['path']).read_bytes()
    piw.write_bytes(destination, data)
    piw.write_json(root / 'binding/delivery.json', {'run_id': contract['run_id'], 'artifact': piw.identity(destination), 'candidate': state['candidate'], 'created_at': piw.utc_now()})
    import piw_completion_guard as guard
    result = guard.verify_completion(session_path)
    piw.write_json(root / 'completion.json', result)
    if result.get('task_complete'):
        evaluation = piw.read_json(result['evaluation']['path'])
        piw.write_json(root / 'evaluation.json', {**evaluation, 'artifact_sha256': result['artifact_sha256'], 'artifact_bytes': result['artifact_bytes'], 'original_evidence': result['evaluation']})
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', nargs='?', choices=('start', 'next', 'plan', 'ingest', 'deliver', 'status'))
    ap.add_argument('--piw-session', required=True, type=Path)
    ap.add_argument('--request-json', type=Path)
    ap.add_argument('--plan-json', type=Path)
    ap.add_argument('--result-json', type=Path)
    ap.add_argument('--host-evidence', type=Path)
    ap.add_argument('--destination', type=Path)
    ap.add_argument('--dest-write', type=Path)
    ap.add_argument('--coordinator', choices=('draft', 'iterate', 'reflection'))
    ap.add_argument('--profile', default='refine')
    ap.add_argument('--mode', default='probe')
    args = ap.parse_args(argv)
    try:
        if args.dest_write:
            piw.assert_output(args.dest_write)
        if args.command == 'start':
            result = start(args.piw_session, piw.read_json(args.request_json))
        elif args.command == 'plan':
            result = record_plan(args.piw_session, piw.read_json(args.plan_json))
        elif args.command == 'ingest':
            result = ingest(args.piw_session, piw.read_json(args.result_json), piw.read_json(args.host_evidence))
        elif args.command == 'deliver':
            result = deliver(args.piw_session, args.destination)
        elif args.command in ('next', 'status'):
            result = next_step(args.piw_session)
        else:
            raise piw.PIWError('PIW-HOST-DISPATCH-REQUIRED', 'Use start/next/plan/ingest with actual native children; legacy receipt-only coordinators cannot perform this task')
    except (piw.PIWError, OSError, ValueError, KeyError, TypeError) as exc:
        result = {'ok': False, 'status': 'execution_error', 'code': getattr(exc, 'code', 'PIW-INVALID-EVIDENCE'), 'message': str(exc), 'task_complete': False}
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result.get('ok') else 4

if __name__ == '__main__':
    raise SystemExit(main())
