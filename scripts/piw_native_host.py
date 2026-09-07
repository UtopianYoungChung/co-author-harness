#!/usr/bin/env python3
"""Small native-host boundary for Codex original JSONL logs.

Python never dispatches cognitive roles. The caller invokes native subagents and
waits, then supplies original host logs. Their integrity is a trust boundary,
not cryptographic authentication. Prefix pins tolerate subsequent log appends.
Synthetic logs are useful integration fixtures, never live-host qualification.
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
import piw_session as piw


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise piw.PIWError(code, message)


def _rows(path: Path, byte_count: int | None = None) -> tuple[bytes, list[dict]]:
    data = path.read_bytes()
    if byte_count is not None:
        data = data[:byte_count]
    # Only complete host log lines; a live parent can be appending concurrently.
    data = data[:data.rfind(b'\n') + 1]
    return data, [json.loads(x) for x in data.splitlines() if x.strip()]


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def _parent_id(meta: dict) -> str | None:
    source = meta.get('source')
    return source.get('subagent', {}).get('thread_spawn', {}).get('parent_thread_id') if isinstance(source, dict) else None


def _session_metadata(rows: list[dict], expected_id: str | None = None) -> list[dict]:
    """The first host row is current identity; later metadata is fork history.

    Codex full-history forks prepend current session_meta, then retain ancestor
    session_meta and events. Admit only unique metadata IDs in the explicitly
    declared fork/parent ancestry, never another current header or foreign ID.
    Turn matching still selects the actual child work from inherited events.
    """
    require(bool(rows) and rows[0].get('type') == 'session_meta', 'PIW-HOST-IDENTITY', 'Original host log must begin with current session metadata')
    metas = [row['payload'] for row in rows if row.get('type') == 'session_meta']
    current = metas[0]
    require(isinstance(current.get('id'), str) and bool(current['id']), 'PIW-HOST-IDENTITY', 'Current host session ID is missing')
    if expected_id is not None:
        require(current['id'] == expected_id, 'PIW-HOST-IDENTITY', 'First host session ID differs from the bound current execution')
    seen = {current['id']}
    ancestors = {value for value in (current.get('forked_from_id'), _parent_id(current)) if value}
    require(current['id'] not in ancestors, 'PIW-HOST-IDENTITY', 'Current session cannot declare itself an ancestor')
    for inherited in metas[1:]:
        inherited_id = inherited.get('id')
        require(isinstance(inherited_id, str) and inherited_id in ancestors and inherited_id not in seen,
                'PIW-HOST-IDENTITY', 'Additional metadata is duplicate or outside declared fork/parent ancestry')
        seen.add(inherited_id)
        declared = {value for value in (inherited.get('forked_from_id'), _parent_id(inherited)) if value}
        require(not (declared & seen), 'PIW-HOST-IDENTITY', 'Inherited metadata contains a cyclic ancestry')
        ancestors.update(declared)
    return metas


def bind_host(host: dict, staging: Path) -> dict:
    require(host.get('adapter') == 'codex-jsonl' and host.get('subagents_available') is True,
            'PIW-HOST-CAPABILITY-UNAVAILABLE', 'This drafting/revision route requires actual native subagents and the codex-jsonl trace adapter')
    logs = Path(host['logs_root']).resolve()
    parent = Path(host['parent_log']).resolve()
    require(parent.is_relative_to(logs) and not logs.is_relative_to(staging),
            'PIW-HOST-TRACE-LOCATION', 'Use original host logs outside task staging')
    _, rows = _rows(parent)
    meta = _session_metadata(rows)
    return {**host, 'logs_root': str(logs), 'parent_log': str(parent), 'parent_execution_id': meta[0]['id'],
            'trust_boundary': 'Original host JSONL integrity is trusted; hashes detect changes but are not host authentication.'}


def verify_execution(host: dict, evidence: dict, request: dict, result: dict, pins: dict | None = None) -> dict:
    child = Path(evidence['child_log']).resolve()
    parent = Path(host['parent_log']).resolve()
    require(child.is_relative_to(Path(host['logs_root']).resolve()) and child != parent,
            'PIW-HOST-TRACE-LOCATION', 'Child must have its own original host log')
    child_data, rows = _rows(child, pins.get('child', {}).get('bytes') if pins else None)
    parent_data, parent_rows = _rows(parent, pins.get('parent', {}).get('bytes') if pins else None)
    if pins:
        for name, data in [('child', child_data), ('parent', parent_data)]:
            require(piw.digest(data) == pins[name]['sha256'] and len(data) == pins[name]['bytes'],
                    'PIW-HOST-TRACE-DRIFT', 'Pinned host log prefix changed: ' + name)
    execution_id = evidence['agent_execution_id']
    turn_id = evidence['turn_id']
    metas = _session_metadata(rows, execution_id)
    parent_metas = _session_metadata(parent_rows, host['parent_execution_id'])
    known_parent_history = {item['id']: item for item in parent_metas}
    for inherited in metas[1:]:
        if inherited['id'] in known_parent_history:
            known = known_parent_history[inherited['id']]
            require(all(inherited.get(key) == known.get(key) for key in ('source', 'forked_from_id')),
                    'PIW-HOST-IDENTITY', 'Inherited metadata conflicts with the original parent identity/ancestry')
    meta = metas[0]
    parent_id = _parent_id(meta)
    require(parent_id == host['parent_execution_id'], 'PIW-HOST-PARENT', 'Host does not identify this child as a native subagent of the bound caller')
    starts = [r for r in parent_rows if r.get('type') == 'event_msg'
              and r['payload'].get('type') == 'item_completed'
              and r['payload'].get('item', {}).get('type') == 'SubAgentActivity'
              and r['payload']['item'].get('kind') == 'started'
              and r['payload']['item'].get('agent_thread_id') == execution_id]
    require(bool(starts), 'PIW-HOST-DISPATCH-MISSING', 'No native SubAgentActivity start in parent host log')
    started = [r for r in rows if r.get('type') == 'event_msg' and r['payload'].get('type') == 'task_started' and r['payload'].get('turn_id') == turn_id]
    completed = [r for r in rows if r.get('type') == 'event_msg' and r['payload'].get('type') == 'task_complete' and r['payload'].get('turn_id') == turn_id]
    require(len(started) == 1 and len(completed) == 1, 'PIW-HOST-NOT-FINISHED', 'Required host turn lacks a unique finished outcome')
    require(_time(started[0]['timestamp']) >= _time(request['created_at']) and _time(completed[0]['timestamp']) >= _time(started[0]['timestamp']),
            'PIW-HOST-STALE-EXECUTION', 'Host execution predates this request or completion precedes execution')
    final = completed[0]['payload'].get('last_agent_message', '').strip()
    if final.startswith('```json') and final.endswith('```'):
        final = final[7:-3].strip()
    try:
        actual_result = json.loads(final)
    except (ValueError, TypeError) as exc:
        raise piw.PIWError('PIW-HOST-RESULT-MISSING', 'Child final response must be the substantive result JSON') from exc
    require(actual_result == result, 'PIW-HOST-RESULT-MISMATCH', 'Supplied result differs from the actual finished host output')
    require(result.get('agent_execution_id') == execution_id, 'PIW-HOST-IDENTITY', 'Result must identify the actual child session')
    return {'agent_execution_id': execution_id, 'turn_id': turn_id, 'child_log': str(child),
            'finished_at': completed[0]['timestamp'], 'pins': {
                'child': {'path': str(child), 'bytes': len(child_data), 'sha256': piw.digest(child_data)},
                'parent': {'path': str(parent), 'bytes': len(parent_data), 'sha256': piw.digest(parent_data)}},
            'child_complete_ordinal': completed[0].get('ordinal'),
            'parent_dispatch_ordinal': starts[0].get('ordinal'), 'trust_boundary': host['trust_boundary']}
