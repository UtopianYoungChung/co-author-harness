#!/usr/bin/env python3
"""Install an exact current-byte development snapshot into Hermes profiles.

This is local installation, not release qualification. Native host metadata is
derived from version.json; original source files and a hash inventory travel
together. Existing installs/configs are backed up before replacement.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import yaml
import destination_capability as destination

ROOT = Path(__file__).resolve().parent.parent
NAME = 'co-author-harness'
ADDED_FILES = ('scripts/hermes_plugin.py', 'scripts/piw_hermes_host.py',
               'scripts/install_hermes.py', 'scripts/hermes_host_smoketest.py',
               'references/HERMES_DESKTOP.md')


def atomic(path, data):
    if destination.classify(path) != 'ungoverned':
        destination.assert_writable(path, purpose='Hermes local plugin installation')
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    with tmp.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    if path.read_bytes() != data:
        raise RuntimeError('Install readback mismatch: ' + str(path))


def snapshot():
    paths = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z']).decode('utf-8', errors='strict').split('\0')
    paths = sorted(set(p for p in paths if p) | set(ADDED_FILES))
    deleted = set(subprocess.check_output(
        ['git', '-C', str(ROOT), 'diff', '--name-only', '--diff-filter=D']
    ).decode('utf-8', errors='strict').splitlines())
    files = {}
    for rel in paths:
        p = ROOT / rel
        if not p.exists() and rel in deleted:
            continue
        if p.is_symlink() or not p.resolve().is_relative_to(ROOT) or not p.is_file():
            raise RuntimeError('Invalid source member: ' + rel)
        files[rel] = p.read_bytes()
    version = json.loads(files['version.json'])
    manifest = {'name': version['name'], 'version': version['version'],
                'description': json.loads(files['plugin.json'])['description'],
                'provides_hooks': ['subagent_start', 'subagent_stop', 'on_session_end']}
    files['plugin.yaml'] = yaml.safe_dump(manifest, sort_keys=False).encode('utf-8')
    files['__init__.py'] = b'"""Hermes native entry point; identity is derived at installation."""\nfrom .scripts.hermes_plugin import register\n'
    inventory = {p: {'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)} for p,b in files.items()}
    provenance = {'kind': 'local_development_snapshot', 'source_root': str(ROOT),
                  'source_head': subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True,encoding='utf-8',errors='strict').strip(),
                  'source_status': subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True,encoding='utf-8',errors='strict'),
                  'version': version['version'], 'files': inventory,
                  'release_qualified': False}
    files['HERMES_INSTALLATION.json'] = (json.dumps(provenance, indent=2) + '\n').encode('utf-8')
    for rel in paths:
        if rel not in files:
            continue
        if (ROOT / rel).read_bytes() != files[rel]:
            raise RuntimeError('Source changed during snapshot: ' + rel)
    return files, provenance


def enable_config(original):
    text = original.decode('utf-8', errors='strict')
    full = yaml.safe_load(text) or {}
    plugins = dict(full.get('plugins') or {})
    plugins['enabled'] = list(dict.fromkeys([*(plugins.get('enabled') or []), NAME]))
    if NAME in (plugins.get('disabled') or []):
        plugins['disabled'] = [n for n in plugins['disabled'] if n != NAME]
    block = yaml.safe_dump({'plugins': plugins}, sort_keys=False, allow_unicode=True)
    match = re.search(r'(?m)^plugins:[^\r\n]*(?:\r?\n|$)', text)
    if match:
        tail = re.search(r'(?m)^[^\s#][^\r\n]*:', text[match.end():])
        end = match.end() + tail.start() if tail else len(text)
        updated = text[:match.start()] + block + text[end:]
    else:
        updated = text.rstrip('\r\n') + '\n' + block
    expected = {**full, 'plugins': plugins}
    if yaml.safe_load(updated) != expected:
        raise RuntimeError('Config change would affect settings outside plugins')
    return updated.encode('utf-8')


def install(home, all_profiles=False):
    home = home.resolve(strict=True)
    if destination.classify(home) not in {'external', 'ungoverned'}:
        raise RuntimeError('Hermes installation requires an external, ungoverned host home')
    targets = [home]
    if all_profiles:
        targets += sorted(p.parent for p in (home / 'profiles').glob('*/config.yaml'))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    files, provenance = snapshot()
    results = []
    for profile in targets:
        if not profile.resolve().is_relative_to(home):
            raise RuntimeError('Profile escapes selected Hermes home')
        config = profile / 'config.yaml'
        original = config.read_bytes()
        new_config = enable_config(original)
        target = profile / 'plugins' / NAME
        stage = target.with_name(NAME + '.install-' + stamp)
        backup = profile / '_backups' / ('co-author-harness-' + stamp)
        for rel, data in files.items():
            atomic(stage / rel, data)
        backup.mkdir(parents=True)
        atomic(backup / 'config.yaml', original)
        if config.read_bytes() != original:
            raise RuntimeError('Concurrent config change; refusing activation')
        if target.exists():
            if target.is_symlink() or not target.resolve().is_relative_to(home):
                raise RuntimeError('Existing installation escapes selected Hermes home')
            os.replace(target, backup / 'plugin')
        os.replace(stage, target)
        atomic(config, new_config)
        for rel, data in files.items():
            if (target / rel).read_bytes() != data:
                raise RuntimeError('Installed member differs: ' + rel)
        results.append({'profile': 'default' if profile == home else profile.name,
                        'path': str(target), 'files_verified': len(files), 'backup': str(backup)})
    return {'version': provenance['version'], 'kind': provenance['kind'], 'installed': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hermes-home', type=Path, required=True)
    parser.add_argument('--all-profiles', action='store_true')
    args = parser.parse_args()
    print(json.dumps(install(args.hermes_home, args.all_profiles), indent=2))
