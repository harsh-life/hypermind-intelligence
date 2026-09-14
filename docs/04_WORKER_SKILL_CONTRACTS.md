# Hypermind Track A — Worker & Skill Contracts

**Status:** REVISED — canonical replacement for the prior worker/skill contract document.
**Related documents:** 01_ARCHITECTURE.md · MODEL_REGISTRY.md · EVALUATION_BENCHMARKING.md · IMPLEMENTATION_ROADMAP.md · DARWIN_FUTURE.md
**Core principle:** a worker or skill contract is independent of the underlying model. The contract defines the role; the Model Registry defines which model currently fulfils it. Swapping models never requires editing this document.

---

## Worker Registry & Manifests

**[LOCKED — architecture; PROVISIONAL — specific workers v1.0]**

Stage 1 is NOT "three 2–3B models." Stage 1 is N narrow specialist workers. Each worker is defined by a manifest. The number of workers is an implementation variable.

**[LOCKED]** The worker contract is independent of the underlying model. A worker's manifest defines the role, its input/output schema, its evidence obligations, and its limits — it does NOT hardcode which model fulfils it. Model selection lives in the Model Registry (see MODEL_REGISTRY.md) and is bound to the worker by role name only, so a model implementation can be replaced without editing the worker contract.

### Worker Manifest Schema

Every worker lives at `workers/{worker_id}/` and contains:

```
workers/{worker_id}/
├── manifest.json
├── system_prompt.md
└── schema.json
```

**manifest.json schema** — organized around the eight required contract fields (role, input, task, output, evidence, limits, escalation, quality):

```json
{
  "worker_id": "string — unique identifier",
  "version": "semver",
  "role": "string — one sentence: the analytical job this worker is responsible for",
  "input": {
    "schema_ref": "reference to schema.json#/input",
    "description": "string — what information this worker receives"
  },
  "task": "string — what reasoning/inference this worker performs on that input",
  "output": {
    "schema_ref": "reference to schema.json#/output",
    "description": "string — the required structured result"
  },
  "evidence": {
    "required_refs": ["fields the worker must cite from raw_evidence_path or upstream ExtractorJSON"],
    "rule": "every finding must reference the evidence it was derived from — no unreferenced claims"
  },
  "limits": {
    "cannot_decide": ["e.g., whether a finding is a real vulnerability — that is the Judge's job"],
    "cannot_execute": ["this worker never calls a tool or touches the execution environment directly"]
  },
  "escalation": {
    "policy": "human | discard | retry",
    "rule": "when evidence is insufficient, return status: PARTIAL or UNKNOWN — never invent a result to appear complete"
  },
  "quality": {
    "evaluated_via": "reference to EVALUATION_BENCHMARKING.md's Model Benchmarking Protocol",
    "success_criteria": "string — what a valid output looks like",
    "failure_criteria": "string — what constitutes a failed output"
  },
  "worker_role_binding": "string — the role name used to look up the current model implementation in MODEL_REGISTRY.md. This field is a POINTER, not a model identifier.",
  "allowed_tools": [],
  "context_window_tokens": 4096,
  "timeout_seconds": 60,
  "retry_limit": 2
}
```

**Why `worker_role_binding` is a pointer, not a model name:** the worker contract must survive a model swap unmodified. If the Model Registry's benchmark later selects a different implementation for the `endpoint_mapper` role, this manifest does not change — only the Model Registry entry does.

### Initial Workers (v1.0)

