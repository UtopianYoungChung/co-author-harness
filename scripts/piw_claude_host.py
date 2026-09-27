#!/usr/bin/env python3
"""Claude Code / Claude Desktop native-host boundary over original session JSONL.

Claude Code writes one JSONL per session under the host's project log root and
one JSONL per native subagent under ``<session-id>/subagents/agent-<id>.jsonl``.
The parent records the ``Agent``/``Task`` ``tool_use`` block that dispatched the
child and the ``tool_result`` row that returned its final message; the child log
carries every turn of that subagent with its own ``agentId``.

A host that launches the child asynchronously (Claude Code 2.1.283 in a
non-interactive session does so even when the dispatch asks for foreground)
returns ``{"isAsync": true, "status": "async_launched"}`` as the tool_result and
later writes the finished child's message into the parent log as a
``<task-notification>`` user row. That row is host-written: its ``origin.kind``
is ``task-notification`` and its ``promptSource`` is ``system``, which a typed
prompt never carries. Exactly one completed notice for the same agent and
dispatch then stands in for the synchronous tool_result, and its ``<result>``
must equal the child's final message.

Python never dispatches cognitive roles here. The caller invokes the host's
native Agent tool with the exact role request and waits; this module verifies
parent-child linkage, request binding, a finished outcome, the exact returned
result and pinned log prefixes. Original log integrity is a trust boundary, not
cryptographic authentication. Synthetic logs are integration fixtures only.
"""
from __future__ import annotations
import json
from pathlib import Path
import piw_session as piw

ADAPTER = 'claude-code-jsonl'
DISPATCH_TOOLS = ('Agent', 'Task')
TRUST = 'Original Claude Code session JSONL integrity is trusted; hashes detect changes but are not host authentication.'


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ''.join(block.get('text', '') for block in content if isinstance(block, dict) and block.get('type') == 'text')
    return ''


def _session_ids(rows: list[dict]) -> set[str]:
    return {row['sessionId'] for row in rows if isinstance(row.get('sessionId'), str) and row['sessionId']}


def bind_host(host: dict, staging: Path) -> dict:
    from piw_native_host import require, _rows
    require(host.get('adapter') == ADAPTER and host.get('subagents_available') is True,
            'PIW-HOST-CAPABILITY-UNAVAILABLE', 'This drafting/revision route requires actual native Claude Code subagents')
    logs = Path(host['logs_root']).resolve()
    parent = Path(host['parent_log']).resolve()
    require(parent.is_relative_to(logs) and not logs.is_relative_to(staging),
            'PIW-HOST-TRACE-LOCATION', 'Use original Claude Code session logs outside task staging')
    require(parent.suffix == '.jsonl', 'PIW-HOST-IDENTITY', 'Parent log must be the session JSONL')
    _, rows = _rows(parent)
    ids = _session_ids(rows)
    require(len(ids) == 1, 'PIW-HOST-IDENTITY', 'Parent session log must carry exactly one session identity')
    parent_id = ids.pop()
    require(parent.stem == parent_id, 'PIW-HOST-IDENTITY', 'Parent log filename must be its session identity')
    declared = host.get('parent_execution_id')
    require(declared in (None, parent_id), 'PIW-HOST-IDENTITY', 'Declared parent session differs from the original log')
    return {**host, 'logs_root': str(logs), 'parent_log': str(parent), 'parent_execution_id': parent_id, 'trust_boundary': TRUST}


def _dispatches(parent_rows: list[dict], turn_id: str, token: str) -> list[dict]:
    hits = []
    for row in parent_rows:
        if row.get('type') != 'assistant' or not isinstance(row.get('message'), dict):
            continue
        for block in row['message'].get('content') or []:
            if isinstance(block, dict) and block.get('type') == 'tool_use' and block.get('id') == turn_id \
                    and block.get('name') in DISPATCH_TOOLS and token in json.dumps(block.get('input'), ensure_ascii=False):
                hits.append(row)
    return hits


