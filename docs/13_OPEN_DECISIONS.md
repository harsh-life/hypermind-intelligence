# 13_OPEN_DECISIONS.md
## Hypermind — Track A — Open Decisions

**Document:** STEP 13 of 15 · Track A Documentation Package
**Status:** REVISED 2026-09-15 — a substantial batch of decisions resolved by Harsh via direct architecture discussion. This revision **records** those decisions as authoritative. It does not reopen, reinterpret, or substitute them with the previously-proposed designs from `01`–`12`. Where a prior document's proposal is superseded, that document carries a pointer back here rather than being silently rewritten wholesale.
**Purpose:** unchanged — the single place every decision (resolved or still open) is recorded, so no one has to reconstruct context from eleven other documents.

---

## How This Document Is Organized

- **§0 — Resolution Log** — what changed in this revision and why, at a glance.
- **§1 — RESOLVED DECISIONS (LOCKED)** — decisions Harsh has made directly. These are now authoritative. Do not treat any superseded recommendation elsewhere in `01`–`12` as still governing where it conflicts with an entry here.
- **§2 — Remaining Open Items** — the small number of items not addressed in this revision, or explicitly left as "needs clarification" by Harsh's own decision text.
- **§3 — Follow-On Items Requiring Harsh's Confirmation** — narrow, downstream questions this revision's decisions raise in specific other documents (e.g., whether to also edit an acceptance gate), which were *not* explicitly decided and are not resolved here.
- **Summary Table** and **Cross-Document Impact Table** at the end.

---

# §0 — Resolution Log

On 2026-09-15, Harsh resolved OD-18, OD-06, OD-27, OD-17, OD-04, OD-08, and OD-11 through direct architecture discussion, explicitly rejecting the *previously proposed* designs in `07` §4 (forced egress proxy as a mandatory mechanism) and the framing of OD-27 as prompt/expected-answer benchmarking. In the same discussion, Harsh also answered nearly every other outstanding item in this document (OD-01, 02, 03, 09, 10, 12, 13, 14, 15, 16, 19, 20, 21, 22, 23, 24, 25, 26). Each is recorded below with its own entry. Nothing in this revision was inferred or extrapolated beyond what was explicitly stated — where a decision leaves a genuine gap, it is marked **NEEDS CLARIFICATION**, not silently filled.

---

# §1 — RESOLVED DECISIONS (LOCKED)

## OD-18 — Network / Egress Authorization
**STATUS: LOCKED**

**Prior proposal (superseded):** `07` §4 proposed a mandatory, per-run forced egress proxy (dynamically created Docker network, DNS-inclusive, fail-closed) as *the* mechanism enforcing that a tool container can only reach the current run's authorized target. That proposal is **no longer adopted as a requirement**. `07` §4 has been annotated in place to point here (see Cross-Document Impact Table) rather than being deleted — the proxy remains a legitimate future defense-in-depth option, not a rejected one.

**Authoritative decision:**
- Every network-capable tool request initiated by a model/worker must pass through the **Scope Gate** before the request is executed.
- The Scope Gate is the deterministic authorization checkpoint — this is a *reframing of authority*, not a new component. It already existed as step 2 of the Orchestrator's five-check chain (`02` §11); it is now explicitly the sole required enforcement point for network scoping at the MVP stage, not a network-layer proxy.
- The run's authorized scope (the **RunScope** — see OD-23 below) is established at the beginning of the run and contains the authorized domains, IPs/CIDRs, exclusions, ports/protocols, and other relevant constraints.
- The model may dynamically decide which authorized operation/tool it needs next. It may **not** grant itself new authorization or expand the run's scope.
- A tool request is authorized only when the requested operation/target is within the established RunScope. A Scope Gate denial means the tool request is never executed.
- This preserves the governing spine unchanged: **MODEL PROPOSES → POLICY/SCOPE DECIDES → TOOL EXECUTES.**
- The purpose of this decision is explicitly *not* to force every tool through a specific proxy path — the Scope Gate/Orchestrator check chain is the authorized checkpoint, full stop.

**Explicit constraints on this decision (do not violate when implementing):**
- Do not claim a proxy has been adopted — none has.
- Do not remove the possibility of future lower-level (network-layer) enforcement — it may still be added later if required.
- Do not add any technical enforcement mechanism beyond the Scope Gate check that hasn't been explicitly selected.
- Implementation-level networking details (how a container is actually launched, what if anything constrains its raw sockets) are left to the relevant implementation phase — not decided here.

