"""Native Hermes skill registration and original child-execution observations.

No model dispatch or model configuration changes occur in this plugin. Hooks
record host events; fixture calls to these hooks are not live qualification.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

if __package__:
    from . import destination_capability as destination
else:
    import destination_capability as destination

ROOT = Path(__file__).resolve().parent.parent
_LOCK = threading.RLock()


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def trace_path(root, session_id):
    return Path(root) / (hashlib.sha256(session_id.encode('utf-8')).hexdigest() + '.jsonl')


def record(root, session_id, kind, **payload):
    if not isinstance(session_id, str) or not session_id:
        return
    path = trace_path(root, session_id)
    if destination.classify(path) != 'ungoverned':
        destination.assert_writable(path, purpose='Hermes native execution trace')
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            header = {'type': 'session_meta', 'session_id': session_id, 'adapter': 'hermes-hooks-jsonl'}
            with path.open('xb') as f:
                f.write((_json(header) + '\n').encode('utf-8'))
                f.flush()
                os.fsync(f.fileno())
        row = {'type': kind, 'timestamp': datetime.now(timezone.utc).isoformat(), **payload}
        with path.open('ab') as f:
            f.write((_json(row) + '\n').encode('utf-8'))
            f.flush()
            os.fsync(f.fileno())


def register(ctx):
    from hermes_constants import get_hermes_home
    from agent.skill_utils import yaml_load

    policy = json.loads((ROOT / 'references/policies/command_surface.v1.json').read_text(encoding='utf-8'))
    # Unavailable bodies are intentionally not exposed. Legacy and maintainer
    # skills remain explicitly loadable, preserving the canonical public menu.
    names = policy['public'] + policy['hidden']['legacy'] + policy['hidden']['maintainer']
    for name in names:
        path = ROOT / 'skills' / name / 'SKILL.md'
        content = path.read_text(encoding='utf-8-sig')
        fm = yaml_load(content.split('---', 2)[1])
        if fm['name'] != name:
            raise ValueError('Skill name mismatch: ' + name)
        ctx.register_skill(name, path, fm['description'], fm)

    traces = get_hermes_home() / 'plugin-data/co-author-harness/host-traces'

    def context(info):
        sid = info.get('session_id', '')
        record(traces, sid, 'session_context')
        # Hermes does not expose the session's effective tool surface to this
        # callback. The caller must attest it; plugin loading alone is no proof.
        host = {'adapter': 'hermes-hooks-jsonl', 'subagents_available': None,
                'logs_root': str(traces), 'parent_log': str(trace_path(traces, sid)),
                'parent_execution_id': sid}
        return (
            f'Co-author harness package root: {ROOT}\n'
            'For an academic writing request or a named harness command, load '
            'skill_view(name="co-author-harness:<name>"). Read package AGENTS.md '
            'and references/AGENTS.md. Resolve package-relative references, agents '
            'and scripts from the package root above using file/terminal tools. '
            'skill_view file paths are skill-local. Ordinary unrelated requests do not invoke the harness.\n'
            'Public skills: ' + ', '.join(policy['public']) + '\n'
            'Preserve all existing authority, protected-path, source-verification and model-pin rules. '
            'Unavailable capabilities remain unavailable; dependency requirements still apply. '
            'For drafting/revision read references/HERMES_DESKTOP.md and '
            'references/PROJECT_INDEPENDENT_WORKFLOW.md. Native delegate_task children '
            'must inherit the selected model/provider; never supply overrides. '
            'Complete subagents_available from whether delegate_task is actually '
            'callable in this session. Leave it unknown until checked; '
            'plugin loading grants neither tool availability nor seat authority. '
            'If native children or original trace evidence is unavailable, report '
            'PIW-HOST-CAPABILITY-UNAVAILABLE. Do not synthesize role evidence.\n'
            'This session host binding: ' + _json(host)
        )

    def started(parent_session_id='', child_session_id='', child_goal='', **kwargs):
        record(traces, parent_session_id, 'child_started', child_session_id=child_session_id,
               child_goal=child_goal)
        record(traces, child_session_id, 'child_started', parent_session_id=parent_session_id,
               child_goal=child_goal)

    def ended(session_id='', turn_id='', completed=False, failed=False, interrupted=False, **kwargs):
        record(traces, session_id, 'turn_finished', turn_id=turn_id, completed=completed,
               failed=failed, interrupted=interrupted)

    def stopped(parent_session_id='', child_session_id='', child_summary='', child_status='', **kwargs):
        record(traces, child_session_id, 'child_stopped', parent_session_id=parent_session_id,
               summary=child_summary, status=child_status)

    ctx.register_system_prompt_section('co-author-harness', context)
    ctx.register_hook('subagent_start', started)
    ctx.register_hook('on_session_end', ended)
    ctx.register_hook('subagent_stop', stopped)
