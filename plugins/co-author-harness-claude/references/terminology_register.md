# TERMINOLOGY REGISTER — Project-Tier Glossary Lookup

**Status (created 2026-07-07, full-links coherence audit).** This file is the canonical
lookup that `DETERMINISTIC_CHECKS.md` (term-density), `SAFEGUARD_LAYER.md` (functional
removability term source), and `lay_term_lexicons.md` cite. It shipped as a *cited but
absent* target from v0.7.x until this audit; checks that consulted it fell through
silently. It now exists as an explicit empty register so absence is no longer ambiguous.

**Contract.** Projects populate a project-local copy at
`<project>/research_notes/terminology_register.md` (one row per term: term |
single sense | first-use locus | P-stage cap). This package-level file carries no
project entries by design. A check that finds no project-local register and no rows
here MUST treat the lookup as "register empty" (advisory), not as an error.

| Term | Single sense | First-use locus | P-stage cap |
|---|---|---|---|
| *(package-level register intentionally empty — see contract above)* | | | |
