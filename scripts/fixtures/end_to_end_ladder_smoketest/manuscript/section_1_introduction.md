# 1. Introduction

The deployment of autonomous review agents in academic writing pipelines
raises a question that requires substantive engagement: under what
conditions does an autonomous Evaluator produce findings that a human
reviewer would endorse? Two threads in the literature inform this
question. The first, drawn from goal-oriented modeling and dependency
analysis (Yu, 1995; Horkoff, 2011), treats the question as one of
preference propagation between intentional actors. The second, drawn
from Wohlin-style snowball discovery (Wohlin, 2014), treats it as a
question of reference-pool saturation: a finding is trustworthy when the
sources that motivate it are themselves verifiable through external
verifiers.

This paper integrates these threads. The author argues that the
trustworthiness of an autonomous review pipeline reduces to two
empirically tractable conditions: (a) every finding cites a passage
whose source is independently verifiable, and (b) every claim in the
manuscript resolves to a source in the pipeline's reference pool. The
first condition is the grounding contract; the second is the coverage
contract. The paper develops both and reports a pilot study.
