"""Portable archives preserve original bindings and fail on missing or changed proof."""
import json
import tempfile
import unittest
from pathlib import Path
import piw_acceptance_smoketest as fixture
import piw_session as piw
import piw_archive as archive
import piw_metrics


class ArchiveTests(unittest.TestCase):
    def test_archive_survives_original_session_removal_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory(prefix='piw-archive-') as out:
            with tempfile.TemporaryDirectory(prefix='piw-original-') as original:
                session, request = fixture.setup(Path(original), revision=True)
                fixture.finish(session, request)
                metrics = piw_metrics.measure(session)
                self.assertEqual(metrics['recorded_role_executions'], 4)
                self.assertEqual(metrics['correction_cycles'], 0)
                self.assertTrue(all(r['elapsed_seconds'] >= 0 and r['context_tokens'] is None for r in metrics['roles']))
                self.assertGreaterEqual(metrics['time_to_last_verified_role_seconds'], metrics['time_to_first_candidate_seconds'])
                with self.assertRaises(piw.PIWError):
                    archive.export_archive(session, piw.ROOT / 'outputs/co-author-harness/archive-refusal')
                receipt = archive.export_archive(session, Path(out) / 'saved')
                manifest = Path(receipt['manifest']['path'])
                pin = receipt['manifest']['sha256']
                doc = json.loads(manifest.read_text(encoding='utf-8'))
            result = archive.verify_archive(manifest, pin)
            self.assertEqual(result['status'], 'archived_evidence_verified')
            self.assertFalse(result['task_complete'])
            self.assertFalse(result['research_acceptance'])
            artifact = next(x for x in doc['files'] if x['original_path'].endswith('final.md'))
            member = manifest.parent / artifact['member']
            before = member.read_bytes()
            member.write_bytes(before + b'tampered')
            with self.assertRaises(piw.PIWError): archive.verify_archive(manifest, pin)
            member.write_bytes(before)
            missing = next(x for x in doc['files'] if x['original_path'].endswith('parent.jsonl'))
            doc['files'].remove(missing)
            manifest.write_bytes(piw.json_bytes(doc))
            with self.assertRaises(piw.PIWError): archive.verify_archive(manifest, pin)
            with self.assertRaises(piw.PIWError): archive.verify_archive(manifest, piw.digest(manifest.read_bytes()))

    def test_export_refuses_incomplete_session(self):
        with tempfile.TemporaryDirectory(prefix='piw-incomplete-') as raw:
            root = Path(raw)
            session, _ = fixture.setup(root)
            with self.assertRaises(piw.PIWError): archive.export_archive(session, root / 'archive')


if __name__ == '__main__': unittest.main()
