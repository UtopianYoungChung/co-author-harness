"""Fast lane: two child dispatches, a two-file reading list, a citation gate and an uncertified receipt."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import fast_lane as fl
import full_run_contract_check as scope
import piw_session as piw

SCRIPTS = Path(__file__).resolve().parent
GOOD = 'Memos help readers act (Smith, 2020).\n\n## References\n\nSmith, J. (2020). Memos. Press.\n'
BAD = 'Memos help readers act (Jones, 2019).\n'
CLEAR = 'verdict: clear\n\n- [ADVISORY] para 1: fine\n\nChecked grounding.\n'
BLOCK = 'verdict: blocking\n\n- [BLOCKING] para 1: claim has no source\n'


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = fl.main([str(x) for x in argv])
    return code, json.loads(out.getvalue())


class Lane:
    def __init__(self, tmp, brief='Write a one paragraph memo.\n', input_text=None, extra=()):
        self.tmp = Path(tmp)
        (self.tmp / 'brief.md').write_text(brief, encoding='utf-8')
        args = ['open', '--task-root', self.tmp / 'task', '--brief', self.tmp / 'brief.md', *extra]
        self.input = None
        if input_text is not None:
            self.input = self.tmp / 'input.md'
            self.input.write_bytes(input_text.encode('utf-8'))
            args += ['--input', self.input]
        self.code, self.opened = run(*args)
        self.session = self.opened.get('session_path')

    def request(self, role):
        code, r = run('request', '--session', self.session, '--role', role)
        return (code, r, json.loads(Path(r['request_path']).read_text('utf-8')) if code == 0 else None)

    def generate(self, body, child='g1'):
        code, r, req = self.request('generator')
        assert code == 0, r
        Path(req['output_path']).write_bytes(body.encode('utf-8'))
        return run('record', '--session', self.session, '--role', 'generator', '--child-id', child, '--child-model', 'sonnet')

    def evaluate(self, findings, child='e1'):
        code, r, req = self.request('evaluator')
        assert code == 0, r
        Path(req['output_path']).write_bytes(findings.encode('utf-8'))
        return run('record', '--session', self.session, '--role', 'evaluator', '--child-id', child)

    def deliver(self, name='final.md'):
        return run('deliver', '--session', self.session, '--destination', self.tmp / name)


class FastLaneTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='fast-lane-')
        self.tmp = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def test_new_draft_happy_path_has_two_file_reading_list_and_uncertified_receipt(self):
        lane = Lane(self.tmp)
        self.assertEqual(lane.code, 0)
        self.assertEqual(scope.check_scope('project_independent', Path(lane.request('generator')[1]['request_path']).read_text('utf-8')), [])
        binding = json.loads(Path(lane.session).read_text('utf-8'))
        self.assertEqual([Path(x['path']).name for x in binding['rules']], ['GROUNDING_PROTOCOL.md', 'CITATION_DISCIPLINE.md'])
        self.assertEqual((binding['run_scope'], binding['lane'], binding['certified'], binding['lifecycle_terminal'], binding['research_acceptance']),
                         ('project_independent', 'fast', False, False, False))
        self.assertEqual(lane.generate(GOOD)[1]['status'], 'awaiting_evaluator')
        code, _, req = lane.request('evaluator')
        self.assertEqual(scope.check_scope('project_independent', Path(lane.session).parent.joinpath('requests', '1-evaluator.json').read_text('utf-8')), [])
        self.assertEqual(lane.evaluate(CLEAR)[1]['status'], 'ready_to_deliver')
        code, receipt = lane.deliver()
        self.assertEqual(code, 0, receipt)
        self.assertEqual((Path(self.tmp) / 'final.md').read_bytes(), GOOD.encode('utf-8'))
        self.assertEqual((receipt['lane'], receipt['certified'], receipt['lifecycle_terminal'], receipt['research_acceptance']), ('fast', False, False, False))
        self.assertEqual(receipt['corrections_used'], 0)
        self.assertEqual([x['role'] for x in receipt['children']], ['generator', 'evaluator'])
        self.assertEqual(run('status', '--session', lane.session)[1]['status'], 'delivered')

    def test_revision_reads_selected_pass_rules_and_leaves_input_untouched(self):
        original = 'Memos help readers act (Smith, 2020).\r\n\r\n## References\r\n\r\nSmith, J. (2020). Memos. Press.\r\n'
        lane = Lane(self.tmp, input_text=original, extra=('--pass', 'grammar-mechanics-pass', 'sentence-level-pass', '--exclude', 'sentence-level-pass'))
        binding = json.loads(Path(lane.session).read_text('utf-8'))
        self.assertEqual([Path(x['path']).name for x in binding['rules']], ['GROUNDING_PROTOCOL.md', 'CITATION_DISCIPLINE.md', 'blue_book_grammar_guidelines.md'])
        self.assertEqual(binding['exclusions'], ['sentence-level-pass'])
        code, _, req = lane.request('generator')
        self.assertEqual(req['input_path'], str(lane.input.resolve()))
        self.assertEqual(req['run_scope'], 'project_independent')
        lane.generate(original.replace('help', 'guide'))
        lane.evaluate(CLEAR)
        self.assertEqual(lane.deliver('input.md')[1]['code'], 'FAST-INPUT-APPLY-SEPARATE')
        self.assertEqual(lane.deliver('out/final.md')[0], 0)
        self.assertEqual(lane.input.read_bytes(), original.encode('utf-8'))

    def test_blocking_review_then_one_correction_then_clear(self):
        lane = Lane(self.tmp)
        lane.generate(BAD)
        self.assertEqual(lane.evaluate(BLOCK)[1]['status'], 'awaiting_generator')
        self.assertEqual(lane.deliver()[1]['code'], 'FAST-NOT-READY')
        code, _, req = lane.request('generator')
        self.assertEqual(req['findings_to_address'], ['- [BLOCKING] para 1: claim has no source'])
        self.assertEqual(lane.generate(BAD)[1]['code'], 'FAST-NO-CHANGE')
        self.assertEqual(lane.generate(GOOD)[0], 0)
        self.assertEqual(lane.evaluate(CLEAR)[1]['status'], 'ready_to_deliver')
        code, receipt = lane.deliver()
        self.assertEqual((code, receipt['corrections_used']), (0, 1))

    def test_blockers_after_the_limit_end_needs_revision(self):
        lane = Lane(self.tmp)
        lane.generate(BAD)
        lane.evaluate(BLOCK)
        lane.generate(BAD + 'More.\n')
        self.assertEqual(lane.evaluate(BLOCK)[1]['status'], 'needs_revision')
        self.assertEqual(lane.request('generator')[1]['code'], 'FAST-NEEDS-REVISION')
        self.assertEqual(lane.deliver()[1]['code'], 'FAST-NEEDS-REVISION')

    def test_lifecycle_claims_are_refused(self):
        for extra in (('--lifecycle-terminal',), ('--research-acceptance',), ('--promotion',), ('--run-scope', 'full_lifecycle')):
            self.assertEqual(Lane(self.tmp, extra=extra).opened['code'], 'FAST-NON-TERMINAL', extra)
        for line in ('research_acceptance: true', 'lifecycle_terminal: yes', 'run_scope: full_lifecycle'):
            self.assertEqual(Lane(self.tmp, brief='Write a memo.\n' + line + '\n').opened['code'], 'FAST-NON-TERMINAL', line)

    def test_unresolved_citation_in_candidate_refuses_delivery(self):
        lane = Lane(self.tmp)
        lane.generate(BAD)
        code, r, req = lane.request('evaluator')
        self.assertTrue(req['bibliography_inventory_errors'])
        lane.evaluate(CLEAR)
        code, r = lane.deliver()
        self.assertEqual((code, r['code']), (4, 'FAST-CITATIONS-UNRESOLVED'))
        self.assertFalse((Path(self.tmp) / 'final.md').exists())

    def test_unsupported_syntax_in_authors_input_is_allowed_but_added_syntax_is_refused(self):
        author = 'We follow \\cite{a} here.\n'
        lane = Lane(self.tmp, input_text=author)
        lane.generate('We follow \\cite{a} here, briefly.\n')
        lane.evaluate(CLEAR)
        code, receipt = lane.deliver()
        self.assertEqual(code, 0, receipt)
        self.assertEqual(len(receipt['citation_gate']['author_syntax_errors_allowed']), 1)
        again = Path(self.tmp) / 'again'
        again.mkdir()
        added = Lane(again, input_text=author)
        added.generate('We follow \\cite{a} and \\cite{b} here.\n')
        added.evaluate(CLEAR)
        self.assertEqual(added.deliver()[1]['code'], 'FAST-CITATIONS-UNRESOLVED')
        fresh_draft = Lane(again)
        fresh_draft.generate('We follow \\cite{a} here.\n')
        fresh_draft.evaluate(CLEAR)
        self.assertEqual(fresh_draft.deliver()[1]['code'], 'FAST-CITATIONS-UNRESOLVED')

    def test_sequence_and_role_rules(self):
        lane = Lane(self.tmp)
        self.assertEqual(lane.request('evaluator')[1]['code'], 'FAST-SEQUENCE')
        self.assertEqual(run('record', '--session', lane.session, '--role', 'evaluator', '--child-id', 'e1')[1]['code'], 'FAST-SEQUENCE')
        self.assertEqual(lane.deliver()[1]['code'], 'FAST-NOT-READY')
        lane.generate(GOOD, child='same')
        code, r, req = lane.request('evaluator')
        Path(req['output_path']).write_bytes(CLEAR.encode('utf-8'))
        self.assertEqual(run('record', '--session', lane.session, '--role', 'evaluator', '--child-id', 'same')[1]['code'], 'FAST-ROLE-DISTINCT')
        self.assertEqual(lane.evaluate(CLEAR, child='other')[0], 0)

    def test_malformed_findings_are_refused(self):
        for bad in ('no verdict here\n', 'verdict: maybe\n', 'verdict: clear\n- [BLOCKING] para 1: x\n',
                    'verdict: blocking\n- [ADVISORY] para 1: x\n', 'verdict: blocking\n- [BLOCKING] no colon\n', ''):
            lane = Lane(Path(tempfile.mkdtemp(dir=self.tmp)))
            lane.generate(GOOD)
            self.assertEqual(lane.evaluate(bad)[1]['code'], 'FAST-FINDINGS-SHAPE', repr(bad))

    def test_delivery_cannot_land_in_the_session_folder(self):
        lane = Lane(self.tmp)
        lane.generate(GOOD)
        lane.evaluate(CLEAR)
        target = Path(lane.session).parent / 'draft' / 'copy.md'
        code, r = run('deliver', '--session', lane.session, '--destination', target)
        self.assertEqual(r['code'], 'FAST-DELIVERY-LOCATION')

    def test_protected_workbench_task_root_is_refused(self):
        brief = Path(self.tmp) / 'brief.md'
        brief.write_text('Write a memo.\n', encoding='utf-8')
        code, r = run('open', '--task-root', Path(self.tmp) / '60_Workbench' / 'w1' / 'manuscript', '--brief', brief)
        self.assertEqual((code, r['code']), (4, 'DEST-PROTECTED'))

    def test_hook_allows_fast_session_writes_only(self):
        lane = Lane(self.tmp)
        root = Path(lane.session).parent

        def hook(path, fast=True):
            env = {k: v for k, v in os.environ.items() if k not in ('FRC_GATE_HOOK_DISABLE', 'FRC_PIW_SESSION', 'FRC_FAST_SESSION')}
            env['FRC_PARENT_SCOPE'] = 'project_independent'
            if fast:
                env['FRC_FAST_SESSION'] = lane.session
            payload = {'hook_event_name': 'PreToolUse', 'tool_name': 'Write', 'tool_input': {'file_path': str(path)}}
            run_ = subprocess.run([sys.executable, str(SCRIPTS / 'hooks' / 'full_run_pretooluse_gate.py')], input=json.dumps(payload),
                                  capture_output=True, text=True, encoding='utf-8', env=env)
            return json.loads(run_.stdout).get('hookSpecificOutput', {}).get('permissionDecision', 'allow') if run_.stdout.strip() else 'allow'
        self.assertEqual(hook(root / 'draft' / 'candidate-1.md'), 'allow')
        self.assertEqual(hook(root / 'review' / 'findings-1.md'), 'allow')
        self.assertEqual(hook(root / 'state.json'), 'deny')
        self.assertEqual(hook(root / 'draft' / '..' / 'binding.json'), 'deny')
        self.assertEqual(hook(Path(self.tmp) / 'elsewhere.md'), 'deny')
        self.assertEqual(hook(root / 'draft' / 'candidate-1.md', fast=False), 'deny')


if __name__ == '__main__':
    unittest.main()
