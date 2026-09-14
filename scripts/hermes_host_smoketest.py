#!/usr/bin/env python3
"""Hermes adapter fixtures. These are not live-host qualification evidence."""
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml

import hermes_plugin as plugin
import install_hermes as installer
import piw_native_host as native
import piw_session as piw


class Context:
    def __init__(self):
        self.skills = {}
        self.hooks = {}
        self.section = None

    def register_skill(self, name, path, description, frontmatter):
        self.skills[name] = (path, description, frontmatter)

    def register_hook(self, name, callback):
        self.hooks[name] = callback

    def register_system_prompt_section(self, name, callback):
        self.section = callback


class HermesAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        constants = types.ModuleType('hermes_constants')
        constants.get_hermes_home = lambda: self.home
        skill_utils = types.ModuleType('agent.skill_utils')
        skill_utils.yaml_load = yaml.safe_load
        self.ctx = Context()
        with patch.dict(sys.modules, {'hermes_constants': constants, 'agent.skill_utils': skill_utils}):
            plugin.register(self.ctx)
        self.traces = self.home / 'plugin-data/co-author-harness/host-traces'
        self.ctx.section({'session_id': 'parent'})
        self.host = native.bind_host({'adapter': 'hermes-hooks-jsonl', 'subagents_available': True,
                                     'logs_root': str(self.traces), 'parent_log': str(plugin.trace_path(self.traces, 'parent')),
                                     'parent_execution_id': 'parent'}, self.home / 'staging')
        self.request = {'created_at': piw.utc_now(), 'role': 'generator', 'request_id': 'fixture-request'}
        self.result = {'agent_execution_id': 'child', 'prose': 'A substantive fixture result.'}
        self.evidence = {'agent_execution_id': 'child', 'turn_id': 'turn', 'child_log': str(plugin.trace_path(self.traces, 'child'))}

    def run_child(self, completed=True, failed=False, interrupted=False, token=None, result=None):
        goal = token if token is not None else 'COAUTHOR_REQUEST_SHA256=' + piw.digest(piw.json_bytes(self.request))
        self.ctx.hooks['subagent_start'](parent_session_id='parent', child_session_id='child', child_goal=goal)
        self.ctx.hooks['on_session_end'](session_id='child', turn_id='turn', completed=completed, failed=failed, interrupted=interrupted)
        self.ctx.hooks['subagent_stop'](parent_session_id='parent', child_session_id='child', child_status='completed',
                                       child_summary=json.dumps(result or self.result))

    def test_registered_surface_and_context(self):
        policy = json.loads((plugin.ROOT / 'references/policies/command_surface.v1.json').read_text(encoding='utf-8'))
        expected = set(policy['public'] + policy['hidden']['legacy'] + policy['hidden']['maintainer'])
        self.assertEqual(set(self.ctx.skills), expected)
        self.assertIn('IS-theory-pass', self.ctx.skills)
        self.assertFalse(set(policy['hidden']['unavailable']) & set(self.ctx.skills))
        text = self.ctx.section({'session_id': 'parent'})
        self.assertLessEqual(len(text), 4000)
        self.assertIn(str(plugin.ROOT), text)
        binding = json.loads(text.split('This session host binding: ', 1)[1])
        self.assertIsNone(binding['subagents_available'])

    def test_unknown_or_disabled_session_capability_refused(self):
        for available in (None, False):
            with self.subTest(available=available):
                with self.assertRaises(piw.PIWError) as raised:
                    native.bind_host({**self.host, 'subagents_available': available}, self.home / 'staging')
                self.assertEqual(raised.exception.code, 'PIW-HOST-CAPABILITY-UNAVAILABLE')

    def test_completion_and_prefix_replay(self):
        self.run_child()
        bound = native.verify_execution(self.host, self.evidence, self.request, self.result)
        plugin.record(self.traces, 'parent', 'unrelated_later_event')
        self.assertEqual(native.verify_execution(self.host, bound, self.request, self.result, bound['pins']), bound)

    def test_budget_exhaustion_is_not_completion(self):
        self.run_child(completed=False)
        with self.assertRaisesRegex(piw.PIWError, 'successful finished'):
            native.verify_execution(self.host, self.evidence, self.request, self.result)

    def test_structured_failure_wins_over_summary(self):
        self.run_child(failed=True)
        with self.assertRaises(piw.PIWError):
            native.verify_execution(self.host, self.evidence, self.request, self.result)

    def test_interruption_refused(self):
        self.run_child(interrupted=True)
        with self.assertRaises(piw.PIWError):
            native.verify_execution(self.host, self.evidence, self.request, self.result)

    def test_unbound_request_refused(self):
        self.run_child(token='not the current request')
        with self.assertRaisesRegex(piw.PIWError, 'dispatch'):
            native.verify_execution(self.host, self.evidence, self.request, self.result)

    def test_result_tampering_refused(self):
        self.run_child()
        result = {**self.result, 'prose': 'Edited after execution'}
        with self.assertRaisesRegex(piw.PIWError, 'original host output'):
            native.verify_execution(self.host, self.evidence, self.request, result)

    def test_trace_tampering_refused(self):
        self.run_child()
        bound = native.verify_execution(self.host, self.evidence, self.request, self.result)
        path = Path(self.evidence['child_log'])
        path.write_bytes(path.read_bytes().replace(b'substantive', b'manipulated'))
        with self.assertRaisesRegex(piw.PIWError, 'prefix changed'):
            native.verify_execution(self.host, bound, self.request, self.result, bound['pins'])

    def test_wrong_parent_refused(self):
        self.run_child()
        with self.assertRaises(piw.PIWError):
            native.verify_execution({**self.host, 'parent_execution_id': 'foreign'}, self.evidence, self.request, self.result)

    def test_missing_original_dispatch_refused(self):
        self.run_child()
        parent = Path(self.host['parent_log'])
        rows = [r for r in parent.read_bytes().splitlines() if b'child_started' not in r]
        parent.write_bytes(b'\n'.join(rows) + b'\n')
        with self.assertRaises(piw.PIWError):
            native.verify_execution(self.host, self.evidence, self.request, self.result)

    def test_stale_execution_refused(self):
        self.request['created_at'] = '2999-01-01T00:00:00+00:00'
        self.run_child()
        with self.assertRaises(piw.PIWError):
            native.verify_execution(self.host, self.evidence, self.request, self.result)

    def test_enable_preserves_other_settings(self):
        data = ('# Unicode: 한글\nmodel:\n  default: chosen\n  provider: selected\n'
                'plugins:\n  enabled: [existing]\n  disabled: [co-author-harness, other]\n'
                'fallback_providers:\n- provider: unchanged\n  model: unchanged\n').encode('utf-8')
        result = installer.enable_config(data)
        before, after = yaml.safe_load(data), yaml.safe_load(result)
        self.assertEqual({k:v for k,v in before.items() if k != 'plugins'}, {k:v for k,v in after.items() if k != 'plugins'})
        self.assertEqual(after['plugins']['enabled'], ['existing', 'co-author-harness'])
        self.assertEqual(after['plugins']['disabled'], ['other'])
        self.assertTrue(result.startswith(data.split(b'plugins:')[0]))
        self.assertEqual(installer.enable_config(result), result)

    def test_trace_refuses_governed_destination(self):
        with patch.dict(os.environ, {'COAUTHOR_EXTRA_GOVERNED_ROOTS': str(self.home)}):
            with self.assertRaises(plugin.destination.DestinationRefused):
                plugin.record(self.traces, 'protected-session', 'session_context')
        self.assertFalse(plugin.trace_path(self.traces, 'protected-session').exists())

    def test_installer_refuses_governed_destination(self):
        with patch.dict(os.environ, {'COAUTHOR_EXTRA_GOVERNED_ROOTS': str(self.home)}):
            with self.assertRaises(RuntimeError):
                installer.install(self.home)
            target = self.home / 'protected.txt'
            with self.assertRaises(installer.destination.DestinationRefused):
                installer.atomic(target, b'forbidden')
        self.assertFalse(target.exists())

    def test_installer_accepts_external_home_and_backs_up(self):
        config = b'model:\n  default: chosen\n  provider: selected\n'
        (self.home / 'config.yaml').write_bytes(config)
        target = self.home / 'plugins/co-author-harness'
        target.mkdir(parents=True)
        (target / 'previous.txt').write_bytes(b'previous installation')
        result = installer.install(self.home)
        row = result['installed'][0]
        backup = Path(row['backup'])
        self.assertEqual((backup / 'config.yaml').read_bytes(), config)
        self.assertEqual((backup / 'plugin/previous.txt').read_bytes(), b'previous installation')
        manifest = json.loads((target / 'HERMES_INSTALLATION.json').read_text())
        self.assertFalse(manifest['release_qualified'])
        self.assertTrue((target / '__init__.py').is_file())
        self.assertEqual(yaml.safe_load((self.home / 'config.yaml').read_text())['model'],
                         yaml.safe_load(config)['model'])


if __name__ == '__main__':
    unittest.main()
