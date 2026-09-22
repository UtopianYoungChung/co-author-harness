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


def build(candidate_text: str, changed_unit_ids=None, *, contribution='advances') -> dict:
    """A minimal valid review covering exactly the required units."""
    inventory = prefilter.inventory(candidate_text)
    by_id = {u['unit_id']: u for u in inventory['units']}
    needed, changed, neighbours = coherence.required_units(candidate_text, changed_unit_ids)
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
    for unit_id in changed:
        if 'commitment' in by_id[unit_id]['markers']:
            for row in inventory['commitment_candidates']:
                if row['unit_id'] == unit_id:
                    review['commitment_occurrences'].append({
                        'commitment': row['sentence'],
                        'occurrence_locators': [f'{unit_id}:{row["line"]}'],
                        'status': 'carried',
                    })
    return review


def attach(result: dict, candidate_text: str, changed_unit_ids=None) -> dict:
    result['coherence_review'] = build(candidate_text, changed_unit_ids)
    return result
