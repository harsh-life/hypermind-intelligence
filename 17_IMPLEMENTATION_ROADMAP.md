# Hypermind Track A — Implementation Timeline (First 10 Weeks)

**Status:** REVISED — canonical replacement for the prior implementation/roadmap document.
**Related documents:** 01_ARCHITECTURE.md · MODEL_REGISTRY.md · WORKER_SKILL_CONTRACTS.md · EVALUATION_BENCHMARKING.md · DARWIN_FUTURE.md

---

## Implementation Timeline

**[LOCKED — revised sequence]**

**The practical sequence, stated explicitly before the week-by-week table:** Track A does not require every specialist model to be internally developed before useful research can begin. The intended order is:

```
1. Build the minimum control/orchestration/evidence spine (Stage 0, Extractor, Evidence Gate, Registries as empty structures)
2. Integrate a small number of suitable existing model implementations (MODEL_REGISTRY.md candidates — local Qwen models first, since they require no benchmark to start using safely)
3. Benchmark them against their worker/skill contracts (EVALUATION_BENCHMARKING.md)
4. Use the working system on authorized targets/labs
5. Observe real bottlenecks and failures
6. Improve workers, contracts, evaluation, and orchestration from those observations
7. Accumulate validated evidence and reusable security patterns
8. Later use those validated capabilities/patterns as inputs to the specialist-swarm / Darwin research layer (DARWIN_FUTURE.md — future only)
```

**The goal of the first 10 weeks is to reach the first useful research loop quickly — not to spend the entire period building or fine-tuning models.** Do not turn Phase 2a into a full specialist swarm during this window.

| Week | Task |
|---|---|
| 1 | Docker setup. Tool Registry v1.0 written and committed. Sandbox (DVWA/Juice Shop) running. Extractor GBNF schema designed. Study 20 public IDOR disclosures. Model Registry scaffolded as an empty structure — no candidates benchmarked yet. |
| 2 | Extractor built and tested against sandbox nuclei/subfinder output, using the currently-selected local Qwen implementation (no benchmark required to start — it's already the default, lowest-risk choice). 3-strike escalation tested. Raw evidence preservation tested. |
| 3 | Worker manifests written (endpoint_mapper, object_reference_analyst, auth_analyzer) per the decoupled contract format (WORKER_SKILL_CONTRACTS.md). Worker output tested on sandbox ExtractorJSON using the default local Qwen candidate. |
| 4 | IDOR skill manifest written (methodology.md, system_prompt.md, few-shot examples) per the decoupled contract format (WORKER_SKILL_CONTRACTS.md). Judge role scaffolded (UNDECIDED model to be resolved — see MODEL_REGISTRY.md open item). |
| 5 | Full pipeline integration on sandbox using default candidates throughout. Scope Gate tests: 50+ cases. Evidence Gate tested. Deduplication tested. **First role-specific benchmark run (EVALUATION_BENCHMARKING.md)** — measure the default Qwen candidates against their actual worker/skill contracts on sandbox data, record real numbers (not estimates) in the Model Registry. |
| 6 | HumanReviewPackage assembly. Harsh runs replication_command on known sandbox finding — verified under 2 minutes? If the Week 5 benchmark surfaced a weak role, evaluate ONE additional candidate (e.g., an illustrative candidate from MODEL_REGISTRY.md) against that specific role's contract — do not batch-evaluate all candidates speculatively. |
| 7 | First real in-scope target selected (human decision). Full pipeline run, Pushpal + Harsh co-sign every step. Observe real bottlenecks — this is the first genuine signal for which roles need a better candidate or a contract fix. |
| 8 | First real IDOR submission attempt. Outcome drives all next decisions, including whether any Model Registry entry needs re-benchmarking based on real-target performance (not just sandbox performance). |
| 9 | SSRF pipeline: SSRF skill manifest written. cloud_metadata_flag logic implemented. Specialist role's currently-selected candidate tested on sandbox for this new skill — a new skill does NOT require a new model, only a new methodology behind the existing specialist_role_binding. |
| 10 | SSRF pipeline integrated. Both IDOR and SSRF pipelines running in parallel on separate in-scope targets. Any validated findings from Weeks 7–10 begin the evidence/pattern accumulation referenced in DARWIN_FUTURE.md (future) — recorded now, used later. |
