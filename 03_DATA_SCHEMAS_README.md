# 03_DATA_SCHEMAS/README.md
## Hypermind — Track A — Data Schema Specifications

**Document:** STEP 03 of 15 · Track A Documentation Package
**Status:** Implementation-ready schema definitions
**Depends on:** `01_ARCHITECTURE.md` (pipeline, trust boundaries, evidence ladder), `02_COMPONENT_SPECS.md` (which component produces/consumes which schema)
**Feeds forward to:** `04`/`05`/`06`/`08` (concrete manifest instances conforming to the manifest schemas defined here), `10_RESEARCH_DATA_PIPELINE.md` (usage policy for the research-data objects defined here), `11`/`12` (schema-validation tests and gates)

---

## How to Read This Document

This is the **first** document where these types are actually defined — `01` and `02` referenced schema names but deferred field-level content here. This document does not point elsewhere for its core content.

To honor "don't repeat overlap," this document factors out structures shared by many schemas into **Common Types** (§1), defined once. Every schema below references them by name (e.g. "see Common Type: Provenance") rather than repeating their fields. Do not copy Provenance's fields into an individual schema's field table — reference it.

Every schema table has the same columns: **Field | Type | Required | Constraint / Enum | Notes**. Every schema ends with one valid example and one invalid example with the reason it's invalid.

Label legend is unchanged from `01`/`02` — **[LOCKED] [REQ] [REC] [ASSUMPTION] [OPEN — REQUIRES HARSH] [FUTURE] [INFERENCE]**. Since most concrete field choices here are engineering decisions the master prompt didn't specify at field level, most are tagged **[REC]** (a sound default, changeable with justification) unless they encode something already locked in `01`/`02`.

---

## Schema Index

| # | Schema | Category | Produced by (see `02`) | Consumed by |
|---|---|---|---|---|
| — | Provenance *(common type)* | Shared | — | embedded in nearly all schemas below |
| — | TrustClassification *(common type)* | Shared | — | embedded in observation→validated ladder schemas |
| 1 | ScopeRequest | Pipeline | Human / Scope Gate caller | Scope Gate (7) |
| 2 | ScopeDecision | Pipeline | Scope Gate (7) | Orchestrator (11) |
| 3 | OrchestratorAction | Pipeline | Orchestrator's planning LLM (11) | Orchestrator's check chain (11) |
| 4 | ToolManifest | Registry | (config, populated in `06`) | Tool Registry (1) |
| 5 | ToolExecutionRequest | Pipeline | Orchestrator (11) | Docker Tool Execution Engine (12) |
| 6 | ToolExecutionResult | Pipeline | Docker Tool Execution Engine (12) | Orchestrator / audit |
| 7 | RawToolOutput | Pipeline | Docker Tool Execution Engine (12) | Extractor (13) |
| 8 | ExtractorInput | Pipeline | Docker Tool Execution Engine (12) | Extractor (13) |
| 9 | ExtractorJSON | Pipeline | Extractor (13) | Worker Execution Framework (14) |
| 10 | WorkerManifest | Registry | (config, populated in `04`) | Worker Registry (2) |
| 11 | WorkerInput | Pipeline | Worker Execution Framework (14) | Worker model invocation |
| 12 | WorkerOutput | Pipeline | Worker Execution Framework (14) | Neutral Judge (15) |
| 13 | JudgeInput | Pipeline | Neutral Judge caller (14→15 assembly) | Neutral Judge (15) |
| 14 | JudgeRoutingDecision | Pipeline | Neutral Judge (15) | Specialist Executor (16) |
| 15 | SkillManifest | Registry | (config, populated in `05`) | Skill Registry (3), Specialist Executor (16) |
| 16 | SpecialistInput | Pipeline | Specialist Executor (16) | Specialist model invocation |
| 17 | SpecialistPoCOutput | Pipeline | Specialist Executor (16) | Evidence Gate (9) |
| 18 | EvidenceGateResult | Pipeline | Evidence Gate (9) | Deduplication Engine (10) |
| 19 | DeduplicationResult | Pipeline | Deduplication Engine (10) | Human Verification Interface (18) |
| 20 | HumanReviewPackage | Pipeline | Deduplication Engine (10) | Human Verification Interface (18) |
| 21 | Report | Pipeline | Report Polisher (17) | Human submission |
| 22 | AuditEvent | Cross-cutting | Any component | Research/Audit Store (19) |
| 23 | FailureEvent | Cross-cutting | Any component | Research/Audit Store (19) |
| 24 | ResearchEvent | Research | Any component (via emit) | Research/Audit Store (19), offline tooling |
| 25 | FindingRecord | Research | derived from ValidationOutcome=submit | Offline evaluation |
| 26 | CandidateFindingRecord | Research | derived from SpecialistPoCOutput | Offline evaluation |
| 27 | ReplicationRecord | Research | derived from SpecialistPoCOutput.replication_command | Offline evaluation, future chaining research |
| 28 | ValidationOutcome | Pipeline + Research | Human Verification Interface (18) | Report Polisher (17), Research Store (19) |
| 29 | ExperimentRecord | Research | Offline tooling (model benchmarking) | Model Registry (4) evaluation metadata |
| 30 | ToolSequenceRecord | Research | derived from AuditEvent stream | Offline strategy/sequence analysis |
| 31 | ModelEvaluationRecord | Research | Offline tooling | Model Registry (4) |
| 32 | DatasetRecord | Research | Offline tooling | `10`'s dataset versioning policy |
| 33 | ModelVersionRecord | Research | Model Registry (4) | Offline tooling, `10` |

---

# §1 — Common Types (Referenced, Not Repeated)

## 1.1 Provenance

Embedded in nearly every schema below. Defined once here.

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `record_id` | string (UUID v4) | Yes | UUID format | Unique per record instance **[REC]** |
| `run_id` | string (UUID v4) | Yes | UUID format | Correlates every record from one pipeline run against one target — the join key for reconstructing a full run's history |
| `created_at` | string (ISO 8601 timestamp, UTC) | Yes | e.g. `2026-08-31T10:15:00Z` | |
| `stage` | string (enum) | Yes | one of: `scope_gate`, `trust_boundary_a`, `orchestrator`, `tool_execution`, `extractor`, `worker`, `judge`, `specialist`, `evidence_gate`, `deduplication`, `human_verification`, `report_polisher` | Must match a component from `02`'s Component Index |
| `source_component` | string | Yes | Must match a component name from `02`'s Component Index (§ headers, e.g. "Neutral Judge") | Human-readable; `stage` is the machine key, this is the display name |
| `model_id` | string | No | Required *if* this record was produced by a model call | References a `ModelManifest.model_id` from `08` |
| `model_version` | string | No | Required if `model_id` present | |
| `tool_id` | string | No | Required *if* this record was produced by a tool execution | References a `ToolManifest.tool_id` from `06` |
| `tool_version` | string | No | Required if `tool_id` present | |

