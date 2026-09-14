"""Export verified task evidence; verify relocated copies without live-path access.

The manifest digest must be retained separately. Hashes bind a captured evidence
set, not host authentication, live execution or research acceptance.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import piw_session as piw
from piw_session import assert_output as assert_writable
import piw_coordinator as coordinator
import piw_native_host as native
from piw_completion_guard import verify_completion

require = native.require


def bindings(value):
    if isinstance(value, dict):
        if {'path', 'sha256', 'bytes'} <= value.keys():
            yield value
        for item in value.values(): yield from bindings(item)
    elif isinstance(value, list):
        for item in value: yield from bindings(item)


def export_archive(session, destination):
    verified = verify_completion(session)
    require(verified['ok'], 'PIW-ARCHIVE-INCOMPLETE', 'Export requires a currently verifiable completed task: ' + verified.get('code', ''))
    contract, root, log, _ = coordinator.replay(session)
    destination = Path(destination).resolve()
    assert_writable(destination)
    require(not destination.exists(), 'PIW-ARCHIVE-EXISTS', 'Use a new archive directory')
    documents = [root / 'binding/piw_session.json', root / 'binding/run.json', root / 'logs/state.json', root / 'binding/delivery.json']
    documents += [Path(e['result']['path']) for e in log['events']]
    documents += [Path(e['request']['path']) for e in log['events'] if e['kind'] == 'role']
    selected = [piw.identity(p) for p in documents]
    for path in documents: selected += list(bindings(piw.read_json(path)))
    trace_paths = {p['path'] for e in log['events'] if e['kind'] == 'role' for p in e['host']['pins'].values()}
    payloads = {}
    for bound in selected:
        path = bound['path']
        with Path(path).open('rb') as stream:
            data = stream.read(bound['bytes'] if path in trace_paths else -1)
        require(len(data) == bound['bytes'] and piw.digest(data) == bound['sha256'], 'PIW-ARCHIVE-DRIFT', 'Evidence changed during export: ' + path)
        if len(data) >= len(payloads.get(path, b'')): payloads[path] = data
    entries = []
    for original, data in sorted(payloads.items()):
        digest = piw.digest(data)
        member = 'objects/' + digest
        piw.write_bytes(destination / member, data)
        entries.append({'original_path': original, 'member': member, 'sha256': digest, 'bytes': len(data), 'trace_prefix': original in trace_paths})
    doc = {'schema_version': 'piw-archive/v1', 'original_session': str(root / 'binding/piw_session.json'),
           'captured_at': piw.utc_now(), 'files': entries, 'task_complete': False,
           'research_acceptance': False, 'trust_boundary': contract['host']['trust_boundary']}
    manifest = destination / 'manifest.json'
    piw.write_json(manifest, doc)
    pin = piw.identity(manifest)
    result = verify_archive(manifest, pin['sha256'])
    return {**result, 'manifest': pin}


def verify_archive(manifest, expected_sha256):
    manifest = Path(manifest).resolve()
    data = manifest.read_bytes()
    require(isinstance(expected_sha256, str) and len(expected_sha256) == 64 and piw.digest(data) == expected_sha256,
            'PIW-ARCHIVE-MANIFEST-DRIFT', 'Supply the separately retained manifest SHA-256')
    doc = json.loads(data)
    require(doc['schema_version'] == 'piw-archive/v1', 'PIW-ARCHIVE-SCHEMA', 'Unsupported evidence archive')
    mapped = {}
    for entry in doc['files']:
        original = entry['original_path']
        member = (manifest.parent / entry['member']).resolve()
        require(member.is_relative_to(manifest.parent) and original not in mapped,
                'PIW-ARCHIVE-MAPPING', 'Archive members must stay inside the archive and original paths must be unique')
        payload = member.read_bytes()
        require(len(payload) == entry['bytes'] and piw.digest(payload) == entry['sha256'],
                'PIW-ARCHIVE-DRIFT', 'Archived evidence bytes changed: ' + original)
        mapped[original] = payload

    def read_bytes(path):
        require(str(path) in mapped, 'PIW-ARCHIVE-MISSING', 'Missing explicit source-to-archive mapping: ' + str(path))
        return mapped[str(path)]

    def read_rows(path, count):
        require(type(count) is int and count >= 0, 'PIW-ARCHIVE-TRACE', 'An archive needs a pinned trace length')
        payload = read_bytes(path)[:count]
        require(payload.endswith(b'\n'), 'PIW-ARCHIVE-TRACE', 'Trace export lacks a complete pinned prefix')
        return payload, [json.loads(x) for x in payload.splitlines() if x.strip()]

    session = json.loads(read_bytes(doc['original_session']))
    root = native.trace_path(session['staging_root'], True)
    require(str(root / 'binding/piw_session.json') == doc['original_session'] and session['scope'] == 'project_independent'
            and not session['terminal_authority'] and not session['terminal_capable'], 'PIW-ARCHIVE-SESSION', 'Original session binding or authority differs')
    contract_path = str(root / 'binding/run.json')
    contract_data = read_bytes(contract_path)
    contract = json.loads(contract_data)
    require(contract['run_id'] == session['piw_work_id'] and contract['session']['path'] == doc['original_session'],
            'PIW-ARCHIVE-SESSION', 'Original run and session differ')
    for binding in bindings(contract):
        coordinator._fresh(binding, read_bytes=read_bytes)
    log = json.loads(read_bytes(root / 'logs/state.json'))
    state = coordinator.replay_records(contract, {'sha256': piw.digest(contract_data)}, log, read_bytes, read_rows)
    require(state['stage'] == 'ready_to_deliver' and not state['unresolved_findings'], 'PIW-ARCHIVE-INCOMPLETE', 'Archived roles do not reach reviewed delivery')
    delivery = json.loads(read_bytes(root / 'binding/delivery.json'))
    require(delivery['run_id'] == contract['run_id'] and delivery['candidate'] == state['candidate'], 'PIW-ARCHIVE-DELIVERY', 'Archive delivery differs from reviewed candidate')
    coordinator._fresh(delivery['artifact'], read_bytes=read_bytes)
    require(all(delivery['artifact'][k] == state['candidate'][k] for k in ('sha256', 'bytes')), 'PIW-ARCHIVE-DELIVERY', 'Delivered bytes differ from reviewed bytes')
    return {'ok': True, 'status': 'archived_evidence_verified', 'code': 'PIW-ARCHIVE-VERIFIED',
            'run_id': contract['run_id'], 'artifact_sha256': delivery['artifact']['sha256'],
            'manifest_sha256': expected_sha256, 'mapped_files': len(mapped), 'host_adapter': contract['host']['adapter'],
            'task_complete': False, 'live_execution_verified': False, 'host_qualified': False,
            'lifecycle_terminal': False, 'research_acceptance': False, 'trust_boundary': doc['trust_boundary']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    export = sub.add_parser('export')
    export.add_argument('--piw-session', required=True, type=Path)
    export.add_argument('--destination', required=True, type=Path)
    verify = sub.add_parser('verify')
    verify.add_argument('--manifest', required=True, type=Path)
    verify.add_argument('--sha256', required=True)
    args = parser.parse_args()
    try:
        result = export_archive(args.piw_session, args.destination) if args.command == 'export' else verify_archive(args.manifest, args.sha256)
    except (piw.PIWError, OSError, ValueError, KeyError, TypeError) as exc:
        result = {'ok': False, 'code': getattr(exc, 'code', 'PIW-ARCHIVE-INVALID'), 'message': str(exc), 'task_complete': False, 'research_acceptance': False}
    print(json.dumps(result, indent=2))
    return 0 if result['ok'] else 2


if __name__ == '__main__': raise SystemExit(main())
