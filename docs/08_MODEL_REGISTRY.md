# Hypermind Track A — Model Registry & Fallback Policy

**Status:** REVISED — canonical replacement for the prior MODEL_REGISTRY.md.
**Related documents:** 01_ARCHITECTURE.md · WORKER_SKILL_CONTRACTS.md · EVALUATION_BENCHMARKING.md · IMPLEMENTATION_ROADMAP.md · DARWIN_FUTURE.md
**Placement note:** the Failure Policy subsection below was previously drifted under the benchmarking document during an earlier edit pass. It has been moved back here, since it describes registry runtime behavior (what happens when a selected model times out or refuses), not benchmarking methodology. This is a placement correction, not a new decision — no content was changed, only relocated.

---

## Model Registry & Fallback Policy

**[LOCKED — revised: role-first, multi-candidate structure]**

Every model **role** in the pipeline has a registry entry. The Orchestrator never hardcodes a model name in application logic — it looks up the role's currently *selected implementation*. A role may have multiple candidate models under evaluation simultaneously; exactly one is marked `approved` and active at a time per role.

```
WORKER ROLE (e.g., "specialist_idor")
    ├── Candidate Model A (benchmark_status: PENDING)
    ├── Candidate Model B (benchmark_status: BENCHMARKED, approved: true)  ← currently selected
    ├── Candidate Model C (benchmark_status: REJECTED — failed false-positive threshold)
    ↓
EVALUATION_BENCHMARKING.md's Benchmark Protocol
    ↓
Selected Implementation (recorded here, referenced by worker_role_binding / specialist_role_binding)
```

**Do not add a candidate to this registry merely because it exists.** A model marketed as "cybersecurity," "pentest," "red-team," or "uncensored" is a candidate for evaluation, nothing more, until the benchmark protocol in EVALUATION_BENCHMARKING.md says otherwise.

### Candidate Model Manifest Schema

Every candidate model considered for any role — local or cloud, generic or security-branded — gets an entry with these fields:

```json
{
  "candidate_id": "string — unique identifier for this candidate entry",
  "model_identity": "string — exact model name and version, e.g. 'Qwen2.5-3B-Instruct' or 'fdtn-ai/Foundation-Sec-8B'",
  "source_provider": "string — e.g. 'Hugging Face / Alibaba', 'Hugging Face / Cisco Foundation AI', 'LiteLLM / Google'",
  "version": "string — exact release tag or commit",
  "intended_worker_role": "string — must match a role name in WORKER_SKILL_CONTRACTS.md (e.g., 'endpoint_mapper', 'specialist_idor')",
  "execution_location": "local | remote",
  "runtime_requirements": {
    "min_ram_gb": 0,
    "min_vram_gb": 0,
    "quantization": "e.g. Q4_K_M, fp16, none"
  },
  "input_format": "string — what the model expects (chat template, raw prompt, etc.)",
  "output_schema_compatibility": "gbnf | json_mode | none | requires_wrapper",
  "benchmark_status": "NOT_YET_BENCHMARKED | PENDING | BENCHMARKED | REJECTED",
  "quality_metrics": {
    "structured_output_validity_rate": null,
    "useful_hypothesis_rate": null,
    "false_positive_rate": null,
    "reference": "EVALUATION_BENCHMARKING.md — null until actually measured, never estimated"
  },
  "latency_ms_p50": null,
  "cost_per_call_usd": 0.0,
  "known_limitations": "string — documented weaknesses, e.g. 'markets itself as uncensored; independent Honeyquest benchmark showed elevated susceptibility to deceptive content (72% fell-for-trap rate) — treat marketing claims with skepticism, see EVALUATION_BENCHMARKING.md'",
  "security_suitability_notes": "string — anything relevant to running this model inside Track A's trust boundaries (see 01_ARCHITECTURE.md Section 6)",
  "approval_status": "candidate | approved | deprecated | rejected",
  "replacement_policy": "string — what triggers re-benchmarking or replacement of this candidate"
}
```

### Illustrative Candidates (examples only — NOT benchmarked, NOT approved)

These are real, verifiable open-weight models worth knowing exist. **None have been benchmarked against a Track A worker contract yet. None are approved. Listing them here is not adoption.**

