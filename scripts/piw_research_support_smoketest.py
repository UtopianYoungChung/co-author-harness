"""Source resolution must not pass an unsupported attribution check."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
import piw_acceptance_smoketest as fixture
import piw_coordinator as coordinator
import piw_session as piw


class AttributionTests(unittest.TestCase):
    def test_matching_source_without_passage_cannot_pass_attribution(self):
        with tempfile.TemporaryDirectory(prefix='piw-attribution-') as raw:
            root = Path(raw)
            session, request = fixture.setup(root)
            source = root / 'source.txt'
            source.write_text('A queue records submitted requests. Recording alone does not grant approval.', encoding='utf-8')
            request['source_excerpts'] = [{'path': str(source), 'source_id': 'S1', 'locator': 'paragraph 1'}]
            request['required_checks'] = [{'id': 'attribution_support', 'required': True, 'source_required': True}]
            coordinator.start(session, request); fixture.plan(session); fixture.ingest_child(session)
            result, _ = fixture.complete_child(session)
            contract, _, log, state = coordinator.replay(session)
            bound_request = piw.read_json(log['pending']['path'])
            with self.assertRaisesRegex(piw.PIWError, 'passage'):
                coordinator.validate_result(contract, bound_request, result, state)
            result['checks'][0]['source_support'] = [{
                'source_id': 'S1', 'source_locator': 'paragraph 1',
                'quote': 'A queue records submitted requests.',
                'claim': 'A queue records submitted requests.', 'status': 'supported'}]
            coordinator.validate_result(contract, bound_request, result, state)
            for field, value in [('quote', 'Every recorded request is approved.'),
                                  ('claim', 'The study proves every request succeeds.'),
                                  ('source_locator', 'page 900'), ('status', 'contested')]:
                with self.subTest(field=field):
                    support = result['checks'][0]['source_support'][0]
                    before = support[field]; support[field] = value
                    with self.assertRaises(piw.PIWError):
                        coordinator.validate_result(contract, bound_request, result, state)
                    support[field] = before


if __name__ == '__main__':
    unittest.main()
