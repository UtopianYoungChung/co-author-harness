# Step 4 — Audit-side re-classification of EXTERNAL tags (detailed procedure)

> **Loaded by** `SKILL.md` after the advisor call returns tagged output. This file is the authoritative procedure for steps 4a–4d: extract, heuristic-reclassify (with the four attribution patterns), force-reclassify, and validate surviving gaps. `SKILL.md` keeps the Step 4 entry heading and pointer; this file owns the patterns and the Python regex heuristics.

---

## Procedure — Step 4 — Audit-side re-classification of EXTERNAL tags

**This step is mandatory.** Even with v1.3.0's improved tag discipline, run-to-run variance and model drift mean prompt-side tagging is best-effort. The re-classifier is the correctness guarantee.

### 4a. Extract all EXTERNAL-tagged items

Scan the advisor response for all instances of `[EXTERNAL: gap]` and `[EXTERNAL: fact]`. Record each with its surrounding sentence.

### 4b. Apply the proper-noun + propositional-verb heuristic

For every `[EXTERNAL: gap]` item, check whether the sentence contains ANY of these patterns:

**Pattern 1 — Proper noun + propositional verb:**
A capitalized name (unicode-aware: matches names with diacritics like Ågerfalk, Coeckelbergh, Dalsgaard) followed by or near one of these verbs: *argues, claims, shows, proposes, defines, contends, holds, maintains, writes, demonstrates, establishes, characterizes, decomposes, operationalizes, extends, coins, introduces, distinguishes, addresses, conceptualizes, theorizes, articulates, frames, develops, formulates, advances.*

Regex (Python, unicode-aware):
```python
import regex  # not re — need \p{Lu} support
PROPOSITIONAL_VERBS = (
    r'(?:argu|claim|show|propos|defin|contend|hold|maintain|writ|'
    r'demonstrat|establish|characteriz|decompos|operationaliz|extend|'
    r'coin|introduc|distinguish|address|conceptualiz|theoriz|'
    r'articulat|fram|develop|formulat|advanc)\w*'
)
PROPER_NOUN = r'\p{Lu}\p{Ll}+'
# Pattern 1: Name + verb
P1 = regex.compile(
    rf'(?:{PROPER_NOUN}(?:\s+(?:and|&)\s+{PROPER_NOUN})*'
    rf'(?:\s+(?:et\s+al\.?|and\s+colleagues))?)'
    rf'\s+{PROPOSITIONAL_VERBS}',
    regex.UNICODE
)
```

**Pattern 2 — Possessive proper noun + domain term:**
```python
# Pattern 2: Author's <term>
P2 = regex.compile(
    rf"(?:{PROPER_NOUN})'s\s+\w+",
    regex.UNICODE
)
```

**Pattern 3 — Appositional attribution:**
```python
# Pattern 3: "Per X, ...", "According to X, ...", and passive
# attributions: "proposed by X", "coined by X", etc.
P3 = regex.compile(
    rf'(?:Per|According\s+to|Following|As\s+\w+\s+by'
    rf'|(?:propos|coin|introduc|develop|advanc|establish|formulat)\w*\s+by)'
    rf'\s+{PROPER_NOUN}',
    regex.UNICODE
)
```

**Pattern 4 — Relative-clause attribution:**
```python
# Pattern 4: "X, who argues", "X et al. (2026), who show"
P4 = regex.compile(
    rf'{PROPER_NOUN}(?:\s+et\s+al\.?)?'
    rf'(?:\s*\([^)]*\))?'        # optional parenthetical (year)
    rf'\s*,\s*who\s+'
    rf'{PROPOSITIONAL_VERBS}',
    regex.UNICODE
)
```

**Abbreviation handling:** The sentence extractor must not treat periods in "et al.", "e.g.", "i.e.", etc. as sentence boundaries. Without this, "Baumer et al. argue..." gets truncated to "argue..." and the name is lost.

### 4c. Force-reclassify

Any `[EXTERNAL: gap]` item matching P1, P2, or P3 is **force-promoted** to `[EXTERNAL: fact]`. Log every promotion:

```
[RECLASSIFIED] gap → fact: "<sentence fragment>" (matched pattern <P1|P2|P3>)
```

### 4d. Validate surviving gaps

After reclassification, every remaining `[EXTERNAL: gap]` must be purely existential — "the manuscript should engage X," "X is not cited," "a gap exists in the treatment of X." If any surviving gap still predicates what the source says or does, manually promote it and log the promotion.

---

