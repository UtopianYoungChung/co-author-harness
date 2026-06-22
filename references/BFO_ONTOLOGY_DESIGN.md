# BFO Ontology Design Guidelines

**Purpose.** This is the single canonical, operational policy that the consuming agents apply when building, extending, formalizing, or auditing a BFO-aligned domain ontology. Its goal is to keep such ontologies faithful to the best available science and interoperable with neighboring ontologies while remaining revisable; it secures this by operationalizing realism, univocity, single-rooted `is_a` structure, and disciplined provenance into checkable rules. It governs formal ontology artifacts only (see *Trigger boundary* below), never ordinary uses of ontological vocabulary. It paraphrases Robert Arp, Barry Smith, and Andrew D. Spear, *Building Ontologies with Basic Formal Ontology* (MIT Press, 2015), especially Chapters 3-4 (PDF pp. 93-155 in the local source copy); cite the book directly for publication-facing claims.

**Trigger boundary.** Apply this file when the requested artifact is a formal ontology, ontology module, taxonomy intended for formalization, ontology term set, ontology definition set, or an audit of one of those artifacts. Do **not** silently impose it on ordinary philosophical uses of *ontology*, conceptual analysis, metaphor analysis, database schemas, knowledge graphs, or manuscripts that merely use ontology/modeling vocabulary. If BFO alignment is not explicit, record it as a proposal or question rather than assuming it.

**Precedence.** Current user instructions, venue/advisor requirements, and project-local ontology decisions win. When a project deliberately uses another upper ontology or rejects a BFO principle, record the divergence and its consequence; do not create a hidden hybrid.

## 1. Design stance

1. **Realism:** represent entities and relations in reality, not concepts, records, diagnoses, or states of knowledge as though those were the domain entities themselves.
2. **Perspectivalism:** allow multiple accurate views and levels of granularity. Prefer coordinated modules maintained with the relevant domain expertise over one totalizing ontology.
3. **Fallibilism:** treat an ontology as a revisable scientific hypothesis. Maintain version history, stable release metadata, and a route for users to report errors and gaps.
4. **Adequatism:** treat entities at each relevant level on their own terms; do not assume higher-granularity entities can be eliminated by reduction.
5. **Reuse:** search for, assess, and reuse quality ontology terms and relations before creating new ones. Preserve provenance and import boundaries.
6. **Utility constrained by realism:** local convenience must not override fidelity to the best available science when that would impair later interoperability.
7. **Open-ended maintenance:** design, evaluation, correction, and coordination with neighboring ontologies continue after first release.
8. **Low-hanging fruit:** begin with the clearest, least controversial domain entities and relations, then expand toward harder cases.

## 2. Five-step construction loop

1. **Demarcate the domain:** state purpose, scope, data to annotate, relevant universals and relations, salient granularity levels, and neighboring ontologies.
2. **Gather a starter terminology:** assemble roughly fifty common, highly general terms from domain experts, quality ontologies, and standard textbooks. Record preferred labels, synonyms, and provenance; remove accidental duplication.
3. **Order provisionally:** arrange the terms from more general to less general.
4. **Regiment iteratively:** add missing parents; identify root terms; create human-readable definitions from the roots downward; test logical, philosophical, and scientific adequacy, consistency, intelligibility, coverage, and compatibility with neighboring ontologies. Iterate between hierarchy and definitions.
5. **Formalize iteratively:** encode the regimented content in a computer-usable ontology language and validate it with appropriate ontology tooling and reasoners. Formalization does not replace the natural-language definitions or their review.

## 3. Terminology rules