**Superseded:** `07` §4's proxy design as a *mandatory MVP requirement*. **Not superseded:** `07` §§1–3, 5–8 (image provisioning, resource limits, timeout, filesystem, secrets, logging, cleanup) — those stand unchanged.

---

## OD-06 — Human Verification
**STATUS: LOCKED**

**Prior proposal (superseded):** the implicit framing across `02` §18 / the construction manual that a human decision gates *every* step reaching a candidate is corrected. Human validation was always structurally required only before **submission** in the canonical pipeline (`01` §5 already places Human Verification after Dedup, not after every internal stage) — this decision confirms and sharpens that reading, and settles OD-06's actual open question (interface mechanism).

**Authoritative decision:**
- Human validation does **not** happen after every model/tool/action step. The system executes an entire authorized test/research run without blocking on a human at each internal step.
- The human validation point is the **promotion of a completed test/candidate artifact into the validated state**:
  `TEST RUN → model/tool execution → evidence → candidate finding/test artifact → verification/review → HUMAN PROMOTION → VALIDATED`
- For MVP: expose an **API-oriented validation interface**. A human manually performs the promotion from candidate to validated state; the human action itself is the validation event. **No dashboard is required for MVP** — a future one-click UI may be built on the same API later.
- The architecture must not require synchronous human approval during every step of a run.
- A powerful cloud LLM may assist with verification/review and produce a structured verification package (recommend, score, summarize, identify contradictions, prioritize what to inspect) — it does **not** replace the human as the final promotion authority. It may not itself perform the candidate → VALIDATED promotion.
- This is **asynchronous/batched human validation of produced artifacts**, not "human-in-the-loop for every action."

**Resolves:** OD-06 (interface mechanism — settled as API, not CLI or dashboard, for MVP).
**Superseded:** nothing structurally — `09` §5's rule ("no `submit` without an identified human, no default/timeout-based auto-decision") was already compatible with this and remains fully in force. This decision resolves *which* interface, not whether human control is still mandatory — it still is.

---

## OD-27 — Model Benchmark / Candidate Evaluation
**STATUS: LOCKED**

**Prior proposal (superseded):** `16`'s Model Benchmarking Protocol and `11` §12's Model Evaluation Harness, as currently written, describe benchmarking as running N prompts against a role's schema and counting schema-valid outputs, plus a human-reviewed sample — a prompt/expected-answer-shaped evaluation. That framing is **superseded**. `11` §12 and `16` need rewriting to reflect the decision below before either is treated as implementation-ready (see Cross-Document Impact Table — flagged, not yet rewritten in this pass).

**Authoritative decision:**
- The benchmark is **not** a simple prompt/expected-answer dataset and is **not** based on model consensus.
- Model roles remain contract-driven; concrete models remain replaceable implementations — this part of `01`/`08`'s architecture is unchanged.
- For a role/task, multiple candidate models may compete under the **same controlled starting conditions** — same relevant initial knowledge/data/context, same authorized capability boundaries. Candidates then independently attempt to solve the task.
- Evaluation considers the actual **trajectory/performance**, including (non-exhaustively): understanding of the task; quality/relevance of actions; number and quality of meaningful experiments; ability to try alternative approaches; adaptation after failure/new evidence; efficiency; evidence quality; hallucinated/fabricated observations; whether claimed actions were actually performed; whether the task was actually solved; policy/scope compliance; and other role-specific dimensions.
- A strong Judge model may evaluate trajectories using a **fixed scoring contract** and explicit evaluation questions/criteria.
- The Judge is **not** a source of ground truth merely because it prefers one model's result — model consensus is not ground truth. Where possible, actual task success is established by an **objective observable result** in the controlled test environment. The Judge evaluates *how well* the candidate performed relative to the task/outcome.
- The Judge should **not** automatically receive the entire original parsed/recon dataset when irrelevant to judging a specific candidate trajectory. Instead, provide the **minimum relevant evaluation package**: candidate trajectory, actions performed, tool results produced by that candidate, evidence generated, claimed result, objective outcome, relevant resource/efficiency information. This reduces token use and reduces bias from over-exposure to the full investigation context.
- Candidate model identity/branding should be **hidden or minimized** in comparative evaluation where practical, to reduce model-family/name bias.
- The winning candidate is the one that performs best against the defined evaluation criteria and actual task outcome — **not** the one that wins a consensus vote.
- Resulting validated trajectories/evaluations may later be used as training/evaluation data for improving or fine-tuning role-specific models.
- The benchmark must remain **controlled, repeatable, and tied to objective outcomes** wherever possible. This is explicitly not "pick five models and let the biggest Judge choose."

