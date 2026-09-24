#!/usr/bin/env python3
"""Negative controls for the argument-coherence obligation.

These fixtures prove the *enforcement*: that a missing, incomplete, stale,
replayed, fabricated, or self-serving coherence review cannot produce a reviewed
completion, and that no caller can suppress the check. They prove nothing about
judgment quality. Semantic detection is measured separately against the seeded
fixtures in `scripts/fixtures/golden/` and scored by
`scripts/eval/golden_eval_score.py`; see
`docs/evaluation/argument-coherence-baseline.md`.

Two layers:

* unit controls exercise `coherence_review.validate` directly;
* route controls drive the real `piw_coordinator` state machine with synthetic
  host traces, reusing `piw_acceptance_smoketest`'s fixture harness.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import coherence_fixture_support as fixture  # noqa: E402
import coherence_prefilter as prefilter  # noqa: E402
import coherence_review as coherence  # noqa: E402
import piw_acceptance_smoketest as acceptance  # noqa: E402
import piw_coordinator as coordinator  # noqa: E402
import piw_completion_guard as guard  # noqa: E402
import piw_session as piw  # noqa: E402

RESULTS: list[dict] = []

SAMPLE = (
    "## Method\n\n"
    "This study asks how maintenance teams decide which alerts to escalate. "
    "The dataset was assembled from three sites over eleven months. "
    "Escalation therefore tracks sensor confidence rather than severity.\n\n"
    "The instrument scores each alert on four dimensions. "
    "Scoring happens at the point of triage.\n\n"
    "Unresolved alerts stay outside the confidence estimate.\n"
)


def record(name, passed, detail=None):
    RESULTS.append({'case': name, 'passed': bool(passed), 'detail': detail})
    print(('PASS ' if passed else 'FAIL ') + name + ((': ' + str(detail)) if detail else ''))


def expect_code(name, expected, callable_, *args, **kwargs):
    try:
        callable_(*args, **kwargs)
    except coherence.ReviewError as exc:
        record(name, exc.code == expected, {'code': exc.code, 'expected': expected})
        return
    except piw.PIWError as exc:  # route controls surface the same codes
        record(name, exc.code == expected, {'code': exc.code, 'expected': expected})
        return
    except Exception as exc:  # noqa: BLE001 - a crash is a failed control
        record(name, False, {'raised': type(exc).__name__, 'message': str(exc)})
        return
    record(name, False, {'code': None, 'expected': expected})


def expect_ok(name, callable_, *args, **kwargs):
    try:
        callable_(*args, **kwargs)
    except (coherence.ReviewError, piw.PIWError) as exc:
        record(name, False, {'unexpected_refusal': getattr(exc, 'code', ''), 'message': str(exc)})
        return
    except Exception as exc:  # noqa: BLE001 - a crash is a failed control
        record(name, False, {'raised': type(exc).__name__, 'message': str(exc)})
        return
    record(name, True)


# ---------------------------------------------------------------- unit controls

def unit_controls():
    good = fixture.build(SAMPLE)
    expect_ok('positive_control_valid_review_clears',
              coherence.validate, SAMPLE, good, require_clear=True)

    # Missing review entirely.
    expect_code('missing_review', 'COHERENCE-REVIEW-MISSING',
                coherence.validate, SAMPLE, None)

    # Incomplete coverage: a required unit dropped.
    short = copy.deepcopy(good)
    dropped = short['scope']['covered_unit_ids'].pop()
    short['units'] = [u for u in short['units'] if u['unit_id'] != dropped]
    expect_code('incomplete_coverage', 'COHERENCE-COVERAGE-INCOMPLETE',
                coherence.validate, SAMPLE, short)

    # A changed unit's neighbour is required even though it was not edited.
    edited = SAMPLE.replace('Scoring happens at the point of triage.',
                            'Scoring happens at the point of triage by the reviewer.')
    changed = prefilter.changed_unit_ids(SAMPLE, edited)
    needed, _, neighbours = coherence.required_units(edited, changed)
    record('neighbours_are_required_coverage',
           bool(neighbours) and set(changed) < set(needed),
           {'changed': changed, 'required': needed})
    only_changed = fixture.build(edited, changed)
    only_changed['scope']['covered_unit_ids'] = list(changed)
    only_changed['units'] = [u for u in only_changed['units'] if u['unit_id'] in set(changed)]
    expect_code('changed_unit_without_neighbours', 'COHERENCE-COVERAGE-INCOMPLETE',
                coherence.validate, edited, only_changed, changed_unit_ids=changed)

    # Replay: a review of the previous candidate presented for the new one.
    expect_code('replayed_review_from_earlier_candidate', 'COHERENCE-REVIEW-STALE',
                coherence.validate, edited, good, changed_unit_ids=changed)

    # Context drift: the candidate moved after the review was produced.
    expect_code('candidate_changed_after_review', 'COHERENCE-REVIEW-STALE',
                coherence.validate, SAMPLE, good,
                candidate_sha256='0' * 64)

    # Unit-level drift: right document, wrong unit bytes.
    tampered = copy.deepcopy(good)
    tampered['units'][0]['sha256'] = '0' * 64
    expect_code('unit_hash_drift', 'COHERENCE-REVIEW-STALE',
                coherence.validate, SAMPLE, tampered)

    # Fabricated sentence coverage: a sentence that is not in the unit.
    invented = copy.deepcopy(good)
    invented['units'][0]['sentences'].append(
        {'text': 'The instrument was validated against an external corpus.',
         'contribution': 'supports', 'finding_id': None})
    expect_code('invented_sentence_coverage', 'COHERENCE-SENTENCE-EVIDENCE-MISSING',
                coherence.validate, SAMPLE, invented)

    # Skipped sentence: partition is not exact.
    skipped = copy.deepcopy(good)
    skipped['units'][0]['sentences'] = skipped['units'][0]['sentences'][:-1]
    expect_code('skipped_sentence_coverage', 'COHERENCE-SENTENCE-EVIDENCE-MISSING',
                coherence.validate, SAMPLE, skipped)

    # A role label is not a determined purpose.
    label = copy.deepcopy(good)
    label['units'][0]['purpose'] = 'Motivation paragraph.'
    expect_code('role_label_is_not_a_purpose', 'COHERENCE-PURPOSE-MISSING',
                coherence.validate, SAMPLE, label)

    # A finding quoting bytes that are not in the candidate.
    fabricated = copy.deepcopy(good)
    fabricated['findings'] = [{
        'id': 'AC-x1', 'class': 'AC-1', 'relationship': 'broken_bridge',
        'passage': 'A sentence that appears nowhere in the reviewed document.',
        'locator': 'u000', 'effect': 'The reader loses the premise for the conclusion.',
        'remedy': 'Move the aside out of the bridge or draw its consequence.',
        'requires_unstated_premise': False, 'blocking': True}]
    fabricated['outcome'] = 'changes_required'
    expect_code('finding_quotes_absent_passage', 'COHERENCE-PASSAGE-UNBOUND',
                coherence.validate, SAMPLE, fabricated)

    # A finding that needs a premise the author never made.
    invented_premise = copy.deepcopy(good)
    invented_premise['findings'] = [{
        'id': 'AC-x2', 'class': 'AC-2', 'relationship': 'answers_other_question',
        'passage': 'Scoring happens at the point of triage.',
        'locator': 'u001', 'effect': 'The paragraph purpose is not served by this sentence.',
        'remedy': 'State the scoring timing consequence the paragraph needs.',
        'requires_unstated_premise': True, 'blocking': True}]
    invented_premise['outcome'] = 'changes_required'
    expect_code('remedy_requires_invented_premise', 'COHERENCE-PREMISE-INVENTED',
                coherence.validate, SAMPLE, invented_premise)

    # A blocking finding cannot coexist with a clean outcome.
    misreported = copy.deepcopy(good)
    misreported['findings'] = [{
        'id': 'AC-x3', 'class': 'AC-1', 'relationship': 'broken_bridge',
        'passage': 'The dataset was assembled from three sites over eleven months.',
        'locator': 'u000', 'effect': 'The therefore-conclusion no longer has an adjacent premise.',
        'remedy': 'Draw the consequence of the dataset sentence or move it.',
        'requires_unstated_premise': False, 'blocking': True}]
    misreported['outcome'] = 'review_complete'
    expect_code('blocking_finding_reported_as_complete', 'COHERENCE-OUTCOME-INVALID',
                coherence.validate, SAMPLE, misreported)

    # A failed review cannot clear a passing check.
    unclear = copy.deepcopy(misreported)
    unclear['outcome'] = 'changes_required'
    expect_code('changes_required_cannot_clear_a_pass', 'COHERENCE-NOT-CLEARED',
                coherence.validate, SAMPLE, unclear, require_clear=True)
    expect_ok('changes_required_is_valid_when_not_clearing',
              coherence.validate, SAMPLE, unclear)

    # Out-of-scope inspection confers no write authority.
    widened = copy.deepcopy(good)
    widened['out_of_scope_observations'] = [{
        'passage': 'Unresolved alerts stay outside the confidence estimate.',
        'locator': 'u002', 'confers_write_authority': True}]
    expect_code('inspection_does_not_widen_write_scope', 'COHERENCE-SCOPE-INVALID',
                coherence.validate, SAMPLE, widened)

    # A user exception is never a semantic pass.
    exception = copy.deepcopy(good)
    exception['user_exception'] = {'authority': 'user said proceed', 'semantic_pass': True}
    expect_code('user_exception_is_not_a_semantic_pass', 'COHERENCE-EXCEPTION-INVALID',
                coherence.validate, SAMPLE, exception)

    # A no-change run still owes a full-scope review, not an empty one.
    needed_nochange, changed_nochange, _ = coherence.required_units(SAMPLE, [])
    record('no_change_run_requires_full_scope_coverage',
           needed_nochange == [u['unit_id'] for u in prefilter.units_for(SAMPLE)]
           and changed_nochange == [],
           {'required': needed_nochange})

    # A commitment in a changed unit must have its occurrences reported.
    promised = SAMPLE.replace(
        'The instrument scores each alert on four dimensions.',
        'We will deliver an instrument that scores each alert on four dimensions.')
    promised_changed = prefilter.changed_unit_ids(SAMPLE, promised)
    silent = fixture.build(promised, promised_changed)
    silent['commitment_occurrences'] = []
    expect_code('commitment_change_without_occurrence_check', 'COHERENCE-COMMITMENT-UNCHECKED',
                coherence.validate, promised, silent, changed_unit_ids=promised_changed)

    # The validator reports what it does and does not establish.
    summary = coherence.validate(SAMPLE, good, require_clear=True)
    record('validation_disclaims_semantic_correctness',
           summary['does_not_establish'].startswith('semantic correctness'),
           summary['does_not_establish'])

    # The pre-filter never reaches a verdict.
    record('prefilter_reaches_no_verdict',
           prefilter.inventory(SAMPLE)['judgment'] == 'not_performed')


# --------------------------------------------------------------- route controls

def route_controls():
    # A multi-paragraph scope, so a coverage control can actually narrow coverage.
    wide = '\n'.join([
        '# Example manuscript',
        '',
        '## Anchor',
        'The term "request" denotes a submitted item, not an approval. [Anchor-A]',
        '',
        '## Scope',
        'Each reviewer examine one request.',
        '',
        'The queue record the decision after the review.',
        '',
        'Unresolved requests remain in the queue.',
        '',
    ]).encode('utf-8')
    wide_revised = wide.replace(b'reviewer examine', b'reviewer examines')

    def run_case(name, expected_code, mutate, *, fixture_bytes=None, artifact=None):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            session, request = acceptance.setup(
                tmp, revision=True, fixture=fixture_bytes or acceptance.FIXTURE)
            coordinator.start(session, request)
            acceptance.ingest_child(session, artifact=artifact)   # diagnosis
            acceptance.plan(session)
            acceptance.ingest_child(session, artifact=artifact)   # generation
            try:
                acceptance.ingest_child(session, mutate=mutate)   # evaluation
            except piw.PIWError as exc:
                record(name, exc.code == expected_code,
                       {'code': exc.code, 'expected': expected_code})
                return
            record(name, False, {'code': None, 'expected': expected_code})

    def drop_review(result, req, contract):
        result.pop('coherence_review', None)

    def drop_check(result, req, contract):
        result['checks'] = [x for x in result['checks'] if x['id'] != 'argument_coherence']

    def mark_not_applicable(result, req, contract):
        for check in result['checks']:
            if check['id'] == 'argument_coherence':
                check['status'] = 'not_applicable'

    def mark_unavailable(result, req, contract):
        for check in result['checks']:
            if check['id'] == 'argument_coherence':
                check['status'] = 'unavailable'

    def narrow_coverage(result, req, contract):
        review = result['coherence_review']
        keep = review['scope']['covered_unit_ids'][:1]
        review['scope']['covered_unit_ids'] = keep
        review['units'] = [u for u in review['units'] if u['unit_id'] in set(keep)]

    def replay_other_bytes(result, req, contract):
        result['coherence_review'] = fixture.build('## Other\n\nEntirely different bytes here.\n')

    def pass_while_failing(result, req, contract):
        review = result['coherence_review']
        unit = review['units'][0]
        review['findings'] = [{
            'id': 'AC-r1', 'class': 'AC-2', 'relationship': 'answers_other_question',
            'passage': unit['sentences'][0]['text'], 'locator': unit['unit_id'],
            'effect': 'The sentence does not serve the purpose stated for this paragraph.',
            'remedy': 'Move the sentence to the paragraph whose question it answers.',
            'requires_unstated_premise': False, 'blocking': True}]
        review['outcome'] = 'review_complete'

    run_case('route_missing_coherence_review', 'COHERENCE-REVIEW-MISSING', drop_review)
    run_case('route_check_omitted_from_results', 'PIW-CHECK-EVIDENCE-MISSING', drop_check)
    run_case('route_check_marked_not_applicable', 'COHERENCE-REVIEW-MISSING', mark_not_applicable)
    run_case('route_check_marked_unavailable', 'COHERENCE-REVIEW-MISSING', mark_unavailable)
    run_case('route_partial_coverage', 'COHERENCE-COVERAGE-INCOMPLETE', narrow_coverage,
             fixture_bytes=wide, artifact=wide_revised)
    run_case('route_review_of_other_bytes', 'COHERENCE-REVIEW-STALE', replay_other_bytes)
    run_case('route_blocking_finding_reported_clean', 'COHERENCE-OUTCOME-INVALID', pass_while_failing)

    # The check cannot be suppressed by a narrower required_checks list, by an
    # exclusion, or by declaring the pass prose-only.
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        session, request = acceptance.setup(tmp, revision=True)
        request['required_checks'] = [{'id': 'grammar', 'required': True}]
        request['review_scope'] = 'prose_only'
        request['exclusions'] = ['argument_coherence', 'chung-academic-voice-pass']
        coordinator.start(session, request)
        packet = coordinator.next_step(session)
        ids = [x['id'] for x in packet['request']['required_checks']]
        record('check_is_not_caller_suppressible', 'argument_coherence' in ids, ids)
        record('child_request_carries_coverage_denominator',
               packet['request']['coherence_scope']['coverage_denominator'] > 0
               and bool(packet['request']['coherence_instruction']),
               packet['request']['coherence_scope'].get('coverage_denominator'))

    # A clean run completes, and completion reports the obligation honestly.
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        session, request = acceptance.setup(tmp, revision=True)
        completion = acceptance.finish(session, request)
        record('clean_run_completes', completion.get('task_complete') is True,
               completion.get('code'))
        record('completion_reports_coherence_without_claiming_correctness',
               completion.get('coherence_status') == 'reviewed_on_delivered_bytes'
               and completion['coherence']['semantic_correctness_established'] is False,
               completion.get('coherence_status'))
        record('completion_remains_non_terminal',
               completion.get('lifecycle_terminal') is False
               and completion.get('research_acceptance') is False)

        # Tampering with the delivered bytes after the review invalidates it.
        candidate = Path(json.loads((Path(session) / 'binding/delivery.json')
                                    .read_text(encoding='utf-8'))['candidate']['path'])
        candidate.write_bytes(candidate.read_bytes() + b'\nAn unreviewed sentence appended after the review.\n')
        after = guard.verify_completion(session)
        record('post_review_edit_refuses_completion',
               after.get('task_complete') is False, after.get('code'))


# ------------------------------------------------ independent source review

def guarded(name, check):
    """Record a control whose failure mode may be an exception, not a result."""
    try:
        passed, detail = check()
    except Exception as exc:  # noqa: BLE001 - a crash is a failed control
        record(name, False, {'raised': type(exc).__name__, 'message': str(exc)})
        return
    record(name, passed, detail)


def _unit_id_starting(text, prefix):
    return next(u['unit_id'] for u in prefilter.inventory(text)['units']
                if u['text'].startswith(prefix))


def source_review_controls():
    """Controls written from the independent source review of 2718107.

    Each reproduces an acceptance mechanism the reviewer found, from invented
    text, before the production code changed. A control named here must fail on
    the code it was written against and pass once the finding is fixed.
    """
    # F2 -- a deletion plus a distant edit must not drop the deletion's neighbour.
    paragraphs = [
        'The board sets two conditions for the route: ridership above a floor and a funded operator.',
        'Both conditions must hold before the board approves the route.',
        'Parking policy in the district is reviewed every spring.',
        'Cycling lanes near the school are widened next year.',
        'The consultation closes at the end of the month.',
    ]
    before = '\n\n'.join(paragraphs) + '\n'
    after = '\n\n'.join(paragraphs[1:4] + ['The consultation ends at the end of the month.']) + '\n'

    def deletion_neighbour():
        changed = prefilter.changed_unit_ids(before, after)
        needed, _, _ = coherence.required_units(after, changed)
        both = _unit_id_starting(after, 'Both conditions')
        return both in needed, {'changed': changed, 'needed': needed, 'expected': both}
    guarded('deletion_plus_distant_edit_requires_surviving_neighbour', deletion_neighbour)
    guarded('unchanged_text_has_no_changed_units',
            lambda: (prefilter.changed_unit_ids(before, before) == [], None))

    duplicated = before + '\n' + paragraphs[3] + '\n'

    def repeated_insertion():
        changed = prefilter.changed_unit_ids(before, duplicated)
        return changed == ['u005'], changed
    guarded('repeated_paragraph_insertion_is_a_change', repeated_insertion)

    moved = '\n\n'.join([paragraphs[0], paragraphs[1], paragraphs[3], paragraphs[4], paragraphs[2]]) + '\n'

    def move_disturbs_old_neighbours():
        changed = prefilter.changed_unit_ids(before, moved)
        needed, _, _ = coherence.required_units(moved, changed)
        both = _unit_id_starting(moved, 'Both conditions')
        cycling = _unit_id_starting(moved, 'Cycling lanes')
        return {both, cycling} <= set(needed), {'changed': changed, 'needed': needed}
    guarded('moved_paragraph_requires_its_old_neighbours', move_disturbs_old_neighbours)

    # F3 -- a section write scope must not truncate the read context.
    original = ('## Method\n\nWe compare interviews and records.\n\n'
                '## Analysis\n\nThe second source checks the first.\n\n'
                'Disagreements are resolved by a third reading.\n').encode('utf-8')
    revised = original.replace(b'We compare interviews and records.', b'We examine records.')

    def cross_section_neighbour():
        files = {'original.bin': original, 'candidate.md': revised}
        scope = coordinator._scope(original, {'description': 'method only', 'section': 'Method'})
        contract = {'requested_scope': scope,
                    'input_snapshot': {'path': 'original.bin', 'bytes': len(original)}}
        out = coordinator.coherence_scope(contract, {'path': 'candidate.md'}, 'evaluation',
                                          read_bytes=files.__getitem__)
        text, changed = out[0], out[1]
        kwargs = {'scope_unit_ids': out[2]} if len(out) > 2 else {}
        needed, _, _ = coherence.required_units(text, changed, **kwargs)
        analysis = _unit_id_starting(text, 'The second source') \
            if 'The second source' in text else None
        return analysis is not None and analysis in needed, {
            'needed': needed, 'analysis_unit': analysis,
            'analysis_in_read_context': 'The second source' in text}
    guarded('section_edit_requires_cross_section_neighbour', cross_section_neighbour)

    def section_diagnosis_keeps_write_scope():
        files = {'original.bin': original, 'candidate.md': original}
        scope = coordinator._scope(original, {'description': 'method only', 'section': 'Method'})
        contract = {'requested_scope': scope,
                    'input_snapshot': {'path': 'original.bin', 'bytes': len(original)}}
        out = coordinator.coherence_scope(contract, {'path': 'candidate.md'}, 'diagnosis',
                                          read_bytes=files.__getitem__)
        kwargs = {'scope_unit_ids': out[2]} if len(out) > 2 else {}
        needed, _, _ = coherence.required_units(out[0], out[1], **kwargs)
        last = _unit_id_starting(out[0], 'Disagreements') if 'Disagreements' in out[0] else None
        # The section plus its boundary neighbour, not the whole document.
        return last is not None and last not in needed, {'needed': needed}
    guarded('section_review_stays_bounded_by_its_neighbours', section_diagnosis_keeps_write_scope)

    # F4 -- one record may not conceal several sentences.
    three = 'A survey records demand. A pilot tests delivery. The report recommends expansion.\n'

    def collapse():
        review = fixture.build(three)
        unit = review['units'][0]
        unit['sentences'] = [{'text': ' '.join(s['text'] for s in unit['sentences']),
                              'contribution': 'advances', 'finding_id': None}]
        return review
    expect_code('multi_sentence_record_is_rejected', 'COHERENCE-SENTENCE-MERGED',
                lambda: coherence.validate(three, collapse()))

    titled = 'Dr. Lee reviewed the queue before noon. It cleared by evening.\n'
    expect_ok('abbreviation_is_not_a_sentence_boundary',
              lambda: coherence.validate(titled, fixture.build(titled)))

    ambiguous = 'The pilot ran until Jan. Riders returned in March.\n'

    def declared_merge(token, reason):
        review = fixture.build(ambiguous)
        unit = review['units'][0]
        unit['sentences'] = [{'text': ambiguous.strip(), 'contribution': 'advances',
                              'finding_id': None,
                              'merged_boundaries': [{'after': token, 'reason': reason}]}]
        return review
    expect_ok('declared_abbreviation_merge_is_accepted',
              lambda: coherence.validate(ambiguous, declared_merge(
                  'Jan.', 'Jan. abbreviates January here; the pilot ran until January riders returned.')))

    def false_merge():
        review = fixture.build(three)
        unit = review['units'][0]
        unit['sentences'] = [{'text': three.strip(), 'contribution': 'advances', 'finding_id': None,
                              'merged_boundaries': [
                                  {'after': 'demand.', 'reason': 'Claimed abbreviation that is a word.'},
                                  {'after': 'delivery.', 'reason': 'Claimed abbreviation that is a word.'}]}]
        return review
    expect_code('ordinary_word_cannot_be_declared_an_abbreviation', 'COHERENCE-SENTENCE-MERGED',
                lambda: coherence.validate(three, false_merge()))

    # F5 -- both coherence authorities are bound, read and drift-checked.
    def rules_bound():
        names = {Path(r['path']).name for r in piw.rule_bindings([], [])}
        return {'ARGUMENT_COHERENCE.md', 'SAFEGUARD_LAYER.md'} <= names, sorted(names)
    guarded('coherence_rules_bound_without_optional_passes', rules_bound)

    def rule_drift(name):
        with tempfile.TemporaryDirectory() as raw:
            session, request = acceptance.setup(Path(raw), revision=True)
            request['passes'] = []
            completion = acceptance.finish(session, request)
            if completion.get('task_complete') is not True:
                return False, {'baseline_not_complete': completion.get('code')}
            real = coordinator._read_bytes
            target = piw.ROOT / 'references' / name

            def virtual(path):
                data = real(path)
                if Path(path).resolve() == target.resolve():
                    return data.replace(b'Check 9', b'Check 9 and stated limits', 1) + b'\n'
                return data
            coordinator._read_bytes = virtual
            try:
                after = guard.verify_completion(session)
            finally:
                coordinator._read_bytes = real
            return after.get('task_complete') is False, after.get('code')
    guarded('argument_coherence_rule_drift_refuses_completion',
            lambda: rule_drift('ARGUMENT_COHERENCE.md'))
    guarded('safeguard_layer_rule_drift_refuses_completion',
            lambda: rule_drift('SAFEGUARD_LAYER.md'))
    guarded('bound_rule_drift_refuses_completion_control',
            lambda: rule_drift('GROUNDING_PROTOCOL.md'))

    # F6 -- commitments need explicit, located assessment.
    fresh = 'This study will compare bus wait times in two districts.\n'

    def emptied(text, changed=None):
        review = fixture.build(text, changed)
        review['commitment_occurrences'] = []
        return review
    expect_code('fresh_commitment_requires_assessment', 'COHERENCE-COMMITMENT-UNCHECKED',
                lambda: coherence.validate(fresh, emptied(fresh)))

    before_def = 'A case means one trip.\n\nCases are counted per district.\n'
    after_def = 'A case means one completed trip.\n\nCases are counted per district.\n'
    changed_def = prefilter.changed_unit_ids(before_def, after_def)
    expect_code('changed_definition_requires_assessment', 'COHERENCE-COMMITMENT-UNCHECKED',
                lambda: coherence.validate(after_def, emptied(after_def, changed_def),
                                           changed_unit_ids=changed_def))

    def absent_key():
        review = fixture.build(fresh)
        review.pop('commitment_occurrences', None)
        return review
    expect_code('commitment_assessment_cannot_be_omitted', 'COHERENCE-COMMITMENT-UNCHECKED',
                lambda: coherence.validate(fresh, absent_key()))

    def false_locator():
        review = fixture.build(fresh)
        review['commitment_occurrences'] = [{
            'commitment': 'This study will compare bus wait times in two districts.',
            'unit_id': 'u000', 'status': 'carried',
            'assessment': 'Otherwise valid row; only the locator is under test.',
            'occurrence_locators': ['unit u999, line 999999']}]
        return review
    expect_code('nonexistent_occurrence_locator_is_rejected', 'COHERENCE-PASSAGE-UNBOUND',
                lambda: coherence.validate(fresh, false_locator()))

    def misquoted_locator():
        review = fixture.build(fresh)
        review['commitment_occurrences'] = [{
            'commitment': 'This study will compare bus wait times in two districts.',
            'unit_id': 'u000', 'status': 'carried',
            'assessment': 'Otherwise valid row; only the locator is under test.',
            'occurrence_locators': [{'unit_id': 'u000', 'quote': 'wait times in four districts'}]}]
        return review
    expect_code('occurrence_quote_must_occur_in_named_unit', 'COHERENCE-PASSAGE-UNBOUND',
                lambda: coherence.validate(fresh, misquoted_locator()))
    expect_ok('fixture_commitment_assessment_validates',
              lambda: coherence.validate(fresh, fixture.build(fresh)))


def main() -> int:
    unit_controls()
    route_controls()
    source_review_controls()
    failed = [r for r in RESULTS if not r['passed']]
    print(json.dumps({'passed': len(RESULTS) - len(failed), 'failed': len(failed),
                      'establishes': 'enforcement of the coherence obligation',
                      'does_not_establish': 'judgment quality; see docs/evaluation/argument-coherence-baseline.md'}))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
