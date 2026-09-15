# 02_COMPONENT_SPECS.md
## Hypermind — Track A — Component Implementation Specifications

**Document:** STEP 02 of 15 · Track A Documentation Package
**Status:** Implementation-ready component contracts
**Depends on:** `01_ARCHITECTURE.md` (architectural WHAT/WHY, pipeline, trust boundaries — not repeated here)
**Feeds forward to:** `03` (full schemas), `04`/`05`/`06`/`08` (manifests/registry entries), `09` (full security policy), `11` (full test cases), `12` (full acceptance gates)

---

## How to Read This Document

This document does **not** repeat what `01_ARCHITECTURE.md` already established. Where content overlaps, this document points back rather than restating:

- **Purpose / WHY** → already covered per-component in `01_ARCHITECTURE.md` §19. Here it's one line + a pointer.
- **Full field-level schemas** → deferred to `03_DATA_SCHEMAS/`. Here we only name which schema types a component consumes/produces.
- **Concrete manifests, tool entries, model entries** → deferred to `04`/`05`/`06`/`08`. Here we define the *generic execution framework* those manifests plug into.
- **Full test cases** → deferred to `11_TEST_PLAN/`. Here we note which test categories apply.
- **Full acceptance gates** → deferred to `12_ACCEPTANCE_CRITERIA/`. Here we note which gates this component is responsible for satisfying.

What **is** new and unique to this document: **Responsibilities, Inputs/Outputs (interface-level, not field-level), Dependencies, State, Interfaces (concrete contract shapes), Security Constraints (implementation-specific), Failure Handling (mechanism-level), and Observability** — none of which appear anywhere else in the package.

Label legend is unchanged from `01_ARCHITECTURE.md` §"Decision Label Legend" — **[LOCKED] [REQ] [REC] [ASSUMPTION] [OPEN — REQUIRES HARSH] [FUTURE] [INFERENCE]**.

---

## Component Index

| # | Component | Group | Architectural ref (01) | Detail doc |
|---|---|---|---|---|
| 1 | Tool Registry | Infrastructure | §18 | `06_TOOL_REGISTRY/` |
| 2 | Worker Registry | Infrastructure | §18 | `04_WORKER_MANIFESTS/` |
| 3 | Skill Registry | Infrastructure | §18 | `05_SKILL_MANIFESTS/` |
| 4 | Model Registry | Infrastructure | §18 | `08_MODEL_REGISTRY/` |
| 5 | Model Serving Layer (Ollama) | Infrastructure | §16 | `08_MODEL_REGISTRY/` |
| 6 | Policy Engine (OPA/Rego) | Policy & Gating | §6, §19.1 | `09_SECURITY_POLICIES/` |
| 7 | Scope Gate | Policy & Gating | §19.1 | `09_SECURITY_POLICIES/` |
| 8 | Trust Boundary A — Input Guard | Policy & Gating | §6, §19.2 | `09_SECURITY_POLICIES/` |
| 9 | Evidence Gate | Policy & Gating | §19.9 | `12_ACCEPTANCE_CRITERIA/` |
| 10 | Deduplication Engine | Policy & Gating | §19.10 | `12_ACCEPTANCE_CRITERIA/` |
| 11 | Orchestrator / Planner | Core Pipeline | §19.3 | — |
| 12 | Docker Tool Execution Engine | Core Pipeline | §17, §19.4 | `07_DOCKER_SPEC/` |
| 13 | Extractor | Core Pipeline | §19.5 | `08_MODEL_REGISTRY/` |
| 14 | Worker Execution Framework | Core Pipeline | §19.6 | `04_WORKER_MANIFESTS/` |
| 15 | Neutral Judge | Core Pipeline | §19.7 | `08_MODEL_REGISTRY/` |
| 16 | Specialist Executor | Core Pipeline | §19.8 | `05_SKILL_MANIFESTS/` |
| 17 | Report Polisher | Core Pipeline | §19.12 | `08_MODEL_REGISTRY/` |
| 18 | Human Verification Interface | Human Interface | §19.11, §15 | — |
| 19 | Research / Audit Store | Data Layer | §13, §19.13 | `10_RESEARCH_DATA_PIPELINE.md` |

---

# GROUP 1 — Infrastructure: Registries & Serving

Registries are the deterministic backbone (`01` §18). This section specifies the **registry mechanism itself** — how registration, lookup, and validation work — not the entries inside them, which are content-specific documents (`04`/`05`/`06`/`08`).

## 1. Tool Registry

| Field | Specification |
|---|---|
| **Purpose** | See `01` §18, §19.4. Deterministic gatekeeper answering "may this tool run, how, and where?" |
| **Responsibilities** | (1) Store versioned ToolManifest entries; (2) Reject lookups for unregistered tool_ids; (3) Validate a requested invocation against its manifest (input schema, allowed stage, resource limits) before authorizing; (4) Expose only currently-approved tools — no dynamic/ad-hoc tool addition at runtime **[LOCKED]** |
| **Inputs** | ToolLookupRequest (tool_id, requested stage context) |
| **Outputs** | ToolManifest (if registered + valid) or RegistryRejection |
| **Dependencies** | Tool manifest store (versioned config, e.g. files or a config DB — **[OPEN — REQUIRES HARSH] OD-08:** storage mechanism for registry manifests not specified) |
| **State** | Stateless at query time; manifests are versioned static config loaded at startup **[REQ]** |
| **Interfaces** | `lookup(tool_id: str) -> ToolManifest \| RegistryRejection`<br>`validate_invocation(tool_id: str, request: ToolExecutionRequest) -> bool` |
| **Schemas** | ToolManifest, ToolExecutionRequest — full fields in `03`; concrete entries in `06_TOOL_REGISTRY/` |
| **Security Constraints** | Registry is read-only at runtime from the Orchestrator's perspective — no code path lets an LLM add/modify a manifest **[LOCKED]** |
| **Failure Handling** | Unregistered tool_id → RegistryRejection, Orchestrator rejects the action (`01` §14) |
| **Observability** | Every lookup logged (tool_id, result, caller context) |
| **Tests** | See `11` — registry tests category |
| **Acceptance Criteria** | See `12` — "unregistered tools cannot execute" gate |

