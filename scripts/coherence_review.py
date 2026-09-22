"""Argument-coherence evidence validation, shared by both enforcement routes.

This module checks that a coherence review was **executed against these exact
bytes and covered the scope it claims**. It never checks whether the reviewer
read the paragraph's purpose correctly or whether a finding is right. Passing
validation means the obligation in `references/ARGUMENT_COHERENCE.md` was run
and dispositioned, not that the prose is coherent. Section 6 of that file states
this limit; nothing downstream may report it otherwise.

Anti-fabrication is the point of the exact-partition rule below: a unit's
supplied sentence texts must reconstruct the unit's own text, and every quoted
passage must occur in the candidate. A review copied from other bytes, replayed
from an earlier candidate, or written from a summary cannot satisfy either.
"""
from __future__ import annotations

import coherence_prefilter as prefilter

CONTRIBUTIONS = ('advances', 'supports', 'qualifies', 'background', 'transition', 'none')
CLASSES = ('AC-1', 'AC-2', 'AC-3', 'AC-4', 'AC-5')
RELATIONSHIPS = ('purpose_unrecoverable', 'no_contribution', 'answers_other_question',
                 'unexplained_meaning_change', 'promise_without_payoff', 'broken_bridge',
                 'disconnected_neighbour')
OUTCOMES = ('review_complete', 'changes_required', 'review_incomplete')
COMMITMENT_STATUS = ('carried', 'uncarried', 'not_applicable')

MIN_PURPOSE = 40
MIN_PROSE = 20


class ReviewError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def require(condition, code, message):
    if not condition:
        raise ReviewError(code, message)


def normalized(text):
    return ' '.join(str(text).split())


def _text(value, minimum, code, message):
    require(isinstance(value, str) and len(value.strip()) >= minimum, code, message)
    return value


def required_units(candidate_text, changed_unit_ids=None, *, neighbour_radius=1):
    """Units a review must cover: changed units plus their immediate neighbours.

    `changed_unit_ids=None` means no prior version was bound (a fresh draft) and
    an empty list means nothing changed; in both cases every prose unit in the
    requested scope is required. A no-change run still owes a review explaining
    why the unchanged bytes satisfy the request, and an empty denominator would
    make that review vacuous. Neighbours are required because AC-5 is
    unreachable from the changed bytes alone.
    """
    units = prefilter.units_for(candidate_text)
    ids = [u['unit_id'] for u in units]
    if not changed_unit_ids:
        return ids, list(changed_unit_ids or []), []
    changed = [x for x in ids if x in set(changed_unit_ids)]
    needed, neighbours = set(changed), set()
    for unit_id in changed:
        position = ids.index(unit_id)
        for offset in range(-neighbour_radius, neighbour_radius + 1):
            index = position + offset
            if 0 <= index < len(ids) and ids[index] not in needed:
                neighbours.add(ids[index])
    needed |= neighbours
    return [x for x in ids if x in needed], changed, [x for x in ids if x in neighbours]


