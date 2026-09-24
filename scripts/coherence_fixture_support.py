"""Build a schema-valid `coherence_review` for integration fixtures.

This is test plumbing, never a review. Every record it produces is marked
`synthetic: true` and it always returns `outcome: review_complete` with no
findings, because a fixture has no judgment to report. Its only job is to let
mechanical suites exercise the coordinator's coherence gate without each suite
re-deriving the unit partition. Real dispositions come from a native child that
executed `references/ARGUMENT_COHERENCE.md`; see
`scripts/argument_coherence_smoketest.py` for the negative controls that prove
this plumbing cannot stand in for one.
"""
from __future__ import annotations

import coherence_prefilter as prefilter
import coherence_review as coherence

PURPOSE = ('Synthetic fixture purpose statement of sufficient length to satisfy the '
           'evidence contract; it asserts no judgment about this paragraph.')


ASSESSMENT = ('Synthetic fixture assessment; it records that the row exists and '
              'asserts nothing about whether the commitment is carried.')


def build(candidate_text: str, changed_unit_ids=None, *, scope_unit_ids=None,
          contribution='advances') -> dict:
    """A minimal valid review covering exactly the required units."""
    inventory = prefilter.inventory(candidate_text)
    by_id = {u['unit_id']: u for u in inventory['units']}
    needed, changed, neighbours = coherence.required_units(
        candidate_text, changed_unit_ids, scope_unit_ids=scope_unit_ids)
    units = []
    for unit_id in needed:
        unit = by_id[unit_id]
        units.append({
            'unit_id': unit_id,
            'sha256': unit['sha256'],
            'purpose': PURPOSE,
            'sentences': [{'text': sentence, 'contribution': contribution, 'finding_id': None}
                          for sentence in prefilter.split_sentences(unit['text'])],
        })
    review = {
        'synthetic': True,
        'candidate_sha256': inventory['target_sha256'],
        'scope': {'covered_unit_ids': list(needed), 'changed_unit_ids': list(changed),
                  'neighbours_reviewed': list(neighbours)},
        'units': units,
        'commitment_occurrences': [],
        'findings': [],
        'out_of_scope_observations': [],
        'outcome': 'review_complete',
    }
    # One not_applicable row per promise, definition or question sentence in the
    # required units: the rows exist, so the obligation's bookkeeping holds, and
    # their status claims nothing a fixture cannot know.
    needed_set = set(needed)
    candidates = [row for row in inventory['commitment_candidates'] if row['unit_id'] in needed_set]
    with_candidates = {row['unit_id'] for row in candidates}
    for unit_id in needed:
        if (set(prefilter.COMMITMENT_MARKERS) & set(by_id[unit_id]['markers'])
                and unit_id not in with_candidates):
            candidates.append({'unit_id': unit_id,
                               'sentence': prefilter.split_sentences(by_id[unit_id]['text'])[0]})
    for row in candidates:
        review['commitment_occurrences'].append({
            'commitment': row['sentence'],
            'unit_id': row['unit_id'],
            'status': 'not_applicable',
            'occurrence_locators': [],
            'assessment': ASSESSMENT,
        })
    return review


def attach(result: dict, candidate_text: str, changed_unit_ids=None, scope_unit_ids=None) -> dict:
    result['coherence_review'] = build(candidate_text, changed_unit_ids,
                                       scope_unit_ids=scope_unit_ids)
    return result