## 2. Worker Registry

| Field | Specification |
|---|---|
| **Purpose** | See `01` §18, §19.6. Answers "which analytical jobs (WHAT) exist?" |
| **Responsibilities** | Same mechanism as Tool Registry (register / lookup / validate), scoped to WorkerManifest entries instead of ToolManifest |
| **Inputs** | WorkerLookupRequest (worker_id) |
| **Outputs** | WorkerManifest or RegistryRejection |
| **Dependencies** | Worker manifest store (same open question as OD-08) |
| **State** | Stateless at query time; manifests are versioned static config **[REQ]** |
| **Interfaces** | `lookup(worker_id: str) -> WorkerManifest \| RegistryRejection` |
| **Schemas** | WorkerManifest — full fields in `03`; concrete entries in `04_WORKER_MANIFESTS/` |
| **Security Constraints** | Read-only at runtime; a Worker cannot self-register or self-modify its manifest **[LOCKED]** |
| **Failure Handling** | Unregistered worker_id → RegistryRejection |
| **Observability** | Every lookup logged (worker_id, result) |
| **Tests** | See `11` |
| **Acceptance Criteria** | See `12` — "unregistered workers cannot execute" gate |

## 3. Skill Registry

| Field | Specification |
|---|---|
| **Purpose** | See `01` §18, §19.8. Answers "HOW should this vulnerability class be investigated?" |
| **Responsibilities** | Same registry mechanism, scoped to SkillManifest entries. Additionally: (1) must never expose a Skill to the Judge component — only to the Specialist Executor **[LOCKED, critical]** |
| **Inputs** | SkillLookupRequest (skill_id or vulnerability_class) |
| **Outputs** | SkillManifest or RegistryRejection |
| **Dependencies** | Skill manifest store (OD-08) |
| **State** | Stateless at query time **[REQ]** |
| **Interfaces** | `lookup(skill_id: str) -> SkillManifest \| RegistryRejection`<br>*(no interface exists for Judge to call this registry — enforced by omission, not just policy)* **[LOCKED]** |
| **Schemas** | SkillManifest — full fields in `03`; concrete entries in `05_SKILL_MANIFESTS/` |
| **Security Constraints** | Access-controlled by caller identity: only the Specialist Executor may query this registry **[LOCKED — enforces "Judge principle" from `01` §19.7]** |
| **Failure Handling** | Unregistered skill_id → RegistryRejection; unauthorized caller → RegistryRejection + audit event |
| **Observability** | Every lookup logged with caller identity — an unexpected caller (e.g. Judge) attempting a lookup is a security-relevant log event, not just a routine one |
| **Tests** | See `11` — must include a negative test that the Judge cannot reach this registry |
| **Acceptance Criteria** | See `12` — "unregistered skills cannot load" gate + Judge-neutrality gate |

## 4. Model Registry