**Validation [LOCKED]:** exactly one of `model_id`/`tool_id` may be set for any given record, or neither (e.g. a deterministic gate like the Evidence Gate sets neither) — never both, since a single record is produced by either a model or a tool execution, not both simultaneously.

## 1.2 TrustClassification

The observation → interpretation → candidate → validated ladder from `01` §8, formalized as a required enum field on every schema that carries data along it.

| Value | Meaning | First appears at (schema) |
|---|---|---|
| `RAW_OBSERVATION` | Untrusted, target-controlled, unprocessed | RawToolOutput (7) |
| `MODEL_INTERPRETATION` | A model's reading of an observation — not yet a claim about a vulnerability | ExtractorJSON (9), WorkerOutput (12) |
| `CANDIDATE_FINDING` | A specific vulnerability claim with proposed evidence, not yet human-confirmed | SpecialistPoCOutput (17) |
| `VALIDATED_FINDING` | Passed Evidence Gate + explicit human SUBMIT | ValidationOutcome (28), FindingRecord (25) |

**[LOCKED]** No code path may set `trust_classification` to `VALIDATED_FINDING` except the Human Verification Interface writing a `ValidationOutcome` with `decision: submit`. This is the schema-level enforcement of `01`'s "only human validation produces ground truth" principle — `12_ACCEPTANCE_CRITERIA/` will include a test asserting no other component ever emits this value.

---

# §2 — Pipeline Schemas (in pipeline order)

