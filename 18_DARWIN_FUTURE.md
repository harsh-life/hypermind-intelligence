# Hypermind Track A — Future: Darwin / Vulnerability Chaining

**Status:** REVISED — canonical replacement for the prior Darwin/future evolution document. One clarification added; no structural change; not moved into the MVP.
**Related documents:** 01_ARCHITECTURE.md · MODEL_REGISTRY.md · WORKER_SKILL_CONTRACTS.md · EVALUATION_BENCHMARKING.md · IMPLEMENTATION_ROADMAP.md

---

## Future — Darwin / Vulnerability Chaining

**[FUTURE — not Phase 2a]**

Phase 2a must first prove reliable individual vulnerability discovery and validation. Only after that does chaining make sense.

The Darwin system is a deferred research extension that would chain validated findings:

```
Validated Finding A + Validated Finding B
        ↓
Candidate chain hypothesis
        ↓
Evaluation (evidence-based, not speculative)
        ↓
Genetic selection (which chains are worth pursuing)
        ↓
Mutation (variants of the chain)
        ↓
Crossover (combining chain elements)
        ↓
Chain scoring (severity × reproducibility × novelty)
        ↓
Survival threshold (below threshold → discard)
        ↓
Human validation (same gate as individual findings)
```

**Key constraint for the future Darwin system:** it operates on validated evidence and patterns, not raw model output. A chain of hallucinations is not a finding. The input to Darwin must be the same quality evidence that currently exits the Evidence Gate and passes human verification. **Raw model output is never a Darwin success signal — only evidence that has cleared the same Evidence Gate and human verification every individual finding clears today.**

**Relationship to the revised model-composition architecture (see 01_ARCHITECTURE.md, MODEL_REGISTRY.md):** treating models as swappable, benchmarked implementations behind stable worker/skill contracts is intended to make it easier, over time, to accumulate the validated capabilities, patterns, evidence, and evaluation signals that a future Darwin system would search over. A better-benchmarked specialist produces more reliable validated findings; more validated findings is a larger, cleaner corpus for Darwin to eventually draw from. This is a downstream benefit of the Model Registry's benchmarking discipline, not a reason to build Darwin now.

```
validated Track A evidence (Evidence Gate + Human Verification, defined in the Track A PRD)
        ↓
structured patterns/capabilities (research memory)
        ↓
candidate generation (future)
        ↓
controlled evaluation (future — same Evidence Gate discipline)
        ↓
evidence
        ↓
fitness
        ↓
selection / mutation / recombination (future)
```

Do not implement. Do not design in Phase 2a. Record here so it is not forgotten.
