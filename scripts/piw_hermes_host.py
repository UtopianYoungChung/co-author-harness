"""Verify original Hermes plugin lifecycle logs, including a successful turn.

Integrity of the original host logs is a trust boundary, as for codex-jsonl.
This adapter does not dispatch agents and never upgrades a fixture to live proof.
"""
from pathlib import Path
import json
import piw_session as piw


def bind_host(host, staging):
    from piw_native_host import require, _rows
    require(host.get('subagents_available') is True, 'PIW-HOST-CAPABILITY-UNAVAILABLE', 'Native Hermes children are required')
    logs = Path(host['logs_root']).resolve()
    parent = Path(host['parent_log']).resolve()
    require(parent.is_relative_to(logs) and not logs.is_relative_to(staging),
            'PIW-HOST-TRACE-LOCATION', 'Use original Hermes hook logs outside task staging')
    _, rows = _rows(parent)
    require(bool(rows) and rows[0].get('adapter') == 'hermes-hooks-jsonl'
            and rows[0].get('type') == 'session_meta' and bool(rows[0].get('session_id')),
            'PIW-HOST-IDENTITY', 'Original Hermes session header is required')
    require(host.get('parent_execution_id') == rows[0]['session_id'], 'PIW-HOST-IDENTITY', 'Parent session differs')
    return {**host, 'logs_root': str(logs), 'parent_log': str(parent),
            'trust_boundary': 'Original Hermes lifecycle-hook JSONL integrity is trusted; hashes detect changes, not host authentication.'}


def verify_execution(host, evidence, request, result, pins=None, read_rows=None):
    from piw_native_host import require, _rows, _time, trace_path
    parent = trace_path(host['parent_log'], read_rows is not None)
    child = trace_path(evidence['child_log'], read_rows is not None)
    require(child != parent and child.is_relative_to(trace_path(host['logs_root'], read_rows is not None)),
            'PIW-HOST-TRACE-LOCATION', 'Use the distinct original child log')
    data = {}
    rows = {}
    for name, path in [('parent', parent), ('child', child)]:
        data[name], rows[name] = (read_rows or _rows)(path, pins[name]['bytes'] if pins else None)
        if pins:
            require(piw.digest(data[name]) == pins[name]['sha256'] and len(data[name]) == pins[name]['bytes'],
                    'PIW-HOST-TRACE-DRIFT', 'Pinned Hermes trace prefix changed')
        expected = host['parent_execution_id'] if name == 'parent' else evidence['agent_execution_id']
        require(bool(rows[name]) and rows[name][0] == {'adapter': 'hermes-hooks-jsonl', 'type': 'session_meta', 'session_id': expected},
                'PIW-HOST-IDENTITY', 'Hermes log header differs from bound session')
        require(sum(r.get('type') == 'session_meta' for r in rows[name]) == 1,
                'PIW-HOST-IDENTITY', 'Duplicate Hermes session header')
    token = 'COAUTHOR_REQUEST_SHA256=' + piw.digest(piw.json_bytes(request))
    starts = [r for r in rows['child'] if r.get('type') == 'child_started'
              and r.get('parent_session_id') == host['parent_execution_id'] and token in r.get('child_goal', '')]
    dispatch = [r for r in rows['parent'] if r.get('type') == 'child_started'
                and r.get('child_session_id') == evidence['agent_execution_id'] and token in r.get('child_goal', '')]
    require(len(starts) == 1 and len(dispatch) == 1, 'PIW-HOST-DISPATCH-MISSING', 'No unique native dispatch bound to this role request')
    turns = [r for r in rows['child'] if r.get('type') == 'turn_finished' and r.get('turn_id') == evidence['turn_id']]
    stops = [r for r in rows['child'] if r.get('type') == 'child_stopped']
    require(len(turns) == 1 and len(stops) == 1 and turns[0].get('completed') is True
            and turns[0].get('failed') is False and turns[0].get('interrupted') is False
            and stops[0].get('status') == 'completed', 'PIW-HOST-NOT-FINISHED', 'Child lacks a successful finished native turn')
    require(stops[0].get('parent_session_id') == host['parent_execution_id'], 'PIW-HOST-PARENT', 'Completion parent differs')
    require(_time(request['created_at']) <= _time(dispatch[0]['timestamp']) <= _time(starts[0]['timestamp'])
            <= _time(turns[0]['timestamp']) <= _time(stops[0]['timestamp']),
            'PIW-HOST-STALE-EXECUTION', 'Hermes native execution is stale or out of order')
    final = stops[0].get('summary', '').strip()
    if final.startswith('```json') and final.endswith('```'):
        final = final[7:-3].strip()
    try:
        actual = json.loads(final)
    except (ValueError, TypeError) as exc:
        raise piw.PIWError('PIW-HOST-RESULT-MISSING', 'Child must return substantive result JSON') from exc
    require(actual == result, 'PIW-HOST-RESULT-MISMATCH', 'Result differs from original host output')
    require(result.get('agent_execution_id') == evidence['agent_execution_id'], 'PIW-HOST-IDENTITY', 'Result child session differs')
    return {**evidence, 'finished_at': stops[0]['timestamp'], 'pins': {
        name: {'path': str(path), 'bytes': len(data[name]), 'sha256': piw.digest(data[name])}
        for name, path in [('parent', parent), ('child', child)]}, 'trust_boundary': host['trust_boundary']}
