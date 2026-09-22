#!/usr/bin/env python3
"""Standalone coordinator/verifier integration fixtures; NOT live host acceptance.

These fixtures deliberately construct synthetic Codex log records to test the
real entry points. No fixture is cognitive execution or an AT04-AT13 host pass.
The fixed AT01-AT14 acceptance matrix is reported separately by live exercises.
"""
from __future__ import annotations
import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
import piw_session as piw
import piw_coordinator as coordinator
import piw_completion_guard as guard
import coherence_fixture_support as coherence_fixture

SCRIPTS = Path(__file__).resolve().parent
FIXTURE = b'# Example manuscript\n\n## Anchor\nThe term "request" denotes a submitted item, not an approval. [Anchor-A]\n\n## Scope\nEach reviewer examine one request. The queue record the decision after the review.\n'
REVISED = FIXTURE.replace(b'reviewer examine', b'reviewer examines').replace(b'queue record', b'queue records')
BOM_FIXTURE = b'\xef\xbb\xbf# Scope\nEach reviewer examine one request.\n\n# Anchor\nPreserve this section.\n'
RESULTS = []


def host_row(kind, payload, timestamp=None):
    return {'timestamp': timestamp or piw.utc_now(), 'type': kind, 'payload': payload}


def append_log(path, row):
    data = path.read_bytes() if path.exists() else b''
    piw.write_bytes(path, data + (json.dumps(row) + '\n').encode())


def setup(tmp, revision=False, max_corrections=3, available=True, proposal=False, fixture=FIXTURE):
    logs = tmp / 'synthetic-host'
    logs.mkdir(parents=True)
    parent_id = str(uuid.uuid4())
    parent = logs / 'parent.jsonl'
    append_log(parent, host_row('session_meta', {'id': parent_id, 'source': 'synthetic-integration-fixture'}))
    source = tmp / 'input.md'
    if revision:
        piw.write_bytes(source, fixture)
    opened = piw.open_session(ingress_kind='mss_revision' if revision else 'standalone', mss_path=source if revision else None, outputs_root=tmp / 'output')
    session = Path(opened['staging_root'])
    request = {'brief': 'Grammar correction within the Scope section; preserve the terminology and argument.' if revision else 'Explain the conceptual distinction between request recording and approval; invent no studies or sources.',
               'requested_scope': {'description': 'Scope section grammar only', 'section': 'Scope'} if revision else {'description': 'whole draft'},
               'host': {'adapter': 'codex-jsonl', 'subagents_available': available, 'logs_root': str(logs), 'parent_log': str(parent)},
               'exclusions': ['chung-academic-voice-pass'], 'max_corrections': max_corrections, 'proposal_only': proposal}
    return session, request


def plan(session):
    return coordinator.record_plan(session, {'summary': 'Map the independent diagnosis and user scope to a bounded correction preserving untouched bytes.', 'steps': ['Correct only diagnosed agreement errors; preserve terminology, argument, citations and all untouched bytes.']})


