#!/usr/bin/env python3
"""Render/install native Codex role pointers; never change models or hook trust.

Default is a dry run. Use --write with an explicit personal/project agents
directory. Existing different files are refused; remove/update them explicitly.
Role instructions stay canonical in agents/*.md, not duplicated in TOML.
"""
from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLES = {
    'planner': 'Plan and coordinate a scoped harness workflow.',
    'evaluator': 'Evaluate harness artifacts and report evidence-bound findings.',
    'generator': 'Generate or revise artifacts within the authorized harness scope.',
    'reflector': 'Route legacy reflection requests to the appropriate reflection mode.',
    'reflector-probe': 'Run a lightweight mid-round harness integrity probe.',
    'reflector-closeout': 'Run full closeout reflection when the governed workflow permits it.',
}


def render_roles(root: Path = ROOT) -> dict[str, str]:
    root = root.resolve()
    result = {}
    for role, description in ROLES.items():
        prompt = root / 'agents' / f'{role}.md'
        if not prompt.is_file():
            raise ValueError(f'missing canonical role: {prompt}')
        name = 'coauthor_' + role.replace('-', '_')
        instructions = (
            f'You are the co-author-harness {role} role. Package root: {root.as_posix()}. '
            f'Before performing the role, read {prompt.as_posix()}, '
            f'{(root / "AGENTS.md").as_posix()}, and the references required by that role. '
            'Inherit the exact parent run_scope and task boundaries; do not invent authority. '
            'Read the canonical skill_bodies and role_prompt bound in the dispatch request '
            'from its package_root before execution. Other needed skills are under '
            f'{(root / "skills").as_posix()}/<skill>/SKILL.md; skill catalog metadata alone '
            'does not load those bodies. Preserve host-native child execution and original '
            'trace requirements. If required files or host capabilities are unavailable, '
            'report that limitation instead of simulating a completed role. '
            'No task completion implies lifecycle completion, research acceptance, or promotion.'
        )
        result[f'{name}.toml'] = '\n'.join(
            f'{key} = {json.dumps(value, ensure_ascii=False)}'
            for key, value in {'name': name, 'description': description,
                               'developer_instructions': instructions}.items()
        ) + '\n'
    return result


def render_config(destination: Path, *, root: Path = ROOT, include_hooks: bool = False) -> str:
    """Explicit declarations also work on hosts without standalone discovery."""
    blocks = ['# Generated harness role bindings; models and permissions are inherited.']
    for filename, text in render_roles(root).items():
        role = tomllib.loads(text)
        blocks.append(f'[agents.{role["name"]}]\ndescription = {json.dumps(role["description"])}\n'
                      f'config_file = {json.dumps((destination.resolve() / filename).as_posix())}')
    if include_hooks:
        # Explicit opt-in fallback for hosts that do not discover plugin hooks.
        # Absolute commands do not depend on plugin-scoped environment variables.
        config = json.loads((root / 'hooks/codex.json').read_text(encoding='utf-8'))
        for event, groups in config['hooks'].items():
            for group in groups:
                block = f'[[hooks.{event}]]\n'
                if 'matcher' in group:
                    block += f'matcher = {json.dumps(group["matcher"])}\n'
                handler = dict(group['hooks'][0])
                handler['command'] = 'sh "' + (root.resolve() / 'scripts/hooks/run_codex_hook.sh').as_posix() + '"'
                handler['commandWindows'] = 'cmd.exe /d /c ""' + str(root.resolve() / 'scripts/hooks/run_codex_hook.cmd') + '""'
                block += f'[[hooks.{event}.hooks]]\n'
                block += '\n'.join(f'{key} = {json.dumps(value)}' for key, value in handler.items())
                blocks.append(block)
    return '\n\n'.join(blocks) + '\n'


def install(destination: Path, *, write: bool = False, root: Path = ROOT,
            config_output: Path | None = None, include_hooks: bool = False) -> dict:
    rendered = render_roles(root)
    if include_hooks and config_output is None:
        raise ValueError('--include-hooks requires --config-output')
    outputs = {destination / name: content for name, content in rendered.items()}
    if config_output is not None:
        if config_output in outputs:
            raise ValueError('configuration output collides with a role file')
        outputs[config_output] = render_config(destination, root=root, include_hooks=include_hooks)
    # Preflight every collision before creating anything.
    for path, content in outputs.items():
        if path.exists() and path.read_text(encoding='utf-8') != content:
            raise ValueError(f'refusing to overwrite different agent configuration: {path}')
    if write:
        for path, content in outputs.items():
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8', newline='\n')
    return {'mode': 'written' if write else 'dry-run', 'agent_dir': str(destination.resolve()),
            'roles': list(rendered), 'package_root': str(root.resolve()),
            'config_output': str(config_output.resolve()) if config_output else None,
            'fallback_hooks_included': include_hooks,
            'hook_trust_changed': False, 'model_settings_changed': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent-dir', required=True, type=Path)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--config-output', type=Path,
                        help='Optional new config fragment or <name>.config.toml profile; existing different files are refused')
    parser.add_argument('--include-hooks', action='store_true',
                        help='Include the two hook events only when native plugin hook discovery is unavailable')
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.agent_dir, write=args.write,
                                 config_output=args.config_output, include_hooks=args.include_hooks), indent=2))
        return 0
    except (OSError, ValueError) as exc:
        parser.exit(1, f'CODEX-AGENT-SETUP: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