**Resolves:** OD-27 (bootstrap dataset question) — the bootstrap set is a controlled collection of actual vulnerability/task cases (trajectory-evaluable), not a prompt/answer set. See also Q17/Q18/Q19 below for sample-size and threshold framing.

---

## OD-17 — Nuclei / Tool Authorization
**STATUS: PARTIALLY LOCKED — the authorization *model* is LOCKED; the concrete Nuclei template/capability policy is DEFERRED.**

**What is LOCKED:** the capability-oriented model below — the model may request a capability dynamically, and the Scope Gate/policy check authorizes or denies it before execution. This governs Nuclei exactly as it governs every other tool, and is not conditional on anything further.

**What is DEFERRED, not resolved:** which specific Nuclei templates/capabilities are actually permitted, and any concrete restriction on them, is **not decided by this entry**. That is real security-judgment work explicitly deferred to the Nuclei activation/implementation phase — this decision does not pre-authorize the full upstream template library, and does not itself grant Nuclei `active` status. Do not read the LOCKED authorization model as having settled what Nuclei is actually allowed to run.

**Prior proposal (superseded):** the framing in `13` (prior revision) and `06` §5 that OD-17 requires a Harsh-curated static allowlist of Nuclei template tags before any activation, implying a fixed, small, hardcoded template list. That framing is corrected — it should not be read as license to cripple model agency down to a tiny predetermined action sequence.

**Authoritative decision:**
- The model may reason about what additional information or operation it needs.
- The model may request an appropriate tool/capability dynamically.
- The request must pass through the Scope Gate / deterministic policy before execution.
- The model cannot grant itself new authorization or expand scope.
- The tool then executes the authorized operation and returns evidence.
- Boundary: **MODEL DECIDES WHAT IT NEEDS → POLICY/SCOPE DECIDES WHETHER IT IS AUTHORIZED → TOOL EXECUTES.**
- Nuclei operates within this same authorized capability/policy boundary as every other tool, while preserving meaningful model decision-making.
- Do not invent a giant static template list unless a later implementation/security decision explicitly requires one. Where a specific Nuclei capability/template restriction is actually required, it is defined based on the actual capability being implemented and verified during the relevant implementation phase — not pre-decided here.

**Effect on `06`'s Nuclei entry:** its `[REQ, blocking]` note ("must not be activated until OD-17's curated `template_tags` allowlist exists") is **superseded** by this decision — Nuclei is now governed by the same capability-request-through-Scope-Gate model as every other tool, not held to a separate pre-built allowlist requirement. See Cross-Document Impact Table.

---

## OD-04 / OD-08 / OD-11 — Storage
**STATUS: Architecture and boundaries LOCKED for all three · concrete storage technology DEFERRED for OD-08 and OD-11 · OD-04 LOCKED (no live engine required for MVP; see narrow residual note under §3)**

**What is LOCKED (architecture/boundaries):** run independence; structured machine-readable data as canonical source of truth with human-friendly formats as exports only; no automatic cross-run query from the live pipeline; clear separation between registry storage, per-run evidence, dedup state (if any), and research/audit history; separation from Track B/Mem0; local-to-the-execution-system for MVP.

**What is DEFERRED (concrete technology):** for OD-08, that manifests are git-tracked JSON/YAML is the locked *canonical form*; anything beyond that (tooling, validation scripts, directory layout specifics) is implementation-phase work. For OD-11, the exact local storage mechanism — plain structured files vs. a lightweight local datastore, and which one — is explicitly left open, to be chosen "where actual querying/indexing requirements justify it" at implementation time, not pre-selected here.

**Prior proposal (superseded):** `13`'s prior revision treated OD-04 as "pick a storage technology for a live deduplication findings index." That framing is superseded — the decision below reconsiders whether a live dedup engine is needed at all for MVP, rather than picking storage for one.

