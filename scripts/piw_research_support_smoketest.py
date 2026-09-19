"""Source resolution must not pass an unsupported attribution check."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
import piw_acceptance_smoketest as fixture
import piw_coordinator as coordinator
import piw_session as piw
import copy
import json
import bibliography_review as bibliography
from bibliography_fixture_support import synthetic_review


MANUSCRIPT = '# Study\n\nThe original framework distinguished recording from approval [1].\n\n# References\n\n[1] Example, A. (1970). A foundational framework.\n'


def ingest_review(session, result, evidence):
    # The existing integration harness uses explicitly synthetic host traces.
    log = Path(evidence['child_log'])
    rows = [json.loads(x) for x in log.read_text(encoding='utf-8').splitlines()]
    rows[-1]['payload']['last_agent_message'] = json.dumps(result)
    log.write_text(''.join(json.dumps(x) + '\n' for x in rows), encoding='utf-8')
    return coordinator.ingest(session, result, evidence)


class BibliographyWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='bibliography-workflow-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.index = 0

    def setup_review(self, text=MANUSCRIPT, scope='substantive', source_text=None):
        self.index += 1
        root = self.root / str(self.index)
        root.mkdir()
        session, request = fixture.setup(root, max_corrections=0)
        source = root / 'source.txt'
        source.write_text(source_text or 'The original framework distinguished recording from approval. The source does not establish a current research gap.', encoding='utf-8')
        request['source_excerpts'] = [{'path': str(source), 'source_id': 'S1', 'locator': 'paragraph 1'}]
        request['required_checks'] = [{'id': 'brief_and_scope', 'required': True}]
        request['review_scope'] = scope
        coordinator.start(session, request)
        fixture.plan(session)
        fixture.ingest_child(session, artifact=text.encode('utf-8'))
        result, evidence = fixture.complete_child(session)
        contract = piw.read_json(session / 'binding/run.json')
        result['bibliography_review'] = synthetic_review(text, contract['source_excerpts'])
        return session, result, evidence

    def assert_refused(self, result, evidence, session, code):
        with self.assertRaises(piw.PIWError) as cm:
            ingest_review(session, result, evidence)
        self.assertEqual(cm.exception.code, code)

    def assert_completion_blocked(self, session):
        with self.assertRaises(piw.PIWError):
            coordinator.deliver(session, session.parent / 'blocked.md')
        self.assertFalse(fixture.verify_cli(session)[1]['task_complete'])

    def finish_review(self, session, result, evidence, status='assessed'):
        ingest_review(session, result, evidence)
        reflection, host = fixture.complete_child(session)
        if 'bibliography_review' in result:
            reflection['bibliography_review'] = copy.deepcopy(result['bibliography_review'])
        ingest_review(session, reflection, host)
        completed = coordinator.deliver(session, session.parent / 'delivered.md')
        self.assertTrue(completed['task_complete'])
        self.assertEqual(completed['bibliography_status'], status)
        exit_code, verified = fixture.verify_cli(session)
        self.assertEqual(exit_code, 0)
        self.assertTrue(verified['task_complete'])
        self.assertEqual(verified['bibliography_status'], status)

    def test_undated_citations_require_support_through_completion(self):
        for citation in ('(Example, n.d.)', 'Example (n.d.)', '(Example, N.D.)'):
            with self.subTest(citation=citation):
                text = MANUSCRIPT.replace('[1].', citation + '.').replace('(1970)', '(n.d.)')
                session, result, evidence = self.setup_review(text)
                support = result['bibliography_review']['source_support']
                self.assertEqual(len(support), 1)
                result['bibliography_review']['source_support'] = []
                self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-COVERAGE')
                self.assert_completion_blocked(session)
                result['bibliography_review']['source_support'] = support
                self.finish_review(session, result, evidence)

    def test_detected_unresolved_citations_cannot_deliver_with_zero_support(self):
        for text in ('# Note\n\nThe framework works (Missing, n.d.).\n',
                     '# Note\n\nUnknown (2027) proposes a framework.\n',
                     MANUSCRIPT.replace('[1].', 'Example (2027).'),
                     MANUSCRIPT.replace('[1].', '(Example, n.d.invalid).')):
            with self.subTest(text=text):
                session, result, evidence = self.setup_review(text)
                self.assertEqual(result['bibliography_review']['source_support'], [])
                self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-INVENTORY')
                self.assert_completion_blocked(session)

    def test_citation_locators_and_qualifiers_reopen_review_through_completion(self):
        text = MANUSCRIPT.replace('[1].', '(Example, 1970, p. 1).')
        original_session, original, original_host = self.setup_review(text)
        self.finish_review(original_session, original, original_host)
        for citation in ('(Example, 1970, p. 999)', '(contra Example, 1970, p. 1)',
                         '(see also Example, 1970, p. 1)', '(Example, 1970, sec. 1)'):
            with self.subTest(citation=citation):
                changed = text.replace('(Example, 1970, p. 1)', citation)
                session, result, evidence = self.setup_review(changed)
                self.assertNotEqual(result['bibliography_review']['coverage_sha256'],
                                    original['bibliography_review']['coverage_sha256'])
                result['bibliography_review'] = copy.deepcopy(original['bibliography_review'])
                self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-STALE')
                self.assert_completion_blocked(session)

    def test_ordinary_calendar_years_do_not_require_bibliography_review(self):
        for text in ('# Plan\n\nA report will be delivered next year (2027).\n',
                     '# Plan\n\nThe project spans two years (2027–2028).\n'):
            with self.subTest(text=text):
                session, result, evidence = self.setup_review(text)
                self.assertEqual(len(bibliography.inventory(text)['non_citations']), 1)
                self.assertFalse(bibliography.has_sources(text))
                self.assertNotIn('bibliography', [row['id'] for row in result['checks']])
                result.pop('bibliography_review')
                self.finish_review(session, result, evidence, status='not_applicable')

    def test_possessive_narrative_citations_require_support_through_completion(self):
        for author in ("Smith et al.'s", 'Smith et al.’s', "Smith's", 'Smith’s',
                       "Smith and Jones's", 'Smith and Jones’s'):
            with self.subTest(author=author):
                text = (f'# Study\n\n{author} (2020) framework distinguishes recording from approval.\n\n'
                        '# References\n\nSmith, A. (2020). A foundational framework.\n')
                session, result, evidence = self.setup_review(text)
                support = result['bibliography_review']['source_support']
                result['bibliography_review']['source_support'] = []
                self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-COVERAGE')
                self.assert_completion_blocked(session)
                self.assertEqual(len(support), 1)
                self.assertEqual(bibliography.inventory(text)['non_citations'], [])
                result['bibliography_review']['source_support'] = support
                self.finish_review(session, result, evidence)

    def test_unresolved_narrative_candidates_ignore_capitalization(self):
        for author in ('eResearch', 'eresearch', 'ERESEARCH', "smith et al.'s", 'smith et al.’s'):
            for references in ('', '\n# References\n\nOther, A. (2020). Unrelated work.\n'):
                with self.subTest(author=author, references=bool(references)):
                    text = f'# Study\n\n{author} (2020) proposes a framework.\n' + references
                    session, result, evidence = self.setup_review(text)
                    result['bibliography_review']['source_support'] = []
                    self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-INVENTORY')
                    self.assert_completion_blocked(session)
                    self.assertTrue(bibliography.has_sources(text))
                    self.assertEqual(bibliography.inventory(text)['non_citations'], [])

    def test_ambiguous_years_require_positive_calendar_evidence(self):
        for paragraph in ('(2020)', 'The framework (2020) explains recording.',
                          'The project (2027–2028) discusses approval.',
                          'Next year is discussed by eResearch (2020).',
                          'The project spans two years according to eResearch (2020).'):
            with self.subTest(paragraph=paragraph):
                text = '# Study\n\n' + paragraph + '\n'
                session, result, evidence = self.setup_review(text)
                self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-INVENTORY')
                self.assert_completion_blocked(session)
                self.assertEqual(bibliography.inventory(text)['non_citations'], [])

    def test_calendar_evidence_is_explicit_bound_and_subordinate_to_source_match(self):
        text = MANUSCRIPT.replace('# References', 'A report is due next year (2027).\n\n# References')
        session, result, evidence = self.setup_review(text)
        row = result['bibliography_review']['non_citations'][0]
        self.assertEqual(row['calendar_context'], 'next year')
        row['calendar_context'] = 'unsupported assertion'
        self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-NONCITATION')
        self.assert_completion_blocked(session)
        row['calendar_context'] = 'next year'
        self.finish_review(session, result, evidence)
        # Even an explicit calendar phrase cannot hide a matching narrative author.
        text = '# Study\n\nNext year (2027) proposes a framework.\n\n# References\n\nNext year, A. (2027). A framework.\n'
        session, result, evidence = self.setup_review(text)
        support = result['bibliography_review']['source_support']
        result['bibliography_review']['source_support'] = []
        self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-COVERAGE')
        self.assert_completion_blocked(session)
        self.assertEqual(len(support), 1)
        result['bibliography_review']['source_support'] = support
        self.finish_review(session, result, evidence)

    def test_non_citation_classification_is_bound_and_cannot_exclude_a_citation(self):
        text = MANUSCRIPT.replace('# References',
            'Example discussed the framework. A report will be delivered next year (2027).\n\n# References')
        session, result, evidence = self.setup_review(text)
        classifications = result['bibliography_review'].pop('non_citations')
        self.assertEqual(len(classifications), 1)
        self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-NONCITATION')
        self.assert_completion_blocked(session)
        result['bibliography_review']['non_citations'] = classifications
        self.finish_review(session, result, evidence)
        session, result, evidence = self.setup_review()
        result['bibliography_review']['non_citations'] = classifications
        result['bibliography_review']['source_support'] = []
        self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-NONCITATION')
        self.assert_completion_blocked(session)

    def test_numeric_renumbering_with_dates_preserves_review_through_completion(self):
        text = MANUSCRIPT.replace('# References', 'A report is due next year (2027).\n\n# References')
        session, original, evidence = self.setup_review(text)
        self.finish_review(session, original, evidence)
        session, result, evidence = self.setup_review(text.replace('[1]', '[19]'))
        result['bibliography_review'] = copy.deepcopy(original['bibliography_review'])
        self.finish_review(session, result, evidence)

    def test_numeric_group_structure_is_not_erased_with_labels(self):
        text = MANUSCRIPT.replace('[1].', '[1, 2].') + '\n[2] Second, B. (1980). Another framework.\n'
        session, original, evidence = self.setup_review(text)
        self.finish_review(session, original, evidence)
        renumbered = text.replace('[1]', '[10]').replace('[2]', '[20]').replace('[1, 2]', '[10, 20]')
        session, result, evidence = self.setup_review(renumbered)
        result['bibliography_review'] = copy.deepcopy(original['bibliography_review'])
        self.finish_review(session, result, evidence)
        session, result, evidence = self.setup_review(text.replace('[1, 2]', '[1; 2]'))
        result['bibliography_review'] = copy.deepcopy(original['bibliography_review'])
        self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-STALE')
        self.assert_completion_blocked(session)

    def test_classic_and_nonjournal_source_complete_through_delivery_and_cli(self):
        session, result, evidence = self.setup_review()
        result['bibliography_review']['sources'][0]['source_type'] = 'book / historical monograph'
        ingest_review(session, result, evidence)
        reflection, host = fixture.complete_child(session)
        reflection['bibliography_review'] = copy.deepcopy(result['bibliography_review'])
        ingest_review(session, reflection, host)
        completed = coordinator.deliver(session, self.root / 'final.md')
        self.assertTrue(completed['task_complete'])
        self.assertEqual(completed['bibliography_status'], 'assessed')
        self.assertEqual(fixture.verify_cli(session)[0], 0)
        (self.root / 'final.md').write_text(MANUSCRIPT + '\n[2] Added, B. (2026). New work.', encoding='utf-8')
        self.assertNotEqual(fixture.verify_cli(session)[0], 0)

    def test_historical_source_cannot_clear_current_gap(self):
        session, result, evidence = self.setup_review()
        result['bibliography_review']['source_support'][0]['role'] = 'research_gap'
        self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-CURRENCY')

    def test_pre_1900_classic_is_not_rejected_for_its_age(self):
        session, result, evidence = self.setup_review(MANUSCRIPT.replace('1970', '1850'))
        self.assertEqual(ingest_review(session, result, evidence)['request']['phase'], 'reflection')

    def test_indirect_source_cannot_masquerade_as_primary(self):
        session, result, evidence = self.setup_review()
        result['bibliography_review']['sources'][0]['material_kind'] = 'secondary'
        self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-INDIRECT')

    def test_explicitly_indirect_use_is_admissible(self):
        text = MANUSCRIPT.replace('The original framework', 'As summarized in the review, the original framework')
        session, result, evidence = self.setup_review(text)
        result['bibliography_review']['sources'][0]['material_kind'] = 'secondary'
        row = result['bibliography_review']['source_support'][0]
        row.update(directness='indirect', indirection_marker='As summarized in the review')
        self.assertEqual(ingest_review(session, result, evidence)['request']['phase'], 'reflection')

    def test_unverified_constructed_identity_is_not_admitted(self):
        session, result, evidence = self.setup_review()
        result['bibliography_review']['sources'][0]['identity_status'] = 'constructed'
        self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-UNVERIFIED')

    def test_unassessed_reference_and_use_are_individually_blocking(self):
        text = MANUSCRIPT.replace('[1].', '[1, 2].') + '\n[2] Another, B. (2026). Another account.\n'
        for field in ('sources', 'source_support'):
            with self.subTest(field=field):
                session, result, evidence = self.setup_review(text)
                result['bibliography_review'][field].pop()
                self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-COVERAGE')

    def test_repeated_citation_needs_separate_support(self):
        text = MANUSCRIPT.replace('# References', 'A broader universal claim is also attributed to it [1].\n\n# References')
        session, result, evidence = self.setup_review(text)
        result['bibliography_review']['source_support'].pop()
        self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-COVERAGE')

    def test_reference_claim_and_attachment_changes_stale_prior_review(self):
        _, original, _ = self.setup_review()
        for text in (MANUSCRIPT + '\n[2] Another, B. (2026). Added reference.\n',
                     MANUSCRIPT.replace('recording from approval', 'recording from approval and proved universal effectiveness'),
                     MANUSCRIPT.replace('A foundational framework', 'A different framework')):
            session, result, evidence = self.setup_review(text)
            result['bibliography_review'] = copy.deepcopy(original['bibliography_review'])
            self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-STALE')

    def test_pure_renumbering_reuses_exact_assessments(self):
        _, original, _ = self.setup_review()
        session, result, evidence = self.setup_review(MANUSCRIPT.replace('[1]', '[19]'))
        result['bibliography_review'] = copy.deepcopy(original['bibliography_review'])
        # Both source files have identical content and locator; source ID is stable.
        self.assertEqual(ingest_review(session, result, evidence)['request']['phase'], 'reflection')

    def test_prose_only_completion_explicitly_does_not_clear_bibliography(self):
        session, result, evidence = self.setup_review(scope='prose_only')
        self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-SCOPE')
        result.pop('bibliography_review')
        ingest_review(session, result, evidence)
        fixture.ingest_child(session)
        completed = coordinator.deliver(session, self.root / 'prose-only.md')
        self.assertTrue(completed['task_complete'])
        self.assertEqual(completed['bibliography_status'], 'not_assessed_prose_only')

    def test_missing_assessment_and_reflector_omission_do_not_clear(self):
        session, result, evidence = self.setup_review()
        original = result.pop('bibliography_review')
        self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-UNASSESSED')
        result['bibliography_review'] = original
        ingest_review(session, result, evidence)
        reflection, host = fixture.complete_child(session)
        self.assert_refused(reflection, host, session, 'BIBLIOGRAPHY-UNASSESSED')

    def test_unresolved_check_is_recordable_but_blocks_dependent_completion(self):
        session, result, evidence = self.setup_review()
        result.pop('bibliography_review')
        next(x for x in result['checks'] if x['id'] == 'bibliography')['status'] = 'unavailable'
        response = ingest_review(session, result, evidence)
        self.assertEqual(response['status'], 'needs_revision')
        self.assertFalse(fixture.verify_cli(session)[1]['task_complete'])

    def test_advisor_guidance_needs_verified_communication_and_style_treatment(self):
        text = MANUSCRIPT.replace('Example, A. (1970). A foundational framework.', 'Advisor, A. (2026). Personal communication.')
        session, result, evidence = self.setup_review(text)
        self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-COMMUNICATION')

    def test_inline_personal_communication_is_supported_when_explicitly_verified(self):
        text = '# Note\n\nThe participant clarified the scope (A. Example, personal communication, September 18, 2026).\n'
        confirmation = 'Synthetic user confirmation: A. Example clarified the scope on September 18, 2026.'
        session, result, evidence = self.setup_review(text, source_text=confirmation)
        source = result['bibliography_review']['sources'][0]
        source.update(material_kind='personal_communication', communication_provenance='explicit_user_confirmation',
                      identity_status='user_confirmed', attribution='Synthetic confirmation of speaker and date in this fixture.',
                      citation_style='APA-style in-text communication for this synthetic fixture.',
                      style_treatment='In-text only; no invented title or publication status.')
        source['communication_record'] = {'source_id': 'S1', 'locator': 'paragraph 1', 'quote': confirmation,
                                          'speaker': 'A. Example', 'date': 'September 18, 2026'}
        result['bibliography_review']['source_support'][0]['directness'] = 'personal_communication'
        self.assertEqual(ingest_review(session, result, evidence)['request']['phase'], 'reflection')

    def test_unsupported_syntax_is_not_silently_cleared(self):
        session, result, evidence = self.setup_review(MANUSCRIPT.replace('[1].', r'\cite{example}.'))
        self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-INVENTORY')

    def test_source_change_and_missing_challenging_search_remain_unresolved(self):
        session, result, evidence = self.setup_review()
        result['bibliography_review']['source_support'][0]['discovery']['challenging_evidence'] = ''
        self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-JUDGMENT-MISSING')
        result['bibliography_review']['source_support'][0]['discovery']['challenging_evidence'] = 'No contemporary gap is asserted; the bounded fixture includes a limiting sentence.'
        result['bibliography_review']['sources'][0]['inspected'][0]['sha256'] = '0' * 64
        self.assert_refused(result, evidence, session, 'BIBLIOGRAPHY-MATERIAL')


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
