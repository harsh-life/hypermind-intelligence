# Hypermind Track A — Model Evaluation & Benchmarking Protocol

**Status:** REVISED 2026-09-15 — the benchmarking methodology below is superseded by OD-27's resolution (see `13_OPEN_DECISIONS.md`). This is now the canonical source for how a candidate model earns a place in the Model Registry, rewritten to reflect trajectory-based evaluation.
**Related documents:** 01_ARCHITECTURE.md · MODEL_REGISTRY.md · WORKER_SKILL_CONTRACTS.md · IMPLEMENTATION_ROADMAP.md · DARWIN_FUTURE.md · 13_OPEN_DECISIONS.md (OD-27, authoritative decision text)

---

## Model Benchmarking Protocol

**[LOCKED — REVISED 2026-09-15 per OD-27, see `13_OPEN_DECISIONS.md`]**

Role-specific benchmarking is a first-class Track A activity — it happens before a candidate is promoted from `candidate` to `approved`, and it happens again whenever a new candidate is proposed for an existing role.

**This is explicitly NOT a simple prompt/expected-answer dataset comparison, and it is NOT based on model consensus.** The previous version of this document described N-prompt schema-validity counting as the primary method; that framing is superseded by the trajectory-based model below, per OD-27.

```
candidate models (MODEL_REGISTRY.md's Candidate Model table)
        ↓
role-specific, trajectory-based benchmark (this document)
        ↓
selection (approval_status: approved) — a human decision, informed by Judge evaluation, never a consensus vote
        ↓
deployment behind the stable worker/skill contract (WORKER_SKILL_CONTRACTS.md — unchanged)
```

### The Trajectory-Based Method

Model roles remain contract-driven; concrete models remain replaceable implementations — none of that changes.

For a role/task, multiple candidate models may compete under the **same controlled starting conditions**: the same relevant initial knowledge/data/context, and the same authorized capability boundaries. Candidates then **independently** attempt to solve the task — they do not share findings, state, trajectories, or reasoning with one another.

Evaluation considers the actual **trajectory**, not just the final output shape:

| Dimension | What it captures |
|---|---|
| Task understanding | Did the candidate correctly grasp what it was asked to do? |
| Action quality/relevance | Were the actions taken useful given the evidence available at each step? |
| Experimentation | Number and quality of meaningful experiments attempted |
| Adaptation | Ability to try alternative approaches; adjustment after failure or new evidence |
| Efficiency | Resource/time cost relative to outcome achieved |
| Evidence quality | Whether cited evidence actually supports the claim made |
| Fabrication check | Whether any observation or action was hallucinated rather than actually performed |
| Actual task success | Whether the task was **actually solved** — established by an objective, observable result in the controlled test environment wherever possible, not by the candidate's own self-report |
| Policy/scope compliance | Did the candidate ever attempt or imply an out-of-scope action? |
| Role-specific dimensions | Additional criteria defined per role (see role-specific notes below) |

### The Judge's Role in Benchmarking

A strong Judge model may evaluate candidate trajectories using a **fixed scoring contract** and explicit evaluation questions/criteria. Critically:

- **The Judge is not a source of ground truth merely because it prefers one candidate's result.** Model consensus is never ground truth (this mirrors the live-pipeline rule that a Judge's `confidence` is never a substitute for the Evidence Gate).
- **Actual task success, where possible, is established by an objective observable result** in the controlled test environment (e.g., did the replication command actually reproduce the planted vulnerability?) — the Judge evaluates *how well* the candidate performed relative to that outcome, it does not itself define the outcome.
- **The Judge does not automatically receive the entire original parsed/recon dataset.** It receives the **minimum relevant evaluation package**: the candidate's trajectory, actions performed, tool results the candidate itself produced, evidence generated, the candidate's claimed result, the objective outcome, and relevant resource/efficiency information. This reduces token use and reduces bias from over-exposure to context irrelevant to judging that specific candidate.
- **Candidate model identity/branding is hidden or minimized in comparative evaluation where practical**, to reduce model-family/name bias.
- **The winning candidate is the one that performs best against the defined evaluation criteria and the actual task outcome — never the one that wins a popularity/consensus vote among Judge opinions.**

**Do not reduce this protocol to "pick several models and let the biggest Judge choose."** The benchmark must remain controlled, repeatable, and tied to objective outcomes wherever possible.

### Practical Parameters (deliberately left unfixed)

- **Number of trials/cases per candidate:** determined by the evaluation experiment, not a fixed N at the architecture level. Run each candidate across enough representative trials/cases to establish that a result isn't a one-off success or failure; the exact count is adjusted per role, vulnerability class, and observed reliability.
- **Promotion threshold:** based on **actual demonstrated task performance** (per the trajectory dimensions above, including successful reproduction/demonstration of the target outcome), not an arbitrary universal numeric threshold fixed in advance. Additional role-specific scoring parameters may be defined as needed. The strongest candidate is selected based on validated performance, and the promotion decision itself remains a human one (see MODEL_REGISTRY.md).
- **Runtime/quantization:** candidates are evaluated under the configuration that represents how they'd actually be used (local, containerized, or a compatible external/cloud runtime) — models are not forced into one identical quantization/runtime merely for benchmark uniformity. Quantization/configuration is part of the candidate's implementation and is recorded as experiment provenance. The initial candidate pool should stay practical for the available execution environment rather than attempting to benchmark unlimited large models simultaneously.
- **Structured-output mechanism:** candidates are not forced to use an identical generation-constraint mechanism (GBNF vs. JSON mode vs. other) merely for fairness — the Judge/processing layer is responsible for arranging, validating, and storing each candidate's output correctly so results remain comparable.

**Absolute rule, unchanged: do not invent benchmark results, and do not claim a model has been benchmarked unless this repository contains the actual benchmark run output (the real trajectory, not a summary).** A `quality_metrics`/experiment field with a null value means "not yet measured" — never an estimate, vendor claim, or assumption. The illustrative candidates table in MODEL_REGISTRY.md intentionally shows `NOT_YET_BENCHMARKED` for every entry because no benchmark has been run in this documentation package.

**A candidate that fails the benchmark is recorded as `rejected` with the reason, not silently dropped.** A rejection is itself useful information for future candidate evaluation and belongs in the registry's history.

**Resulting validated trajectories/evaluations may later be used as training/evaluation data** for improving or fine-tuning role-specific models (fine-tuning itself remains user-controlled and ungated by a fixed threshold — see MODEL_REGISTRY.md).

### Where Benchmark Results Get Recorded

This document defines the *process*. The *results* live in MODEL_REGISTRY.md's Candidate Model Manifest entries (the `quality_metrics`, `benchmark_status`, and `approval_status` fields). Do not create a second results ledger — one canonical record per candidate, in the Model Registry.

### Relationship to Fine-Tuning

Fine-tuning (LoRA/QLoRA, per 01_ARCHITECTURE.md's non-goals and the Track A PRD's dataset lifecycle documentation) is gated behind demonstrated need: Plan A (an existing candidate, benchmarked and selected) must be shown insufficient, and a validated dataset of sufficient size must exist, before fine-tuning is considered. A fine-tuned model is itself just another candidate that must pass this same benchmarking protocol before promotion to `approved` — fine-tuning does not exempt a model from being measured.