1. Include terms used for important domain entities by influential scientific communities; seek domain-expert consensus and explicitly track unresolved usage conflicts.
2. Track synonyms, but select one preferred label for each intended meaning. Do not invent a new preferred expression where an established, adequate domain term exists, and do not assign a familiar term a novel meaning without explicit qualification.
3. Use singular common nouns or noun phrases for universals and defined classes.
4. For human review displays, render common-noun labels consistently in lowercase italics. Treat this as a presentation convention; obey the syntax required by the ontology serialization or editing tool.
5. Avoid acronyms and abbreviations unless they are stable scientific terms such as *DNA* or *AIDS*.
6. Give each ontology entity a unique, permanent alphanumeric identifier. Preserve the identifier across versions while the referent and definition remain stable; never recycle retired identifiers for a new meaning.
7. Enforce univocity: a term and relational expression has one meaning on every use. Synonyms may share a meaning, but one is the preferred label.
8. Avoid ambiguous mass-noun labels. Use an ontologically explicit count form such as *portion of tissue* or *maximal portion of tissue* when that is what is meant.
9. Keep universals and defined classes in the ontology; keep particulars/instances in a separate assertion or data artifact. If combined operationally as a knowledge base, preserve the distinction.

## 4. Definition rules

1. Define every non-root term. Define a root through an imported higher-level genus or declare it primitive and provide elucidations, examples, usage guidance, and axioms.
2. Prefer an Aristotelian genus-differentia definition: `S =def. a G that Ds`, where `G` is the immediate asserted parent and `Ds` distinguishes `S` from its siblings.
3. State necessary and jointly sufficient conditions using essential features supported by the relevant science. For artifacts, intended function may supply essential features.
4. Work top-down from general terms toward specific terms, revising the taxonomy when definition work reveals an error.
5. Avoid circularity: neither the term nor a near synonym may do the explanatory work in its definition.
6. Use terms that are logically, scientifically, or ontologically simpler and more intelligible than the term defined; define or import technical terms used in the differentia.
7. Do not infer a universal merely from an arbitrary Boolean combination. Avoid complement classes such as *nonrabbit* as ontology entries and arbitrary disjunctions such as *mammal or bacterium*. Internal negative conditions can be legitimate when they define a scientifically recognized positive class, such as a cell type that lacks a nucleus.
8. Make definitions unpackable: in extensional contexts, substituting a definition for its term must preserve grammar, reference, meaning, and truth value.

## 5. Taxonomy rules

1. Build a central `is_a` backbone as a single-rooted directed acyclic hierarchy. Other relations may add structures such as partonomies, but do not replace the backbone.
2. Ensure `is_a` completeness: every included term belongs to the backbone and every non-root term reaches the root through successive `is_a` edges.
3. Validate each `A is_a B` assertion with the all-some test: every instance of `A` is an instance of `B`. Do not cross ontological categories merely because labels are associated in practice.
4. Maintain asserted single inheritance: each non-root term has exactly one asserted parent. Use reasoning to derive polyhierarchies or application views where useful; do not silently encode competing asserted parents.
5. Apply the open-world assumption: absence of a term or assertion does not entail its negation. Design for extension and correction and never claim the ontology is a complete assay of a nontrivial scientific domain.
6. Follow objectivity: represent what exists, not what is known, recorded, scheduled, diagnosed, or unclassified. Distinguish disease from diagnosis, magnitude from measurement result, and entity from information about the entity.

## 6. Required provenance and validation record

For each ontology release or substantive audit, record:

- declared BFO applicability and any project-authorized departures;
- domain, purpose, scope, granularity, and competency questions or annotation needs;
- reused ontologies/terms, versions, licenses, identifiers, and import mappings;
- preferred labels, synonyms, textual definitions, definition sources, and term stewards;
- asserted hierarchy validation, reasoner results, unresolved contradictions, and known coverage gaps;
- ontology version, change history, deprecated identifiers, migration notes, and feedback/error-report channel.

Evaluation reports violations by rule name and evidence. Generation does not repair an ontological commitment by silently changing the domain claim. Substantive choices about scope, upper ontology, identity, or competing scientific classifications route to the user or designated domain authority.

## 7. BFO conformance, relations, lifecycle, and release gate

### 7.1 BFO conformance profile

Sections 1-6 operationalize realism-based design methodology (Arp, Smith, and Spear, Chapters 3-4). Calling an artifact *BFO-aligned* requires meeting the following in addition, and the record must declare each:

