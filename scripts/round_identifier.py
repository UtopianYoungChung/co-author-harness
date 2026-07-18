#!/usr/bin/env python3
"""round_identifier - the one definition of a round identifier.

WHY A NEUTRAL MODULE
--------------------
`round_YYYY-MM-DD_NNN` was defined once, in
`artefact_frontmatter_validate.ROUND_ID_RE`, which is correct for artefacts and
wrong as a home for everyone: the PHASE STATE now carries a round identifier
too (`terminal_round_id`), and `phase_state_validate` importing the artefact
validator would drag `reader_accessibility_policy` and
`reader_accessibility_candidates` into the phase-state subsystem. Those modules
have nothing to do with phase state; the dependency would be real, permanent,
and only there to borrow a regex.

The alternative -- copying the pattern -- is the failure this whole workstream
documents, one layer down: two definitions of one fact, agreeing today,
drifting later, with no signal when they diverge.

So the identifier gets a neutral owner that depends on nothing, and both
consumers compose it. `artefact_frontmatter_validate.ROUND_ID_RE` is now an
alias of this pattern, so the artefact side and the state side cannot disagree
about what a round is.
"""

from __future__ import annotations

import re

# round_YYYY-MM-DD_NNN -- the format established by
# references/ARTEFACT_FRONTMATTER_SCHEMA.md (F6/F7/F8 `round_id`). This module
# is the implementation; that document remains the contract.
ROUND_ID_RE = re.compile(r"^round_\d{4}-\d{2}-\d{2}_\d{3}$")

ROUND_ID_FORMAT = "round_YYYY-MM-DD_NNN"


def is_valid_round_id(value: object) -> bool:
    """True iff `value` is a well-formed round identifier.

    Type-checked first: `ROUND_ID_RE.match(7)` raises TypeError, and a
    malformed ledger must produce a finding, never an exception.
    """
    return isinstance(value, str) and ROUND_ID_RE.match(value) is not None
