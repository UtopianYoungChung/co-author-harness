# Citation checks file — input schema of the quote-binding gate

**Scope.** `reviews/citation_checks.json` is the evidence that the quote-binding
gate reads. The gate is `scripts/citation_gate/verify_locators.py` plus
`validate_sources.py`, vendored from the author's working copy (see its
`PROVENANCE.json`). `/quick-deterministic` (`scripts/audit/run_all.py`) looks for
the file in `reviews/` beside the manuscript or up to two directories above it,
runs both tools, and relays their conclusions as `CIT-LOC-*` findings
(`scripts/audit/audit_citations.py`). Without the file every citation stays
`UNVERIFIED` (`CIT-LOC-000`). The rules the gate enforces are
`GROUNDING_PROTOCOL.md` Rules 1, 3, 4 and 4a; this page states only the shape
of the file.

The tools themselves take no `--help`. Their usage lines are in each script's
module docstring:

```
python verify_locators.py checks.json [--verbose] [--legacy] [--citing-document PATH]
python validate_sources.py checks.json [--verbose] [--offline]
python reconcile_citations.py <document> [--bib-heading "Bibliography"] [--bib-start LINE] [--verbose]
```

Both PDF-reading tools need PyMuPDF. Without it `verify_locators.py` exits 3
with `GATE_UNAVAILABLE`, `validate_sources.py` reports each PDF as unopenable,
and the auditor relays either as an environment fault (`CIT-LOC-001`) that
still blocks (`CIT-LOC-003`), not as a citation defect.

## A minimal file that passes both tools

This file passes both tools with exit 0, and `run_all.py` reports no `CIT-LOC`
finding for it. The PDF's first page names the author and title, and page 2
carries the quote with the printed folio "2":

```json
{
  "citing_document": {"path": "manuscript/draft.md", "sha256": "<sha256 of draft.md's bytes>"},
  "sources": {
    "yu2011": {
      "pdf": "sources/yu-2011.pdf",
      "offset": 0,
      "cite": {"author": "Yu", "title": "Social Modeling", "year": 2011},
      "version": "version_of_record",
      "no_doi_reason": "book chapter without a DOI"
    }
  },
  "checks": [
    {
      "id": "C1",
      "source": "yu2011",
      "page": 2,
      "element": "E1",
      "quote": "Actors depend on each other for goals to be achieved",
      "claim_text": "Strategic actors depend on each other for goals to be achieved",
      "class": "PARAPHRASE",
      "bridge": "The claim adds 'strategic' as the source's term for its actors; the dependency relation is stated verbatim.",
      "dropped_terms": {"strategic": "the source calls its actors strategic throughout; the qualifier adds no claim"}
    }
  ],
  "claims": [{"id": "K1", "elements": ["E1"]}]
}
```

The manuscript sentence it binds is `Strategic actors depend on each other for
goals to be achieved (Yu, 2011, p. 2).`

## Fields

**Top level**

| Key | Required | Meaning |
|---|---|---|
| `citing_document` | yes | `path` (relative to the working directory) and `sha256` of the manuscript the evidence is for; a file that binds no manuscript must say so in `not_a_manuscript` with a written reason instead. The run fails if the bytes differ, if a check's `claim_text` is not in the document, or if a cited sentence has no check (`UNCOVERED`). `run_all.py` passes the audited file as `--citing-document`, which overrides `path`. |
| `sources` | yes | Map of source key to source record (below). |
| `checks` | yes | One entry per quote bound to a claim element. |
| `claims` | yes | List of `{"id", "elements": [...]}`; every element needs at least one bound check, or it is reported `UNSUPPORTED`. |
| `bib_numbers` | no | Map of bibliography number to source key, for numeric citation styles. |

**Source record**

| Key | Required | Meaning |
|---|---|---|
| `pdf` | yes | Path to the source PDF, relative to the working directory. |
| `offset` | yes | Printed page number minus the PDF's 1-based page number (a PDF whose first page is printed p. 3 has offset 2). It must be confirmable from the folios the source prints. |
| `cite` | yes | `author`, `title`, `year`. The PDF's first two pages must contain the author and title, or the file is the wrong one (item 9a). |
| `version` | yes | One of `version_of_record`, `author_manuscript`, `web_rendering`, `official_print` (item 9b). |
| `doi` or `no_doi_reason` | yes | Without one, retraction status is not checked (item 10). |

**Check**

| Key | Required | Meaning |
|---|---|---|
| `id` | yes | Unique check id. |
| `source` | yes | A key of `sources`. |
| `page` | yes | Printed page the quote is on. |
| `quote` | yes | Verbatim text that must be found on that page. |
| `element` | yes | The claim element this check supports (listed under `claims`). |
| `claim_text` | yes | The element's exact words in the manuscript; the load-bearing terms are derived from it. |
| `class` | yes | `VERBATIM`, `PARAPHRASE`, `MAPPED` or `EXTENDED`, strongest first. A claim term missing from the quote forces `MAPPED` or `EXTENDED` unless it is listed in `inflections` or dropped with a reason. |
| `bridge` | unless `VERBATIM` | Written reasoning from the quote to the claim. |
| `modality_scope` | for `VERBATIM` | A written statement (at least 15 characters) that the quote's modality and scope match the claim's. |
| `dropped_terms` | no | `{term: reason}` for derived claim terms the quote need not carry. |
| `inflections` | no | `{term: [forms]}` for other word forms that count as the term. |
| `key_terms` | no | The load-bearing subset whose absence forces `MAPPED` or `EXTENDED`. |
| `section` | no | Where the claim sits in the manuscript. |