## 2.1 ScopeRequest

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = scope_gate` | |
| `target_identifier` | string | Yes | e.g. domain, IP range, program handle | The thing being requested for authorization |
| `authorization_reference` | string | Yes | e.g. bounty-program scope-doc URL or ID | Must point to human-verifiable proof of authorization — this field existing does not itself grant scope; the Scope Gate/Policy Engine evaluates it |
| `requested_by` | string | Yes | human identifier | Who is asking |
| `notes` | string | No | free text | |

**Valid example:**
```json
{
  "provenance": {"record_id": "a1...", "run_id": "r1...", "created_at": "2026-08-31T10:00:00Z", "stage": "scope_gate", "source_component": "Scope Gate"},
  "target_identifier": "*.example-bounty.com",
  "authorization_reference": "https://bugcrowd.com/example-program/scope",
  "requested_by": "harsh",
  "notes": "New quarter, re-confirming scope before first run"
}
```

**Invalid example (reason: missing authorization_reference — a target cannot be requested without a pointer to proof of authorization):**
```json
{
  "provenance": {"...": "..."},
  "target_identifier": "*.example-bounty.com",
  "requested_by": "harsh"
}
```

## 2.2 ScopeDecision

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = scope_gate` | |
| `request_record_id` | string (UUID) | Yes | must reference a ScopeRequest.provenance.record_id | |
| `decision` | string (enum) | Yes | `allow` \| `deny` | **[LOCKED]** ambiguous cases must resolve to `deny` per `02` §7 |
| `reason` | string | Yes | | Machine-readable reason, always present even on allow, for audit completeness |
| `policy_version` | string | Yes | | Which Rego policy bundle version evaluated this |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "scope_gate"},
  "request_record_id": "a1...",
  "decision": "allow",
  "reason": "target matches authorized scope pattern *.example-bounty.com",
  "policy_version": "scope-policy-v3"
}
```

**Invalid example (reason: `decision` value not in enum):**
```json
{
  "decision": "maybe",
  "reason": "unclear",
  "policy_version": "scope-policy-v3"
}
```

## 2.3 OrchestratorAction

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = orchestrator`, `model_id`/`model_version` required (this is a model-proposed record) | |
| `proposed_action_type` | string (enum) | Yes | `tool_execution` \| `worker_invocation` \| `specialist_investigation` | What kind of action is being proposed |
| `target_registry_id` | string | Yes | a tool_id, worker_id, or skill_id depending on `proposed_action_type` | This is what gets checked against the relevant registry |
| `proposed_parameters` | object | Yes | shape depends on `proposed_action_type` | e.g. for `tool_execution`, this becomes the basis of a `ToolExecutionRequest` if authorized |
| `session_action_count` | integer | Yes | ≥ 1 | Session-scoped counter per `02` §11 State — used for bounded-retry/loop-prevention (exact bound is OD-02) |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "orchestrator", "model_id": "planner-model", "model_version": "v1"},
  "proposed_action_type": "tool_execution",
  "target_registry_id": "subfinder",
  "proposed_parameters": {"domain": "example-bounty.com"},
  "session_action_count": 1
}
```

**Invalid example (reason: `proposed_action_type` not in enum — this is exactly the kind of proposal the Orchestrator's schema-validation check, `02` §11, must reject before even reaching scope/registry checks):**
```json
{
  "proposed_action_type": "delete_all_findings",
  "target_registry_id": "n/a",
  "proposed_parameters": {}
}
```

## 2.4 ToolManifest

**[LOCKED field list — matches master-prompt STEP 06 exactly; this schema is the structural contract, concrete instances are `06_TOOL_REGISTRY/`.]**

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `tool_id` | string | Yes | unique | |
| `name` | string | Yes | | |
| `version` | string | Yes | pinned, e.g. semver or commit hash | |
| `purpose` | string | Yes | | |
| `category` | string (enum) | Yes | Canonical value set lives in the Tool Registry (`06`), not fixed here — current values: `recon` \| `ai_security` \| `web_probe` \| `vulnerability_scan` (the 4th, `vulnerability_scan`, was added by `06` for Nuclei under the extension permission below) | **[REC]** — extend as needed via registry update, not a code change; this schema doc states the set as of last update, the registry is authoritative for the current set |
| `input_schema` | object (JSON Schema) | Yes | | Defines what a valid `ToolExecutionRequest.parameters` looks like for this tool |
| `output_schema` | object (JSON Schema) | No | | Best-effort; tool output is inherently untrusted/variable, so this is advisory, not strictly enforced the way `input_schema` is |
| `container_image` | string | Yes | pinned digest, not a mutable tag | See `07_DOCKER_SPEC/` for full policy |
| `network_requirements` | object | Yes | least-privilege description | See `07` |
| `filesystem_requirements` | object | Yes | | See `07` |
| `resource_limits` | object | Yes | CPU/memory/PID ceilings | See `07`; exact defaults are OD-02 |
| `timeout_seconds` | integer | Yes | > 0 | |
| `allowed_stages` | array of string | Yes | subset of pipeline stage names | Where in the pipeline this tool may legitimately be invoked |
| `risk_classification` | string (enum) | Yes | `low` \| `medium` \| `high` | Informs audit scrutiny level |
| `failure_handling` | string | Yes | free text describing tool-specific failure notes | |
| `audit_requirements` | string | Yes | free text | e.g. "log full command line, redact secrets" |

**Valid example (abbreviated):**
```json
{
  "tool_id": "subfinder",
  "name": "Subfinder",
  "version": "v2.6.3",
  "purpose": "passive subdomain enumeration",
  "category": "recon",
  "input_schema": {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]},
  "container_image": "sha256:abc123...",
  "network_requirements": {"egress": "dns + https only"},
  "filesystem_requirements": {"read_only_root": true},
  "resource_limits": {"cpu": "1", "memory_mb": 512},
  "timeout_seconds": 120,
  "allowed_stages": ["tool_execution"],
  "risk_classification": "low",
  "failure_handling": "on timeout, treat partial output as untrusted, do not retry automatically",
  "audit_requirements": "log domain input and exit code"
}
```

**Invalid example (reason: `container_image` uses a mutable tag `:latest` instead of a pinned digest, violating `07`'s reproducibility requirement):**
```json
{
  "tool_id": "subfinder",
  "container_image": "projectdiscovery/subfinder:latest"
}
```

## 2.5 ToolExecutionRequest

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = orchestrator` (this is what the Orchestrator authorizes) | |
| `tool_id` | string | Yes | must resolve via Tool Registry | |
| `parameters` | object | Yes | must validate against `ToolManifest.input_schema` | |
| `authorized_by_action_id` | string (UUID) | Yes | references the OrchestratorAction that this request fulfills | Traceability from proposal to authorized execution |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "orchestrator"},
  "tool_id": "subfinder",
  "parameters": {"domain": "example-bounty.com"},
  "authorized_by_action_id": "a2..."
}
```

**Invalid example (reason: `parameters` does not satisfy `subfinder`'s declared input_schema — missing required `domain`):**
```json
{
  "tool_id": "subfinder",
  "parameters": {},
  "authorized_by_action_id": "a2..."
}
```

## 2.6 ToolExecutionResult

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = tool_execution`, `tool_id`/`tool_version` required | |
| `request_record_id` | string (UUID) | Yes | references the ToolExecutionRequest | |
| `exit_status` | string (enum) | Yes | `success` \| `timeout` \| `crash` \| `resource_exhausted` | |
| `duration_ms` | integer | Yes | ≥ 0 | |
| `raw_output_record_id` | string (UUID) | No | required if `exit_status = success` or partial output was captured | References the associated `RawToolOutput` |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "tool_execution", "tool_id": "subfinder", "tool_version": "v2.6.3"},
  "request_record_id": "b1...",
  "exit_status": "success",
  "duration_ms": 4213,
  "raw_output_record_id": "c1..."
}
```

**Invalid example (reason: `exit_status = success` but no `raw_output_record_id` — a successful execution must reference its output):**
```json
{
  "request_record_id": "b1...",
  "exit_status": "success",
  "duration_ms": 4213
}
```

## 2.7 RawToolOutput

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = tool_execution` | |
| `trust_classification` | TrustClassification | Yes | must equal `RAW_OBSERVATION` | **[LOCKED]** — this is the schema-level marker that the content crosses TB-B |
| `content` | string | Yes | raw text/binary-as-base64 | **[LOCKED]** must never be parsed as instructions by any downstream consumer — enforced at the Extractor per `02` §13 |
| `truncated` | boolean | Yes | | true if output exceeded a capture size limit (limit is OD-02-adjacent, not fixed here) |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "tool_execution", "tool_id": "subfinder", "tool_version": "v2.6.3"},
  "trust_classification": "RAW_OBSERVATION",
  "content": "sub1.example-bounty.com\nsub2.example-bounty.com\n",
  "truncated": false
}
```

**Invalid example (reason: `trust_classification` set to something other than `RAW_OBSERVATION` — a raw tool output must never claim a higher trust level than it has earned):**
```json
{
  "trust_classification": "VALIDATED_FINDING",
  "content": "...",
  "truncated": false
}
```

## 2.8 ExtractorInput

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = extractor` | |
| `raw_output_record_id` | string (UUID) | Yes | references a RawToolOutput | This schema is essentially a typed pointer + context, not a copy of the raw content, to avoid duplicating potentially large/untrusted payloads across records **[REC]** |
| `extraction_target_schema` | string | Yes | e.g. `"ExtractorJSON.v1"` | Which output shape the Extractor is being asked to produce |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "extractor"},
  "raw_output_record_id": "c1...",
  "extraction_target_schema": "ExtractorJSON.v1"
}
```

**Invalid example (reason: references a `raw_output_record_id` that doesn't exist — referential integrity failure):**
```json
{
  "raw_output_record_id": "nonexistent-id",
  "extraction_target_schema": "ExtractorJSON.v1"
}
```

## 2.9 ExtractorJSON

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = extractor`, `model_id`/`model_version` required | |
| `trust_classification` | TrustClassification | Yes | must equal `MODEL_INTERPRETATION` | |
| `source_raw_output_record_id` | string (UUID) | Yes | references the RawToolOutput this was extracted from | Preserves the observation→interpretation link |
| `entities` | array of object | Yes | shape: `{type: string, value: string, confidence: float 0-1}` | Structured, normalized findings — e.g. endpoints, parameters found |
| `schema_valid` | boolean | Yes | must be `true` for this record to exist at all | Per `02` §13, non-schema output is rejected before it becomes an ExtractorJSON record — this field is present for audit completeness even though it should always be true in a persisted record |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "extractor", "model_id": "qwen-extractor", "model_version": "1.5b-q4"},
  "trust_classification": "MODEL_INTERPRETATION",
  "source_raw_output_record_id": "c1...",
  "entities": [
    {"type": "endpoint", "value": "/api/v1/users/{id}", "confidence": 0.94}
  ],
  "schema_valid": true
}
```

**Invalid example (reason: `confidence` out of 0-1 range):**
```json
{
  "entities": [{"type": "endpoint", "value": "/api/v1/users/{id}", "confidence": 1.5}],
  "schema_valid": true
}
```

## 2.10 WorkerManifest

**[LOCKED field list — matches master-prompt STEP 04 exactly.]**

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `worker_id` | string | Yes | unique | |
| `purpose` | string | Yes | | |
| `input_schema` | object (JSON Schema) | Yes | | validates WorkerInput.payload |
| `output_schema` | object (JSON Schema) | Yes | | validates WorkerOutput.payload |
| `model` | string | Yes | references a Model Registry role/model_id | |
| `system_prompt` | string | Yes | | |
| `allowed_tools` | array of string | Yes | may be empty | Per `02` §14, this is enforced at the framework level, not just prompted |
| `timeout_seconds` | integer | Yes | > 0 | |
| `retry_limit` | integer | Yes | ≥ 0 | |
| `resource_limits` | object | Yes | | |
| `success_criteria` | string | Yes | free text | |
| `failure_criteria` | string | Yes | free text | |
| `must_not` | array of string | Yes | may be empty | **[REQ]** — explicit prohibited behaviors, enforced structurally where possible per `02` §14 |
| `provenance_requirements` | string | Yes | free text describing what this worker must log | |

**Valid example (abbreviated):**
```json
{
  "worker_id": "endpoint_mapper",
  "purpose": "map discovered endpoints from ExtractorJSON entities",
  "input_schema": {"type": "object"},
  "output_schema": {"type": "object"},
  "model": "worker-model-candidate-a",
  "system_prompt": "You map API endpoints. You do not evaluate whether any endpoint is vulnerable.",
  "allowed_tools": [],
  "timeout_seconds": 30,
  "retry_limit": 2,
  "resource_limits": {"max_tokens": 2048},
  "success_criteria": "produces a structured endpoint map",
  "failure_criteria": "output is not valid JSON or contains no endpoints when input clearly had some",
  "must_not": ["evaluate vulnerability likelihood", "propose exploit steps"],
  "provenance_requirements": "log input entity count and output endpoint count"
}
```

**Invalid example (reason: `must_not` is missing entirely — required per this schema, since it's the structural enforcement point from `02` §14):**
```json
{
  "worker_id": "endpoint_mapper",
  "purpose": "map endpoints"
}
```

## 2.11 WorkerInput

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = worker` | |
| `worker_id` | string | Yes | must resolve via Worker Registry | |
| `payload` | object | Yes | must validate against the resolved `WorkerManifest.input_schema` | |
| `source_extractor_record_id` | string (UUID) | Yes | references the ExtractorJSON this worker is analyzing | |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "worker"},
  "worker_id": "endpoint_mapper",
  "payload": {"entities": [{"type": "endpoint", "value": "/api/v1/users/{id}"}]},
  "source_extractor_record_id": "d1..."
}
```

**Invalid example (reason: `worker_id` references an unregistered worker):**
```json
{
  "worker_id": "nonexistent_worker",
  "payload": {}
}
```

## 2.12 WorkerOutput

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = worker`, `model_id`/`model_version` required | |
| `trust_classification` | TrustClassification | Yes | must equal `MODEL_INTERPRETATION` | |
| `worker_id` | string | Yes | | |
| `payload` | object | Yes | must validate against `WorkerManifest.output_schema` | |
| `retry_count` | integer | Yes | ≥ 0 | |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "worker", "model_id": "worker-model-candidate-a", "model_version": "v1"},
  "trust_classification": "MODEL_INTERPRETATION",
  "worker_id": "endpoint_mapper",
  "payload": {"mapped_endpoints": [{"path": "/api/v1/users/{id}", "method": "GET"}]},
  "retry_count": 0
}
```

**Invalid example (reason: `trust_classification` incorrectly set to `CANDIDATE_FINDING` — a Worker interprets, it does not produce a vulnerability candidate; that's the Specialist's job):**
```json
{
  "trust_classification": "CANDIDATE_FINDING",
  "worker_id": "endpoint_mapper",
  "payload": {}
}
```

## 2.13 JudgeInput

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = judge` | |
| `worker_output_record_ids` | array of string (UUID) | Yes | ≥ 1 | The WorkerOutputs being assembled for evaluation |
| `accumulated_evidence` | object | Yes | | Free-form structured accumulation across possibly-multiple worker outputs |
| `contains_skill_content` | boolean | Yes | **must equal `false`** | **[LOCKED]** — schema-level assertion enforcing the Judge Principle; `12`'s Judge-neutrality gate validates this field is always false on every JudgeInput record ever created |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "judge"},
  "worker_output_record_ids": ["e1...", "e2..."],
  "accumulated_evidence": {"endpoints": ["/api/v1/users/{id}"], "auth_findings": []},
  "contains_skill_content": false
}
```

**Invalid example (reason: `contains_skill_content = true` — this record must never be constructible with this value; its presence at all in a real record is a critical audit finding):**
```json
{
  "contains_skill_content": true,
  "accumulated_evidence": {"idor_methodology": "try incrementing user IDs..."}
}
```

## 2.14 JudgeRoutingDecision

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = judge`, `model_id`/`model_version` required | |
| `decision` | string (enum) | Yes | `route_to_skill` \| `needs_more_evidence` \| `drop` | |
| `target_skill_id` | string | No | required if `decision = route_to_skill`; must resolve via Skill Registry | |
| `reasoning` | string | Yes | | Judge's stated reasoning — required for audit and for the `14` neutrality check |
| `confidence` | float | Yes | 0.0–1.0 | **[REQ]** per `01`'s evidence-over-confidence principle: this field exists for logging/research purposes only and must never be treated as sufficient on its own to bypass the Evidence Gate downstream |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "judge", "model_id": "judge-model", "model_version": "v1"},
  "decision": "route_to_skill",
  "target_skill_id": "idor_v1",
  "reasoning": "endpoint pattern and object-reference usage are consistent with IDOR investigation prerequisites",
  "confidence": 0.78
}
```

**Invalid example (reason: `decision = route_to_skill` but `target_skill_id` is missing):**
```json
{
  "decision": "route_to_skill",
  "reasoning": "looks promising",
  "confidence": 0.78
}
```

## 2.15 SkillManifest

**[LOCKED field list — matches master-prompt STEP 05 exactly.]**

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `skill_id` | string | Yes | unique | |
| `vulnerability_class` | string | Yes | **[REC]** validated against the Skill Registry's known set rather than a hard-coded enum, to preserve the "swappable Skills" extensibility principle from `01` §4 — see note below | |
| `methodology` | string | Yes | free text | |
| `system_prompt` | string | Yes | | |
| `few_shot_examples` | array of object | Yes | may be empty for a new skill | Sourced from validated research data per `10`, never from unvalidated candidates |
| `references` | array of string | Yes | may be empty | e.g. OWASP references |
| `expected_inputs` | object (JSON Schema) | Yes | | |
| `expected_outputs` | object (JSON Schema) | Yes | | Should require a `replication_command`-shaped field, consistent with `02` §16 |
| `permissions` | array of string | Yes | may be empty | What this Skill's Specialist invocation is allowed to reference (e.g. which tools' outputs) |
| `version` | string | Yes | | |
| `provenance` | Provenance | Yes | | Who/what created this manifest version |
| `validation_status` | string (enum) | Yes | `draft` \| `active` \| `deprecated` | |

**[REC note on `vulnerability_class`:** a fully closed enum (IDOR/SSRF/AUTH_BYPASS/PRIVILEGE_ESCALATION) is simpler to validate but requires a schema change to add a new class, which conflicts with "skills must be swappable" (`01` §4). Recommend treating this as a registry-validated string (checked against currently-registered Skill entries) rather than a hard enum. This is a genuine design trade-off, not something to silently lock — flagged as **OD-12** below.]

**Valid example (abbreviated):**
```json
{
  "skill_id": "idor_v1",
  "vulnerability_class": "IDOR",
  "methodology": "Test object reference manipulation across authenticated endpoints...",
  "system_prompt": "You investigate IDOR vulnerabilities using the following methodology...",
  "few_shot_examples": [],
  "references": ["https://owasp.org/www-community/attacks/..."],
  "expected_inputs": {"type": "object"},
  "expected_outputs": {"type": "object", "required": ["replication_command"]},
  "permissions": ["read_endpoint_map", "read_auth_findings"],
  "version": "1.0.0",
  "provenance": {"...": "...", "stage": "specialist"},
  "validation_status": "active"
}
```

**Invalid example (reason: `expected_outputs` doesn't require `replication_command` — violates the reproducibility requirement from `01`/`02`):**
```json
{
  "skill_id": "idor_v1",
  "expected_outputs": {"type": "object"}
}
```

## 2.16 SpecialistInput

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = specialist` | |
| `skill_id` | string | Yes | must resolve via Skill Registry | |
| `evidence_context` | object | Yes | | Assembled from JudgeRoutingDecision + accumulated evidence |
| `judge_routing_record_id` | string (UUID) | Yes | references the JudgeRoutingDecision that authorized this investigation | |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "specialist"},
  "skill_id": "idor_v1",
  "evidence_context": {"endpoints": ["/api/v1/users/{id}"]},
  "judge_routing_record_id": "f1..."
}
```

**Invalid example (reason: `skill_id` doesn't resolve — must fail the Skill Registry lookup, not proceed with a null methodology):**
```json
{
  "skill_id": "unregistered_skill_xyz",
  "evidence_context": {}
}
```

## 2.17 SpecialistPoCOutput

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = specialist`, `model_id`/`model_version` required | |
| `trust_classification` | TrustClassification | Yes | must equal `CANDIDATE_FINDING` | |
| `skill_id` | string | Yes | | |
| `vulnerability_claim` | string | Yes | | Human-readable description of what's claimed |
| `replication_command` | string | Yes | **must be non-empty** | **[LOCKED]** per `01`/`02` — the Evidence Gate hard-requires this; a Specialist output without it must fail downstream, not be treated as acceptable |
| `supporting_evidence` | object | Yes | | e.g. request/response pairs, observed behavior |
| `specialist_confidence` | float | Yes | 0.0–1.0 | Same caveat as JudgeRoutingDecision.confidence — logging/research only, never a bypass mechanism |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "specialist", "model_id": "specialist-model", "model_version": "v1"},
  "trust_classification": "CANDIDATE_FINDING",
  "skill_id": "idor_v1",
  "vulnerability_claim": "GET /api/v1/users/{id} returns other users' data when id is incremented without authorization check",
  "replication_command": "curl -H 'Authorization: Bearer <user_a_token>' https://target/api/v1/users/12346",
  "supporting_evidence": {"request": "...", "response_snippet": "..."},
  "specialist_confidence": 0.81
}
```

**Invalid example (reason: `replication_command` is empty — this record must not exist in this form; per `02` §16 this should fail the Evidence Gate, and per this schema it should ideally be rejected at construction time):**
```json
{
  "trust_classification": "CANDIDATE_FINDING",
  "vulnerability_claim": "possible IDOR",
  "replication_command": "",
  "specialist_confidence": 0.4
}
```

## 2.18 EvidenceGateResult

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = evidence_gate` (no model/tool — this is deterministic per `02` §9) | |
| `source_poc_record_id` | string (UUID) | Yes | references the SpecialistPoCOutput | |
| `result` | string (enum) | Yes | `pass` \| `fail` \| `needs_more_evidence` | |
| `checks_performed` | array of object | Yes | shape: `{check_name: string, passed: boolean}` | Per `02` §9 Observability requirement — individual check results, not just the aggregate |
| `reasons` | array of string | Yes | may be empty if `result = pass` | Required and non-empty if `result` is `fail` or `needs_more_evidence` |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "evidence_gate"},
  "source_poc_record_id": "g1...",
  "result": "pass",
  "checks_performed": [
    {"check_name": "replication_command_present", "passed": true},
    {"check_name": "no_known_fp_pattern", "passed": true}
  ],
  "reasons": []
}
```

**Invalid example (reason: `result = fail` but `reasons` is empty — a fail must always be explainable):**
```json
{
  "result": "fail",
  "checks_performed": [{"check_name": "replication_command_present", "passed": false}],
  "reasons": []
}
```

## 2.19 DeduplicationResult

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = deduplication` | |
| `source_poc_record_id` | string (UUID) | Yes | | |
| `result` | string (enum) | Yes | `unique` \| `duplicate` | |
| `matched_finding_id` | string (UUID) | No | required if `result = duplicate` | References the prior finding this duplicates — see `01`/`02` OD-04 on the index this is checked against |
| `match_confidence` | float | No | 0.0–1.0, required if `result = duplicate` | |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "deduplication"},
  "source_poc_record_id": "g1...",
  "result": "unique"
}
```

**Invalid example (reason: `result = duplicate` but `matched_finding_id` missing):**
```json
{
  "result": "duplicate",
  "match_confidence": 0.95
}
```

## 2.20 HumanReviewPackage

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = human_verification` | |
| `poc_record_id` | string (UUID) | Yes | | |
| `full_evidence_trail` | array of string (UUID) | Yes | ordered list of every record_id from RawToolOutput through EvidenceGateResult that contributed to this candidate | This is what makes the review package reviewable — a human should never have to reconstruct the trail themselves |
| `evidence_gate_result_id` | string (UUID) | Yes | must reference an EvidenceGateResult with `result = pass` | **[LOCKED]** a package must not reach a human without having passed the Evidence Gate |
| `deduplication_result_id` | string (UUID) | Yes | must reference a DeduplicationResult with `result = unique` | **[LOCKED]** |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "human_verification"},
  "poc_record_id": "g1...",
  "full_evidence_trail": ["c1...", "d1...", "e1...", "f1...", "g1...", "h1...", "i1..."],
  "evidence_gate_result_id": "h1...",
  "deduplication_result_id": "i1..."
}
```

**Invalid example (reason: references an EvidenceGateResult that did not pass — this package should never have been constructed):**
```json
{
  "evidence_gate_result_id": "h_fail_1...",
  "deduplication_result_id": "i1..."
}
```

## 2.21 Report

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = report_polisher`, `model_id`/`model_version` required | |
| `validation_outcome_record_id` | string (UUID) | Yes | must reference a ValidationOutcome with `decision = submit` | **[LOCKED]** — enforces `02` §17's "only runs after SUBMIT" constraint at the data level |
| `formatted_title` | string | Yes | | |
| `formatted_body` | string | Yes | | |
| `source_claims` | array of string (UUID) | Yes | every source record this report's content is traceable to | Used by the "no unbacked claims" test in `02` §17/`11` |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "report_polisher", "model_id": "polisher-model", "model_version": "v1"},
  "validation_outcome_record_id": "j1...",
  "formatted_title": "IDOR in GET /api/v1/users/{id} allows unauthorized data access",
  "formatted_body": "## Summary\n...",
  "source_claims": ["g1...", "j1..."]
}
```

**Invalid example (reason: references a ValidationOutcome that isn't a submit — this Report must not exist):**
```json
{
  "validation_outcome_record_id": "j_discard_1..."
}
```

## 2.22 AuditEvent

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | any `stage` | |
| `event_type` | string (enum) | Yes | `authorized` \| `rejected` \| `gate_passed` \| `gate_failed` \| `human_decision` \| `registry_lookup` | Extend via registry update, not schema change **[REC]** |
| `detail` | object | Yes | | Event-type-specific structured detail |
| `related_record_ids` | array of string (UUID) | Yes | may be empty | |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "orchestrator"},
  "event_type": "rejected",
  "detail": {"reason": "unregistered tool_id", "attempted_tool_id": "nmap-aggressive"},
  "related_record_ids": ["a2..."]
}
```