| candidate_id | model_identity | source | license | benchmark_status | Note |
|---|---|---|---|---|---|
| cand-001 | Foundation-Sec-8B | Hugging Face / Cisco Foundation AI, released Apr 2025 | Apache 2.0 | NOT_YET_BENCHMARKED | Llama-3.1-8B continued-pretrained on cybersecurity corpus (threat intel, CVE data, IR docs). Competitive with much larger models on CTIBENCH per its technical report — a company claim, not yet independently verified by us. |
| cand-002 | Foundation-Sec-8B-Reasoning | Hugging Face / Cisco Foundation AI, released Jan 2026 | Apache 2.0 | NOT_YET_BENCHMARKED | Adds instruction-following + reasoning traces to cand-001. |
| cand-003 | WhiteRabbitNeo (V2/V2.5/V3) | Hugging Face / WhiteRabbitNeo | mixed (check per-release) | NOT_YET_BENCHMARKED | Explicitly marketed as "uncensored," Llama-3.1-8B/70B based. **Independent third-party evaluation (Honeyquest for LLMs, arXiv 2606.21037) measured WhiteRabbitNeo-2 falling for deceptive/trap content 72% of the time — the highest rate in that study's cohort, worse than frontier closed models on that specific measure.** This is the concrete evidence behind this document's rule that "uncensored" is not a quality criterion: the marketing claim and the independently measured behavior are not the same thing. |
| cand-004 | pentest-v2 (Qwen3-8B LoRA fine-tune) | Hugging Face (community, gewsefa) | Apache 2.0 (base) | NOT_YET_BENCHMARKED | LoRA rank-4 fine-tune on 2,804 examples from GTFOBins/HackTricks/HackTheBox/PayloadsAllTheThings. Self-reported 100% on a 10-task GTFOBins benchmark vs. ~25% zero-shot baseline — small sample, self-reported, not independently verified. Illustrates that a cheap community LoRA fine-tune is itself a viable candidate class worth benchmarking, not just base models. |

**The Honeyquest finding above is the single clearest piece of evidence for why this document insists on benchmarking over branding:** the model with the strongest "cybersecurity/offensive" marketing in this table performed *worst* on an independent behavioral measure. A candidate's name, license, or marketing copy tells you nothing about its fitness for a specific worker role. Only the benchmark protocol in EVALUATION_BENCHMARKING.md does.

### Currently Selected Implementations (v1.0 — subject to benchmarking)

This table records what is *currently running* per role. It is a snapshot of selected implementations, not a permanent architectural commitment — any row can change without touching the worker/skill contracts (WORKER_SKILL_CONTRACTS.md) or the pipeline architecture (01_ARCHITECTURE.md).

| Role | Currently Selected | Fallback 1 | Fallback 2 (eval-tier, cloud) | Constraint | Max Attempts |
|---|---|---|---|---|---|
| extractor | qwen2.5:1.5b (Ollama local) | qwen2.5:3b (Ollama local) | — | GBNF | 3 |
| worker (endpoint_mapper, object_reference_analyst, auth_analyzer) | qwen2.5:3b (Ollama local) | qwen2.5:1.5b (Ollama local) | — | GBNF | 2 |
| judge | UNDECIDED — must be distinct from specialist, local-hosted by default | qwen2.5:14b (Ollama local, candidate) | — | json_mode | 2 |
| specialist | qwen2.5:14b or qwen2.5:32b (local, hardware-permitting) — see hardware sizing note | qwen2.5:7b (local, lighter fallback) | gemini/gemini-1.5-flash (LiteLLM, cloud eval-tier only) | json_mode | 2 |
| report_polisher | qwen2.5:7b (local) | qwen2.5:3b (local) | gemini/gemini-1.5-flash (LiteLLM, cloud eval-tier only) | none | 1 |

**Note on hardware sizing:** the specific local model size for the specialist role (7B/14B/32B) depends on what the host machine can run. Benchmark against the smallest model first (7B) and only move up if the smaller model demonstrably fails to produce valid `SpecialistPoCOutput` at an acceptable rate. This is itself an application of Rule 2 (determinism/simplicity first, see 01_ARCHITECTURE.md Section 4) to model selection.

**Note on the illustrative candidates table above:** none of Foundation-Sec-8B, WhiteRabbitNeo, or the pentest-v2 LoRA fine-tune are in the "currently selected" table. They are unevaluated candidates for the `specialist` and `worker` roles once the benchmark protocol (EVALUATION_BENCHMARKING.md) has been run against them. Do not promote any of them to "currently selected" without a completed benchmark entry. **[Updated 2026-09-15]** No candidate — security-branded/"uncensored" or otherwise — is architecturally excluded from any role, including Judge, on the basis of branding or origin alone; see the model-selection philosophy note below.