**workers/endpoint_mapper/**

```json
{
  "worker_id": "endpoint_mapper_v1",
  "role": "Map every reachable endpoint in the ExtractorJSON and identify those containing object references (numeric IDs, UUIDs, sequential parameters).",
  "worker_role_binding": "endpoint_mapper",
  "evidence": {
    "required_refs": ["ExtractorJSON.extracted_entities[].source_line_ref"],
    "rule": "every endpoint claim must cite the ExtractorJSON entity it came from"
  },
  "limits": {
    "cannot_decide": ["whether an object reference is exploitable — that is Stage 2 Judge + Stage 3 specialist"],
    "cannot_execute": ["no tool calls, no direct target contact"]
  },
  "escalation": {
    "policy": "discard",
    "rule": "if no object references found, status: SUCCESS with empty findings — not a failure"
  },
  "timeout_seconds": 60,
  "retry_limit": 2
}
```

**workers/object_reference_analyst/**

```json
{
  "worker_id": "object_reference_analyst_v1",
  "role": "Analyse object references found by the endpoint mapper. Determine whether IDs are sequential/guessable (IDOR risk) or UUIDs (low risk). Check whether authentication appears present on all HTTP methods for each endpoint.",
  "worker_role_binding": "object_reference_analyst",
  "evidence": {
    "required_refs": ["endpoint_mapper WorkerOutput.findings[].evidence_refs"],
    "rule": "sequential/UUID classification must reference the actual ID values observed, not an assumption"
  },
  "limits": {
    "cannot_decide": ["final IDOR classification — that is the Judge's role"],
    "cannot_execute": ["no tool calls, no direct target contact"]
  },
  "escalation": {
    "policy": "retry",
    "rule": "if ID pattern is ambiguous, status: PARTIAL with confidence < 0.5 — never guess sequential vs. UUID"
  },
  "timeout_seconds": 60,
  "retry_limit": 2
}
```

**workers/auth_analyzer/**

```json
{
  "worker_id": "auth_analyzer_v1",
  "role": "Analyse authentication and session structure. Identify JWT usage, OAuth flows, session token patterns, and any endpoint where authentication appears inconsistent or absent.",
  "worker_role_binding": "auth_analyzer",
  "evidence": {
    "required_refs": ["ExtractorJSON.extracted_entities[] where type == auth_pattern"],
    "rule": "every auth-inconsistency claim must cite the specific header/token/flow observed"
  },
  "limits": {
    "cannot_decide": ["whether an auth inconsistency is exploitable — that is Stage 2/3"],
    "cannot_execute": ["no tool calls, no direct target contact"]
  },
  "escalation": {
    "policy": "discard",
    "rule": "if auth pattern is unclear from available evidence, status: PARTIAL — never assume a flaw exists"
  },
  "timeout_seconds": 60,
  "retry_limit": 2
}
```

**Do not expand this worker set merely because additional cybersecurity models exist.** A new worker is added only when a genuinely new analytical job is needed — not because a new candidate model could theoretically fill an existing role differently (that's a Model Registry event, not a new worker).

### WorkerOutput Schema

```json
{
  "worker_id": "string",
  "version": "string",
  "target": "string",
  "timestamp": "ISO8601",
  "findings": [
    {
      "endpoint": "string",
      "observation": "string — evidence-based only, no speculation",
      "candidate_class": "IDOR | SSRF | AUTH_BYPASS | PRIV_ESC | UNKNOWN",
      "confidence": 0.0,
      "evidence_refs": ["reference to raw_evidence_path entries"]
    }
  ],
  "status": "SUCCESS | PARTIAL | FAILED",
  "failure_reason": "null unless FAILED"
}
```

---

## Skill Registry & Manifests

**[LOCKED — architecture; PROVISIONAL — skill content v1.0]**

Skills are SEPARATE from workers. A worker defines WHAT analytical job a model performs. A skill defines HOW to approach a specific vulnerability class.

**The Judge is neutral and uses no skill.** The specialist executor uses the skill.

### Skill Manifest Schema

Every skill lives at `skills/{skill_id}/` and contains:

```
skills/{skill_id}/
├── manifest.json
├── methodology.md
├── system_prompt.md
├── schema.json
└── references/
    └── (extracted methodology notes, provenance tracked)
```

**manifest.json schema:**

```json
{
  "skill_id": "string",
  "version": "semver",
  "vulnerability_class": "IDOR | SSRF | AUTH_BYPASS | PRIV_ESC",
  "description": "one paragraph on what this vulnerability class is",
  "required_evidence_fields": ["list of fields required before specialist runs"],
  "specialist_role_binding": "string — the role name used to look up the current model implementation in MODEL_REGISTRY.md. A pointer, not a model identifier — same decoupling rule as worker manifests above.",
  "plan": "PlanA_FewShot | PlanB_FineTuned",
  "few_shot_examples_path": "path to examples file",
  "required_output_fields": ["replication_command", "evidence", "poc_steps"],
  "cloud_metadata_flag_applicable": false,
  "provenance": {
    "references": ["source, license, version, what was extracted"]
  }
}
```

**Why this changed:** the skill manifest previously embedded `specialist_model` directly, conflating the skill (methodology) with the model implementation that executes it. The skill's methodology, few-shot examples, and required output fields must survive a specialist model swap unmodified — swapping from one open-weight candidate to another (see MODEL_REGISTRY.md) should never require touching `methodology.md` or this manifest.

### Initial Skills

**skills/idor/** — IDOR / BOLA
**skills/ssrf/** — SSRF including cloud metadata chain detection
**skills/auth_bypass/** — JWT / OAuth / Session flaws
**skills/priv_esc/** — Vertical and horizontal privilege escalation

Full methodology and system prompts are in each skill's `methodology.md` and `system_prompt.md`. They are NOT in this document — they are in the repository under `skills/`.

**Do not expand this skill set merely because additional cybersecurity models exist.** A new skill is added only when Track A takes on a genuinely new vulnerability class — not because a new candidate model happens to be good at something adjacent.