def _completions(parent_rows: list[dict], turn_id: str, execution_id: str) -> list[dict]:
    hits = []
    for row in parent_rows:
        outcome = row.get('toolUseResult')
        if row.get('type') != 'user' or not isinstance(outcome, dict) or outcome.get('agentId') != execution_id:
            continue
        blocks = row.get('message', {}).get('content') if isinstance(row.get('message'), dict) else None
        if any(isinstance(b, dict) and b.get('type') == 'tool_result' and b.get('tool_use_id') == turn_id for b in blocks or []):
            hits.append(row)
    return hits


NOTICE_ORIGIN = 'task-notification'


def _notice_header(content: str) -> str:
    """The host-written fields of a notice: everything before the child's ``<result>``."""
    cut = content.find('<result>')
    return content if cut < 0 else content[:cut]


def _notice_field(header: str, tag: str) -> str | None:
    open_tag, close_tag = f'<{tag}>', f'</{tag}>'
    start = header.find(open_tag)
    if start < 0:
        return None
    end = header.find(close_tag, start)
    return header[start + len(open_tag):end].strip() if end >= 0 else None


def _notice_result(content: str) -> str | None:
    """The child's final message as the host relayed it (it may itself contain tags)."""
    start, end = content.find('<result>'), content.rfind('</result>')
    return content[start + len('<result>'):end] if 0 <= start < end else None


def _async_notices(parent_rows: list[dict], turn_id: str, execution_id: str) -> list[dict]:
    """Host-written completion notices for one asynchronously launched child."""
    hits = []
    for row in parent_rows:
        origin = row.get('origin')
        if row.get('type') != 'user' or not isinstance(origin, dict) or origin.get('kind') != NOTICE_ORIGIN \
                or row.get('promptSource') != 'system':
            continue
        message = row.get('message')
        content = message.get('content') if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.lstrip().startswith('<task-notification>'):
            continue
        header = _notice_header(content)
        if _notice_field(header, 'task-id') == execution_id and _notice_field(header, 'tool-use-id') == turn_id:
            hits.append(row)
    return hits