**[RESOLVED 2026-09-15 — see `13_OPEN_DECISIONS.md` OD-22 and role-initialization decisions]** The items below were previously open; they are now locked:

- **Judge model identity is not permanently selected at the architecture level, and this is intentional, not a gap.** Judge implementations are treated as interchangeable "Lego" building blocks: the **initial** Judge candidate is a heavyweight cloud model capable of strong reasoning and evaluation, but additional Judge candidates may be added or removed later by the user, and the winning implementation remains fully replaceable per the existing role/contract/model-implementation separation (§ "Model Implementation vs. Architecture" in `01`). No Judge model identity is ever hardcoded as *the* architectural winner.
- **Judge/Specialist model-family diversity is not a mandatory architecture-level restriction.** The user decides which model components are used together for a given configuration; diversity may be considered during evaluation but is not a hard registry constraint. (This explicitly reverses the diversity-mandate recommendation this document previously carried under OD-22 — see `13_OPEN_DECISIONS.md` for the reasoning and the risk this consciously accepts.)
- **No architecture-level exclusion exists against "security-branded," "uncensored," or similarly positioned models for any role, including Judge.** Model selection is user-controlled; candidates are evaluated per the trajectory-based benchmark (`13_OPEN_DECISIONS.md` OD-27, `16`) rather than rejected solely for branding or origin. The Honeyquest/WhiteRabbitNeo evidence in this document's candidate table remains valid and relevant *as benchmark input*, not as a categorical exclusion rule.
- **Report Polisher is treated as another Judge-like model/component**, not a fundamentally separate model category — it follows the same interchangeable-implementation, benchmark-before-promotion discipline as any Judge candidate.
- **Initial candidate set is role-specific, not one fixed model system-wide:** Judge starts with a heavyweight cloud model; Worker uses a small model specialized for its specific job; Specialist uses a model demonstrated to perform well with the relevant knowledge/data pipeline for that specialist task (the attached knowledge pipeline may be expanded/reduced/changed per the specialist's actual requirements); Report Polisher is Judge-like per above.
- **Re-benchmarking of an already-approved model is user-controlled** — no automatic re-benchmark trigger exists for MVP (e.g., on an upstream model update).
- **Model licensing is a user-controlled decision for MVP** — no rigid architecture-level license-exclusion policy is enforced at this stage.
- **Model serving is not locked to Ollama as the sole backend.** Different candidates may use different compatible inference backends/runtimes where necessary, provided they satisfy the same role contract and are evaluated under controlled conditions — the model interface remains runtime-agnostic so HF/open-weight candidates aren't excluded merely for requiring a different serving mechanism.
- **Fine-tuning trigger is user-controlled, not an automatic threshold.** The system may accumulate validated trajectories/results/evaluation artifacts usable for fine-tuning later, but there is no automatic fine-tuning trigger or mandatory numeric threshold enforced by the architecture in the MVP — the user decides when accumulated evidence is sufficient and when a fine-tuned model is ready to replace a candidate. **Note:** this loosens the specific "2,000+ validated proprietary examples" numeric gate stated elsewhere (`01` §3, `16`) — see `13_OPEN_DECISIONS.md` §3 item 3, flagged there as not yet reconciled with that `[LOCKED]` text.

### Failure Policy — Technical Failure vs. Model Refusal

These are fundamentally different failure modes and handled differently:

**Technical failure** (timeout, malformed JSON despite constraint, network error): retry with the same model up to retry_limit, then try fallback models in order, then escalate to human.

**Model refusal** (model returns "I cannot assist with this" or equivalent): do NOT retry to defeat the refusal. Do NOT rephrase to circumvent. Classify the refusal type, check whether a fallback model is approved for this task, try the fallback. If all approved models refuse, fail closed → human review. The pipeline never jailbreaks its own models.

```
Primary model
      │
      ▼
Task
      │
  ┌───┴──────────┐
  │              │
Success    Technical failure or Refusal?
  │              │
  ▼          ┌──┴───────────────────┐
Continue     │                      │
          Technical failure     Model refusal
             │                      │
          Retry with           Check fallback
          same model           models list
             │                      │
         (retry_limit)         Approved?
             │                 YES  │  NO
             ▼                  │   ▼
         Fallback 1         Try    Fail closed
         (if exists)        fallback → human
```