**Invalid example (reason: `event_type` not in enum):**
```json
{
  "event_type": "something_happened",
  "detail": {}
}
```

## 2.23 FailureEvent

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | any `stage` | |
| `failure_type` | string (enum) | Yes | `timeout` \| `crash` \| `resource_exhausted` \| `schema_invalid` \| `model_refusal` \| `unreachable_dependency` | |
| `detail` | string | Yes | | |
| `retry_count_at_failure` | integer | Yes | ≥ 0 | |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "extractor"},
  "failure_type": "schema_invalid",
  "detail": "Extractor output did not conform to ExtractorJSON.v1 after generation",
  "retry_count_at_failure": 0
}
```

**Invalid example (reason: `failure_type` not in enum):**
```json
{
  "failure_type": "oops",
  "detail": "something broke"
}
```

---

# §3 — Research Data Objects

**[LOCKED]** Every schema in this section is written to the Research/Audit Store (component 19) only. None is ever read back into a live pipeline decision (`01` §13, `02` §19). Full usage rules (how these become evaluation sets, few-shot sources, etc.) are `10_RESEARCH_DATA_PIPELINE.md`'s job — this section defines only their structural shape.

## 3.1 ResearchEvent

The generic envelope every other research object is wrapped in when written to the store.

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | | |
| `event_category` | string (enum) | Yes | `finding` \| `candidate` \| `replication` \| `validation` \| `experiment` \| `tool_sequence` \| `model_evaluation` \| `dataset` \| `model_version` | Determines which of §3.2–3.10's schema the `payload` conforms to |
| `payload` | object | Yes | shape determined by `event_category` | |
| `trust_classification` | TrustClassification | Yes | | Preserved even in the research store — this is precisely what keeps validated and unvalidated records distinguishable, per `12`'s gate |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "human_verification"},
  "event_category": "validation",
  "payload": {"...": "a ValidationOutcome object"},
  "trust_classification": "VALIDATED_FINDING"
}
```

