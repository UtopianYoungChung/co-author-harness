# Citation auditor fixture — known-good

This fixture exercises the resolution path. Every citation below points
to a rule that exists in the live anchor set (Rules 1–7 and 7a).

## Prose form

The Reflector grounds every action in `GROUNDING_PROTOCOL.md §Rule 1`
and verifies references per `GROUNDING_PROTOCOL.md §Rule 3`.

## Short form

The architecture canonical citation is `[GP §1]` and the sub-rule
form is `[GP §7a]`.

## Multi-rule list

Per `GROUNDING_PROTOCOL.md §§Rule 4, Rule 6, Rule 7a` the writer must
quote before attribute, never fill gaps, and chain verification.

## Non-citation false positives must NOT fire

Phrases like "Rule 99 of the international standard" without the
`GROUNDING_PROTOCOL.md` qualifier are not matched — the auditor errs
on the side of precision over recall for prose-style false positives.