**Authoritative decision — core storage philosophy:**
- Run independence and auditable persistence. Each run is independently recorded as its own artifact set, preserving as appropriate: run metadata, raw observations, tool outputs/evidence, model outputs, candidate findings, validation results, final report/artifacts, provenance/lineage.
- A run does **not** automatically become live memory for future runs. Historical runs may later be consumed by the **offline** research/improvement system (patterns, hypotheses, training/eval data) — the live execution pipeline does not casually query historical research data as an implicit cross-run memory mechanism. This is fully consistent with, and reinforces, the existing Research Store firewall (`02` §19, `10` §1) — nothing here weakens that guarantee.
- For MVP, storage remains **local to the running system** where practical.
- **Structured machine-readable formats are the canonical source of truth** (e.g., JSON/JSONL, or an appropriate local structured datastore). Human-friendly formats (XLSX/CSV/HTML/PDF) are exports/views, never authoritative storage.
- Do not introduce additional storage technologies for future scale unless the actual workload/contract requires them.
- Preserve clear separation between: registry storage (OD-08), per-run evidence/findings, deduplication state (if any — see below), and research/audit history (OD-11) — and maintain the existing architectural separation from Track B / Mem0.
- "Run independence" does **not** mean "no persistence." Persistence is required; what's avoided is automatic cross-run behavioral influence in the live pipeline.

**OD-08 (registry manifest storage) — specifically:**
**LOCKED (canonical form):** registry manifests (Tool/Worker/Skill/Model) are version-controlled JSON/YAML files directly in the Git repository for MVP — human-reviewable, diffable, versioned, reproducible. No separate database required for MVP. **DEFERRED (implementation detail):** anything beyond that canonical form — validation tooling, exact directory layout, load-time mechanics — is left to the registry implementation phase, not decided here.

**OD-11 (Research/Audit Store) — specifically:**
**LOCKED (architecture):** remains local to the execution system for MVP. Runs persisted as independent, auditable artifact sets. Structured machine-readable data is canonical; human-friendly formats are exports. The live pipeline does not automatically query historical runs as implicit cross-run memory. **DEFERRED (concrete technology):** whether the local implementation uses simple structured files, a lightweight local datastore, or both, is intentionally left open — chosen only where actual querying/indexing needs justify it, at implementation time, not pre-selected here. (This also resolves **OD-24**: no additional application-level encryption-at-rest or long-term retention policy is required for the current MVP; storage inherits normal OS/filesystem security, and retention/cleanup remains an operational, not an application-enforced, concern — that part is fully LOCKED, not deferred.)

**OD-04 (Deduplication) — specifically:**
The prior assumption that a live cross-run deduplication index is required is reconsidered. Each Track A run is intentionally independent — findings, evidence, model outputs, and reports stay associated with their originating run and are not merged with other runs during live execution. Candidate models in competitive evaluation (OD-27) also operate independently on the same task and do not share findings/state/trajectories with one another; the Judge evaluates each candidate independently.
**Therefore: no live deduplication mechanism is required for MVP** solely to prevent repeated findings across independent runs. Repeated findings across runs may be retained as independent historical records. Cross-run similarity/consolidation is handled later, offline, by the research/analysis system as accumulated runs are used to improve the system.
This resolves **OD-10** as moot for MVP: since no live dedup index exists, no dedup-index-outage failure policy is required. If a dedicated deduplication subsystem is introduced later, its failure behavior will be decided when that subsystem is actually designed.

---

## Other Items Resolved in the Same Discussion

