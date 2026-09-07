#!/usr/bin/env python3
"""Portable task-local bindings. Binding is never a performed prose review."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import destination_capability as destination
import invocation_scope as invocation

ROOT = Path(__file__).resolve().parents[1]
STAGING_SUBDIRS = ('binding', 'plan', 'draft', 'evaluate', 'reflect', 'overlays', 'logs')
PASS_RULES = {
    'grammar-mechanics-pass': ['blue_book_grammar_guidelines.md'],
    'sentence-level-pass': ['bacon_2009_well_crafted_sentence_guidelines.md', 'voice_preservation_guidelines.md', 'EMDASH_BUNDLE_DISCIPLINE.md'],
    'chung-academic-voice-pass': ['chung_academic_voice_guidelines.md'],
}

class PIWError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def identity(path: Path) -> dict[str, Any]:
    path = Path(path).resolve()
    data = path.read_bytes()
    return {'path': str(path), 'sha256': digest(data), 'bytes': len(data)}

def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode('utf-8')

def assert_output(path: Path) -> str:
    """Ordinary explicit/task-local outputs may be ungoverned; discovered protection wins."""
    path = Path(path).resolve()
    parts = [x.casefold() for x in path.parts]
    if '60_workbench' in parts and 'manuscript' in parts:
        raise PIWError('DEST-PROTECTED', 'Standalone state cannot authorize a Workbench manuscript write')
    kind = destination.classify(path)
    if kind == 'ungoverned':
        return kind
    try:
        return destination.assert_writable(path, purpose='standalone task output')
    except destination.DestinationRefused as exc:
        raise PIWError(exc.code, str(exc)) from exc

def write_bytes(path: Path, data: bytes) -> None:
    """Same-directory temp, flush/fsync, replace, byte-for-byte host read-back."""
    path = Path(path).resolve()
    assert_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
        if path.read_bytes() != data:
            raise PIWError('PIW-WRITE-INTEGRITY', str(path))
    finally:
        if os.path.exists(name):
            os.unlink(name)

def write_json(path: Path, obj: Any) -> None:
    write_bytes(path, json_bytes(obj))

def read_json(path: Path | str) -> Any:
    return json.loads(Path(path).read_text(encoding='utf-8'))

def mint_work_id(when: datetime | None = None) -> str:
    return 'piw-' + (when or datetime.now(timezone.utc)).strftime('%Y%m%d') + '-' + secrets.token_hex(8)

def default_staging_root(outputs_root: Path, work_id: str) -> Path:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', work_id):
        raise PIWError('PIW-WORK-ID', 'work-id must be one safe path component')
    return Path(outputs_root) / 'co-author-harness' / 'staging' / work_id

def create_staging_layout(staging_root: Path) -> None:
    assert_output(staging_root)
    for name in STAGING_SUBDIRS:
        (staging_root / name).mkdir(parents=True, exist_ok=True)

def pin_mss(mss_path: Path) -> dict[str, Any]:
    pin = identity(mss_path)
    data = Path(pin['path']).read_bytes()
    encoding = 'utf-8-sig' if data.startswith(b'\xef\xbb\xbf') else 'utf-8'
    data.decode(encoding, errors='strict')
    return {**pin, 'encoding': encoding, 'pinned_at': utc_now(), 'history_reconstruct': 'forbidden'}

def verify_mss_pin(pin: dict[str, Any]) -> dict[str, Any]:
    try:
        actual = identity(Path(pin['path']))
        ok = all(actual[k] == pin[k] for k in ('sha256', 'bytes'))
    except (OSError, KeyError, TypeError):
        ok = False
    return {'ok': ok, 'code': 'OK' if ok else 'MSS_PIN_DRIFT', 'message': 'Input pin matches current bytes' if ok else 'Pinned manuscript is absent or its bytes changed'}

def refuse_history_reconstruct(action: str | None = None) -> dict[str, Any]:
    return {'ok': False, 'code': invocation.FRC_PIW_HISTORY_RECONSTRUCT, 'history_reconstruct': 'forbidden', 'message': 'Do not invent milestones, accepts, F9 or bootstrap-as-history: ' + str(action or '')}

def build_session_object(*, work_id: str, ingress_kind: str, staging_root: Path, mss_pin: dict | None = None, harness_head: str | None = None, classify_invoke: str | None = None) -> dict:
    if ingress_kind not in ('standalone', 'mss_revision') or (ingress_kind == 'mss_revision' and not mss_pin):
        raise PIWError('PIW-INGRESS', 'Revision ingress requires actual input bytes and pin')
    obj = {'schema_version': '2.0.0', 'plane': invocation.PROJECT_INDEPENDENT, 'scope': invocation.PROJECT_INDEPENDENT, 'piw_work_id': work_id, 'work_id': work_id, 'ingress': ingress_kind, 'ingress_kind': ingress_kind, 'created_at': utc_now(), 'staging_root': str(staging_root.resolve()), 'native_project_required': False, 'terminal_authority': False, 'terminal_capable': False, 'history_reconstruct': 'forbidden', 'clean_mint': 'forbidden', 'research_acceptance': False}
    if mss_pin:
        obj['mss_pin'] = mss_pin
    if classify_invoke:
        obj['classify_invoke'] = classify_invoke
    return obj

def open_session(*, ingress_kind: str = 'standalone', mss_path: Path | None = None, outputs_root: Path | None = None, work_id: str | None = None, classify_invoke: str | None = None, allow_history_reconstruct: bool = False) -> dict:
    if allow_history_reconstruct:
        raise PIWError(invocation.FRC_PIW_HISTORY_RECONSTRUCT, refuse_history_reconstruct()['message'])
    outputs = Path(outputs_root or os.environ.get('COAUTHOR_OUTPUTS_ROOT') or Path(tempfile.gettempdir()) / 'coauthor-tasks')
    wid = work_id or mint_work_id()
    staging = default_staging_root(outputs, wid).resolve()
    if staging.exists():
        raise PIWError('PIW-RUN-EXISTS', 'A run identity cannot be reused')
    pin = pin_mss(mss_path) if ingress_kind == 'mss_revision' and mss_path else None
    session = build_session_object(work_id=wid, ingress_kind=ingress_kind, staging_root=staging, mss_pin=pin, classify_invoke=classify_invoke)
    create_staging_layout(staging)
    if pin:
        write_json(staging / 'binding/mss_pin.json', pin)
        write_bytes(staging / 'binding/original.bin', Path(pin['path']).read_bytes())
    session_path = staging / 'binding/piw_session.json'
    write_json(session_path, session)
    return {'ok': True, 'piw_work_id': wid, 'staging_root': str(staging), 'session_path': str(session_path), 'mss_pin_path': str(staging / 'binding/mss_pin.json') if pin else None, 'session': session}

def load_session(piw_session: Path | str) -> dict:
    path = Path(piw_session)
    if path.is_dir():
        path = path / 'binding/piw_session.json'
    return read_json(path)

def resolve_staging_root(piw_session: Path | str) -> Path:
    return Path(load_session(piw_session)['staging_root']).resolve()

def validate_session(piw_session: Path | str) -> dict:
    session = load_session(piw_session)
    staging = resolve_staging_root(piw_session)
    source = Path(piw_session).resolve()
    expected = staging / 'binding/piw_session.json'
    if (source if source.is_file() else source / 'binding/piw_session.json') != expected:
        raise PIWError('PIW-SESSION-TARGET', 'Session location and bound staging root differ')
    if session.get('scope') != invocation.PROJECT_INDEPENDENT or session.get('terminal_authority') or session.get('terminal_capable'):
        raise PIWError('PIW-SESSION-AUTHORITY', 'Invalid standalone scope/authority')
    assert_output(staging)
    ingress = session.get('ingress')
    if ingress not in ('standalone', 'mss_revision') or session.get('ingress_kind') != ingress:
        raise PIWError('PIW-INGRESS', 'Ingress aliases must agree and identify the actual input kind')
    if ingress == 'standalone' and (session.get('mss_pin') or (staging / 'binding/mss_pin.json').exists() or (staging / 'binding/original.bin').exists()):
        raise PIWError('PIW-INGRESS', 'Revision evidence cannot be silently downgraded to standalone draft')
    if ingress == 'mss_revision':
        path = staging / 'binding/mss_pin.json'
        if not path.is_file() or not session.get('mss_pin'):
            raise PIWError('PIW-MISSING-INPUT-PIN', 'Revision pin is required')
        pin = read_json(path)
        if pin != session['mss_pin']:
            raise PIWError('PIW-INPUT-PIN-MISMATCH', 'Session and revision pin differ')
        checked = verify_mss_pin(pin)
        if not checked['ok']:
            raise PIWError(checked['code'], checked['message'])
        original = identity(staging / 'binding/original.bin')
        if any(original[k] != pin[k] for k in ('sha256', 'bytes')):
            raise PIWError('PIW-INPUT-SNAPSHOT-DRIFT', 'Original byte snapshot changed')
    return {'ok': True, 'code': 'OK', 'session': session, 'staging_root': str(staging)}

def rule_bindings(passes: list[str], exclusions: list[str]) -> list[dict]:
    names = ['GROUNDING_PROTOCOL.md']
    for name in passes:
        if name in exclusions:
            continue
        if name not in PASS_RULES:
            raise PIWError('PIW-RULE-UNKNOWN', 'Unsupported rule profile: ' + name)
        names.extend(PASS_RULES[name])
    return [identity(ROOT / 'references' / name) for name in dict.fromkeys(names)]

def validate_authoritative_binding(path: Path) -> dict:
    """Reuse the read-only native contract validator; never invent lifecycle state."""
    path = Path(path).resolve()
    if path.name != 'assignment_contract.json' or path.parent.name != 'reviews' or not path.is_file():
        raise PIWError('PIW-AUTHORITATIVE-BINDING-INVALID', 'Supply the actual project reviews/assignment_contract.json; supplied authority is never silently dropped')
    from assignment_process_gate import validate_resolved_contract
    findings = validate_resolved_contract(path.parent.parent)
    if findings:
        raise PIWError('PIW-AUTHORITATIVE-BINDING-INVALID', json.dumps(findings))
    contract = read_json(path)
    source = Path(contract['assignment_source']['path'])
    if not source.is_absolute():
        source = path.parent.parent / source
    return {'contract': identity(path), 'assignment_source': identity(source), 'context_only': True, 'native_validation': 'assignment_process_gate.validate_resolved_contract'}


def bind_pass(*, pass_name: str, text: str | None = None, input_path: Path | None = None, venue_path: Path | None = None, authoritative_binding: Path | None = None, scope: str = 'whole input', exclusions: list[str] | None = None) -> dict:
    project_context = validate_authoritative_binding(authoritative_binding) if authoritative_binding is not None else None
    exclusions = sorted(set('chung-academic-voice-pass' if 'chung' in str(x).lower() else x for x in (exclusions or [])))
    rules = rule_bindings([pass_name], exclusions)
    if input_path:
        data = input_path.read_bytes()
        input_binding = pin_mss(input_path)
    elif text is not None:
        data = text.encode('utf-8')
        input_binding = {'kind': 'pasted_text', 'sha256': digest(data), 'bytes': len(data), 'encoding': 'utf-8'}
    else:
        raise PIWError('PIW-INPUT-REQUIRED', 'Supply text or a file')
    venue = identity(venue_path) if venue_path else None
    return {'ok': True, 'status': 'bound_not_reviewed', 'pass': pass_name, 'input': input_binding, 'text': data.decode('utf-8-sig'), 'requested_scope': scope, 'rules': rules, 'package_version': read_json(ROOT / 'version.json'), 'project_context': project_context, 'venue': venue, 'venue_text': venue_path.read_text(encoding='utf-8') if venue_path else None, 'precedence': ['user', 'venue/advisor', 'project', 'packaged rules'], 'exclusions': exclusions, 'performed_checks': [], 'task_complete': False, 'instruction': 'Host reads these rules and input, performs the selected checks, and returns substantive findings or an explained clean result with locators. This packet is not judgment.'}

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    op = sub.add_parser('open')
    op.add_argument('--ingress', choices=('standalone', 'mss_revision'), default='standalone')
    op.add_argument('--mss-path', type=Path)
    op.add_argument('--outputs-root', type=Path)
    op.add_argument('--work-id')
    op.add_argument('--classify-invoke')
    op.add_argument('--allow-history-reconstruct', action='store_true')
    for command in ('verify-pin', 'show', 'validate'):
        sub.add_parser(command).add_argument('--piw-session', required=True)
    sub.add_parser('refuse-history-reconstruct').add_argument('--action', default='history_reconstruct')
    bp = sub.add_parser('bind-pass')
    bp.add_argument('--pass-name', required=True, choices=tuple(PASS_RULES))
    inp = bp.add_mutually_exclusive_group(required=True)
    inp.add_argument('--text')
    inp.add_argument('--input-path', type=Path)
    bp.add_argument('--venue-path', type=Path)
    bp.add_argument('--authoritative-binding', type=Path)
    bp.add_argument('--scope', default='whole input')
    bp.add_argument('--exclude', action='append', default=[])
    args = ap.parse_args(argv)
    try:
        if args.cmd == 'open':
            result = open_session(ingress_kind=args.ingress, mss_path=args.mss_path, outputs_root=args.outputs_root, work_id=args.work_id, classify_invoke=args.classify_invoke, allow_history_reconstruct=args.allow_history_reconstruct)
        elif args.cmd == 'bind-pass':
            result = bind_pass(pass_name=args.pass_name, text=args.text, input_path=args.input_path, venue_path=args.venue_path, authoritative_binding=args.authoritative_binding, scope=args.scope, exclusions=args.exclude)
        elif args.cmd == 'show':
            result = load_session(args.piw_session)
        elif args.cmd == 'refuse-history-reconstruct':
            result = refuse_history_reconstruct(args.action)
        else:
            result = validate_session(args.piw_session)
    except (PIWError, OSError, ValueError) as exc:
        result = {'ok': False, 'code': getattr(exc, 'code', 'PIW-INPUT-ERROR'), 'message': str(exc)}
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result.get('ok', True) else 4

if __name__ == '__main__':
    raise SystemExit(main())
