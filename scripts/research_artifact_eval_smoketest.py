"""Artifact quality requires bound output and separate, explicit adjudication."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
import piw_session as piw

SPEC = importlib.util.spec_from_file_location('research_eval', Path(__file__).parent / 'eval/research_artifact_eval.py')
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


class BenchmarkTests(unittest.TestCase):
    def test_packet_hides_answer_checks_and_binds_sources(self):
        packet = evaluation.prepare('memo')
        self.assertNotIn('checks', packet['packet'])
        self.assertNotIn('dimensions', packet['packet'])
        self.assertEqual(packet['packet_sha256'], piw.digest(piw.json_bytes(packet['packet'])))

    def test_missing_adjudication_and_drift_cannot_pass(self):
        with tempfile.TemporaryDirectory() as raw:
            artifact = Path(raw) / 'memo.md'
            artifact.write_text('A bounded research memo candidate.', encoding='utf-8')
            packet = evaluation.prepare('memo')
            submission = {'case': 'memo', 'packet_sha256': packet['packet_sha256'], 'artifact': piw.identity(artifact),
                          'execution_kind': 'synthetic_fixture', 'host': {'adapter': 'fixture', 'model': 'fixture', 'configuration': 'test'}}
            measured = evaluation.score(submission)
            self.assertFalse(measured['case_thresholds_passed'])
            self.assertFalse(measured['quality_qualified'])
            artifact.write_text('Changed after the submitted review.', encoding='utf-8')
            with self.assertRaises(ValueError): evaluation.score(submission)

    def test_synthetic_scores_are_never_live_quality_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            artifact = Path(raw) / 'memo.md'
            artifact.write_text('A bounded research memo candidate.', encoding='utf-8')
            submission = {'case': 'memo', 'packet_sha256': evaluation.prepare('memo')['packet_sha256'],
                          'artifact': piw.identity(artifact), 'execution_kind': 'synthetic_fixture',
                          'host': {'adapter': 'fixture', 'model': 'fixture', 'configuration': 'test'}}
            review = {'case': 'memo', 'artifact_sha256': submission['artifact']['sha256'], 'reviewer': {'kind': 'human', 'identity': 'synthetic-test-declaration'},
                      'critical_failures': [], 'scores': {d: {'value': 4, 'rationale': 'Synthetic assessment tests validator behavior only.', 'locators': ['paragraph 1']} for d in evaluation.MANIFEST['dimensions']}}
            result = evaluation.score(submission, review, piw.digest(piw.json_bytes(review)))
            self.assertFalse(result['case_thresholds_passed'])
            review['scores']['coverage']['value'] = True
            with self.assertRaises(ValueError): evaluation.score(submission, review, piw.digest(piw.json_bytes(review)))


if __name__ == '__main__': unittest.main()