### OD-01 — Promptfoo
**STATUS: LOCKED.** Keep Promptfoo for MVP, repositioned into the **model-evaluation toolchain** (alongside the OD-27 trajectory-based Judge evaluation), not reinstated as a Tool-Registry entry for scanning third-party bounty targets. It may be used for repeatable prompt/model testing, structured-output checks, regression testing, and comparative model evaluation. Trajectory-based evaluation remains responsible for judging actual task performance, experimentation, adaptation, evidence, and objective outcomes. *(See §3 for the narrow residual question this raises about `06`'s existing Tool Registry Promptfoo entry.)*

### OD-02 — Retry/timeout/resource numeric values
**STATUS: LOCKED (as a deferred-and-configurable approach; no numeric values ratified).** Do not ratify the proposed per-component default numbers yet. The system is built with these values **configurable**. Real components are executed and observed first (model latency, tool runtime, memory/CPU behavior, retry behavior, resource pressure); operational values are established and tuned from real execution results, not predefined arbitrarily. This also resolves the `14` FINDING-3 timeout-nesting question the same way: **do not ratify the proposed model-timeout ≤ worker-timeout ≤ (independent) tool-timeout hierarchy yet** — timeout relationships remain configurable and are established after observing real execution/failure behavior.

### OD-03 — Host hardware profile
**STATUS: LOCKED.** Track A is developed in `harsh-life/hypermind-intelligence` and designed to be **portable**, not tied to one machine. Current environments: development/construction on a 4 GB RAM MacBook Air M1; heavier execution/testing on a separate 16 GB RAM laptop. The 4 GB Mac is not the architecture's resource ceiling. The 16 GB laptop's exact specs (including GPU/VRAM) should be verified before heavy model benchmarking. Model execution must be resource-aware (not hardcoded CPU-only or GPU-dependent) — role requirements, benchmark performance, and available resources jointly determine model selection, which may include locally-hosted/open-weight models or approved external/cloud models.

### OD-09 — Formalize TB-A's ScreenResult as a schema
**STATUS: LOCKED.** Formalize `ScreenResult` as a proper `03` schema rather than an ad-hoc log format, incorporated as Trust Boundary A is built. *(See Cross-Document Impact Table — added to `03` as a documented amendment.)*

### OD-12 — SkillManifest.vulnerability_class enum shape
**STATUS: LOCKED.** Open, registry-validated string, not a closed enum — confirms `03` §2.15's existing recommendation. Allows new vulnerability classes without a schema change per class.

### OD-13 — RawToolOutput truncation cap
**STATUS: LOCKED (as a deferred approach; no cap imposed for MVP).** Do not impose the proposed fixed 10 MB cap. Tool output is initially handled without an arbitrary hard size ceiling; real tool-output volume, memory behavior, context pressure, and execution characteristics are observed first. Any future output-size limit is introduced from measured behavior, not an arbitrary starting value.

### OD-14 — AI-security Skill gap
**STATUS: LOCKED.** Garak/PyRIT remain registered but **inactive and unroutable** for now — not activated until a corresponding AI-security Skill/capability exists **and** there is an applicable target scope for them.

### OD-15 — Manifest provenance inconsistency
**STATUS: LOCKED.** Adopt a shared `ManifestProvenance` structure across `ToolManifest`, `WorkerManifest`, and `SkillManifest` — the preferred common provenance representation, applied as the manifest schema is implemented. *(See Cross-Document Impact Table — added to `03` as a documented amendment.)*

### OD-16 — IDOR / Privilege-Escalation boundary
**STATUS: LOCKED (deferred).** Do not add special hardcoded tie-breaking logic yet. The Judge handles these cases using the general evaluation/role contract while real findings accumulate. Revisit after enough real routed candidates exist to justify a specific rule.

### OD-19 — ToolManifest.expected_output missing from `03`
**STATUS: LOCKED.** Formally add `expected_output` to `03`'s `ToolManifest` schema as an actual contract field, not an informal one only present in `06`'s instances. *(See Cross-Document Impact Table — added to `03` as a documented amendment.)*

### OD-20 — Cryptographic image signature verification
**STATUS: LOCKED (deferred).** Do not add signature verification for MVP. Digest pinning is the current baseline. Stronger verification can be added later if required.

### OD-21 — Subfinder OSINT provider API keys
**STATUS: LOCKED.** Keep Subfinder at zero third-party API secrets for MVP by default. Do not introduce a secrets-management/injection surface unless a specific OSINT provider capability is actually required.

### OD-22 — Judge/Specialist model-family diversity
**STATUS: LOCKED — reverses the prior recommendation.** Model-family diversity between Judge and Specialist is **not** a mandatory architecture-level restriction. The user decides which model components ("Lego pieces") are used together for a given configuration. Diversity may be considered during evaluation, but the architecture does not impose a hard registry constraint requiring different model families.
**Note, stated plainly because this reverses `14`'s RISK-2 mitigation stance:** `14`'s audit recommended *mandating* diversity specifically because no test in `11`/`12` currently catches a same-family Judge/Specialist pairing, and flagged the absence of such a test as a real, undetected risk to the finder/judge separation. This decision knowingly accepts that risk rather than mitigating it via a registry constraint. Recorded here as a deliberate, informed choice — not overlooked.

### OD-23 — authorization_reference: presence-only or validated?
**STATUS: LOCKED — resolved via a richer mechanism than either original option.** Track A uses a **source-flexible RunScope model**. The initial authorized scope for a run may originate from: human-provided scope; an uploaded structured scope file; or (later) normalized information extracted from an authorized bug-bounty/client scope source. A parser/model may extract and normalize scope information into a structured *candidate* RunScope, but it does **not** itself grant authorization. Before execution, the authorized RunScope is established/confirmed (by a human) and then used by the Scope Gate, which combines it with fixed policy constraints and evaluates every network-capable tool request before execution.
**RunScope structure** (fields, as applicable — populated per authorized engagement, never hardcoded into the architecture): `authorization_reference`, allowed domains, allowed subdomains, allowed IPs/CIDRs, allowed ports/protocols, exclusions, prohibited operation classes, relevant run metadata. *(See Cross-Document Impact Table — `03` §2.1/§2.2 need this richer shape; flagged, not yet rewritten in this pass.)*

### OD-24 — Log and research-store retention/encryption
**STATUS: LOCKED.** Folded into OD-11 above — no additional application-level encryption-at-rest or long-term retention policy required for the current MVP. Storage inherits normal OS/filesystem security; retention/cleanup is an operational concern, not a built-in application-enforced policy.

### OD-25 — Retroactive false-negative annotation mechanism
**STATUS: LOCKED (deferred).** Defer the specially-typed `ResearchEvent` mechanism. Existing run/evidence recording remains sufficient for now. Revisit when an actual false-negative/research-feedback workflow demonstrates the need.

### OD-26 — Dataset pruning policy
**STATUS: LOCKED.** Benchmark/evaluation datasets are versioned artifacts. If a contaminated or invalid case is discovered: the affected case is marked/excluded from future evaluation, and/or a corrected dataset version is issued. Historical `ExperimentRecord`s must retain the dataset version they were evaluated against, so past model results remain reproducible and traceable.

---

# §2 — Remaining Open Items

## OD-05 — Observability/logging stack
**STATUS: STILL OPEN.** Not addressed in this round of decisions. `13`'s prior non-blocking recommendation (lightweight structured JSON logging, adopted by the implementer, no gating decision needed) stands as the only guidance on record. Not reclassified, not resolved.

---

# §3 — Follow-On Items Requiring Harsh's Confirmation

These are narrow, downstream questions raised *by* the resolved decisions above, applying to specific other documents. They are not re-opening anything — they are asking how far the recorded decision should reach into documents this pass did not touch.

1. **OD-04 / Dedup acceptance gates — RESOLVED in the 2026-09-15 cleanup pass.** `12`'s Group I (AC-027, AC-028) and `11` §5.6's DEDUP-001–004 are now explicitly marked **N/A / DEFERRED FOR MVP** in both documents, preserved in place as future tests/gates for if and when a live cross-run deduplication subsystem is actually introduced. Not deleted, not silently dropped.

2. **OD-01 / Promptfoo's existing Tool Registry entry.** `06`'s Promptfoo entry (§8) was written for a different use case — an offensive/scanning tool against third-party AI targets, gated `provisional_pending_OD-01` specifically over the OpenAI-acquisition conflict-of-interest concern. The new decision repositions Promptfoo into the *model-evaluation toolchain* instead. Does this mean `06`'s Tool-Registry entry (for target-scanning use) stays exactly as it was — still inactive, still pending — because the new decision doesn't speak to that use case at all? Recorded as unaffected/separate pending your confirmation.

3. **Fine-tuning gate language in `01` §3 — RESOLVED in the 2026-09-15 cleanup pass.** `01` §3's numeric "2,000+ validated proprietary examples" gate has been removed and replaced with text reflecting the user-controlled sufficiency judgment already recorded under `08`'s fine-tuning note above. No replacement numeric threshold was invented. See Cross-Document Impact Table.

4. **`03` §2.1/§2.2 RunScope shape — still open, unchanged from the prior revision.** OD-23's RunScope field list is richer than the current `ScopeRequest`/`ScopeDecision` schemas (which hold only `target_identifier` + `authorization_reference`). A documented amendment noting the intended richer shape has been added to `03` (see Cross-Document Impact Table), but the schema tables themselves have not been restructured — that's real schema design work, left for the implementation phase per OD-23's own text.

Items 1 and 3 are now closed. Items 2 and 4 remain open and do not require an answer before further documentation recording continues — they matter once the affected document is actually touched for implementation.

---

## Summary Table (Quick Reference)

| ID | Short title | Status | Note |
|---|---|---|---|
| OD-01 | Promptfoo status | **LOCKED** | Repositioned to model-eval toolchain; see §3 item 2 |
| OD-02 | Retry/timeout/resource values | **LOCKED (deferred/configurable)** | No numbers ratified; determined from real execution |
| OD-03 | Host hardware profile | **LOCKED** | Portable; 4GB dev / 16GB execution; resource-aware |
| OD-04 | Dedup index vs. Mem0 boundary | **LOCKED** | No live dedup engine for MVP; `11`/`12` dedup tests/gates marked N/A/DEFERRED FOR MVP |
| OD-05 | Observability/logging stack | OPEN | Unaddressed this round |
| OD-06 | Human Verification interface | **LOCKED** | API-oriented, async/batched, no dashboard for MVP |
| OD-08 | Registry manifest storage | **Architecture LOCKED** | Git-tracked JSON/YAML is the canonical form; tooling/layout DEFERRED |
| OD-09 | ScreenResult schema | **LOCKED** | Formalized in `03` |
| OD-10 | Dedup outage: fail closed/open | **LOCKED (moot)** | No live dedup index exists for MVP |
| OD-11 | Research Store storage tech | **Architecture LOCKED** | Local, canonical-structured-data; exact tech (files vs. datastore) DEFERRED |
| OD-12 | vulnerability_class enum shape | **LOCKED** | Open, registry-validated string |
| OD-13 | Output truncation cap | **LOCKED (deferred)** | No fixed cap for MVP |
| OD-14 | AI-security Skill gap | **LOCKED** | Registered, inactive, unroutable until Skill+scope exist |
| OD-15 | SkillManifest.provenance fit | **LOCKED** | Shared `ManifestProvenance` across all 3 manifest types |
| OD-16 | IDOR/PrivEsc boundary | **LOCKED (deferred)** | No hardcoded rule yet |
| OD-17 | Nuclei template allowlist | **Model LOCKED · concrete policy DEFERRED** | Capability-request-through-Scope-Gate model is settled; which templates/capabilities are actually permitted is not |
| OD-18 | Network egress scoping mechanism | **LOCKED** | Scope Gate is the checkpoint; no proxy mandated |
| OD-19 | ToolManifest.expected_output gap | **LOCKED** | Formally added to `03` |
| OD-20 | Image signature verification | **LOCKED (deferred)** | Digest pinning only for MVP |
| OD-21 | OSINT provider API keys | **LOCKED** | Zero secrets for MVP |
| OD-22 | Judge/Specialist model diversity | **LOCKED** | Not mandatory; reverses prior recommendation |
| OD-23 | authorization_reference validation depth | **LOCKED** | Source-flexible, confirmed RunScope model |
| OD-24 | Log/research-store retention & encryption | **LOCKED** | Folded into OD-11; minimal for MVP |
| OD-25 | Retroactive false-negative mechanism | **LOCKED (deferred)** | Existing recording sufficient for now |
| OD-26 | Dataset contamination pruning policy | **LOCKED** | Versioned artifacts; mark/exclude or reissue |
| OD-27 | Benchmarking bootstrap dataset | **LOCKED** | Trajectory-based, controlled, objective-outcome evaluation |

**26 of 26 previously-tracked decisions now have a recorded status; OD-05 remains open, the other 25 have an architectural resolution recorded.** Several of those 25 (OD-04, OD-08, OD-11, OD-17) are resolved at the architecture level while explicitly naming a narrower implementation-level detail as still DEFERRED — see each entry above for exactly what remains open. OD-07 remains reserved into OD-04, never a standalone item.

**On reading this table:** "LOCKED" here means the architectural question is settled, not that every implementation detail is decided. Where a decision names a DEFERRED sub-item, that sub-item is intentionally left for the relevant implementation phase — it is not an oversight and not still under debate.

---

## Cross-Document Impact Table

Where a canonical document's existing text would otherwise contradict a decision above. "Annotated" = a pointer/superseded-note was added in this pass without deleting the original content. "Flagged only" = identified here but not yet edited, pending your direction (see §3).

| Document | Section | Old status | Action taken |
|---|---|---|---|
| `07_DOCKER_SPEC_README.md` | §4 Network Policy | Proposed forced-proxy as OD-18's resolution | **Annotated** — superseded note added, proxy content kept as a future option |
| `06_TOOL_REGISTRY_README.md` | Cross-cutting OD-18 note | Asked "how is egress dynamically scoped" as unresolved | **Annotated** — superseded note pointing to `13` OD-18 |
| `06_TOOL_REGISTRY_README.md` | §5 Nuclei entry | `[REQ, blocking]` on OD-17 allowlist | **Annotated** — superseded note pointing to `13` OD-17 |
| `02_COMPONENT_SPECS.md` | §10 Deduplication Engine | Described as needing a persisted findings index | **Annotated** — superseded note pointing to `13` OD-04 |
| `02_COMPONENT_SPECS.md` | §18 Human Verification Interface | OD-06 marked fully open (CLI vs. dashboard) | **Annotated** — updated to reflect the API/async decision |
| `03_DATA_SCHEMAS_README.md` | New §4 Amendments | N/A | **Added** — `ManifestProvenance` common type, `ToolManifest.expected_output`, `ScreenResult` schema, RunScope shape note |
| `08_MODEL_REGISTRY.md` | Currently Selected Implementations / Judge row | Judge marked UNDECIDED, diversity recommended | **Annotated** — Judge = interchangeable Lego, initial pick a heavyweight cloud model; diversity not mandated; Report Polisher treated as Judge-like |
| `11_TEST_PLAN_README.md` | §12 Model Evaluation Harness | Described as N-prompt schema-validity benchmarking | **Flagged only** — needs a trajectory-based rewrite; not rewritten in this pass |
| `16_EVALUATION_BENCHMARKING.md` | Whole document | Prompt/expected-answer-shaped criteria table | **Flagged only** — needs a trajectory-based rewrite; not rewritten in this pass |
| `12_ACCEPTANCE_CRITERIA_README.md` | Group I (AC-027/028) | Assumed a live Dedup Engine exists | **Annotated** — marked N/A/DEFERRED FOR MVP, preserved for future use |
| `11_TEST_PLAN_README.md` | §5.6 (DEDUP-001–004) | Assumed a live Dedup Engine exists | **Annotated** — marked N/A/DEFERRED FOR MVP, preserved for future use |
| `01_ARCHITECTURE.md` | §3 Non-Goals (fine-tuning gate) | `[LOCKED]` 2,000+ example numeric gate contradicted the user-controlled fine-tuning decision | **Fixed** — numeric threshold removed, no replacement number invented; gate now reads as user-controlled sufficiency judgment |
| `01_ARCHITECTURE.md` | §5, §9 (pipeline / Orchestrator) | — | **No contradiction found** — already compatible with OD-18/OD-06 as written |
| `09_SECURITY_POLICIES_README.md` | §5 Human-Validation Controls | — | **No contradiction found** — already compatible with OD-06 (validation gates submission, not every step) |
| `10_RESEARCH_DATA_PIPELINE.md` | §1 Firewall | — | **No contradiction found** — fully compatible with, and reinforced by, the OD-04/08/11 storage philosophy |

---

## WHAT YOU SHOULD UNDERSTAND BEFORE NEXT

1. **This revision records decisions; it does not re-derive them.** Every LOCKED entry above states what was decided, not a fresh analysis of tradeoffs — that analysis is no longer relevant now that a decision exists.
2. **"Annotated" is deliberately non-destructive.** Superseded proposals (the egress proxy, the static Nuclei allowlist framing, the live dedup index) remain visible in their original documents as historical/future-optional content, not deleted — consistent with "do not remove the possibility of future lower-level enforcement" and the general project discipline against silently rewriting prior decisions.
3. **Four items in §3 are genuinely unresolved ripple effects, not new open decisions.** They exist only because a resolved decision touches a document this pass didn't rewrite. They should be resolved when that specific document is next touched, not before.
4. **OD-22's reversal is the one decision in this batch that knowingly re-accepts a previously-flagged risk.** Every other resolution either matches or extends the documentation's own prior recommendation. OD-22 is the exception, and it's recorded as a deliberate choice, not an oversight.
