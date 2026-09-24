#!/usr/bin/env python3
"""Claude Code adapter fixtures over synthetic session JSONL; NOT live-host qualification.

Rows mirror the observed Claude Code transcript shape (session log plus
``<session>/subagents/agent-<id>.jsonl``). They exercise the real verifier and
the real coordinator, never cognitive execution.
"""
import json
import tempfile
from datetime import datetime, timedelta, timezone
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import piw_claude_host as claude
import piw_completion_guard as guard
import piw_coordinator as coordinator
import coherence_fixture_support as coherence_fixture
import piw_native_host as native
import piw_session as piw


class ClaudeHost:
    """Writes Claude Code shaped JSONL for one parent session and its subagents."""

    def __init__(self, logs_root: Path, session_id: str | None = None):
        self.logs = logs_root
        self.session_id = session_id or str(uuid.uuid4())
        self.parent = logs_root / f'{self.session_id}.jsonl'
        self.subagents = logs_root / self.session_id / 'subagents'
        self.tick = 0
        self.base = datetime.now(timezone.utc)
        self.append(self.parent, {'type': 'queue-operation', 'operation': 'enqueue', 'sessionId': self.session_id})
        self.append(self.parent, {'type': 'user', 'uuid': str(uuid.uuid4()), 'parentUuid': None, 'isSidechain': False,
                                  'sessionId': self.session_id, 'message': {'role': 'user', 'content': 'Draft the note.'}})

    def stamp(self) -> str:
        # strictly increasing and never behind real time, so a coordinator request created
        # a moment ago always precedes the rows written for it
        self.base = max(datetime.now(timezone.utc), self.base + timedelta(microseconds=1))
        return self.base.isoformat().replace('+00:00', 'Z')

    def append(self, path: Path, row: dict) -> str:
        row = {'timestamp': self.stamp(), **row}
        data = path.read_bytes() if path.exists() else b''
        piw.write_bytes(path, data + (json.dumps(row) + '\n').encode('utf-8'))
        return row['timestamp']

    def dispatch(self, prompt: str, tool: str = 'Agent') -> str:
        turn_id = 'toolu_' + uuid.uuid4().hex[:24]
        self.append(self.parent, {'type': 'assistant', 'uuid': str(uuid.uuid4()), 'isSidechain': False, 'sessionId': self.session_id,
                                  'message': {'role': 'assistant', 'content': [{'type': 'tool_use', 'id': turn_id, 'name': tool,
                                              'input': {'subagent_type': 'co-author-harness:generator', 'prompt': prompt}}]}})
        return turn_id

    def child_run(self, agent_id: str, prompt: str, final: str, stop_reason: str = 'end_turn', session_id: str | None = None, meta_turn: str | None = None) -> Path:
        sid = session_id or self.session_id
        path = self.subagents / f'agent-{agent_id}.jsonl'
        self.subagents.mkdir(parents=True, exist_ok=True)
        base = {'agentId': agent_id, 'isSidechain': True, 'sessionId': sid}
        self.append(path, {**base, 'type': 'user', 'uuid': str(uuid.uuid4()), 'parentUuid': None, 'message': {'role': 'user', 'content': prompt}})
        self.append(path, {**base, 'type': 'attachment', 'uuid': str(uuid.uuid4()), 'attachment': {'type': 'hook_success'}})
        self.append(path, {**base, 'type': 'assistant', 'uuid': str(uuid.uuid4()),
                           'message': {'role': 'assistant', 'content': [{'type': 'text', 'text': final}], 'stop_reason': stop_reason}})
        if meta_turn:
            piw.write_bytes(path.with_suffix('.meta.json'), json.dumps({'agentType': 'co-author-harness:generator', 'toolUseId': meta_turn}).encode())
        return path

    def complete(self, turn_id: str, agent_id: str, final: str, status: str = 'completed') -> str:
        return self.append(self.parent, {'type': 'user', 'uuid': str(uuid.uuid4()), 'isSidechain': False, 'sessionId': self.session_id,
                                         'message': {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': turn_id, 'content': [{'type': 'text', 'text': final}]}]},
                                         'toolUseResult': {'status': status, 'agentId': agent_id, 'agentType': 'co-author-harness:generator',
                                                           'content': [{'type': 'text', 'text': final}]}})

    def run(self, request: dict, result: dict, agent_id: str = 'a' + uuid.uuid4().hex[:16], *, token: str | None = None,
            final: str | None = None, stop_reason: str = 'end_turn', status: str = 'completed', tool: str = 'Agent',
            child_session: str | None = None, meta_turn: str | None = None):
        token = token if token is not None else 'COAUTHOR_REQUEST_SHA256=' + piw.digest(piw.json_bytes(request))
        prompt = 'Role request follows. ' + token + '\n' + json.dumps(request)
        final = final if final is not None else json.dumps(result)
        turn_id = self.dispatch(prompt, tool)
        child = self.child_run(agent_id, prompt, final, stop_reason, child_session, meta_turn)
        self.complete(turn_id, agent_id, final, status)
        return {'agent_execution_id': agent_id, 'turn_id': turn_id, 'child_log': str(child)}


def host_object(host: ClaudeHost, available=True) -> dict:
    return {'adapter': 'claude-code-jsonl', 'subagents_available': available, 'logs_root': str(host.logs), 'parent_log': str(host.parent)}


class ClaudeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.logs = self.root / 'projects' / 'workspace'
        self.logs.mkdir(parents=True)
        self.host_writer = ClaudeHost(self.logs)
        self.staging = self.root / 'staging'
        self.host = native.bind_host(host_object(self.host_writer), self.staging)
        self.request = {'created_at': (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(), 'role': 'generator', 'request_id': 'fixture-request'}
        self.agent = 'a' + uuid.uuid4().hex[:16]
        self.result = {'agent_execution_id': self.agent, 'prose': 'A substantive fixture result.'}

    def run_child(self, **kwargs):
        return self.host_writer.run(self.request, self.result, self.agent, **kwargs)

    def test_bind_derives_parent_identity_and_registry_lists_adapter(self):
        self.assertEqual(self.host['parent_execution_id'], self.host_writer.session_id)
        self.assertIn('claude-code-jsonl', native.ADAPTERS)
        with self.assertRaises(piw.PIWError) as raised:
            native.bind_host({**host_object(self.host_writer), 'parent_execution_id': 'foreign'}, self.staging)
        self.assertEqual(raised.exception.code, 'PIW-HOST-IDENTITY')

    def test_unknown_adapter_and_missing_capability_refused(self):
        for host in ({'adapter': 'unknown-host', 'subagents_available': True}, host_object(self.host_writer, None), host_object(self.host_writer, False)):
            with self.subTest(host=host):
                with self.assertRaises(piw.PIWError) as raised:
                    native.bind_host(host, self.staging)
                self.assertEqual(raised.exception.code, 'PIW-HOST-CAPABILITY-UNAVAILABLE')

    def test_completion_prefix_replay_and_metrics_start(self):
        evidence = self.run_child(meta_turn=None)
        bound = native.verify_execution(self.host, evidence, self.request, self.result)
        self.assertEqual(bound['agent_execution_id'], self.agent)
        self.host_writer.append(self.host_writer.parent, {'type': 'user', 'sessionId': self.host_writer.session_id, 'message': {'role': 'user', 'content': 'later'}})
        self.assertEqual(native.verify_execution(self.host, bound, self.request, self.result, bound['pins']), bound)
        _, rows = native._rows(Path(bound['child_log']), bound['pins']['child']['bytes'])
        self.assertEqual(native.start_timestamp(self.host, rows, bound), bound['started_at'])

    def test_meta_file_must_name_the_dispatching_tool_use(self):
        evidence = self.run_child(meta_turn='toolu_other')
        with self.assertRaisesRegex(piw.PIWError, 'metadata'):
            native.verify_execution(self.host, evidence, self.request, self.result)

    def test_archived_reader_uses_only_captured_prefixes(self):
        evidence = self.run_child()
        bound = native.verify_execution(self.host, evidence, self.request, self.result)
        captured = {p['path']: Path(p['path']).read_bytes()[:p['bytes']] for p in bound['pins'].values()}

        def reader(path, count):
            data = captured[str(path)][:count]
            return data, [json.loads(line) for line in data.splitlines() if line.strip()]
        with patch('piw_native_host._rows', side_effect=AssertionError('Archive must not read live paths')):
            self.assertEqual(native.verify_execution(self.host, bound, self.request, self.result, bound['pins'], reader), bound)
            captured[bound['pins']['child']['path']] = b''
            with self.assertRaises(piw.PIWError):
                native.verify_execution(self.host, bound, self.request, self.result, bound['pins'], reader)

    def test_unfinished_child_refused(self):
        for kwargs, pattern in (({'stop_reason': 'max_tokens'}, 'end_turn'), ({'status': 'failed'}, 'finish successfully')):
            with self.subTest(kwargs=kwargs):
                writer = ClaudeHost(self.logs)
                host = native.bind_host(host_object(writer), self.staging)
                evidence = writer.run(self.request, self.result, self.agent, **kwargs)
                with self.assertRaisesRegex(piw.PIWError, pattern):
                    native.verify_execution(host, evidence, self.request, self.result)

    def test_unbound_request_refused(self):
        evidence = self.run_child(token='not the current request')
        with self.assertRaisesRegex(piw.PIWError, 'dispatch'):
            native.verify_execution(self.host, evidence, self.request, self.result)

    def test_non_dispatch_tool_refused(self):
        evidence = self.run_child(tool='Bash')
        with self.assertRaisesRegex(piw.PIWError, 'dispatch'):
            native.verify_execution(self.host, evidence, self.request, self.result)

    def test_result_tampering_refused(self):
        evidence = self.run_child()
        with self.assertRaisesRegex(piw.PIWError, 'finished host output'):
            native.verify_execution(self.host, evidence, self.request, {**self.result, 'prose': 'Edited after execution'})

    def test_parent_child_final_disagreement_refused(self):
        evidence = self.run_child()
        parent = Path(self.host['parent_log'])
        parent.write_bytes(parent.read_bytes().replace(b'substantive fixture', b'rewritten parent'))
        with self.assertRaisesRegex(piw.PIWError, 'differs from the child'):
            native.verify_execution(self.host, evidence, self.request, self.result)

    def test_trace_tampering_refused(self):
        evidence = self.run_child()
        bound = native.verify_execution(self.host, evidence, self.request, self.result)
        path = Path(evidence['child_log'])
        path.write_bytes(path.read_bytes().replace(b'substantive', b'manipulated'))
        with self.assertRaisesRegex(piw.PIWError, 'prefix changed'):
            native.verify_execution(self.host, bound, self.request, self.result, bound['pins'])

    def test_wrong_parent_refused(self):
        evidence = self.run_child()
        with self.assertRaises(piw.PIWError):
            native.verify_execution({**self.host, 'parent_execution_id': 'foreign'}, evidence, self.request, self.result)

    def test_child_of_other_session_refused(self):
        evidence = self.run_child(child_session=str(uuid.uuid4()))
        with self.assertRaisesRegex(piw.PIWError, 'native subagent'):
            native.verify_execution(self.host, evidence, self.request, self.result)

    def test_foreign_rows_in_child_log_refused(self):
        evidence = self.run_child()
        self.host_writer.append(Path(evidence['child_log']), {'type': 'assistant', 'agentId': 'other', 'isSidechain': True,
                                                              'sessionId': self.host_writer.session_id,
                                                              'message': {'role': 'assistant', 'content': [{'type': 'text', 'text': 'x'}], 'stop_reason': 'end_turn'}})
        with self.assertRaisesRegex(piw.PIWError, 'only this subagent'):
            native.verify_execution(self.host, evidence, self.request, self.result)

    def test_child_log_outside_session_subagents_refused(self):
        evidence = self.run_child()
        stray = self.logs / 'elsewhere' / f'agent-{self.agent}.jsonl'
        stray.parent.mkdir(parents=True)
        stray.write_bytes(Path(evidence['child_log']).read_bytes())
        with self.assertRaisesRegex(piw.PIWError, 'original subagent log'):
            native.verify_execution(self.host, {**evidence, 'child_log': str(stray)}, self.request, self.result)

    def test_missing_original_dispatch_refused(self):
        evidence = self.run_child()
        parent = Path(self.host['parent_log'])
        rows = [r for r in parent.read_bytes().splitlines() if b'tool_use' not in r or b'tool_result' in r]
        parent.write_bytes(b'\n'.join(rows) + b'\n')
        with self.assertRaisesRegex(piw.PIWError, 'dispatch'):
            native.verify_execution(self.host, evidence, self.request, self.result)

    def test_stale_execution_refused(self):
        self.request['created_at'] = '2999-01-01T00:00:00+00:00'
        evidence = self.run_child()
        with self.assertRaisesRegex(piw.PIWError, 'predates'):
            native.verify_execution(self.host, evidence, self.request, self.result)


class ClaudeCoordinatorTests(unittest.TestCase):
    """Real coordinator, verifier and completion guard over synthetic Claude Code traces."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.logs = self.root / 'projects' / 'workspace'
        self.logs.mkdir(parents=True)
        self.writer = ClaudeHost(self.logs)
        opened = piw.open_session(ingress_kind='standalone', mss_path=None, outputs_root=self.root / 'output')
        self.session = Path(opened['staging_root'])

    def complete_child(self, blockers=False):
        packet = coordinator.next_step(self.session)
        req = packet['request']
        contract = piw.read_json(self.session / 'binding/run.json')
        self.assertEqual(req['run_scope'], 'project_independent')
        self.assertTrue(Path(req['role_prompt']['path']).name == f"{req['role']}.md")
        self.assertEqual([Path(x['path']).parent.name for x in req['skill_bodies']], contract['passes'])
        agent_id = 'a' + uuid.uuid4().hex[:16]
        result = {k: req[k] for k in ('run_id', 'step_id', 'role', 'phase', 'target', 'applied_passes', 'exclusions')}
        result.update(request_sha256=packet['request_sha256'], agent_execution_id=agent_id, outcome='completed', rule_reads=req['rules'],
                      summary='Integration fixture explanation: this synthetic result exercises bounded scope checks and evidence validation, and is not an actual cognitive assessment.')
        if req['role'] == 'generator':
            path = self.session / 'draft' / f'candidate-{req["sequence"]}.md'
            piw.write_bytes(path, b'A queue records submitted requests. A policy defines whether a request can receive approval. Recording alone does not grant approval.\n')
            result['artifact'] = piw.identity(path)
            result['addressed_findings'] = [x['id'] for x in req['findings_to_address']]
        else:
            result['checks'] = [{'id': x['id'], 'status': 'pass', 'rationale': 'Synthetic integration assertion supplies a concrete scope-bound check result for validator testing.', 'locators': ['paragraph 1']} for x in req['required_checks']]
            result['findings'] = [{'id': 'F1', 'blocking': True, 'locator': 'paragraph 1', 'message': 'Synthetic planted blocking issue must be corrected before completion.'}] if blockers else []
            scope_text, changed_units, scope_units = coordinator.coherence_scope(contract, req['target'], req['phase'])
            result['coherence_review'] = coherence_fixture.build(scope_text, changed_units, scope_unit_ids=scope_units)
        evidence = self.writer.run(req, result, agent_id)
        return coordinator.ingest(self.session, result, evidence)

    def test_full_draft_loop_completes_through_claude_traces(self):
        request = {'brief': 'Explain the conceptual distinction between request recording and approval; invent no studies or sources.',
                   'requested_scope': {'description': 'whole draft'}, 'host': host_object(self.writer), 'exclusions': ['chung-academic-voice-pass']}
        response = coordinator.start(self.session, request)
        self.assertEqual(response['status'], 'plan')  # standalone draft: no diagnosis before the plan
        self.assertEqual(piw.read_json(self.session / 'binding/run.json')['host']['adapter'], 'claude-code-jsonl')
        coordinator.record_plan(self.session, {'summary': 'Draft one short conceptual note answering the brief without inventing sources or studies.', 'steps': ['Write the note.']})
        self.complete_child()            # generator
        self.complete_child(blockers=True)   # evaluator finds a blocker -> correction
        self.complete_child()            # generator correction
        self.complete_child()            # evaluator clean
        packet = self.complete_child()   # reflector
        self.assertEqual(packet['status'], 'ready_to_deliver')
        delivered = coordinator.deliver(self.session, self.root / 'final.md')
        self.assertTrue(delivered['task_complete'])
        verified = guard.verify_completion(self.session)
        self.assertTrue(verified['task_complete'])
        self.assertFalse(verified.get('lifecycle_terminal'))
        self.assertFalse(verified.get('research_acceptance'))
        self.assertEqual(verified.get('host_adapter', 'claude-code-jsonl'), 'claude-code-jsonl')

    def test_missing_capability_blocks_drafting_only(self):
        request = {'brief': 'Explain the conceptual distinction between request recording and approval.',
                   'requested_scope': {'description': 'whole draft'}, 'host': host_object(self.writer, None)}
        with self.assertRaises(piw.PIWError) as raised:
            coordinator.start(self.session, request)
        self.assertEqual(raised.exception.code, 'PIW-HOST-CAPABILITY-UNAVAILABLE')
        bound = piw.bind_pass(pass_name='grammar-mechanics-pass', text='The set of results are robust.')
        self.assertEqual(bound['status'], 'bound_not_reviewed')


if __name__ == '__main__':
    unittest.main()
