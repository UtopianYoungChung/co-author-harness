# Paragraph and sentence boundaries (claim-coverage-audit)

This note anchors the optional paragraph/sentence splitting rules referenced from `skills/claim-coverage-audit/SKILL.md`.

## Paragraphs

A **paragraph** is a maximal run of non-blank lines separated by one or more blank lines, after stripping the surrounding markdown document structure (headings, fences, and list markers are normal markdown; body text inside lists follows GitHub-flavoured markdown paragraph rules).

## Sentences

Within a paragraph, a **sentence** ends at `.`, `?`, or `!` when followed by whitespace and a capital letter or end of paragraph, except inside obvious abbreviations (e.g. `e.g.`, `i.e.`, `et al.`) where the following token is lowercase.

When this file is absent, `claim-coverage-audit` falls back to standard markdown paragraph boundaries and naive sentence splits as documented in the skill body.
