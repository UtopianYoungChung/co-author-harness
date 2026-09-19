"""Synthetic bibliography records for mechanical tests, never scholarly evidence."""
from pathlib import Path
from bibliography_review import inventory


def synthetic_review(text, materials):
    current = inventory(text)
    result = {'scope': 'bibliography', 'coverage_sha256': current['coverage_sha256'],
              'inventory_complete': True,
              'inventory_rationale': 'Synthetic fixture inventory only; no live scholarly assessment is claimed.',
              'sources': [], 'source_support': [], 'non_citations': current['non_citations']}
    selected = {}
    for ref in current['references']:
        material = next((x for x in materials if x.get('title', '').lower() in ref['reference'].lower() and x.get('title')), materials[0])
        selected[ref['reference_id']] = material
        quote = material.get('passage_text') or Path(material['path']).read_text(encoding='utf-8-sig').strip()
        result['sources'].append({
            'reference_id': ref['reference_id'], 'reference': ref['reference'],
            'identity_status': 'verified', 'identity_rationale': 'Synthetic identity established by the test fixture, not external verification.',
            'provenance': 'Synthetic integration fixture; the test supplies these bytes.',
            'source_type': 'synthetic test text', 'material_kind': 'primary',
            'inspected': [{'source_id': material['source_id'], 'sha256': material['sha256'],
                           'locator': material['locator'], 'quote': quote}],
            'disposition': 'admitted', 'rationale': 'Synthetic admission solely to exercise the validation path.'})
    for use in current['uses']:
        material = selected[use['reference_id']]
        result['source_support'].append({
            **{key: use[key] for key in ('use_id', 'reference_id', 'claim_sha256')},
            'source_id': material['source_id'], 'source_locator': material['locator'],
            'quote': material.get('passage_text') or Path(material['path']).read_text(encoding='utf-8-sig').strip(),
            'role': 'historical_foundation', 'role_rationale': 'Synthetic foundational role for this fixture only.',
            'authority_rationale': 'The fixture defines the source content; no reputation inference.',
            'directness': 'primary', 'directness_rationale': 'The fixture text is inspected directly for this mechanical test.',
            'currency': 'historical', 'currency_rationale': 'Historical illustration only; no current field-wide conclusion.',
            'discovery': {'backward': 'Not applicable: closed synthetic fixture corpus.',
                          'forward': 'Not applicable: no contemporary literature claim.',
                          'challenging_evidence': 'The test controls qualifying and challenging evidence; no live search claimed.'},
            'disposition': 'supported', 'rationale': 'Synthetic support assertion to test machinery, not entailment.',
            'limitations': 'Synthetic fixture only; this does not establish scholarly suitability.'})
    return result


def from_passages(text, passages):
    materials = [{'source_id': row['source_key'] + '@' + row['locator'],
                  'locator': row['locator'], 'title': row['citation']['title'], 'passage_text': row['quote'],
                  **row['extract']} for row in passages]
    return synthetic_review(text, materials)


def attach_evaluation_review(value, artifact, project, passages):
    value['bibliography_review'] = from_passages(artifact.read_text(encoding='utf-8'), passages)
    value['source_materials'] = [
        {'source_id': row['source_key'] + '@' + row['locator'], 'locator': row['locator'],
         'binding': {'path': Path(row['extract']['path']).resolve().relative_to(project.resolve()).as_posix(),
                     'sha256': row['extract']['sha256'], 'byte_length': Path(row['extract']['path']).stat().st_size}}
        for row in passages]
