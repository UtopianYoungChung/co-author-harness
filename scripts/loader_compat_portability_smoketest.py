#!/usr/bin/env python3
"""Prove the release loader check survives a non-UTF-8 Windows console.

Also covers R-3: hook interpreter resolution and loud launch failure.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CHECK = ROOT / "scripts" / "loader-compat-check.py"
HOOKS = ROOT / "hooks" / "hooks.json"
GATE_REL = "scripts/hooks/full_run_pretooluse_gate.py"
WINDOWS_GIT_BASH = Path(r"C:\Program Files\Git\bin\bash.exe")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _hook_launch_command() -> tuple[str, list[str]]:
    config = json.loads(HOOKS.read_text(encoding="utf-8"))
    hook = config["hooks"]["PreToolUse"][0]["hooks"][0]
    stop = config["hooks"]["Stop"][0]["hooks"][0]
    assert hook == stop, "PreToolUse and Stop must share the same interpreter resolver"
    return hook["command"], list(hook.get("args") or [])


def _hook_shell(command: str) -> str:
    """Resolve the configured shell before the test intentionally clears PATH."""
    located = shutil.which(command)
    if located:
        return located
    if os.name == "nt" and WINDOWS_GIT_BASH.is_file() and command == "bash":
        return str(WINDOWS_GIT_BASH)
    raise AssertionError(f"configured hook shell is unavailable: {command!r}")


def case_hook_interpreter_resolution() -> None:
    command, args = _hook_launch_command()
    blob = " ".join([command, *args])
    assert command != "python3", "bare python3 is the R-3 defect"
    assert "CLAUDE_PLUGIN_PYTHON" in blob
    assert "WindowsApps" in blob
    assert "HOOK-INTERPRETER" in blob
    assert GATE_REL in blob.replace("\\", "/")


def case_hook_launch_failure_is_loud() -> None:
    command, args = _hook_launch_command()
    shell = _hook_shell(command)
    env = {
        key: value for key, value in os.environ.items()
        if key not in {"CLAUDE_PLUGIN_PYTHON", "CLAUDE_PLUGIN_ROOT"}
        and key.upper() != "PYTHONUTF8"
    }
    env["PATH"] = ""
    proc = subprocess.run(
        [shell, *args],
        capture_output=True,
        check=False,
        env=env,
        timeout=30,
    )
    combined = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
    assert proc.returncode != 0, combined[-800:]
    assert "HOOK-INTERPRETER" in combined, combined[-800:]


def case_hook_launches_from_resolved_interpreter() -> None:
    command, args = _hook_launch_command()
    shell = _hook_shell(command)
    env = {
        key: value for key, value in os.environ.items()
        if key.upper() != "PYTHONUTF8"
    }
    env["CLAUDE_PLUGIN_PYTHON"] = sys.executable
    env["CLAUDE_PLUGIN_ROOT"] = str(ROOT)
    proc = subprocess.run(
        [shell, *args],
        input=b"{}",
        capture_output=True,
        check=False,
        env=env,
        timeout=30,
    )
    combined = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
    assert proc.returncode == 0, combined[-800:]
    assert "can't open file" not in combined, combined[-800:]


def case_loader_compat_encoding() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        description = "Synthetic loader portability fixture."
        manifest = {
            "name": "loader-portability-fixture",
            "version": "1.0.0",
            "description": description,
            "keywords": ["fixture"],
        }
        marketplace = {
            "plugins": [{
                "name": manifest["name"],
                "version": manifest["version"],
                "description": description,
                "source": {
                    "source": "url",
                    "url": "https://github.com/example/loader-portability-fixture.git",
                },
                "repository": "https://github.com/example/loader-portability-fixture",
            }]
        }
        _write(root / ".claude-plugin/plugin.json", json.dumps(manifest))
        _write(root / ".claude-plugin/marketplace.json", json.dumps(marketplace))
        _write(
            root / "skills/sample/SKILL.md",
            "---\nname: sample\ndescription: Synthetic fixture skill.\n---\n\n# Sample\n",
        )
        _write(root / "agents/sample.md", "# Sample agent\n")
        _write(root / "README.md", "# Fixture\n")
        _write(root / "CHANGELOG.md", "# Changelog\n")

        archive = root / ".claude-plugin/loader-portability-fixture.plugin"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(root.rglob("*")):
                if path.is_file() and path != archive:
                    bundle.write(path, path.relative_to(root).as_posix())

        env = os.environ.copy()
        env["PYTHONUTF8"] = "0"
        env["PYTHONIOENCODING"] = "cp949"
        proc = subprocess.run(
            [
                sys.executable,
                str(CHECK),
                "--plugin-root",
                str(root),
                "--plugin-file",
                str(archive),
            ],
            capture_output=True,
            check=False,
            env=env,
        )
        combined = proc.stdout + proc.stderr
        assert b"UnicodeEncodeError" not in combined, combined[-1200:]
        decoded = combined.decode("utf-8", errors="strict")
        assert proc.returncode == 0, decoded[-1600:]
        # The check's own heading contains an em dash. Requiring it proves the
        # formerly crashing non-CP949 output path was exercised, not bypassed.
        assert "co-author-harness — loader-compat-check" in decoded


def case_codex_hook_events() -> None:
    manifest = json.loads((ROOT / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
    config = json.loads((ROOT / manifest['hooks']).read_text(encoding='utf-8'))
    pre = config['hooks']['PreToolUse'][0]
    stop = config['hooks']['Stop'][0]['hooks'][0]
    handler = pre['hooks'][0]
    assert handler == stop
    assert 'args' not in handler, 'Codex requires a complete command string'
    import re
    for tool in ('apply_patch', 'spawn_agent'):
        assert re.search(pre['matcher'], tool)
    env = {k: v for k, v in os.environ.items() if not k.startswith('FRC_')}
    env.update(PLUGIN_ROOT=str(ROOT), CLAUDE_PLUGIN_ROOT=str(ROOT),
               COAUTHOR_HOOK_PYTHON=sys.executable)
    command = handler['commandWindows'] if os.name == 'nt' else handler['command']
    failed = subprocess.run(command, shell=True, input='{}', capture_output=True,
                            text=True, encoding='utf-8', errors='replace',
                            env={**env, 'COAUTHOR_HOOK_PYTHON': str(ROOT / 'missing-python')},
                            timeout=30)
    assert failed.returncode == 2 and 'HOOK-INTERPRETER' in failed.stderr
    # Exercise the POSIX launcher as well (Git Bash supplies it on Windows).
    bash = _hook_shell('bash')
    posix = subprocess.run([bash, (ROOT / 'scripts/hooks/run_codex_hook.sh').as_posix()],
                           input='{}', capture_output=True, text=True, encoding='utf-8',
                           errors='replace', env={**env, 'PLUGIN_ROOT': ROOT.as_posix()}, timeout=30)
    assert posix.returncode == 0 and json.loads(posix.stdout) == {}, posix.stderr

    def run(payload, scope=None, *, launch=False):
        bound = dict(env)
        if scope:
            bound['FRC_PARENT_SCOPE'] = scope
        proc = subprocess.run(
            command if launch else [sys.executable, str(ROOT / 'scripts/hooks/codex_gate.py')],
            shell=launch, input=json.dumps(payload), capture_output=True,
            text=True, encoding='utf-8', errors='replace', env=bound, timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)

    def denied(result):
        return result.get('hookSpecificOutput', {}).get('permissionDecision') == 'deny'

    with tempfile.TemporaryDirectory(prefix='codex hook space ') as td:
        def patch(body):
            return {'hook_event_name': 'PreToolUse', 'cwd': td, 'tool_name': 'apply_patch',
                    'tool_input': {'command': '*** Begin Patch\n' + body + '\n*** End Patch'}}
        source = patch('*** Add File: src/example.py\n+x = 1')
        assert run(source) == {}, 'ordinary unscoped coding remains allowed'
        assert run(source, launch=True) == {}, 'execute the actual platform launcher'
        # Match the current policy: folder names alone are not harness territory.
        assert run(patch('*** Add File: manuscript/notes.md\n+text')) == {}
        (Path(td) / 'reviews').mkdir()
        (Path(td) / 'reviews/assignment_contract.json').write_text('{}', encoding='utf-8')
        for body in (
            '*** Add File: manuscript/essay.md\n+text',
            '*** Update File: manuscript/essay.md\n@@\n-old\n+new',
            '*** Delete File: manuscript/essay.md',
            '*** Update File: src/notes.md\n*** Move to: manuscript/essay.md\n@@\n-a\n+b',
            '*** Update File: manuscript/essay.md\n*** Move to: src/notes.md\n@@\n-a\n+b',
            '*** Add File: src/a.py\n+x\n*** Add File: manuscript/essay.md\n+text',
            '*** Add File: src/../manuscript/essay.md\n+text',
        ):
            assert denied(run(patch(body))), body
        assert denied(run(patch('*** Add File: manuscript/essay.md\n+text'), launch=True))
        assert denied(run(source, 'project_independent')), 'missing PIW session must refuse'
        assert denied(run(source, 'unknown')), 'unknown scope must refuse'
        assert denied(run({'hook_event_name': 'PreToolUse', 'tool_name': 'apply_patch',
                           'tool_input': {'command': 'not a patch'}}))
        spawn = {'hook_event_name': 'PreToolUse', 'cwd': td, 'tool_name': 'spawn_agent',
                 'tool_input': {'message': 'Write manuscript/essay.md'}}
        assert denied(run(spawn)), 'Codex message must reach the scope gate'
        spawn['tool_input']['message'] = 'run_scope: adhoc_review\nRead and review manuscript/essay.md only.'
        assert run(spawn, 'adhoc_review') == {}, 'matching review scope must remain possible'
        stop_event = {'hook_event_name': 'Stop', 'cwd': td, 'last_assistant_message': 'Checks finished.'}
        assert run(stop_event, launch=True) == {}, 'Stop allow must emit valid JSON'
        stop_event['last_assistant_message'] = 'Lifecycle complete; terminal PASS.'
        assert run(stop_event, 'project_independent', launch=True).get('decision') == 'block'


def case_codex_native_roles() -> None:
    import codex_agent_setup as setup
    rendered = setup.render_roles()
    assert len(rendered) == 6
    assert set(setup.ROLES) == {p.stem for p in (ROOT / 'agents').glob('*.md')}
    for name, text in rendered.items():
        config = tomllib.loads(text)
        assert set(config) == {'name', 'description', 'developer_instructions'}
        assert name == config['name'] + '.toml'
        assert 'skill_bodies' in config['developer_instructions']
        assert (ROOT / 'skills').as_posix() in config['developer_instructions']
    with tempfile.TemporaryDirectory() as td:
        destination = Path(td) / 'agents'
        setup.install(destination)
        assert not destination.exists(), 'dry run must not write'
        setup.install(destination, write=True)
        setup.install(destination, write=True)  # identical reruns are safe
        assert len(list(destination.glob('*.toml'))) == 6
        profile = Path(td) / 'coauthor-harness.config.toml'
        setup.install(destination, write=True, config_output=profile, include_hooks=True)
        config = tomllib.loads(profile.read_text(encoding='utf-8'))
        assert len(config['agents']) == 6
        assert set(config['hooks']) == {'PreToolUse', 'Stop'}
        assert 'model' not in config and 'permissions' not in config
        for role in config['agents'].values():
            assert Path(role['config_file']).is_file()
        for event in config['hooks'].values():
            assert 'PLUGIN_ROOT' not in event[0]['hooks'][0]['commandWindows']
        edited = destination / next(iter(rendered))
        edited.write_text('user edit', encoding='utf-8')
        try:
            setup.install(destination, write=True)
        except ValueError:
            pass
        else:
            raise AssertionError('must refuse a user-edited role')
        assert edited.read_text(encoding='utf-8') == 'user edit'

    def refused(code, target, **kwargs):
        try:
            setup.install(target, **kwargs)
        except ValueError as exc:
            assert str(exc).startswith(code), exc
        else:
            raise AssertionError(f'must refuse {target} with {code}')

    # Dry runs refuse the same destinations; the package cases stay dry so a
    # broken guard cannot write into the checkout or its parent.
    refused('DEST-MISROUTED', ROOT / 'codex-agents')
    refused('SETUP-ENCLOSES-PACKAGE', ROOT.parent)
    assert not (ROOT / 'codex-agents').exists()
    with tempfile.TemporaryDirectory() as td:
        workspace = Path(td) / 'workspace'
        routing = workspace / 'governance' / 'output-routing' / 'output_routing.yaml'
        routing.parent.mkdir(parents=True)
        routing.write_text('schema_version: 1\nroutes: []\n', encoding='utf-8')
        project_agents = workspace / 'project' / '.codex' / 'agents'
        for write in (False, True):
            refused('SETUP-IN-GOVERNED-WORKSPACE', project_agents, write=write)
        personal = Path(td) / 'personal' / 'agents'
        refused('SETUP-IN-GOVERNED-WORKSPACE', personal, write=True,
                config_output=workspace / 'coauthor-harness.config.toml')
        assert not (workspace / 'project').exists() and not personal.exists(), \
            'refusal must precede every write'


def main() -> int:
    case_loader_compat_encoding()
    case_hook_interpreter_resolution()
    case_hook_launch_failure_is_loud()
    case_hook_launches_from_resolved_interpreter()
    case_codex_hook_events()
    case_codex_native_roles()
    print("PASS: loader compatibility check is console-encoding independent")
    print("PASS: hook interpreter resolves and launch failure is loud")
    print("PASS: Codex patch/dispatch/Stop adapters, launchers, and six native role bindings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