def validate(candidate_text, review, *, changed_unit_ids=None, candidate_sha256=None,
             require_clear=False):
    """Validate one `coherence_review` object against the candidate bytes.

    Raises `ReviewError` with a stable code. Returns a summary of what was
    actually covered, for the caller's evidence record.
    """
    require(isinstance(review, dict), 'COHERENCE-REVIEW-MISSING',
            'Substantive prose review requires a coherence_review object '
            '(references/ARGUMENT_COHERENCE.md section 1)')

    inventory = prefilter.inventory(candidate_text)
    actual_sha = inventory['target_sha256']
    declared = review.get('candidate_sha256')
    require(declared == actual_sha, 'COHERENCE-REVIEW-STALE',
            'coherence_review is bound to other bytes than the reviewed candidate')
    if candidate_sha256 is not None:
        require(candidate_sha256 == actual_sha, 'COHERENCE-REVIEW-STALE',
                'Candidate bytes changed after the review was produced')

    by_id = {u['unit_id']: u for u in inventory['units']}
    needed, changed, neighbours = required_units(candidate_text, changed_unit_ids)

    scope = review.get('scope')
    require(isinstance(scope, dict), 'COHERENCE-SCOPE-MISSING',
            'coherence_review must declare its covered scope')
    covered = scope.get('covered_unit_ids')
    require(isinstance(covered, list) and covered and len(set(covered)) == len(covered),
            'COHERENCE-SCOPE-MISSING', 'Declare the distinct prose units actually covered')
    unknown = [x for x in covered if x not in by_id]
    require(not unknown, 'COHERENCE-SCOPE-INVALID',
            'Covered unit is not a prose unit of these bytes: ' + ', '.join(unknown))
    missing = [x for x in needed if x not in set(covered)]
    require(not missing, 'COHERENCE-COVERAGE-INCOMPLETE',
            'Changed units and their immediate neighbours must all be covered; missing: '
            + ', '.join(missing))
    require(set(scope.get('changed_unit_ids', changed)) == set(changed),
            'COHERENCE-SCOPE-INVALID', 'Declared changed units differ from the actual diff')

    units = review.get('units')
    require(isinstance(units, list) and len(units) == len(covered),
            'COHERENCE-UNIT-EVIDENCE-MISSING',
            'Supply one unit record for each covered unit')
    seen, findings_used = set(), set()
    for record in units:
        require(isinstance(record, dict), 'COHERENCE-UNIT-EVIDENCE-MISSING',
                'Each unit record must be an object')
        unit_id = record.get('unit_id')
        require(unit_id in by_id and unit_id in set(covered) and unit_id not in seen,
                'COHERENCE-UNIT-EVIDENCE-MISSING',
                'Unit record must name one distinct covered unit: ' + str(unit_id))
        seen.add(unit_id)
        unit = by_id[unit_id]
        require(record.get('sha256') == unit['sha256'], 'COHERENCE-REVIEW-STALE',
                'Unit record binds other bytes than the candidate unit: ' + unit_id)
        _text(record.get('purpose'), MIN_PURPOSE, 'COHERENCE-PURPOSE-MISSING',
              'State the paragraph purpose determined from the actual text, not a role '
              'label, for ' + unit_id)
        sentences = record.get('sentences')
        require(isinstance(sentences, list) and sentences,
                'COHERENCE-SENTENCE-EVIDENCE-MISSING',
                'Report every substantive sentence of ' + unit_id)
        texts = []
        for item in sentences:
            require(isinstance(item, dict) and isinstance(item.get('text'), str)
                    and item['text'].strip(), 'COHERENCE-SENTENCE-EVIDENCE-MISSING',
                    'Each sentence entry needs the verbatim sentence text in ' + unit_id)
            texts.append(normalized(item['text']))
            contribution = item.get('contribution')
            require(contribution in CONTRIBUTIONS, 'COHERENCE-SENTENCE-EVIDENCE-MISSING',
                    'Contribution must be one of ' + '/'.join(CONTRIBUTIONS)
                    + ' in ' + unit_id)
            if contribution == 'none':
                finding_id = item.get('finding_id')
                require(isinstance(finding_id, str) and finding_id.strip(),
                        'COHERENCE-FINDING-UNBOUND',
                        'A sentence contributing nothing requires a finding id in ' + unit_id)
                findings_used.add(finding_id)
        # Exact partition: the reported sentences must reconstruct the unit.
        require(' '.join(texts) == normalized(unit.get('text', '')),
                'COHERENCE-SENTENCE-EVIDENCE-MISSING',
                'Reported sentences must partition the unit text exactly, with nothing '
                'omitted, reordered or invented, in ' + unit_id)

    candidate_flat = normalized(candidate_text)
    covered_flat = {u: normalized(by_id[u].get('text', '')) for u in covered}
    findings = review.get('findings')
    require(isinstance(findings, list), 'COHERENCE-FINDINGS-MISSING',
            'Return findings or an explained empty list')
    ids = set()
    blocking = []
    for finding in findings:
        require(isinstance(finding, dict), 'COHERENCE-FINDINGS-MISSING',
                'Each finding must be an object')
        finding_id = finding.get('id')
        require(isinstance(finding_id, str) and finding_id.strip() and finding_id not in ids,
                'COHERENCE-FINDINGS-MISSING', 'Findings need distinct ids')
        ids.add(finding_id)
        require(finding.get('class') in CLASSES, 'COHERENCE-FINDINGS-MISSING',
                'Finding class must be one of ' + '/'.join(CLASSES) + ' for ' + finding_id)
        require(finding.get('relationship') in RELATIONSHIPS, 'COHERENCE-FINDINGS-MISSING',
                'Name the failed relationship for ' + finding_id)
        passage = _text(finding.get('passage'), 1, 'COHERENCE-FINDINGS-MISSING',
                        'Quote the exact passage for ' + finding_id)
        flat_passage = normalized(passage)
        require(flat_passage in candidate_flat, 'COHERENCE-PASSAGE-UNBOUND',
                'Quoted passage does not occur in the reviewed bytes: ' + finding_id)
        require(any(flat_passage in text for text in covered_flat.values()),
                'COHERENCE-PASSAGE-UNBOUND',
                'Finding quotes a unit that was not covered; report it under '
                'out_of_scope_observations instead: ' + finding_id)
        _text(finding.get('locator'), 1, 'COHERENCE-FINDINGS-MISSING',
              'Locate ' + finding_id)
        _text(finding.get('effect'), MIN_PROSE, 'COHERENCE-FINDINGS-MISSING',
              'State the effect on the argument, not the rule, for ' + finding_id)
        _text(finding.get('remedy'), MIN_PROSE, 'COHERENCE-FINDINGS-MISSING',
              'State a bounded remedy for ' + finding_id)
        require(finding.get('requires_unstated_premise') is False,
                'COHERENCE-PREMISE-INVENTED',
                'A finding whose explanation or remedy needs a premise the author never '
                'made is not a finding; report the relationship as unrecoverable: '
                + finding_id)
        require(isinstance(finding.get('blocking'), bool), 'COHERENCE-FINDINGS-MISSING',
                'Findings need an explicit blocking disposition: ' + finding_id)
        if finding['blocking']:
            blocking.append(finding_id)
    unbound = sorted(findings_used - ids)
    require(not unbound, 'COHERENCE-FINDING-UNBOUND',
            'Sentence marked as contributing nothing cites an absent finding: '
            + ', '.join(unbound))

    for observation in review.get('out_of_scope_observations', []) or []:
        require(isinstance(observation, dict)
                and normalized(observation.get('passage', '')) in candidate_flat
                and str(observation.get('locator', '')).strip(),
                'COHERENCE-PASSAGE-UNBOUND',
                'Out-of-scope observations still quote and locate actual bytes')
        require(observation.get('confers_write_authority') is False,
                'COHERENCE-SCOPE-INVALID',
                'Inspection beyond the write scope is a finding, never write authority')

    occurrences = review.get('commitment_occurrences', []) or []
    changed_commitment_units = [u for u in changed
                                if 'commitment' in by_id[u]['markers']]
    if changed_commitment_units:
        require(isinstance(occurrences, list) and occurrences,
                'COHERENCE-COMMITMENT-UNCHECKED',
                'A changed unit carries a research commitment; report that commitment\'s '
                'affected occurrences elsewhere in the document '
                '(references/ARGUMENT_COHERENCE.md section 5)')
    for row in occurrences:
        require(isinstance(row, dict), 'COHERENCE-COMMITMENT-UNCHECKED',
                'Each commitment row must be an object')
        commitment = normalized(row.get('commitment', ''))
        require(commitment and commitment in candidate_flat,
                'COHERENCE-PASSAGE-UNBOUND',
                'Quote the commitment as it occurs in the candidate')
        status = row.get('status')
        require(status in COMMITMENT_STATUS, 'COHERENCE-COMMITMENT-UNCHECKED',
                'Commitment status must be one of ' + '/'.join(COMMITMENT_STATUS))
        locators = row.get('occurrence_locators')
        require(isinstance(locators, list), 'COHERENCE-COMMITMENT-UNCHECKED',
                'List the commitment occurrences examined, empty if none exist')
        if status == 'carried':
            require(locators, 'COHERENCE-COMMITMENT-UNCHECKED',
                    'A carried commitment names where it is carried')
        if status == 'uncarried':
            require(row.get('finding_id') in ids, 'COHERENCE-FINDING-UNBOUND',
                    'An uncarried commitment requires an AC-4 finding')

    outcome = review.get('outcome')
    require(outcome in OUTCOMES, 'COHERENCE-OUTCOME-INVALID',
            'Outcome must be one of ' + '/'.join(OUTCOMES))
    if blocking:
        require(outcome == 'changes_required', 'COHERENCE-OUTCOME-INVALID',
                'Unresolved blocking coherence findings mean changes_required')
    if outcome == 'changes_required':
        require(blocking, 'COHERENCE-OUTCOME-INVALID',
                'changes_required needs a substantiated blocking finding')
    if require_clear:
        require(outcome == 'review_complete', 'COHERENCE-NOT-CLEARED',
                'A passing argument_coherence check requires outcome review_complete')

    exception = review.get('user_exception')
    if exception:
        require(isinstance(exception, dict) and str(exception.get('authority', '')).strip()
                and exception.get('semantic_pass') is False,
                'COHERENCE-EXCEPTION-INVALID',
                'A recorded user exception names its authority and is never a semantic pass')

    return {
        'schema': 'coherence-review-validation/v1',
        'candidate_sha256': actual_sha,
        'coverage_denominator': inventory['coverage_denominator'],
        'required_unit_ids': needed,
        'covered_unit_ids': list(covered),
        'changed_unit_ids': changed,
        'neighbour_unit_ids': neighbours,
        'findings': len(findings),
        'blocking_finding_ids': blocking,
        'outcome': outcome,
        'user_exception': bool(exception),
        'establishes': 'evidence integrity and coverage',
        'does_not_establish': 'semantic correctness of the prose or of the findings',
    }