1. the targeted BFO and Relation Ontology versions, each pinned to its own published release/version IRI for import; resolve the official release locators in Section 8 and record the `owl:versionIRI` embedded in each imported artifact; record any conformance standard separately (for example ISO/IEC 21838-2:2021), since a standard is not an import IRI; use the current BFO/RO specifications in Section 8 for version and conformance claims because the 2015 source book predates them;
2. each root term mapped to a BFO upper category, with every domain universal classified as a **continuant** or an **occurrent** (Chapters 5-6) and each continuant further placed as independent, specifically dependent, or generically dependent;
3. reuse of a BFO or Relation Ontology relation wherever one exists, rather than a locally minted equivalent (Chapter 7).

If these cannot be met, label the work *realism-based domain ontology design* rather than *BFO-aligned*, and record the gap. Do not present Chapter 3-4 methodology conformance as full BFO conformance.

### 7.2 Relation discipline

1. Reuse an existing relation (BFO, Relation Ontology) before minting a new one; preserve its identifier and intended reading.
2. Declare domain and range for each relation. These axioms infer classifications rather than validate, so enforce them through a constraint layer (for example SHACL) or reasoner-backed disjointness checks that surface a conflict instead of silently inferring a new type.
3. State temporal qualification explicitly (holds at-all-times versus at-some-time); do not leave a continuant relation time-indifferent by default.
4. Declare inverses where they exist and keep them mutually consistent; do not assert both directions as independent primitives.

### 7.3 Lifecycle and versioning

1. Deprecate, never delete: retire a term by marking it deprecated, never by removing or recycling its identifier.
2. On a semantically significant change of meaning, mint a new identifier and link the old one with a replaced-by note; a non-substantive refinement keeps the identifier and records the revision.
3. Pin every import to a specific version IRI, and record release/version IRIs and migration notes for each release.

### 7.4 Release gate (blocking)

A release or substantive audit must not pass while any check below fails. Statically decidable checks block unconditionally:

- no cycles in the `is_a` backbone; no orphan classes; no recycled or reused retired identifiers;
- every non-root class has a textual definition and exactly one asserted parent;
- all imports and ontology versions are pinned.

Reasoner-dependent checks block when a reasoner is in scope, and are recorded as a known, unverified gap otherwise:

- no unsatisfiable classes; no unintended equivalences or implied polyhierarchy.

To pass, the record must also carry reasoner results (or an explicit `not_run` entry with justification when no reasoner is in scope), positive and negative competency-question outcomes, and explicit approval (not mere documentation) of any departure from this policy.

## 8. Source verification map

Local source: `B:\Agents\knowledge\LLM wiki\raw\inbox\books\Building Ontologies with Basic Formal Ontology (Robert Arp, Barry Smith, Andrew D. Spear) (z-library.sk, 1lib.sk, z-lib.sk).pdf`.

- Design principles and five-step process: PDF pp. 93-105.
- Terminology selection and formatting: PDF pp. 116-129.
- Definition principles: PDF pp. 129-143.
- Taxonomy, open-world assumption, and objectivity: PDF pp. 144-154.

Current conformance and release sources (primary sources; resolve them when the work is performed rather than assuming a remembered release is still current):

- **BFO release and specification:** [official BFO-2020 repository](https://github.com/BFO-ontology/BFO-2020) and [BFO 2020 documentation](https://basic-formal-ontology.org/bfo-2020.html). The repository identifies `21838-2/owl/bfo-core.owl` as the current OWL release; its published ontology IRI is `http://purl.obolibrary.org/obo/bfo.owl` and its embedded version IRI is `http://purl.obolibrary.org/obo/bfo/2020/bfo-core.owl`.
- **Relation Ontology release and specification:** [official RO repository](https://github.com/oborel/obo-relations) and the release artifact PURL `http://purl.obolibrary.org/obo/ro.owl`. Resolve the PURL and record the artifact's embedded `owl:versionIRI`; do not infer a release date from this policy.
- **BFO conformance standard:** [ISO/IEC 21838-2:2021 - Basic Formal Ontology](https://www.iso.org/standard/74572.html). Record a claim of conformance to this standard separately from the ontology import and version IRIs.

These are operational paraphrases, not quotations. When a project needs a publication-facing claim about BFO methodology, cite the book or another primary BFO source directly rather than citing this policy file.
