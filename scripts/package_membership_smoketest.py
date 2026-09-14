"""Tracked fixture workspaces must be refused before they become package bytes."""
from __future__ import annotations

import subprocess
import ast
import tempfile
import unittest
from pathlib import Path

import package_enumeration as package


class MembershipTests(unittest.TestCase):
    def test_fixtures_do_not_allocate_temporary_projects_at_package_root(self):
        offenders = []
        for path in (Path(__file__).parent).glob('*smoketest.py'):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
                if not isinstance(node, ast.Call): continue
                for keyword in node.keywords:
                    value = keyword.value
                    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'str' and value.args:
                        value = value.args[0]
                    if keyword.arg == 'dir' and isinstance(value, ast.Name) and value.id in ('ROOT', 'HARNESS'):
                        offenders.append(f'{path.name}:{node.lineno}')
        self.assertEqual(offenders, [], 'Route package-local temporary fixture projects through the ignored scratch helper')

    def test_transient_workspace_is_refused_but_named_fixtures_ship(self):
        original = package.HARNESS
        with tempfile.TemporaryDirectory(prefix='package-membership-') as raw:
            root = Path(raw)
            def git(*args):
                return subprocess.run([package.GIT, '-C', str(root), *args],
                                      check=True, capture_output=True)
            git('init', '-b', 'main')
            git('config', 'user.name', 'Fixture')
            git('config', 'user.email', 'fixture@example.invalid')
            fixture = root / 'scripts/fixtures/example.json'
            fixture.parent.mkdir(parents=True)
            fixture.write_text('{}', encoding='utf-8')
            git('add', '.'); git('commit', '-m', 'fixture')
            try:
                package.HARNESS = root
                self.assertIn('scripts/fixtures/example.json', package.enumerate_package_files()[0])
                for rel in ('assignment-milestone-checkpoint-leak/reviews/G4_signoff.md',
                            'full-run-valid-template-leak/reviews/completion.json',
                            '.harness-test-scratch/leak/result.json'):
                    with self.subTest(rel=rel):
                        p = root / rel
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_text('synthetic PASS', encoding='utf-8')
                        git('add', '.'); git('commit', '-m', 'leaked fixture')
                        with self.assertRaisesRegex(ValueError, 'PACKAGE-TRANSIENT-MEMBER'):
                            package.enumerate_package_files()
                        git('rm', rel); git('commit', '-m', 'remove fixture')
            finally:
                package.HARNESS = original


if __name__ == '__main__':
    unittest.main()
