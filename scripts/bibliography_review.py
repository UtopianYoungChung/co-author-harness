"""Bibliography/use coverage inside existing role evidence, shared by both routes.

Inventory is deliberately conservative: Markdown numbered and author/year
references are supported; ambiguous citation syntax remains unresolved. This
module checks coverage and provenance, never scholarly entailment. Reviewers
must inspect every claim in each cited paragraph and supply their judgments.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter


class ReviewError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def require(condition, code, message):
    if not condition:
        raise ReviewError(code, message)


def normalized(text):
    return ' '.join(text.split())


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


HEADING = re.compile(r'^#{1,6}\s+(?:references|bibliography|works cited)\s*$', re.I | re.M)
NUMBER = re.compile(r'^(?:\[(\d+)\]|(\d+)[.)])\s*')
YEAR = re.compile(r'(?<!\w)(?:\d{4}[a-z]?|n\.d\.)(?!\w)', re.I)
CITATION = re.compile(r'\[(?:\d+[\s,;\-–]*)+\]|\([^()\n]*(?:\d{4}[a-z]?|n\.d\.|personal communication)[^()\n]*\)', re.I)


def _author(reference):
    return re.split(r',|\s*\(', reference, maxsplit=1)[0].strip()


def _narrative_author(prefix, author):
    # A nearby author elsewhere in the paragraph is not a narrative attachment.
    return bool(re.search(r'(?<!\w)' + re.escape(author)
                          + r'(?:\s+et\s+al\.?|\s+(?:&|and)\s+[\w .’\'-]+)?'
                          + r'(?:[’\']s|[’\'])?\s*$', prefix, re.I))


def _calendar_year(value, prefix, references):
    """A narrow, reproducible non-citation classification, never an ignore list.

    Return positive, adjacent calendar evidence, or None. Failure to recognize
    an author is never evidence of a date: unknown names and ambiguous bare
    years must go through citation resolution regardless of capitalization.
    """
    match = re.fullmatch(r'\(\s*(\d{4})(?:\s*[-–]\s*(\d{4}))?\s*\)', value)
    if not match or not 0 < int(match[1]) <= int(match[2] or match[1]):
        return None
    if any(_narrative_author(prefix, _author(ref['reference'])) for ref in references):
        return None
    # Deliberately small grammar: relative calendar years and explicit spans.
    # The cue must immediately precede the token, not just occur somewhere in
    # its paragraph. Other temporal wording remains unresolved until supported.
    cue = re.search(r'(?<!\w)(?:(?:next|last|this)\s+(?:calendar\s+)?year|'
                    r'spans?\s+(?:[1-9]\d*|two|three|four|five|six|seven|eight|nine|ten)\s+years)\s*$',
                    prefix, re.I)
    return normalized(cue.group()) if cue else None


def inventory(text):
    """Return stable source/use identities; numeric labels are presentation only.

    Paragraph context is part of each use identity, so expanding an attribution
    invalidates that use even when the old quotation remains a substring.
    """
    match = HEADING.search(text)
    references, errors = [], []
    body = text
    if match:
        tail = text[match.end():]
        end = re.search(r'^#{1,6}\s+', tail, re.M)
        ref_text = tail[:end.start()] if end else tail
        body = text[:match.start()] + ('\n\n' + tail[end.start():] if end else '')
        chunks = []
        for line in ref_text.splitlines():
            if not line.strip():
                continue
            # Hanging-indent continuation is part of the preceding entry.
            if line[:1].isspace() and chunks and not NUMBER.match(line.strip()):
                chunks[-1] += ' ' + line.strip()
            else:
                chunks.append(line.strip())
        for line in chunks:
            number = NUMBER.match(line)
            entry = normalized(line[number.end():] if number else line)
            references.append({'reference_id': fingerprint(entry), 'reference': entry,
                               'label': next((x for x in number.groups() if x), '') if number else '',
                               'inline': False})
    if len({x['reference_id'] for x in references}) != len(references):
        errors.append('Duplicate reference identities require explicit reconciliation.')
    labels = [x['label'] for x in references if x['label']]
    if len(labels) != len(set(labels)):
        errors.append('Duplicate bibliography numbers are ambiguous.')
    by_number = {x['label']: x for x in references if x['label']}
    uses, occurrences, contexts, non_citations = [], Counter(), [], []
    for paragraph_index, paragraph in enumerate(re.split(r'\n\s*\n', body), 1):
        if not paragraph.strip():
            continue
        tokens = []
        dates = []
        if re.search(r'\\(?:[a-z]*cite\w*|bibitem)\b|\[@|\[\^', paragraph):
            errors.append(f'paragraph {paragraph_index}: unsupported citation syntax; adapt the inventory before clearance.')
        for token in CITATION.finditer(paragraph):
            value = token.group()
            prefix = paragraph[:token.start()]
            calendar_context = _calendar_year(value, prefix, references)
            if calendar_context is not None:
                dates.append((value, calendar_context))
                continue
            selected = []
            if value.startswith('['):
                labels = []
                for part in re.split(r'[,;]\s*', value[1:-1]):
                    interval = re.fullmatch(r'\s*(\d+)\s*[-–]\s*(\d+)\s*', part)
                    if interval:
                        lo, hi = map(int, interval.groups())
                        if lo > hi or hi - lo > 1000:
                            errors.append('Invalid citation range.')
                            continue
                        labels.extend(str(x) for x in range(lo, hi + 1))
                    else:
                        labels.append(part.strip())
                selected = [by_number[x] for x in labels if x in by_number]
                if len(selected) != len(labels):
                    errors.append(f'paragraph {paragraph_index}: unresolved citation {value}')
            elif 'personal communication' in value.lower():
                entry = normalized(value)
                item = {'reference_id': fingerprint(entry), 'reference': entry, 'label': '', 'inline': True}
                if not any(x['reference_id'] == item['reference_id'] for x in references):
                    references.append(item)
                selected = [item]
            else:
                for part in value[1:-1].split(';'):
                    years = YEAR.findall(part)
                    if not years:
                        errors.append(f'paragraph {paragraph_index}: unresolved citation {part.strip()}')
                    for year in years:
                        candidates = []
                        for ref in references:
                            # Author is the first surname/corporate author preceding a comma or year.
                            author = _author(ref['reference'])
                            bare_year = bool(re.fullmatch(r'\s*' + re.escape(year) + r'\s*', part, re.I))
                            author_matches = (_narrative_author(prefix, author) if bare_year else
                                              re.search(r'(?<!\w)' + re.escape(author) + r'(?!\w)', part, re.I))
                            if year.casefold() in [x.casefold() for x in YEAR.findall(ref['reference'])] and author_matches:
                                candidates.append(ref)
                        if len(candidates) != 1:
                            errors.append(f'paragraph {paragraph_index}: ambiguous/unresolved citation {part.strip()}')
                        else:
                            selected.extend(candidates)
            if not selected:
                errors.append(f'paragraph {paragraph_index}: detected citation resolves to no source: {value}')
            tokens.append((token, selected))
        canonical, last = '', 0
        for token, refs in tokens:
            # Only numeric source labels are presentation. Author/year text,
            # locators, qualifiers and punctuation remain part of the binding.
            replacement = token.group()
            if replacement.startswith('['):
                replacement = re.sub(r'\d+', lambda label: '{' + by_number[label.group()]['reference_id'] + '}'
                                     if label.group() in by_number else label.group(), replacement)
            canonical += paragraph[last:token.start()] + replacement
            last = token.end()
        canonical = normalized(canonical + paragraph[last:])
        contexts.append(canonical)
        claim_hash = fingerprint(canonical)
        for occurrence, (value, calendar_context) in enumerate(dates, 1):
            non_citations.append({'candidate_id': fingerprint([claim_hash, value, occurrence]),
                                  'claim_sha256': claim_hash, 'text': value,
                                  'classification': 'non_citation', 'reason': 'parenthetical_calendar_year',
                                  'calendar_context': calendar_context})
        for _, refs in tokens:
            for ref in refs:
                key = (claim_hash, ref['reference_id'])
                occurrences[key] += 1
                uses.append({'use_id': fingerprint([*key, occurrences[key]]),
                             'reference_id': ref['reference_id'], 'claim_sha256': claim_hash,
                             'claim': normalized(paragraph), 'locator': f'paragraph {paragraph_index}'})
    return {'references': references, 'uses': uses, 'errors': errors, 'non_citations': non_citations,
            'coverage_sha256': fingerprint({'references': sorted(x['reference_id'] for x in references),
                                            'uses': sorted(x['use_id'] for x in uses),
                                            'manuscript_context': contexts})}


def has_sources(text):
    current = inventory(text)
    return bool(HEADING.search(text) or current['references'] or current['uses'] or current['errors'])


def _reason(row, key):
    require(isinstance(row.get(key), str) and len(row[key].strip()) >= 15,
            'BIBLIOGRAPHY-JUDGMENT-MISSING', f'Explain {key}; labels are not scholarly judgments.')


def validate(text, review, materials, read_bytes, *, require_clear=True):
    """Validate evidence against current manuscript and caller-bound materials.

    materials are {source_id, path, sha256, locator}; callers resolve portable
    paths first. They may be excerpts, primary texts, indirect texts, or explicit
    user confirmations. No lookup, discovery hit, or publisher label is proof.
    """
    current = inventory(text)
    require(isinstance(review, dict), 'BIBLIOGRAPHY-UNASSESSED', 'A bibliography-wide assessment is missing.')
    require(review.get('scope') == 'bibliography', 'BIBLIOGRAPHY-SCOPE', 'Prose-only or identity-only work cannot clear a bibliography.')
    require(not current['errors'], 'BIBLIOGRAPHY-INVENTORY', '; '.join(current['errors']))
    require(review.get('coverage_sha256') == current['coverage_sha256'],
            'BIBLIOGRAPHY-STALE', 'References or citation attachments changed after assessment.')
    require(review.get('non_citations', []) == current['non_citations'],
            'BIBLIOGRAPHY-NONCITATION', 'Non-citation classifications must exactly match the current bound inventory; citations cannot be excluded by assertion.')
    require(review.get('inventory_complete') is True, 'BIBLIOGRAPHY-INVENTORY',
            'The reviewer must attest coverage of all references and substantive citation uses, including uncaptured syntax.')
    _reason(review, 'inventory_rationale')
    source_rows, support = review.get('sources'), review.get('source_support')
    require(isinstance(source_rows, list) and all(isinstance(x, dict) for x in source_rows)
            and isinstance(support, list) and all(isinstance(x, dict) for x in support),
            'BIBLIOGRAPHY-COVERAGE', 'Supply source assessments and citation-use support rows.')
    sources = {x.get('reference_id'): x for x in source_rows}
    uses = {x.get('use_id'): x for x in support}
    require(len(sources) == len(source_rows) and set(sources) == {x['reference_id'] for x in current['references']},
            'BIBLIOGRAPHY-COVERAGE', 'Every reference, including uncited entries, needs its own assessment.')
    require(len(uses) == len(support) and set(uses) == {x['use_id'] for x in current['uses']},
            'BIBLIOGRAPHY-COVERAGE', 'Every citation use needs its own assessment; sample support cannot clear the inventory.')
    bound = {x['source_id']: x for x in materials}
    require(all(bound[x['source_id']] == x for x in materials), 'BIBLIOGRAPHY-MATERIAL', 'Conflicting material identities are ambiguous.')
    inspected_text = {}
    unresolved = []
    for ref in current['references']:
        row = sources[ref['reference_id']]
        require(row.get('reference') == ref['reference'], 'BIBLIOGRAPHY-IDENTITY', 'Source identity differs from the delivered reference.')
        require(row.get('disposition') in ('admitted', 'unresolved', 'excluded'), 'BIBLIOGRAPHY-DISPOSITION', 'Record a source disposition.')
        if row['disposition'] != 'admitted':
            unresolved.append(ref['reference_id'])
            _reason(row, 'rationale')
            continue
        require(row.get('identity_status') in ('verified', 'user_confirmed'), 'BIBLIOGRAPHY-UNVERIFIED', 'Constructed/unverified bibliographic records cannot be admitted.')
        for key in ('provenance', 'identity_rationale', 'source_type', 'rationale'):
            _reason(row, key) if key != 'source_type' else require(bool(row.get(key)), 'BIBLIOGRAPHY-UNVERIFIED', 'Record source type.')
        require(row.get('material_kind') in ('primary', 'secondary', 'personal_communication'),
                'BIBLIOGRAPHY-MATERIAL', 'Distinguish primary inspection, indirect material and personal communication.')
        require(row['identity_status'] == 'verified' or row['material_kind'] == 'personal_communication',
                'BIBLIOGRAPHY-UNVERIFIED', 'Ordinary bibliographic identities require verification.')
        if row['source_type'] in ('book_review', 'secondary_summary'):
            require(row['material_kind'] == 'secondary', 'BIBLIOGRAPHY-INDIRECT', 'The inspected review/summary must be classified as secondary material.')
        inspected = row.get('inspected')
        require(isinstance(inspected, list) and inspected, 'BIBLIOGRAPHY-MATERIAL', 'Record material actually inspected.')
        for item in inspected:
            require(isinstance(item, dict), 'BIBLIOGRAPHY-MATERIAL', 'Malformed inspected material.')
            material = bound.get(item.get('source_id'))
            require(material and item.get('sha256') == material['sha256'] and item.get('locator') == material['locator'],
                    'BIBLIOGRAPHY-MATERIAL', 'Inspection must bind a supplied material and locator.')
            data = read_bytes(material['path'])
            require(hashlib.sha256(data).hexdigest() == material['sha256'], 'BIBLIOGRAPHY-MATERIAL-STALE', 'Inspected material changed.')
            text_at_locator = material.get('passage_text', data.decode('utf-8-sig'))
            inspected_text[item['source_id']] = [normalized(x) for x in material.get('passage_texts', [text_at_locator])]
            require(isinstance(item.get('quote'), str) and item['quote'].strip() and any(normalized(item['quote']) in x for x in inspected_text[item['source_id']]),
                    'BIBLIOGRAPHY-MATERIAL', 'Inspection quote must occur in the bound material.')
        if row['material_kind'] == 'personal_communication' or 'personal communication' in ref['reference'].lower():
            require(row['material_kind'] == 'personal_communication' and row.get('communication_provenance') in ('verified_record', 'explicit_user_confirmation'),
                    'BIBLIOGRAPHY-COMMUNICATION', 'Advisor instructions alone are not a verified personal communication record.')
            for key in ('attribution', 'citation_style', 'style_treatment'):
                _reason(row, key)
            record = row.get('communication_record')
            require(isinstance(record, dict), 'BIBLIOGRAPHY-COMMUNICATION', 'Bind the provenance record or explicit user confirmation actually inspected.')
            material = bound.get(record.get('source_id'))
            require(material and record.get('locator') == material['locator'] and record.get('source_id') in {x['source_id'] for x in inspected},
                    'BIBLIOGRAPHY-COMMUNICATION', 'Communication provenance must be an inspected bound record.')
            quote = record.get('quote')
            require(isinstance(quote, str) and quote.strip() and any(normalized(quote) in x for x in inspected_text[record['source_id']]),
                    'BIBLIOGRAPHY-COMMUNICATION', 'Communication confirmation quote is absent.')
            require(all(isinstance(record.get(key), str) and record[key].strip() and record[key] in quote for key in ('speaker', 'date')),
                    'BIBLIOGRAPHY-COMMUNICATION', 'Bind speaker and date to the confirmation, rather than inventing them.')
            if re.search(r'\bAPA\b', row['citation_style'], re.I):
                require(ref['inline'], 'BIBLIOGRAPHY-COMMUNICATION', 'APA personal communications belong in text, not the reference list.')
    for item in current['uses']:
        row = uses[item['use_id']]
        require(row.get('reference_id') == item['reference_id'] and row.get('claim_sha256') == item['claim_sha256'],
                'BIBLIOGRAPHY-STALE', 'Claim context or source attachment changed.')
        require(row.get('disposition') in ('supported', 'unresolved', 'unsupported'), 'BIBLIOGRAPHY-DISPOSITION', 'Record a use disposition.')
        if row['disposition'] != 'supported':
            unresolved.append(item['use_id'])
            _reason(row, 'rationale')
            continue
        source = sources[item['reference_id']]
        require(source.get('disposition') == 'admitted', 'BIBLIOGRAPHY-UNVERIFIED', 'A dependent claim cannot clear an unresolved source.')
        require(row.get('role') in ('historical_foundation', 'current_evidence', 'research_gap', 'method', 'other'),
                'BIBLIOGRAPHY-ROLE', 'Identify the evidential role before admission.')
        for key in ('role_rationale', 'authority_rationale', 'directness_rationale', 'currency_rationale', 'rationale', 'limitations'):
            _reason(row, key)
        require(row.get('currency') in ('current', 'historical', 'not_time_sensitive'), 'BIBLIOGRAPHY-CURRENCY', 'Assess currency separately from source reputation.')
        if row['role'] in ('current_evidence', 'research_gap'):
            require(row['currency'] == 'current' and re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(row.get('assessed_as_of', ''))),
                    'BIBLIOGRAPHY-CURRENCY', 'Historical support alone cannot establish current evidence or a contemporary gap.')
        discovery = row.get('discovery')
        require(isinstance(discovery, dict), 'BIBLIOGRAPHY-DISCOVERY', 'Separate discovery from verification and admission.')
        for key in ('backward', 'forward', 'challenging_evidence'):
            _reason(discovery, key)
        require(row.get('directness') in ('primary', 'indirect', 'personal_communication'), 'BIBLIOGRAPHY-DIRECTNESS', 'Declare directness.')
        if source['material_kind'] == 'secondary':
            require(row['directness'] == 'indirect' and isinstance(row.get('indirection_marker'), str)
                    and row['indirection_marker'].strip() and row['indirection_marker'] in item['claim'],
                    'BIBLIOGRAPHY-INDIRECT', 'Secondary material cannot silently substitute for inspected primary evidence.')
        if source['material_kind'] == 'personal_communication':
            require(row['directness'] == 'personal_communication', 'BIBLIOGRAPHY-COMMUNICATION', 'Represent the communication accurately.')
        inspected_ids = {x['source_id'] for x in source['inspected']}
        material = bound.get(row.get('source_id'))
        require(material and row.get('source_id') in inspected_ids and row.get('source_locator') == material['locator'],
                'BIBLIOGRAPHY-MATERIAL', 'Support must use material inspected for this reference.')
        require(isinstance(row.get('quote'), str) and row['quote'].strip()
                and any(normalized(row['quote']) in x for x in inspected_text[row['source_id']]),
                'BIBLIOGRAPHY-MATERIAL', 'Supporting quote is absent from the inspected material.')
    require(not require_clear or not unresolved, 'BIBLIOGRAPHY-UNRESOLVED', 'Unresolved sources or uses prevent bibliography clearance: ' + ', '.join(unresolved))
    return {'scope': 'bibliography', 'status': 'unresolved' if unresolved else 'assessed',
            'coverage_sha256': current['coverage_sha256'], 'reference_count': len(sources),
            'citation_use_count': len(uses), 'unresolved': unresolved,
            'limitation': 'Coverage/provenance validated; suitability and entailment remain reviewer judgments.'}