**Invalid example (reason: `event_category = validation` but `trust_classification = CANDIDATE_FINDING` — a validation event must carry the post-validation trust level, not the pre-validation one):**
```json
{
  "event_category": "validation",
  "payload": {"...": "..."},
  "trust_classification": "CANDIDATE_FINDING"
}
```

## 3.2 FindingRecord

Derived only from a `ValidationOutcome` where `decision = submit`. This is the "ground truth" research record.

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | | |
| `validation_outcome_record_id` | string (UUID) | Yes | must reference `decision = submit` | **[LOCKED]** |
| `vulnerability_class` | string | Yes | | |
| `skill_id_used` | string | Yes | | |
| `full_evidence_trail` | array of string (UUID) | Yes | | Same shape as HumanReviewPackage's trail, preserved for research reproducibility |
| `outcome_status` | string (enum) | No | `accepted` \| `rejected_by_platform` \| `pending` | **[FUTURE]** — populated later if/when bounty-platform acceptance status is tracked back; not required at record-creation time since that status isn't known yet |

**Valid example:**
```json
{
  "provenance": {"...": "..."},
  "validation_outcome_record_id": "j1...",
  "vulnerability_class": "IDOR",
  "skill_id_used": "idor_v1",
  "full_evidence_trail": ["c1...", "..."],
  "outcome_status": "pending"
}
```

