# Hypermind Track A — Model Evaluation & Benchmarking Protocol

**Status:** NEW — no prior canonical document existed for this activity. This document fills that gap and is now the canonical source for how a candidate model earns a place in the Model Registry.
**Related documents:** 01_ARCHITECTURE.md · MODEL_REGISTRY.md · WORKER_SKILL_CONTRACTS.md · IMPLEMENTATION_ROADMAP.md · DARWIN_FUTURE.md

---

## Model Benchmarking Protocol

**[LOCKED — new, addresses a documentation gap]**

No document previously existed defining how a candidate model earns a place in the Model Registry. This section is that document. Role-specific benchmarking is a first-class Track A activity — it happens before a candidate is promoted from `candidate` to `approved`, and it happens again whenever a new candidate is proposed for an existing role.

```
candidate models (MODEL_REGISTRY.md's Candidate Model table)
        ↓
role-specific benchmark (this document)
        ↓
selection (approval_status: approved)
        ↓
deployment behind the stable worker/skill contract (WORKER_SKILL_CONTRACTS.md — unchanged)
```

### Measurable Criteria

A candidate is benchmarked against the **worker or skill contract for the specific role it's being considered for** (see WORKER_SKILL_CONTRACTS.md) — never in the abstract. The criteria:

| Criterion | What it measures | How it's measured |
|---|---|---|
| Structured-output validity rate | % of outputs that parse against the role's output schema without retry | Run N prompts from held-out sandbox data, count schema-valid outputs |
| Useful hypothesis rate | % of outputs that produce a hypothesis worth passing to the next stage (not just schema-valid, but substantively useful) | Human review of a sample against sandbox ground truth |
| Evidence quality | Whether cited evidence_refs actually support the claim made | Manual spot-check against raw_evidence_path |
| False-positive rate | % of candidate findings that don't survive Evidence Gate / human verification | Track against sandbox known-vulnerable/known-clean endpoints |
| Consistency | Variance in output across repeated runs on the same input at temperature 0.0 | Run the same input N times, measure divergence |
| Latency | p50/p95 response time under realistic load | Timed runs on target hardware |
| Resource usage | RAM/VRAM footprint at runtime | Measured on target host, not vendor-claimed specs |
| Cost | Per-call cost if remote; amortized compute cost if local | Direct measurement |
| Failure/refusal behavior | How the model fails — cleanly (schema-valid "unknown") vs. badly (malformed output, silent wrong answer, unexplained refusal) | Adversarial + edge-case prompt set |
| Prompt-injection robustness | Where relevant (workers/specialists processing target-controlled data) — does the candidate follow injected instructions from Trust Boundary B data? | Run against 01_ARCHITECTURE.md Section 6's Trust Boundary B test cases |
| Reproducibility | Can the same benchmark be re-run later (e.g., after a model update) and produce comparable results? | Versioned benchmark harness, pinned test set |

**Absolute rule: do not invent benchmark results, and do not claim a model has been benchmarked unless this repository contains the actual benchmark run output.** A `quality_metrics` field with a null value means "not yet measured" — it is never filled with an estimate, a vendor claim, or an assumption. The illustrative candidates table in MODEL_REGISTRY.md intentionally shows `NOT_YET_BENCHMARKED` for every entry because no benchmark has been run in this documentation package. When a benchmark is actually run, the result — including a bad result — gets recorded in the Model Registry, and the candidate's `approval_status` updates accordingly.

**A candidate that fails the benchmark is recorded as `rejected` with the reason, not silently dropped.** A rejection is itself useful information for future candidate evaluation and belongs in the registry's history.

### Where Benchmark Results Get Recorded

This document defines the *process*. The *results* live in MODEL_REGISTRY.md's Candidate Model Manifest entries (the `quality_metrics`, `benchmark_status`, and `approval_status` fields). Do not create a second results ledger — one canonical record per candidate, in the Model Registry.

### Relationship to Fine-Tuning

Fine-tuning (LoRA/QLoRA, per 01_ARCHITECTURE.md's non-goals and the Track A PRD's dataset lifecycle documentation) is gated behind demonstrated need: Plan A (an existing candidate, benchmarked and selected) must be shown insufficient, and a validated dataset of sufficient size must exist, before fine-tuning is considered. A fine-tuned model is itself just another candidate that must pass this same benchmarking protocol before promotion to `approved` — fine-tuning does not exempt a model from being measured.