def verify_execution(host: dict, evidence: dict, request: dict, result: dict, pins: dict | None = None, read_rows=None) -> dict:
    from piw_native_host import require, _rows, _time, trace_path
    archived = read_rows is not None
    logs = trace_path(host['logs_root'], archived)
    parent = trace_path(host['parent_log'], archived)
    child = trace_path(evidence['child_log'], archived)
    execution_id = evidence['agent_execution_id']
    turn_id = evidence['turn_id']
    parent_id = host['parent_execution_id']
    require(isinstance(execution_id, str) and bool(execution_id) and isinstance(turn_id, str) and bool(turn_id),
            'PIW-HOST-IDENTITY', 'Evidence must name the child agent id and the dispatching tool_use id')
    require(child != parent and child.is_relative_to(logs / parent_id / 'subagents') and child.name == f'agent-{execution_id}.jsonl',
            'PIW-HOST-TRACE-LOCATION', 'Child must be the original subagent log of this session')
    reader = read_rows or _rows
    data, rows = {}, {}
    for name, path in (('parent', parent), ('child', child)):
        data[name], rows[name] = reader(path, pins[name]['bytes'] if pins else None)
        if pins:
            require(piw.digest(data[name]) == pins[name]['sha256'] and len(data[name]) == pins[name]['bytes'],
                    'PIW-HOST-TRACE-DRIFT', 'Pinned host log prefix changed: ' + name)
    require(_session_ids(rows['parent']) == {parent_id}, 'PIW-HOST-IDENTITY', 'Parent log identity differs from the bound session')
    child_rows = rows['child']
    require(bool(child_rows) and all(row.get('agentId') == execution_id for row in child_rows),
            'PIW-HOST-IDENTITY', 'Child log must contain only this subagent execution')
    require(_session_ids(child_rows) == {parent_id} and all(row.get('isSidechain', True) is True for row in child_rows),
            'PIW-HOST-PARENT', 'Host does not identify this child as a native subagent of the bound caller')
    if not archived:
        meta = child.with_suffix('.meta.json')
        if meta.is_file():
            require(json.loads(meta.read_text(encoding='utf-8')).get('toolUseId') == turn_id,
                    'PIW-HOST-DISPATCH-MISSING', 'Subagent metadata names a different dispatching tool_use')
    token = 'COAUTHOR_REQUEST_SHA256=' + piw.digest(piw.json_bytes(request))
    dispatch = _dispatches(rows['parent'], turn_id, token)
    require(len(dispatch) == 1, 'PIW-HOST-DISPATCH-MISSING', 'No unique native Agent dispatch bound to this role request')
    completion = _completions(rows['parent'], turn_id, execution_id)
    require(len(completion) == 1, 'PIW-HOST-NOT-FINISHED', 'No unique returned tool_result for this subagent')
    outcome = completion[0]['toolUseResult']
    if outcome.get('isAsync') is True and outcome.get('status') == 'async_launched':
        notices = _async_notices(rows['parent'], turn_id, execution_id)
        require(len(notices) == 1, 'PIW-HOST-NOT-FINISHED',
                'An asynchronously launched subagent needs exactly one host completion notice; '
                f'found {len(notices)} (a child resumed after completing cannot be certified)')
        finished = notices[0]
        status = _notice_field(_notice_header(finished['message']['content']), 'status')
        require(status == 'completed', 'PIW-HOST-NOT-FINISHED', 'Subagent did not finish successfully: ' + str(status))
        returned = _notice_result(finished['message']['content'])
        require(returned is not None, 'PIW-HOST-RESULT-MISSING', 'Host completion notice carries no result')
        require(_time(completion[0]['timestamp']) <= _time(finished['timestamp']),
                'PIW-HOST-STALE-EXECUTION', 'Host completion notice predates the asynchronous launch')
    else:
        require(outcome.get('status') == 'completed', 'PIW-HOST-NOT-FINISHED', 'Subagent did not finish successfully: ' + str(outcome.get('status')))
        finished, returned = completion[0], _text(outcome.get('content'))
    first = child_rows[0]
    require(first.get('type') == 'user' and first.get('parentUuid') is None and token in _text(first.get('message', {}).get('content')),
            'PIW-HOST-DISPATCH-MISSING', 'Child log does not begin with the bound role request')
    turns = [row for row in child_rows if row.get('type') in ('user', 'assistant')]
    require(bool(turns) and turns[-1].get('type') == 'assistant', 'PIW-HOST-NOT-FINISHED', 'Child log does not end with a final assistant message')
    last = turns[-1]
    require(isinstance(last.get('message'), dict) and last['message'].get('stop_reason') == 'end_turn',
            'PIW-HOST-NOT-FINISHED', 'Child final turn is not a completed end_turn')
    final = _text(last['message'].get('content')).strip()
    require(final == returned.strip(), 'PIW-HOST-RESULT-MISMATCH', 'Parent tool_result differs from the child final message')
    require(_time(request['created_at']) <= _time(dispatch[0]['timestamp']) <= _time(first['timestamp'])
            <= _time(last['timestamp']) <= _time(finished['timestamp']),
            'PIW-HOST-STALE-EXECUTION', 'Host execution predates this request or its events are out of order')
    if final.startswith('```json') and final.endswith('```'):
        final = final[7:-3].strip()
    try:
        actual = json.loads(final)
    except (ValueError, TypeError) as exc:
        raise piw.PIWError('PIW-HOST-RESULT-MISSING', 'Child final response must be the substantive result JSON') from exc
    require(actual == result, 'PIW-HOST-RESULT-MISMATCH', 'Supplied result differs from the actual finished host output')
    require(result.get('agent_execution_id') == execution_id, 'PIW-HOST-IDENTITY', 'Result must identify the actual child session')
    return {'agent_execution_id': execution_id, 'turn_id': turn_id, 'child_log': str(child),
            'started_at': first['timestamp'], 'finished_at': finished['timestamp'], 'pins': {
                name: {'path': str(path), 'bytes': len(data[name]), 'sha256': piw.digest(data[name])}
                for name, path in (('child', child), ('parent', parent))},
            'trust_boundary': host['trust_boundary']}


def start_timestamp(host: dict, rows: list[dict], evidence: dict) -> str:
    from piw_native_host import require
    require(bool(rows) and rows[0].get('agentId') == evidence['agent_execution_id'], 'PIW-METRICS-START', 'Cannot identify a unique role start')
    return rows[0]['timestamp']