def complete_child(session, *, blockers=False, artifact=None, execution_id=None, outcome='completed', fork_history=False, mutate=None):
    packet = coordinator.next_step(session)
    req = packet['request']
    contract = piw.read_json(session / 'binding/run.json')
    role = req['role']
    eid = execution_id or str(uuid.uuid4())
    tid = str(uuid.uuid4())
    result = {k: req[k] for k in ('run_id', 'step_id', 'role', 'phase', 'target', 'applied_passes', 'exclusions')}
    result.update(request_sha256=packet['request_sha256'], agent_execution_id=eid, outcome=outcome, rule_reads=req['rules'],
                  summary='Integration fixture explanation: this synthetic result exercises bounded scope checks and evidence validation, and is not an actual cognitive assessment.')
    if role == 'generator':
        path = session / 'draft' / f'candidate-{req["sequence"]}.md'
        piw.write_bytes(path, artifact if artifact is not None else REVISED if contract['input'] else b'A queue records submitted requests. A policy defines whether a request can receive approval. Recording alone does not grant approval.\n')
        result['artifact'] = piw.identity(path)
        result['addressed_findings'] = [x['id'] for x in req['findings_to_address']]
    else:
        result['checks'] = [{'id': x['id'], 'status': 'pass', 'rationale': 'Synthetic integration assertion supplies a concrete scope-bound check result for validator testing.', 'locators': ['Scope sentence 1' if contract['input'] else 'paragraph 1']} for x in req['required_checks']]
        result['findings'] = [{'id': 'F1', 'blocking': True, 'locator': 'paragraph 1', 'message': 'Synthetic planted blocking issue must be corrected before completion.'}] if blockers else []
        scope_text, changed_units = coordinator.coherence_scope(contract, req['target'], req['phase'])
        result['coherence_review'] = coherence_fixture.build(scope_text, changed_units)
    if mutate is not None:
        # Tamper before the host log is written, so a negative control reaches the
        # check it targets instead of tripping the host-result comparison first.
        mutate(result, req, contract)
    log = Path(contract['host']['logs_root']) / f'{eid}.jsonl'
    if not log.exists():
        meta = {'id': eid, 'source': {'subagent': {'thread_spawn': {'parent_thread_id': contract['host']['parent_execution_id']}}}}
        if fork_history:
            meta['forked_from_id'] = contract['host']['parent_execution_id']
        append_log(log, host_row('session_meta', meta))
        if fork_history:
            parent_meta = json.loads(Path(contract['host']['parent_log']).read_bytes().splitlines()[0])['payload']
            append_log(log, host_row('session_meta', parent_meta))
            append_log(log, host_row('event_msg', {'type': 'task_started', 'turn_id': 'inherited-parent-turn'}))
        append_log(Path(contract['host']['parent_log']), host_row('event_msg', {'type': 'item_completed', 'item': {'type': 'SubAgentActivity', 'kind': 'started', 'agent_thread_id': eid}}))
    append_log(log, host_row('event_msg', {'type': 'task_started', 'turn_id': tid}))
    append_log(log, host_row('event_msg', {'type': 'task_complete', 'turn_id': tid, 'last_agent_message': json.dumps(result)}))
    evidence = {'child_log': str(log), 'agent_execution_id': eid, 'turn_id': tid}
    return result, evidence


def ingest_child(session, **kwargs):
    result, evidence = complete_child(session, **kwargs)
    return coordinator.ingest(session, result, evidence)


def finish(session, request, no_change=False):
    response = coordinator.start(session, request)
    if response['status'] == 'awaiting_native_child':
        ingest_child(session)
    plan(session)
    ingest_child(session, artifact=FIXTURE if no_change else None)
    ingest_child(session)
    ingest_child(session)
    return coordinator.deliver(session, session.parent.parent.parent.parent / 'final.md')


def verify_cli(session):
    run = subprocess.run([sys.executable, str(SCRIPTS / 'piw_completion_guard.py'), 'verify', '--piw-session', str(session)], capture_output=True, text=True, encoding='utf-8', errors='strict')
    return run.returncode, json.loads(run.stdout)


def hook_cli(session, path=None, *, scope='project_independent', use_session=True, stop=False):
    env = os.environ.copy()
    env.pop('FRC_GATE_HOOK_DISABLE', None)
    env['FRC_PARENT_SCOPE'] = scope
    if use_session:
        env['FRC_PIW_SESSION'] = str(session)
    else:
        env.pop('FRC_PIW_SESSION', None)
    payload = {'hook_event_name': 'Stop', 'last_assistant_message': 'Lifecycle complete; terminal PASS.', 'cwd': str(session)} if stop else {'hook_event_name': 'PreToolUse', 'tool_name': 'Write', 'tool_input': {'file_path': str(path)}}
    run = subprocess.run([sys.executable, str(SCRIPTS / 'hooks/full_run_pretooluse_gate.py')], input=json.dumps(payload), capture_output=True, text=True, encoding='utf-8', errors='strict', env=env)
    return run.returncode, json.loads(run.stdout) if run.stdout.strip() else {}


def authorize_cli(session):
    run = subprocess.run([sys.executable, str(SCRIPTS / 'full_run_contract_check.py'), 'authorize', '--run-scope', 'project_independent', '--piw-session', str(session)], capture_output=True, text=True, encoding='utf-8', errors='strict')
    return run.returncode, json.loads(run.stdout)