**Invalid example (reason: references a ValidationOutcome that was a discard, not a submit):**
```json
{
  "validation_outcome_record_id": "j_discard_1...",
  "vulnerability_class": "IDOR"
}
```

## 3.3 CandidateFindingRecord

Derived from every `SpecialistPoCOutput`, regardless of eventual outcome — this is what makes false-positive/false-negative research analysis possible per `10`.

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | | |
| `poc_record_id` | string (UUID) | Yes | | |
| `eventual_outcome` | string (enum) | Yes | `pending` \| `passed_evidence_gate` \| `failed_evidence_gate` \| `blocked_duplicate` \| `human_discarded` \| `human_submitted` | This field is updated as the candidate progresses — the record is append-only in the sense that a *new* CandidateFindingRecord snapshot is written at each transition, never an in-place mutation of history **[REC]** |

**Valid example:**
```json
{
  "provenance": {"...": "..."},
  "poc_record_id": "g1...",
  "eventual_outcome": "human_submitted"
}
```

**Invalid example (reason: `eventual_outcome` not in enum):**
```json
{
  "poc_record_id": "g1...",
  "eventual_outcome": "unknown"
}
```

## 3.4 ReplicationRecord

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | | |
| `poc_record_id` | string (UUID) | Yes | | |
| `replication_command` | string | Yes | copied from the source SpecialistPoCOutput | Preserved independently so future chaining research (`01` §21 boundary) can query replication primitives without joining back through the full candidate record |
| `validated` | boolean | Yes | | true only if the source candidate reached `VALIDATED_FINDING` |