| Field | Specification |
|---|---|
| **Purpose** | See `01` §10, §18. Answers "which model serves which role, and is it benchmarked as suitable?" |
| **Responsibilities** | (1) Store ModelManifest entries per role; (2) Track primary/fallback status per role; (3) Expose evaluation metadata (dataset, metrics) so a model is never selected on size alone **[LOCKED]**; (4) Support multiple candidate models per role for benchmarking |
| **Inputs** | ModelLookupRequest (role: Extractor \| Worker \| Judge \| Specialist \| ReportPolisher) |
| **Outputs** | ModelManifest (active model for that role) or RegistryRejection |
| **Dependencies** | Model manifest store (OD-08); Model Serving Layer (component 5) |
| **State** | Stateless at query time; "active model per role" is versioned config, changeable only through a recorded registry update, not silently at runtime **[REQ]** |
| **Interfaces** | `lookup(role: str) -> ModelManifest \| RegistryRejection`<br>`list_candidates(role: str) -> List[ModelManifest]` (for benchmarking) |
| **Schemas** | ModelManifest — full fields in `08_MODEL_REGISTRY/` (not `03` — `ModelManifest` was never in the master prompt's STEP 03 schema list; `08` is its correct, sole definition) |
| **Security Constraints** | Role-to-model binding cannot be changed by any LLM-originated request — only by a human-authorized config change **[LOCKED]** |
| **Failure Handling** | No model registered for a required role → the dependent component cannot start; fail at startup, not at runtime **[REC]** |
| **Observability** | Model selection logged with model_id + version at every invocation (this is required provenance for `10`) |
| **Tests** | See `11` |
| **Acceptance Criteria** | See `12` |

## 5. Model Serving Layer (Ollama)

| Field | Specification |
|---|---|
| **Purpose** | See `01` §16. The runtime that actually hosts and serves local open-weight models for every role. |
| **Responsibilities** | (1) Load and serve the model designated by the Model Registry for each role; (2) Expose a uniform inference interface regardless of underlying model; (3) Enforce per-role generation policy (e.g. temperature, max tokens) as configured in the ModelManifest |
| **Inputs** | InferenceRequest (role, prompt/context, generation policy) |
| **Outputs** | InferenceResult (raw model output — **not yet validated against any schema**; schema validation is the calling component's job, e.g. Extractor validates its own output against ExtractorJSON) |
| **Dependencies** | Ollama runtime; host GPU/CPU resources; Model Registry (for which model to load per role) |
| **State** | Loaded models persist in memory between calls (standard Ollama behavior) — this is **infrastructure state, not decision-influencing memory**; it does not violate the "Track A remains operationally stateless" principle, which concerns pipeline *decisions*, not model-weight residency **[INFERENCE — clarifying a boundary the master prompt doesn't spell out]** |
| **Interfaces** | `infer(role: str, prompt: str, generation_policy: dict) -> InferenceResult` |
| **Schemas** | InferenceRequest/InferenceResult are internal, not part of the `03` schema set (they're pre-validation) |
| **Security Constraints** | The serving layer has no execution authority of its own — it only produces text/JSON; all authority lives in the Orchestrator **[LOCKED, consistent with `01` §4]** |
| **Failure Handling** | Model unavailable / OOM / timeout → InferenceResult marked as failure; calling component handles per its own failure policy (e.g. Extractor rejects, does not propagate) |
| **Observability** | Latency, token counts, and resource usage per inference call — needed for capacity planning on the host (relates to OD-03, host hardware profile) |
| **Tests** | See `11` |
| **Acceptance Criteria** | See `12` |

---

# GROUP 2 — Policy & Gating

## 6. Policy Engine (OPA/Rego)

| Field | Specification |
|---|---|
| **Purpose** | See `01` §6, §19.1. Deterministic policy evaluation used by both the Scope Gate (Stage 0) and the Orchestrator's policy check (step P5). |
| **Responsibilities** | (1) Load a versioned Rego policy bundle; (2) Evaluate a named policy against an input document; (3) Return an allow/deny decision with a machine-readable reason; (4) Serve **both** callers (Scope Gate and Orchestrator) through the same evaluation interface — one engine, two call sites, not two engines **[REC]** |
| **Inputs** | PolicyQuery (policy_id, input_document) |
| **Outputs** | PolicyDecision (allow \| deny, reason) |
| **Dependencies** | OPA runtime; versioned Rego policy bundle |
| **State** | Stateless per evaluation; the policy bundle itself is versioned config, not runtime state **[LOCKED]** |
| **Interfaces** | `evaluate(policy_id: str, input_document: dict) -> PolicyDecision` |
| **Schemas** | PolicyQuery, PolicyDecision — full fields in `03` |
| **Security Constraints** | Policy bundle must be version-pinned and auditable; no dynamic policy loading from untrusted (target-controlled or LLM-proposed) input **[REQ]** |
| **Failure Handling** | Evaluation error/timeout → **fail closed (deny)** — never fail open **[LOCKED, "fail safe" principle, `01` §4]** |
| **Observability** | Every evaluation logged: policy_id, input hash (not full input, to avoid log bloat with large payloads), decision, latency |
| **Tests** | See `11` — policy test category |
| **Acceptance Criteria** | See `12` — "unauthorized scope is blocked" gate |

## 7. Scope Gate (Stage 0)

| Field | Specification |
|---|---|
| **Purpose** | See `01` §19.1. First deterministic gate: is this target authorized? |
| **Responsibilities** | (1) Accept a human-confirmed ScopeRequest; (2) Delegate evaluation to the Policy Engine with the scope policy; (3) Emit ScopeDecision; (4) On deny or ambiguity, halt the pipeline before any tool executes **[LOCKED]** |
| **Inputs** | ScopeRequest (target, human authorization reference) |
| **Outputs** | ScopeDecision (allow/deny) → gates entry to Trust Boundary A |
| **Dependencies** | Policy Engine (component 6) |
| **State** | Stateless — no memory of prior scope decisions across runs **[LOCKED, consistent with Track A statelessness]** |
| **Interfaces** | `check_scope(request: ScopeRequest) -> ScopeDecision` |
| **Schemas** | ScopeRequest, ScopeDecision — full fields in `03` |
| **Security Constraints** | This is the first and most consequential gate — a bug here has legal/ethical consequences, not just technical ones. Ambiguous scope must resolve to **deny**, never to allow **[LOCKED]** |
| **Failure Handling** | Policy Engine error → deny (inherits fail-closed from component 6) |
| **Observability** | Every scope decision logged with target identifier and outcome — this is a compliance-relevant log, not just a debug log |
| **Tests** | See `11` |
| **Acceptance Criteria** | See `12` — "unauthorized scope is blocked" gate |

## 8. Trust Boundary A — Input Guard

| Field | Specification |
|---|---|
| **Purpose** | See `01` §6, §19.2. Screens input reaching the Orchestrator for injection/malformed content. |
| **Responsibilities** | (1) Screen human/config input and any assembled LLM-facing prompt using `pytector` (and PromptGuard where specified); (2) Reject on detected injection or malformed input; (3) Run *before* the Orchestrator's planning LLM ever sees the input **[LOCKED]** |
| **Inputs** | Raw input to the Orchestrator (human/config input, prompt-assembly context) |
| **Outputs** | Cleared input (pass-through) or GuardRejection |
| **Dependencies** | pytector library; PromptGuard-for-Agents where specified (per `01` §6) |
| **State** | Stateless — no persisted history of prior inputs is required for this guard to function **[REC]** |
| **Interfaces** | `screen(input: str \| dict) -> ScreenResult` where `ScreenResult = {cleared: bool, reason: Optional[str]}` |
| **Schemas** | ScreenResult is internal (not part of `03`'s core pipeline schema set, since it's a pre-pipeline gate) — **[OPEN — REQUIRES HARSH] OD-09:** should ScreenResult be formalized as a `03` schema for audit purposes? Recommend yes for consistency with provenance requirements, but not decided here. |
| **Security Constraints** | This guard does not decide scope (that's component 7) — it screens for injection/malformed input only. Do not conflate the two responsibilities **[REQ]** |
| **Failure Handling** | Detected injection → reject, emit audit event, halt before Orchestrator |
| **Observability** | Every rejection logged with the detection signal that fired (not the full injected payload, to avoid storing attack strings verbatim in logs — **[REC]**, redact/hash where appropriate) |
| **Tests** | See `11` — adversarial/prompt-injection test category |
| **Acceptance Criteria** | See `12` |

## 9. Evidence Gate

| Field | Specification |
|---|---|
| **Purpose** | See `01` §12, §19.9. Enforces "evidence over confidence" before a candidate reaches deduplication/human review. |
| **Responsibilities** | (1) Check completeness of the SpecialistPoCOutput; (2) Verify a `replication_command` (or equivalent reproducibility artifact) is present and well-formed; (3) Check for known false-positive indicator patterns; (4) Produce a pass/fail/needs-more-evidence result — **never a confidence score treated as final** **[LOCKED]** |
| **Inputs** | SpecialistPoCOutput |
| **Outputs** | EvidenceGateResult (pass \| fail \| needs_more_evidence, reasons) |
| **Dependencies** | None beyond its own rule set (this is largely deterministic checking, not an LLM call) **[REC — recommend deterministic implementation where possible, consistent with "determinism where intelligence isn't needed," `01` §4]** |
| **State** | Stateless per candidate — evaluates the candidate on its own merits, not against history (history-based checks belong to Deduplication, component 10) **[REQ]** |
| **Interfaces** | `evaluate(poc_output: SpecialistPoCOutput) -> EvidenceGateResult` |
| **Schemas** | SpecialistPoCOutput, EvidenceGateResult — full fields in `03` |
| **Security Constraints** | Must not be bypassable by a high Judge or Specialist confidence score — the gate's own checks are authoritative, not any upstream confidence value **[LOCKED]** |
| **Failure Handling** | Missing/malformed replication artifact → fail, not needs_more_evidence (a missing reproducibility artifact is a hard requirement, not a soft one) **[REC]** |
| **Observability** | Every gate decision logged with which specific checks passed/failed (for later false-positive/false-negative research analysis per `10`) |
| **Tests** | See `11` |
| **Acceptance Criteria** | See `12` — "Evidence Gate blocks incomplete findings" gate |

## 10. Deduplication Engine

**[NOTE — OD-04 resolved 2026-09-15, see `13_OPEN_DECISIONS.md`]** This component's premise — that a live, persisted, cross-run findings index is required — has been reconsidered. Track A runs are intentionally independent; no live deduplication mechanism is required for MVP solely to prevent repeated findings across separate runs. Repeated findings across runs may be retained as independent historical records, with cross-run consolidation handled offline by the research/analysis system. The spec below is retained for reference (and for if/when a dedicated dedup subsystem is later designed) but is **not** an MVP build requirement. OD-10 (index-outage failure policy) is correspondingly moot for MVP. See `13_OPEN_DECISIONS.md` §3 item 1 for the open question of whether `12`'s AC-027/AC-028 gates should be marked N/A for MVP.

| Field | Specification |
|---|---|
| **Purpose** | See `01` §19.10. Blocks findings that duplicate a prior one. |
| **Responsibilities** | (1) Compare a gated candidate against a persisted index of prior findings; (2) Flag exact and near-duplicate matches; (3) Pass unique candidates to Human Verification |
| **Inputs** | Gated candidate (post-Evidence-Gate) |
| **Outputs** | DeduplicationResult (unique \| duplicate, matched_finding_id if duplicate) |
| **Dependencies** | A persisted findings index — **[OPEN — REQUIRES HARSH] OD-04 (carried from `01` §19.10):** what this index is and how it stays distinct from Mem0/research memory |
| **State** | **This is the one component in the live pipeline that legitimately requires cross-run persisted state** — a findings index. This does **not** violate the Track A statelessness / Mem0-boundary principle: the principle forbids *decision-influencing memory of arbitrary content* feeding back as if it were current evidence; a findings index checked for exact/near-duplicate matches is a narrow, purpose-built integrity check, not general memory **[INFERENCE — this distinction should be explicitly ratified by Harsh as part of resolving OD-04, not assumed silently]** |
| **Interfaces** | `check_duplicate(candidate: SpecialistPoCOutput) -> DeduplicationResult` |
| **Schemas** | DeduplicationResult — full fields in `03` |
| **Security Constraints** | The findings index must be read/append-only from the pipeline's perspective during normal operation — no code path lets an LLM edit or delete an entry **[REQ]** |
| **Failure Handling** | Index unavailable → **[OPEN — REQUIRES HARSH] OD-10:** fail closed (block all submissions until index is back) vs. fail open with a warning flag for human review. Recommend fail closed for consistency with the fail-safe principle, but this has an operational-availability cost worth Harsh's explicit sign-off. |
| **Observability** | Every dedup check logged with match confidence and outcome |
| **Tests** | See `11` |
| **Acceptance Criteria** | See `12` — "duplicates are blocked" gate |

---

# GROUP 3 — Core Pipeline Execution

## 11. Orchestrator / Planner

| Field | Specification |
|---|---|
| **Purpose** | See `01` §9, §19.3. The control spine: LLM proposes, deterministic checks decide. |
| **Responsibilities** | (1) Accept cleared input (post TB-A); (2) Invoke the planning LLM to propose an action; (3) Run schema validation, scope check, Tool/Worker/Skill registry checks, policy check, and resource check on the proposal, in that order; (4) Authorize execution only if all checks pass; (5) Emit a rejection + audit event on any failure; (6) Never execute a proposal itself — authorization is handed to the relevant execution component (Docker Tool Execution Engine, Worker Execution Framework, or Specialist Executor) **[LOCKED]** |
| **Inputs** | Cleared context (post TB-A); LLM-proposed OrchestratorAction |
| **Outputs** | Authorized invocation (to the relevant executor) or OrchestratorRejection |
| **Dependencies** | Model Serving Layer (for the planning LLM call); Tool/Worker/Skill Registries; Policy Engine; a resource-accounting mechanism (see OD-02, retry/resource limits) |
| **State** | Stateless across pipeline runs; may hold **session-scoped** state only for the duration of a single target's run (e.g. how many actions have been proposed so far, for bounded-retry/loop-prevention purposes) — this session state is discarded at run end, not persisted as memory **[REQ, operationalizes the "bounded orchestration" principle referenced in project history]** |
| **Interfaces** | `propose_and_authorize(context: dict) -> AuthorizedAction \| OrchestratorRejection` (internally composed of the five checks listed under Responsibilities) |
| **Schemas** | OrchestratorAction, AuditEvent — full fields in `03` |
| **Security Constraints** | This component is the single place all authorization logic is concentrated — do not duplicate authorization checks elsewhere in a way that could drift out of sync **[REQ]** |
| **Failure Handling** | Any check fails → reject + audit event, no execution (`01` §14); a proposal that fails schema validation before even reaching scope/registry checks should short-circuit immediately rather than running the full check chain uselessly **[REC — efficiency, not a security requirement]** |
| **Observability** | Every proposal logged with full check-by-check outcome (which of the five checks passed/failed) — critical for debugging and for the cross-document consistency audit in `14` |
| **Tests** | See `11` |
| **Acceptance Criteria** | See `12` — multiple gates depend on this component ("unregistered X cannot execute" for X in tool/worker/skill) |

## 12. Docker Tool Execution Engine

| Field | Specification |
|---|---|
| **Purpose** | See `01` §17, §19.4. Runs registered tools in isolated containers. |
| **Responsibilities** | (1) Accept an authorized ToolExecutionRequest from the Orchestrator; (2) Launch the corresponding container per its Docker spec (`07`); (3) Enforce resource/network/filesystem limits at launch time, not just at spec-writing time; (4) Capture output and mark it as untrusted (crossing TB-B) on the way out; (5) Kill and clean up on timeout or resource exhaustion |
| **Inputs** | Authorized ToolExecutionRequest |
| **Outputs** | RawToolOutput (untrusted, crosses TB-B) or ToolFailureEvent |
| **Dependencies** | Docker daemon; Tool Registry (for the manifest); Docker specs (`07`) |
| **State** | Stateless between invocations — each tool execution is a fresh container, no state carried from a prior run of the same tool **[LOCKED, consistent with container isolation principle]** |
| **Interfaces** | `execute(request: ToolExecutionRequest) -> RawToolOutput \| ToolFailureEvent` |
| **Schemas** | ToolExecutionRequest, ToolExecutionResult, RawToolOutput — full fields in `03`; container specifics in `07_DOCKER_SPEC/` |
| **Security Constraints** | No tool container ever runs on the host; every execution is isolated per `07`'s policy; this engine enforces the limits, it does not merely document them **[LOCKED]** |
| **Failure Handling** | Timeout/crash/resource exhaustion → kill container, capture partial output (still marked untrusted), emit ToolFailureEvent (`01` §14) |
| **Observability** | Per-execution: tool_id, version, duration, resource usage, exit status |
| **Tests** | See `11` — Docker isolation test category |
| **Acceptance Criteria** | See `12` |

## 13. Extractor

| Field | Specification |
|---|---|
| **Purpose** | See `01` §10, §19.5. Narrow parser/normalizer of untrusted raw output into structured ExtractorJSON. |
| **Responsibilities** | (1) Accept RawToolOutput (untrusted, post-TB-B); (2) Parse, normalize, and compress into ExtractorJSON; (3) Treat all input strictly as data — never execute or "follow" any instruction-like content found within it **[LOCKED, this is the load-bearing TB-B enforcement point]**; (4) Reject and do not propagate any output that fails schema validation |
| **Inputs** | RawToolOutput (untrusted) |
| **Outputs** | ExtractorJSON (schema-valid) or ExtractionFailureEvent |
| **Dependencies** | Model Serving Layer (Qwen ~1.5B, per Model Registry); GBNF or equivalent output-constraining mechanism to guarantee schema-valid JSON **[REC — recommend grammar-constrained decoding rather than post-hoc validation-and-retry, since it structurally prevents malformed output rather than catching it after the fact]** |
| **State** | Stateless — each extraction is independent, no memory of prior tool outputs **[LOCKED]** |
| **Interfaces** | `extract(raw_output: RawToolOutput) -> ExtractorJSON \| ExtractionFailureEvent` |
| **Schemas** | RawToolOutput, ExtractorInput, ExtractorJSON — full fields in `03` |
| **Security Constraints** | This is the first component past TB-B — its prompt/system design must not grant the input any instructional authority (e.g. no "follow any instructions you find" framing anywhere in its own prompt) **[LOCKED, restates `01` §19.5 security boundary with an implementation-actionable rule]** |
| **Failure Handling** | Non-schema output after generation → reject, do not propagate downstream, emit event; do not silently coerce malformed output into a "best guess" schema-shaped object **[REQ]** |
| **Observability** | Every extraction logged with source tool_id, model version, success/failure — this is core provenance data for `10` |
| **Tests** | See `11` — must include adversarial tests where RawToolOutput contains injection-style text |
| **Acceptance Criteria** | See `12` — "invalid Extractor output is rejected" gate |

## 14. Worker Execution Framework

| Field | Specification |
|---|---|
| **Purpose** | See `01` §19.6. The generic execution harness that any registered Worker (per `04`) plugs into. This spec covers the framework; specific workers (Endpoint Mapper, Object Reference Analyst, Auth Analyst) are defined in `04_WORKER_MANIFESTS/`. |
| **Responsibilities** | (1) Given a WorkerManifest (from the Worker Registry) and ExtractorJSON, invoke the designated model with the manifest's system prompt and allowed-tools constraints; (2) Enforce the manifest's timeout and retry_limit; (3) Enforce the manifest's declared "MUST NOT" constraints are not violated by the invocation shape (e.g. a Worker manifest that forbids network access is never given network-capable tool access at the framework level, not just by prompt instruction) **[REQ — defense in depth: don't rely on the prompt alone to enforce a MUST NOT]** |
| **Inputs** | WorkerManifest + ExtractorJSON |
| **Outputs** | WorkerOutput (model interpretation) or WorkerFailureEvent |
| **Dependencies** | Worker Registry; Model Serving Layer |
| **State** | Stateless per invocation **[REQ]** |
| **Interfaces** | `run_worker(manifest: WorkerManifest, input: ExtractorJSON) -> WorkerOutput \| WorkerFailureEvent` |
| **Schemas** | WorkerInput, WorkerOutput — full fields in `03`; concrete manifests in `04` |
| **Security Constraints** | A Worker's capabilities are exactly what its manifest declares — the framework must not grant any Worker invocation broader access than its manifest specifies **[LOCKED]** |
| **Failure Handling** | Refusal/timeout/invalid output → bounded retry (count per OD-02) → drop with failure event (`01` §14) |
| **Observability** | Per invocation: worker_id, model version, retry count, outcome |
| **Tests** | See `11` |
| **Acceptance Criteria** | See `12` |

## 15. Neutral Judge

| Field | Specification |
|---|---|
| **Purpose** | See `01` §19.7. Neutrally evaluates whether evidence is sufficient — never told how to find a vulnerability, only how to judge one. |
| **Responsibilities** | (1) Accept JudgeInput composed of WorkerOutputs and accumulated evidence; (2) Assess completeness, consistency, reproducibility, contradictions, false-positive indicators; (3) Produce a JudgeRoutingDecision — route to a Skill, request more evidence, or drop; (4) **Never** query the Skill Registry directly (enforced by component 3's access control, not by the Judge's own restraint) **[LOCKED, structural not just behavioral]** |
| **Inputs** | JudgeInput (WorkerOutputs + evidence so far) — **explicitly never** a SkillManifest or offensive methodology |
| **Outputs** | JudgeRoutingDecision (route_to_skill \| needs_more_evidence \| drop, + reasoning) |
| **Dependencies** | Model Serving Layer (Judge role model, per Model Registry) |
| **State** | Stateless per evaluation — no memory of prior judged candidates influences the current one **[LOCKED]** |
| **Interfaces** | `evaluate(input: JudgeInput) -> JudgeRoutingDecision` |
| **Schemas** | JudgeInput, JudgeRoutingDecision — full fields in `03` |
| **Security Constraints** | The Judge's system prompt must contain no offensive/vulnerability-hunting methodology — its prompt is built exclusively from neutral evaluation criteria **[LOCKED, this is the concrete implementation of `01`'s Judge Principle]** |
| **Failure Handling** | Insufficient evidence → route back for more (not a hard failure, a normal outcome); model error/timeout → bounded retry → drop with event |
| **Observability** | Every routing decision logged with its stated reasoning — needed for the "Judge remains neutral" audit check in `14` and for false-positive research analysis in `10` |
| **Tests** | See `11` — must include a negative test confirming the Judge's prompt contains no Skill content |
| **Acceptance Criteria** | See `12` — "Judge remains neutral" gate |

## 16. Specialist Executor

| Field | Specification |
|---|---|
| **Purpose** | See `01` §19.8. Executes methodology-driven investigation per a swappable Skill. This spec covers the framework; specific Skills (IDOR, SSRF, Auth Bypass, Priv Esc) are `05_SKILL_MANIFESTS/`. |
| **Responsibilities** | (1) Given a JudgeRoutingDecision routing to a specific vuln class, look up the corresponding SkillManifest; (2) Invoke the Specialist model with the Skill's methodology and few-shot examples; (3) Require the output include a `replication_command` (or equivalent) before it's considered complete; (4) Produce SpecialistPoCOutput as a **candidate**, never as validated truth **[LOCKED]** |
| **Inputs** | SkillManifest + accumulated evidence context |
| **Outputs** | SpecialistPoCOutput (candidate finding) or SpecialistFailureEvent |
| **Dependencies** | Skill Registry; Model Serving Layer (Specialist role, local open-weight primary per `01` §10) |
| **State** | Stateless per investigation **[REQ]** |
| **Interfaces** | `investigate(skill: SkillManifest, evidence: dict) -> SpecialistPoCOutput \| SpecialistFailureEvent` |
| **Schemas** | SpecialistInput, SpecialistPoCOutput — full fields in `03`; concrete skills in `05` |
| **Security Constraints** | The Specialist has no execution authority of its own — a `replication_command` it produces is a **proposed** reproduction step, which itself would need to pass back through the Orchestrator's authorization chain if it were ever to be executed automatically (it is not, in the MVP; replication is for human reference) **[REQ — important clarification the master prompt doesn't spell out explicitly]** |
| **Failure Handling** | No reproducible PoC produced → this will fail the Evidence Gate downstream, not a Specialist-level hard failure per se, unless the model call itself errors (then: bounded retry → drop with event) |
| **Observability** | Per investigation: skill_id, model version, whether a replication_command was produced |
| **Tests** | See `11` |
| **Acceptance Criteria** | See `12` — "Specialist produces replication_command" gate |

## 17. Report Polisher

| Field | Specification |
|---|---|
| **Purpose** | See `01` §19.12. Formats a validated finding into a report — formatting only, never discovery. |
| **Responsibilities** | (1) Accept a human-validated finding; (2) Format it into a report draft; (3) **Introduce no new claims** beyond what the validated evidence already supports — this component must not "improve" the finding's substance, only its presentation **[LOCKED]** |
| **Inputs** | Validated finding (post Human Verification, SUBMIT outcome) |
| **Outputs** | Report (draft, for human submission) |
| **Dependencies** | Model Serving Layer (Report Polisher role) |
| **State** | Stateless per report **[REQ]** |
| **Interfaces** | `polish(validated_finding: dict) -> Report` |
| **Schemas** | Report — full fields in `03` |
| **Security Constraints** | This component only runs **after** Human Verification's SUBMIT decision — it must never be reachable on a discarded or needs-more-evidence path **[LOCKED]** |
| **Failure Handling** | Formatting error → return to human with an error note; never silently drop a validated finding |
| **Observability** | Logged per report: which validated finding it formatted, model version |
| **Tests** | See `11` — must include a test that the Polisher's output contains no claim absent from the input |
| **Acceptance Criteria** | See `12` |

---

# GROUP 4 — Human Interface

## 18. Human Verification Interface

**[NOTE — OD-06 resolved 2026-09-15, see `13_OPEN_DECISIONS.md`]** The interface mechanism and the granularity of human involvement are now settled: an **API-oriented validation interface**, not a CLI or dashboard, for MVP. Human validation is the **promotion of a completed candidate to VALIDATED** — asynchronous/batched, not a gate at every internal pipeline step. A cloud LLM may assist by preparing a structured verification package (recommend, score, summarize, flag contradictions) but may never itself perform the promotion. The table below is updated accordingly.

| Field | Specification |
|---|---|
| **Purpose** | See `01` §15, §19.11. The mandatory human-control point #2 — SUBMIT / DISCARD / NEEDS_MORE_EVIDENCE. Structurally, this is the sole point in a run where a human decision is required — every step upstream (tools, Extractor, Workers, Judge, Specialist, Evidence Gate, Dedup) proceeds without blocking on a human. |
| **Responsibilities** | (1) Present a HumanReviewPackage (the gated candidate plus its full evidence trail, optionally accompanied by an LLM-prepared verification package per OD-06) to a human via the validation API; (2) Capture an explicit human decision — no default/timeout-based auto-decision is permitted **[LOCKED]**; (3) Route SUBMIT → Report Polisher, DISCARD → research record, NEEDS_MORE_EVIDENCE → back into the pipeline |
| **Inputs** | HumanReviewPackage (+ optional LLM-prepared verification package, informational only) |
| **Outputs** | ValidationOutcome (submit \| discard \| needs_more_evidence, human identity, timestamp) |
| **Dependencies** | **[LOCKED — OD-06 resolved]** API-oriented interface for MVP; no dashboard required (a future one-click UI may be layered on the same API later). No authentication mechanism is required for MVP (trusted local/authorized user assumption); the system still records the human identity associated with each promotion. Full authentication/access-control is deferred until multi-user or remote operation requires it. |
| **State** | Stateless with respect to pipeline decisions; may need to persist "pending review" items until a human acts, which is operational queuing state, not decision-influencing memory **[REQ]** |
| **Interfaces** | `present(package: HumanReviewPackage) -> None` (API response side)<br>`capture_decision(package_id: str, decision: ValidationOutcome) -> None` (API call side, invoked by the human's action) |
| **Schemas** | HumanReviewPackage, ValidationOutcome — full fields in `03` |
| **Security Constraints** | There must be no code path that produces a ValidationOutcome of "submit" without an explicit human action captured through this interface — this is the concrete mechanism behind "automatic submission is impossible" **[LOCKED]** |
| **Failure Handling** | If the interface is unreachable, the pipeline simply accumulates pending reviews — it does not proceed on their behalf under any circumstance **[LOCKED]** |
| **Observability** | Every decision logged with human identity, timestamp, and package_id — this is both an audit requirement and a research-provenance requirement (`10`) |
| **Tests** | See `11` |
| **Acceptance Criteria** | See `12` — "human verification is mandatory" and "automatic submission is impossible" gates |

---

# GROUP 5 — Data Layer

## 19. Research / Audit Store

| Field | Specification |
|---|---|
| **Purpose** | See `01` §13, §19.13. Observe-only store of provenance-rich records; never steers the live pipeline. |
| **Responsibilities** | (1) Receive and persist events emitted at every pipeline stage; (2) Preserve full provenance (model/version, tool/version, stage, trust-level classification per the observation→interpretation→candidate→validated ladder from `01` §8); (3) Serve read access for **offline** evaluation/benchmarking only; (4) Expose **no** write-back interface that the live pipeline could consult as if it were current evidence **[LOCKED, this is the one-directional guarantee from `01` §13]** |
| **Inputs** | Events from every component (audit events, failure events, gate results, validation outcomes, etc.) |
| **Outputs** | ResearchEvent records (for offline consumption); no outputs feed the live pipeline |
| **Dependencies** | A persistence layer — **[OPEN — REQUIRES HARSH] OD-11:** storage technology not specified (this is distinct from OD-08's registry-manifest storage and OD-04's dedup-index storage; all three are separate open storage decisions and should not be assumed to share a backend without an explicit decision) |
| **State** | Persisted, by definition — this is a store. The critical property is not statelessness but **directionality**: write paths exist from every live component into this store; no read path exists from this store back into any live decision point **[LOCKED]** |
| **Interfaces** | `record(event: ResearchEvent) -> None` (write, called by every component)<br>`query(filters: dict) -> List[ResearchEvent]` (read, for offline tooling only — **must not** be called by any component in Groups 1-4 during live pipeline execution) **[REQ]** |
| **Schemas** | ResearchEvent, FindingRecord, CandidateFindingRecord, ReplicationRecord, ValidationOutcome, ExperimentRecord, ToolSequenceRecord, ModelEvaluationRecord, DatasetRecord, ModelVersionRecord — full fields in `03`; full usage rules in `10_RESEARCH_DATA_PIPELINE.md` (that document is the authority on *how* this data becomes useful later — this spec only covers the store's own interface) |
| **Security Constraints** | Write-only from the live pipeline's perspective; read access is a separate, offline-tooling concern with its own access control **[REQ]** |
| **Failure Handling** | Store unavailable → the live pipeline **must not block** on this (`01` §19.13 failure modes) — recording failures are logged locally and retried/reconciled later, never allowed to stall a live decision **[REC]** |
| **Observability** | Store health, write success/failure rates, storage growth — meta-observability for the observability system itself |
| **Tests** | See `11` — research-data integrity test category |
| **Acceptance Criteria** | See `12` — "research records preserve provenance" and "validated and unvalidated records remain distinguishable" gates |

---

## New Open Decisions Raised in This Document

Carried forward to `13_OPEN_DECISIONS.md` alongside OD-01 through OD-04 from `01_ARCHITECTURE.md`:

| ID | Question | Raised in |
|---|---|---|
| **OD-05** | What observability/logging stack (structured logging framework, metrics backend) is used across all components? | Multiple (implicit) |
| **OD-06** | **RESOLVED 2026-09-15** — API-oriented, async/batched, no dashboard for MVP. See `13_OPEN_DECISIONS.md`. | §18 |
| **OD-08** | **ARCHITECTURE RESOLVED 2026-09-15** — git-tracked JSON/YAML is the canonical form; concrete tooling/layout DEFERRED to implementation. See `13_OPEN_DECISIONS.md`. | §1–4 |
| **OD-09** | **RESOLVED 2026-09-15** — yes, formalized in `03`. See `13_OPEN_DECISIONS.md`. | §8 |
| **OD-10** | **RESOLVED 2026-09-15 (moot)** — no live dedup index exists for MVP. See `13_OPEN_DECISIONS.md`. | §10 |
| **OD-11** | **ARCHITECTURE RESOLVED 2026-09-15** — local, canonical-structured-data; exact technology (files vs. datastore) DEFERRED to implementation. See `13_OPEN_DECISIONS.md`. | §19 |

None of these are silently resolved here. They are surfaced for `13_OPEN_DECISIONS.md`.

---

## WHAT YOU SHOULD UNDERSTAND BEFORE NEXT

Before `03_DATA_SCHEMAS/`, these concepts from this document matter most:

1. **This document defined contracts, not content.** You now know *how* a Worker gets invoked (the framework) but not the three specific Workers (that's `04`). Keep this separation straight — it's the same Workers-vs-Skills discipline applied one layer deeper, to "framework vs. instance."

2. **Three separate open storage questions exist — don't conflate them.** OD-08 (registry manifests), OD-04 (dedup findings index), and OD-11 (research/audit store) are three different persistence needs with three different access patterns (read-mostly config, read/append integrity check, write-heavy audit log). They may end up on different technologies. Don't assume "we'll just use one database" without checking that assumption against all three access patterns.

3. **"Stateless" doesn't mean "no state anywhere."** Notice how many components are correctly stateless *for pipeline decisions* while still legitimately holding some form of state (session-scoped counters in the Orchestrator, loaded model weights in the Serving Layer, a pending-review queue in the Human Verification Interface). The actual rule is narrower and more precise than "no state": **no persisted content is allowed to silently become current evidence.** Learn to check any new state against that specific rule, not against a blanket "stateless" label.

4. **The Skill Registry's access control is structural, not just a policy statement.** Notice component 3 doesn't just say "the Judge shouldn't use this" — it says no interface exists for the Judge to call it. This is "defense in depth": a security property enforced by what code *can* do, not only by what it's *told* to do. You'll see this pattern again in Worker manifests (`04`) enforcing MUST-NOT constraints at the framework level, not just the prompt level.

5. **A `replication_command` is a proposal, not an execution.** The Specialist Executor spec makes explicit something the master prompt implies but doesn't spell out: even the reproduction step the Specialist proposes is not itself run automatically. This matters when you get to `05_SKILL_MANIFESTS/` — a Skill's methodology describes *what to investigate*, and any command it proposes is for human reference, not autonomous re-execution.

6. **Observability is new territory, not previously covered.** Every component now has an Observability row — this is intentionally the first place the package addresses "how do you know what the system is doing while it runs," which is separate from both the architecture (`01`) and the eventual test plan (`11`). Get comfortable with the idea that logging/metrics requirements are a first-class design concern here, not an afterthought bolted on later.

7. **Seven new open decisions were surfaced (OD-05, OD-06, OD-08, OD-09, OD-10, OD-11), on top of the four from `01`.** This is expected, not a sign of a weak spec — implementation-level detail always reveals gaps a pure architecture document doesn't surface. `13_OPEN_DECISIONS.md` exists specifically to collect all of them without losing track of any.
