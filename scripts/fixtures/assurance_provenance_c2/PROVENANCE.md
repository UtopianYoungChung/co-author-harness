# C2 self-authored miniature PDF provenance

All prose in this fixture was authored for the co-author-harness C2 assurance-provenance tests. It contains no external paper, quotation, figure, font asset, or copyrighted source file.

`miniature_source.tex` is the generation source. The PDF was built locally with MiKTeX-pdfTeX 4.23 (MiKTeX 25.12), executable SHA-256 `de48c5ef651d2ded45e8d82188af22aaeebf0055d679b090609aff1881d97d30`, under `SOURCE_DATE_EPOCH=0`, `-halt-on-error`, and `-interaction=batchmode`. The source suppresses creation dates and trailer IDs. Tests consume the committed PDF bytes and do not require LaTeX.

Canonical raw extraction was produced locally with Poppler `pdftotext` 24.04.0, executable SHA-256 `640b9a93fa31fc093860c635cd410a3e30f7d1e6166cb1130993fb1985f474ff`, using `-enc UTF-8`. Tests consume the committed raw and normalized outputs and do not silently re-extract with a different executable.

The three pages deliberately contain:

- a repeated locator sentence on pages 1 and 3;
- a phrase divided across the page 1/page 2 boundary; and
- words whose `fi` sequences exercise the PDF font's ligature extraction path.

`hashes.json` records the exact committed fixture inputs and expected outputs. `expected_page_span_map.json` uses zero-based, end-exclusive UTF-8 byte offsets.