**Valid example:**
```json
{
  "provenance": {"...": "..."},
  "poc_record_id": "g1...",
  "replication_command": "curl -H 'Authorization: Bearer <user_a_token>' https://target/api/v1/users/12346",
  "validated": true
}
```

**Invalid example (reason: empty `replication_command` — mirrors the SpecialistPoCOutput constraint, since this is a derived record):**
```json
{
  "replication_command": "",
  "validated": false
}
```

## 3.5 ValidationOutcome

*(also a live-pipeline schema, per the Schema Index — Human Verification Interface both uses this to drive Report Polisher AND it's written to the Research Store, hence its dual listing.)*

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | `stage = human_verification` | |
| `human_review_package_id` | string (UUID) | Yes | | |
| `decision` | string (enum) | Yes | `submit` \| `discard` \| `needs_more_evidence` | |
| `human_identity` | string | Yes | | **[LOCKED]** required per `02` §18 — no anonymous/default decisions |
| `decided_at` | string (ISO 8601) | Yes | | |
| `discard_reason` | string | No | required if `decision = discard` | Feeds false-positive research analysis |

**Valid example:**
```json
{
  "provenance": {"...": "...", "stage": "human_verification"},
  "human_review_package_id": "k1...",
  "decision": "discard",
  "human_identity": "harsh",
  "decided_at": "2026-08-31T11:00:00Z",
  "discard_reason": "replication_command works but impact is below program's minimum severity threshold"
}
```

**Invalid example (reason: `decision = discard` but `discard_reason` missing — loses the false-positive research signal):**
```json
{
  "decision": "discard",
  "human_identity": "harsh",
  "decided_at": "2026-08-31T11:00:00Z"
}
```

## 3.6 ExperimentRecord

For offline model-benchmarking experiments (per `01` §10, models are selected by benchmarking, not size).

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | | |
| `experiment_id` | string | Yes | | |
| `role_under_test` | string (enum) | Yes | `extractor` \| `worker` \| `judge` \| `specialist` \| `report_polisher` | |
| `candidate_model_ids` | array of string | Yes | ≥ 1 | |
| `evaluation_dataset_id` | string | Yes | references a DatasetRecord | |
| `results_per_model` | array of object | Yes | shape: `{model_id: string, metrics: object}` | |
| `winner_model_id` | string | No | | Not required — an experiment may conclude "no clear winner yet" |

**Valid example:**
```json
{
  "provenance": {"...": "..."},
  "experiment_id": "exp-judge-2026-08",
  "role_under_test": "judge",
  "candidate_model_ids": ["judge-model-a", "judge-model-b"],
  "evaluation_dataset_id": "ds-judge-eval-v1",
  "results_per_model": [
    {"model_id": "judge-model-a", "metrics": {"precision": 0.82, "recall": 0.71}},
    {"model_id": "judge-model-b", "metrics": {"precision": 0.79, "recall": 0.75}}
  ]
}
```

**Invalid example (reason: `role_under_test` not in enum):**
```json
{
  "role_under_test": "orchestrator",
  "candidate_model_ids": ["x"]
}
```

## 3.7 ToolSequenceRecord

For sequence/strategy analysis — reconstructed offline from a run's AuditEvent stream, not written directly by any live component.

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | | |
| `run_id` | string (UUID) | Yes | groups this sequence to one target run | |
| `sequence` | array of object | Yes | ordered, shape: `{tool_id: string, order_index: integer, outcome: string}` | |
| `led_to_candidate` | boolean | Yes | | Whether this sequence eventually produced a CandidateFindingRecord — the key signal for "which sequences are worth repeating" research |

**Valid example:**
```json
{
  "provenance": {"...": "..."},
  "run_id": "r1...",
  "sequence": [
    {"tool_id": "subfinder", "order_index": 1, "outcome": "success"},
    {"tool_id": "httpx", "order_index": 2, "outcome": "success"}
  ],
  "led_to_candidate": true
}
```

**Invalid example (reason: `sequence` entries not ordered — `order_index` values are not sequential):**
```json
{
  "sequence": [{"tool_id": "httpx", "order_index": 5}, {"tool_id": "subfinder", "order_index": 1}]
}
```

## 3.8 ModelEvaluationRecord

The persisted output of an ExperimentRecord, formalized as the record type the Model Registry (`08`) reads from when populating `evaluation_dataset`/`evaluation_metrics` fields.

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | | |
| `model_id` | string | Yes | | |
| `role` | string (enum) | Yes | same enum as ExperimentRecord.role_under_test | |
| `evaluation_dataset_id` | string | Yes | | |
| `metrics` | object | Yes | | e.g. precision/recall/latency — shape is role-dependent, not fixed here |
| `known_limitations` | array of string | Yes | may be empty | Feeds directly into `08_MODEL_REGISTRY/`'s `known_limitations` field |

**Valid example:**
```json
{
  "provenance": {"...": "..."},
  "model_id": "judge-model-a",
  "role": "judge",
  "evaluation_dataset_id": "ds-judge-eval-v1",
  "metrics": {"precision": 0.82, "recall": 0.71},
  "known_limitations": ["struggles with contradictory evidence from more than 3 workers"]
}
```

**Invalid example (reason: `role` not in enum):**
```json
{
  "model_id": "x",
  "role": "orchestrator"
}
```

## 3.9 DatasetRecord

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | | |
| `dataset_id` | string | Yes | | |
| `version` | string | Yes | versioning **policy** (semver vs. timestamp-based, etc.) is `10`'s decision, not this schema's — this field just holds whatever value that policy produces | |
| `source_record_ids` | array of string (UUID) | Yes | | Which underlying records (e.g. FindingRecords) compose this dataset |
| `purity_notes` | string | Yes | free text | **[REC]** — explicit field for documenting any known contamination risk, directly supporting `01`/`02`'s "one false positive poisons the flywheel" concern |

**Valid example:**
```json
{
  "provenance": {"...": "..."},
  "dataset_id": "ds-judge-eval-v1",
  "version": "2026-08-31",
  "source_record_ids": ["m1...", "m2..."],
  "purity_notes": "all source records verified as human-submitted findings only; no discarded candidates included"
}
```

**Invalid example (reason: `purity_notes` empty — required field left blank undermines the whole point of tracking it):**
```json
{
  "dataset_id": "ds-judge-eval-v1",
  "purity_notes": ""
}
```

## 3.10 ModelVersionRecord

| Field | Type | Required | Constraint / Enum | Notes |
|---|---|---|---|---|
| `provenance` | Provenance | Yes | | |
| `model_id` | string | Yes | | |
| `version` | string | Yes | | |
| `parent_version` | string | No | | For fine-tuned/LoRA derivatives — null for a base open-weight model |
| `training_data_reference` | string | No | required if `parent_version` is set | Must reference a DatasetRecord, never an unvalidated candidate source — this is the schema-level enforcement of `01`/`02`'s fine-tuning-gated-behind-clean-data rule |

**Valid example:**
```json
{
  "provenance": {"...": "..."},
  "model_id": "specialist-idor-lora-v1",
  "version": "v1",
  "parent_version": "qwen2.5-1.5b-base",
  "training_data_reference": "ds-idor-validated-v2"
}
```

**Invalid example (reason: `parent_version` set but `training_data_reference` missing — a derivative model must be traceable to the dataset that produced it):**
```json
{
  "model_id": "specialist-idor-lora-v1",
  "parent_version": "qwen2.5-1.5b-base"
}
```

---

## New Open Decisions Raised in This Document

| ID | Question | Raised in |
|---|---|---|
| **OD-12** | `vulnerability_class` on SkillManifest: closed enum vs. registry-validated open string? Recommendation given (open string), not locked. | §2.15 |
| **OD-13** | Exact output-size truncation limit for `RawToolOutput.truncated` (ties to OD-02's resource limits, but is specifically a capture-size question, not a container resource question) | §2.7 |

Carried forward with OD-01 through OD-11 into `13_OPEN_DECISIONS.md`.

---

## WHAT YOU SHOULD UNDERSTAND BEFORE NEXT

Before `04_WORKER_MANIFESTS/`, these concepts matter most:

1. **Common types exist so you don't repeat yourself — use them.** Every schema with a `provenance` field means "see §1.1," not "here are eight more fields." When you eventually implement this in code, Provenance should be one shared struct/class embedded everywhere, not copy-pasted.

2. **`trust_classification` is now a real, checkable field, not just a narrative idea from `01`.** `RAW_OBSERVATION → MODEL_INTERPRETATION → CANDIDATE_FINDING → VALIDATED_FINDING` is enforced schema-by-schema: RawToolOutput can only ever be `RAW_OBSERVATION`, ExtractorJSON/WorkerOutput can only be `MODEL_INTERPRETATION`, SpecialistPoCOutput can only be `CANDIDATE_FINDING`, and `VALIDATED_FINDING` is reachable by exactly one path (a `ValidationOutcome` with `decision = submit`). This is the concrete mechanism `12_ACCEPTANCE_CRITERIA/` will test against.

3. **JudgeInput.`contains_skill_content` must always be `false`.** This is a small field carrying a large amount of the Judge-neutrality guarantee — it turns "the Judge should stay neutral" from a prompt-writing discipline into something a unit test can assert on every single record.

4. **SpecialistPoCOutput.`replication_command` being non-empty is a hard schema requirement, not a soft recommendation.** Combined with the Evidence Gate's check, this is the concrete data-level enforcement of "evidence over confidence" — a candidate without a reproduction step structurally cannot become a validated finding.

5. **Manifests (Worker/Skill/Tool) have field lists the master prompt already fixed.** You'll notice §2.4, §2.10, and §2.15 don't have much design discretion in them — they're transcriptions of what STEP 04/05/06 will need. When you get there, the manifests you write must conform to these exact shapes.

6. **Research objects are derived, not independently authored.** Notice FindingRecord, CandidateFindingRecord, and ReplicationRecord are explicitly described as *derived from* pipeline schemas, never as something a component invents fresh. This is what keeps the research layer honest — it can only ever reflect what actually happened in the live pipeline, never something extra.

7. **Two new open decisions (OD-12, OD-13) plus eleven carried forward = thirteen items now waiting in `13_OPEN_DECISIONS.md`.** OD-12 in particular is worth sitting with before `05_SKILL_MANIFESTS/`: whether vulnerability classes are a closed enum or an open, registry-checked string changes how much friction there is to ever add a fifth Skill after IDOR/SSRF/Auth-Bypass/Priv-Esc.