def record(name, passed, detail):
    RESULTS.append({'name': name, 'passed': passed, 'evidence_level': 'synthetic_integration', 'detail': detail})
    print(('PASS ' if passed else 'FAIL ') + name + ': ' + str(detail))


def expect_error(name, fn, expected):
    try:
        result = fn()
        record(name, False, {'unexpected': result})
    except piw.PIWError as exc:
        record(name, exc.code == expected, {'code': exc.code, 'expected': expected})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix='piw-integration-') as tmpdir:
        tmp = Path(tmpdir)
        session, req = setup(tmp / 'draft')
        completed = finish(session, req)
        rc, checked = verify_cli(session)
        record('draft_task_complete_nonterminal', completed.get('task_complete') is True and rc == 0 and checked['lifecycle_terminal'] is False and checked['research_acceptance'] is False, {'code': checked['code'], 'rc': rc})
        evidence_target = Path(checked['evaluation']['path'])
        evidence_before = evidence_target.read_bytes()
        expect_error('delivery_cannot_overwrite_evaluation_evidence', lambda: coordinator.deliver(session, evidence_target), 'PIW-DELIVERY-LOCATION')
        record('collision_refusal_preserves_evidence_bytes', evidence_target.read_bytes() == evidence_before, 'Exact evaluator bytes unchanged')
        expect_error('delivery_cannot_overwrite_completion_export', lambda: coordinator.deliver(session, session / 'completion.json'), 'PIW-DELIVERY-LOCATION')
        forked, req = setup(tmp / 'forked-host')
        coordinator.start(forked, req); plan(forked)
        for _ in range(3):
            ingest_child(forked, fork_history=True)
        completed_fork = coordinator.deliver(forked, tmp / 'forked-final.md')
        rc, rechecked_fork = verify_cli(forked)
        record('actual_fork_metadata_shape_and_inherited_turn', completed_fork.get('task_complete') is True and rc == 0 and rechecked_fork.get('task_complete') is True, {'rc': rc, 'code': rechecked_fork['code']})
        first_host = piw.read_json(forked / 'logs/state.json')['events'][1]['host']
        completed_host_log = Path(first_host['child_log'])
        append_log(completed_host_log, host_row('event_msg', {'type': 'token_count'}))
        rc, appended = verify_cli(forked)
        record('fork_trace_prefix_allows_later_appends', rc == 0 and appended.get('task_complete') is True, {'rc': rc})
        append_bytes = completed_host_log.read_bytes()
        tampered_bytes = append_bytes.replace(first_host['agent_execution_id'].encode(), str(uuid.uuid4()).encode(), 1)
        piw.write_bytes(completed_host_log, tampered_bytes)
        rc, tampered = verify_cli(forked)
        record('fork_trace_prefix_rejects_changed_history', rc != 0 and tampered.get('code') == 'PIW-HOST-TRACE-DRIFT', {'rc': rc, 'code': tampered.get('code')})
        piw.write_bytes(completed_host_log, append_bytes)
        fork_negative, req = setup(tmp / 'fork-negative')
        coordinator.start(fork_negative, req); plan(fork_negative)
        fork_result, fork_evidence = complete_child(fork_negative, fork_history=True)
        fork_log = Path(fork_evidence['child_log'])
        original_fork = fork_log.read_bytes()
        fork_rows = [json.loads(x) for x in original_fork.splitlines()]
        conflicting_parent = copy.deepcopy(fork_rows)
        conflicting_parent[1]['payload']['source'] = 'conflicting-foreign-source'
        cyclic_parent = copy.deepcopy(fork_rows)
        cyclic_parent[1]['payload']['forked_from_id'] = fork_evidence['agent_execution_id']
        for name, altered_rows in (
            ('fork_rejects_conflicting_parent_metadata', conflicting_parent),
            ('fork_rejects_cyclic_ancestry', cyclic_parent),
            ('fork_rejects_foreign_metadata', fork_rows[:2] + [host_row('session_meta', {'id': str(uuid.uuid4()), 'source': 'foreign'})] + fork_rows[2:]),
            ('fork_rejects_duplicate_current_metadata', fork_rows[:2] + [copy.deepcopy(fork_rows[0])] + fork_rows[2:]),
            ('fork_rejects_duplicate_ancestor_metadata', fork_rows[:2] + [copy.deepcopy(fork_rows[1])] + fork_rows[2:]),
            ('fork_rejects_missing_current_header', fork_rows[1:]),
        ):
            piw.write_bytes(fork_log, b''.join((json.dumps(x) + '\n').encode() for x in altered_rows))
            expect_error(name, lambda: coordinator.ingest(fork_negative, fork_result, fork_evidence), 'PIW-HOST-IDENTITY')
            piw.write_bytes(fork_log, original_fork)
        revision, req = setup(tmp / 'revision', revision=True, proposal=True)
        completed = finish(revision, req)
        record('revision_actual_bytes_and_proposal_preservation', completed.get('task_complete') is True and Path(completed['artifact']['path']).read_bytes() == REVISED and (tmp / 'revision/input.md').read_bytes() == FIXTURE, {'code': completed['code']})
        unchanged, req = setup(tmp / 'unchanged', revision=True)
        completed = finish(unchanged, req, no_change=True)
        record('explained_no_change_uses_all_roles', completed.get('task_complete') is True and Path(completed['artifact']['path']).read_bytes() == FIXTURE, completed['code'])
        correction, req = setup(tmp / 'correction')
        coordinator.start(correction, req); plan(correction); ingest_child(correction)
        found = ingest_child(correction, blockers=True)
        corrected = ingest_child(correction)
        ingest_child(correction); ingest_child(correction)
        completed = coordinator.deliver(correction, tmp / 'correction-final.md')
        record('finding_driven_correction_and_new_review', found['request']['phase'] == 'generation' and corrected['request']['phase'] == 'evaluation' and completed.get('task_complete') is True and completed['correction_cycles'] == 1, completed['code'])
        exhausted, req = setup(tmp / 'exhaustion', max_corrections=1)
        coordinator.start(exhausted, req); plan(exhausted); ingest_child(exhausted)
        ingest_child(exhausted, blockers=True); ingest_child(exhausted)
        stopped = ingest_child(exhausted, blockers=True)
        rc, result = verify_cli(exhausted)
        record('correction_limit_needs_revision', stopped['status'] == 'needs_revision' and rc != 0 and result['code'] == 'PIW-NEEDS-REVISION', {'rc': rc, 'code': result['code']})
        unavailable, req = setup(tmp / 'unavailable', available=False)
        expect_error('native_capability_absent', lambda: coordinator.start(unavailable, req), 'PIW-HOST-CAPABILITY-UNAVAILABLE')
        binding = piw.bind_pass(pass_name='grammar-mechanics-pass', text='Each reviewer examine a request.')
        record('read_only_binding_survives_without_subagents', binding['status'] == 'bound_not_reviewed' and not binding['task_complete'], binding['status'])
        expect_error('invalid_explicit_governed_binding', lambda: piw.bind_pass(pass_name='grammar-mechanics-pass', text='Text.', authoritative_binding=tmp / 'bad.json'), 'PIW-AUTHORITATIVE-BINDING-INVALID')
        expect_error('protected_destination', lambda: piw.assert_output(tmp / 'research/60_Workbench/w/manuscript/main.md'), 'DEST-PROTECTED')
        # Restore every tampered copy before the next independent negative probe.
        contract, _, log, _ = coordinator.replay(revision)
        alterations = [
            ('missing_reflection', Path(log['events'][-1]['result']['path']), None, 'PIW-REQUIRED-EVIDENCE-MISSING'),
            ('missing_review', Path(log['events'][-2]['result']['path']), None, 'PIW-REQUIRED-EVIDENCE-MISSING'),
            ('missing_revision_pin', revision / 'binding/mss_pin.json', None, 'PIW-MISSING-INPUT-PIN'),
            ('input_drift', Path(contract['input']['path']), b'changed input', 'MSS_PIN_DRIFT'),
            ('stale_final', Path(piw.read_json(revision / 'binding/delivery.json')['artifact']['path']), b'changed final prose', 'PIW-FINAL-BYTES-STALE'),
        ]
        for name, path, replacement, expected in alterations:
            original = path.read_bytes()
            if replacement is None:
                path.unlink()
            else:
                piw.write_bytes(path, replacement)
            rc, result = verify_cli(revision)
            record(name, rc != 0 and result['code'] == expected, {'rc': rc, 'code': result['code'], 'expected': expected})
            piw.write_bytes(path, original)
        rc, result = authorize_cli(revision)
        record('full_run_authorize_valid_standalone', rc == 0 and result.get('status') == 'OK', {'rc': rc, 'status': result.get('status')})
        pinpath = revision / 'binding/mss_pin.json'
        original_pin = pinpath.read_bytes(); pinpath.unlink()
        rc, result = authorize_cli(revision)
        codes = [x['code'] for x in result.get('findings', [])]
        record('full_run_authorize_missing_revision_pin', rc != 0 and 'PIW-MISSING-INPUT-PIN' in codes, {'rc': rc, 'codes': codes})
        piw.write_bytes(pinpath, original_pin)
        for name, path, scope, use_session, expected in [
            ('hook_permitted_task_output', revision / 'draft/new-candidate.md', 'project_independent', True, None),
            ('hook_missing_session', revision / 'draft/new-candidate.md', 'project_independent', False, 'FRC-PIW-SESSION-REQUIRED'),
            ('hook_unknown_scope', revision / 'draft/new-candidate.md', 'bogus', True, 'FRC-SCOPE-UNKNOWN'),
            ('hook_protected_workbench', tmp / 'research/60_Workbench/w/manuscript/main.md', 'project_independent', True, 'DEST-PROTECTED'),
            ('hook_outside_bound_run', tmp / 'outside.md', 'project_independent', True, 'PIW-OUTPUT-SCOPE')]:
            rc, result = hook_cli(revision, path, scope=scope, use_session=use_session)
            reason = result.get('hookSpecificOutput', {}).get('permissionDecisionReason', '')
            record(name, rc == 0 and ((not result) if expected is None else expected in reason), {'rc': rc, 'reason': reason})
        rc, result = hook_cli(revision, stop=True)
        record('hook_terminal_refusal_exact', rc == 0 and result.get('decision') == 'block' and 'FRC-PIW-NON-TERMINAL' in result.get('reason', ''), result)
        # Valid optional project context uses the preexisting read-only contract validator.
        from assignment_fixture_support import write_valid_contract
        context_root = tmp / 'optional-project'
        (context_root / 'reviews').mkdir(parents=True)
        write_valid_contract(context_root)
        binding = piw.bind_pass(pass_name='grammar-mechanics-pass', text='A valid sentence.', authoritative_binding=context_root / 'reviews/assignment_contract.json')
        record('valid_optional_project_context_without_lifecycle', binding['project_context']['context_only'] is True and not (context_root / 'reviews/phase_state.json').exists(), binding['project_context']['native_validation'])
        contextual, req = setup(tmp / 'profile-venue')
        venue = tmp / 'venue.md'
        piw.write_bytes(venue, b'Use the serial comma in lists for this venue.\n')
        req.update(profile='structural', venue_path=str(venue))
        coordinator.start(contextual, req)
        packet = plan(contextual)
        record('profile_venue_exclusion_in_child_brief', packet['request']['profile'] == 'structural' and packet['request']['venue'] == piw.identity(venue) and packet['request']['exclusions'] == ['chung-academic-voice-pass'], {'profile': packet['request']['profile'], 'venue_sha256': packet['request']['venue']['sha256']})
        import piw_overlay_attach as overlays
        excluded = overlays.attach_overlay(contextual, overlay='Chung voice')
        record('excluded_overlay_stays_inactive', excluded['status'] == 'noop' and excluded['reason_code'] == 'PIW-OVERLAY-EXCLUDED', excluded['reason_code'])
        expect_error('overlay_flag_is_not_evidence', lambda: overlays.attach_overlay(contextual, evidence_present=True), 'PIW-OVERLAY-EVIDENCE-REQUIRED')
        request_result, request_host = complete_child(contextual)
        request_result['exclusions'] = []
        expect_error('role_cannot_reenable_excluded_voice', lambda: coordinator.ingest(contextual, request_result, request_host), 'PIW-EXCLUSION-DRIFT')
        for name, claim in [('forged_completion_flag', {'completion': True}), ('file_presence_only', {'signal': 'file_presence'}), ('terminal_promotion', {'piw_session': str(revision), 'promotion': True})]:
            result = guard.evaluate_completion_claim(claim)
            expected = 'FRC-PIW-NON-TERMINAL' if name == 'terminal_promotion' else 'PIW-FAKE-COMPLETION'
            record(name, not result.get('completion') and result['code'] == expected, result['code'])
        impersonation, req = setup(tmp / 'impersonation')
        coordinator.start(impersonation, req); plan(impersonation)
        gen, host = complete_child(impersonation); coordinator.ingest(impersonation, gen, host)
        ev, evhost = complete_child(impersonation, execution_id=gen['agent_execution_id'])
        expect_error('generator_cannot_evaluate_itself', lambda: coordinator.ingest(impersonation, ev, evhost), 'PIW-ROLE-IMPERSONATION')
        failed, failedhost = complete_child(impersonation, outcome='timed_out')
        expect_error('timed_out_reviewer', lambda: coordinator.ingest(impersonation, failed, failedhost), 'PIW-EXECUTION-FAILED')
        replayed = copy.deepcopy(ev); replayed['run_id'] = 'another-run'
        expect_error('replayed_wrong_run', lambda: coordinator.ingest(impersonation, replayed, evhost), 'PIW-WRONG-RUN-OR-STEP')
        altered = copy.deepcopy(ev); altered['agent_execution_id'] = str(uuid.uuid4())
        altered['summary'] += ' Caller has altered this claimed output.'
        expect_error('result_does_not_match_actual_host_output', lambda: coordinator.ingest(impersonation, altered, evhost), 'PIW-HOST-RESULT-MISMATCH')
        bom_scoped, bom_req = setup(tmp / 'scope-bom', revision=True, fixture=BOM_FIXTURE)
        try:
            coordinator.start(bom_scoped, bom_req)
            bom_scope = piw.read_json(bom_scoped / 'binding/run.json')['requested_scope']
            expected_end = BOM_FIXTURE.index(b'# Anchor')
            record('utf8_bom_first_heading_scope', bom_scope['start_byte'] == 3 and bom_scope['end_byte'] == expected_end and bom_scope['prefix_sha256'] == piw.digest(BOM_FIXTURE[:3]) and bom_scope['suffix_sha256'] == piw.digest(BOM_FIXTURE[expected_end:]), bom_scope)
        except piw.PIWError as exc:
            record('utf8_bom_first_heading_scope', False, {'code': exc.code, 'message': str(exc)})
        # A claimed Generator must not replace the required pre-plan Evaluator diagnosis.
        sequence, req = setup(tmp / 'role-sequence', revision=True)
        packet = coordinator.start(sequence, req)
        bound_req = packet['request']
        bound_req['role'] = 'generator'
        contract = piw.read_json(sequence / 'binding/run.json')
        expect_error('generator_cannot_impersonate_initial_diagnosis', lambda: coordinator.validate_result(contract, bound_req, {}, coordinator.initial_state(contract)), 'PIW-ROLE-SEQUENCE')
        scoped, req = setup(tmp / 'scope', revision=True)
        coordinator.start(scoped, req); ingest_child(scoped); plan(scoped)
        result, evidence = complete_child(scoped, artifact=REVISED.replace(b'[Anchor-A]', b'[Altered]'))
        expect_error('unrequested_section_change', lambda: coordinator.ingest(scoped, result, evidence), 'PIW-SCOPE-DRIFT')
    summary = {'passed': sum(x['passed'] for x in RESULTS), 'failed': sum(not x['passed'] for x in RESULTS), 'tests': RESULTS, 'live_host_acceptance': 'not_exercised_by_this_suite', 'fixed_AT01_AT14_matrix': 'separate_required_live_evidence'}
    if args.report:
        piw.write_json(args.report, summary)
    print(json.dumps({k: summary[k] for k in ('passed', 'failed', 'live_host_acceptance')}))
    return 0 if not summary['failed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
