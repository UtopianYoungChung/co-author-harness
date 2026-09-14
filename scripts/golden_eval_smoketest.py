"""Regression checks for false scholarly-evaluation credit and unsafe baselines."""
from __future__ import annotations
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'scripts/eval/golden_eval_score.py'
spec = importlib.util.spec_from_file_location('golden_scorer', SCRIPT)
scorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scorer)
MANIFEST = json.loads((ROOT / 'scripts/fixtures/golden/manifest.json').read_text(encoding='utf-8'))


def finding(code='C-8/M-1', line=15):
    return {'finding_code': code, 'severity': 'MAJOR', 'line': line,
            'location_hint': 'paragraph at the specified source line'}


def run_doc(findings, fixture='golden_p2_theory.md'):
    return {'fixture': fixture, 'pass': 'evaluator', 'evaluator': {
        'host': 'synthetic-test', 'model': 'fixture', 'configuration': 'test-v1'},
        'findings': findings}


class GoldenTests(unittest.TestCase):
    def test_blinding_removes_answer_header_and_preserves_line_numbers(self):
        source = (scorer.MANIFEST.parent / 'golden_p2_theory.md').read_text(encoding='utf-8')
        blinded = scorer.blind_text(source)
        self.assertNotIn('seeded defects', blinded)
        self.assertNotIn('DEFECT', blinded)
        self.assertEqual(blinded.count('\n'), source.count('\n'))

    def test_generic_code_cannot_earn_credit(self):
        with self.assertRaisesRegex(ValueError, 'code'):
            scorer.score(run_doc([finding('C', 15)] * 6), MANIFEST)

    def test_correct_code_at_wrong_location_is_not_a_detection(self):
        result = scorer.score(run_doc([finding(line=19)]), MANIFEST)
        self.assertEqual(result['recall'], 0.0)
        self.assertEqual(result['extra_findings'], 1)

    def test_located_detection_and_duplicates(self):
        result = scorer.score(run_doc([finding(), finding()]), MANIFEST)
        self.assertEqual(result['per_defect'], {
            'D1': False, 'D2': True, 'D3': False, 'D4': False, 'D5': False, 'D6': False})
        self.assertEqual(result['extra_findings'], 1)

    def test_composite_family_does_not_steal_component_detection(self):
        result = scorer.score(run_doc([finding('C-6', 11)]), MANIFEST)
        self.assertEqual(result['recall'], 0.0)

    def test_p1_control_detects_an_exact_p2_family_alias(self):
        result = scorer.score(run_doc([finding('M-1', 13)], 'golden_p1_brief.md'), MANIFEST)
        self.assertEqual(result['false_positives'], 1)

    def test_unbaselined_measurement_is_not_a_gate_pass(self):
        result = scorer.score(run_doc([]), MANIFEST)
        self.assertEqual(result['baseline_status'], 'not_supplied')
        self.assertIs(result['gate_passed'], False)

    def test_all_correct_locations_retain_full_recall(self):
        defects = MANIFEST['fixtures']['golden_p2_theory.md']['defects']
        result = scorer.score(run_doc([finding(d['expected_code_family'], d['line']) for d in defects]), MANIFEST)
        self.assertEqual(result['recall'], 1.0)
        self.assertEqual(result['extra_findings'], 0)
        self.assertFalse(result['gate_passed'])

    def test_comparable_baseline_and_regression(self):
        baseline = scorer.score(run_doc([finding()]), MANIFEST)
        same = scorer.score(run_doc([finding()]), MANIFEST)
        scorer.compare_baseline(same, baseline)
        self.assertTrue(same['gate_passed'])
        worse = scorer.score(run_doc([]), MANIFEST)
        scorer.compare_baseline(worse, baseline)
        self.assertFalse(worse['gate_passed'])

    def test_baseline_from_another_fixture_or_configuration_is_refused(self):
        with tempfile.TemporaryDirectory(prefix='golden-score-') as raw:
            root = Path(raw)
            findings_path = root / 'findings.json'
            baseline_path = root / 'baseline.json'
            findings_path.write_text(json.dumps(run_doc([])), encoding='utf-8')
            baseline = scorer.score(run_doc([]), MANIFEST)
            for key, value in [('fixture', 'golden_p1_brief.md'),
                               ('evaluator', {'host': 'foreign', 'model': 'other', 'configuration': 'x'})]:
                with self.subTest(key=key):
                    changed = copy.deepcopy(baseline); changed[key] = value
                    baseline_path.write_text(json.dumps(changed), encoding='utf-8')
                    result = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT),
                        str(findings_path), '--baseline', str(baseline_path)],
                        capture_output=True, text=True, encoding='utf-8')
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
