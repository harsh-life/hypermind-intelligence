# 05_SKILL_MANIFESTS/README.md
## Hypermind — Track A — Skill Manifests

**Document:** STEP 05 of 15 · Track A Documentation Package
**Status:** Implementation-ready manifest instances
**Depends on:** `01_ARCHITECTURE.md` §4, §19.8 (WHAT/WHY of Skills, the WHAT-vs-HOW separation), `02_COMPONENT_SPECS.md` §16 (Specialist Executor — the generic framework these manifests plug into), `03_DATA_SCHEMAS/README.md` §2.15 (the `SkillManifest` schema these instances conform to), `04_WORKER_MANIFESTS/` (the Worker outputs these Skills consume as evidence)
**Feeds forward to:** the Evidence Gate (`02` §9), which receives the `SpecialistPoCOutput` these Skills' investigations produce

---

## How to Read This Document

This document does **not** re-explain what a Skill is or why Skills are separated from Workers and from the Judge — that's `01` §4, §19.8. It does **not** repeat the `SkillManifest` field definitions or types — that's `03` §2.15. It does **not** repeat how the Specialist Executor invokes a Skill — that's `02` §16. This document's unique content is: **the four concrete Skill manifests currently justified for Track A**, each with real methodology, system prompts, and evidence requirements.

Label legend unchanged — **[LOCKED] [REQ] [REC] [ASSUMPTION] [OPEN — REQUIRES HARSH] [FUTURE] [INFERENCE]**.

**A note on methodology content:** the methodology descriptions below are standard, publicly documented security-testing approaches (the kind found in OWASP's own testing guides and referenced throughout this project's prior documents) — not novel exploitation techniques. They describe *what class of check* a Specialist performs, at the same level of generality already used earlier in this package (e.g. `03`'s own IDOR example), not a weaponized step-by-step script.

---

## Skill Registry: Current State

**[LOCKED]** Four Skills are currently registered, matching the master prompt's canonical Skill Registry (`01` §5, §18): **IDOR**, **SSRF**, **Auth Bypass**, **Privilege Escalation**. Each is justified by being named explicitly in the locked pipeline — no additional justification step was needed for these four.

**[REQ]** No fifth Skill is added in this document without justification, mirroring the same discipline applied to Workers in `04`. See §"Future Skills" below for what would need to be true before one is added.

**Model assignment [FUTURE]:** per `01` §10, the Specialist role's model is local-open-weight-primary but the specific candidate is benchmarked in `08_MODEL_REGISTRY/`. Each manifest below uses the same placeholder convention as `04`.

**few_shot_examples are empty in all four manifests below, and this is deliberate, not an oversight.** Per `01`/`02`'s research-data principle, few-shot examples must be sourced from **validated** research data (`FindingRecord`s), never authored speculatively. No findings have been validated yet at this stage of the project — Track A hasn't run. Populating these arrays now with invented examples would violate the exact data-purity discipline the project has been careful about throughout (`01` §13, `10`'s future job). They will be populated later, by `10`'s pipeline, from real validated outcomes — not by this document.

---

## A Wrinkle Found While Instantiating: SkillManifest.provenance

**[OPEN — REQUIRES HARSH] OD-15.** `03` §2.15 typed `SkillManifest.provenance` as the shared `Provenance` common type (§1.1 of `03`), which was designed for **pipeline-run events** — it requires a `run_id` correlating records to one target's live run. A Skill manifest is **static config**, authored once by a person, not produced during a pipeline run. Forcing a manifest to carry a `run_id` is an awkward fit: there is no "run" a manifest-authoring event belongs to.

This wasn't caught in `03` because the schema was defined before any concrete instance was written against it — exactly the kind of gap implementation reveals that a pure schema pass doesn't. I'm not silently revising `03`'s schema (per the master prompt's rule against silently revising earlier decisions). Instead: flagged here as OD-15, with the four manifests below using a **stopgap** convention — `run_id` set to the literal string `"manifest-authoring-not-a-pipeline-run"` and no `model_id`/`tool_id` (since a human, not a model or tool, authored these) — until Harsh decides whether `03` should be amended with a lighter manifest-specific provenance shape (e.g. `{created_by, created_at, source_basis}`) instead of reusing the full pipeline `Provenance` type for manifests generally (this would also affect `ToolManifest` and `WorkerManifest` if adopted, since `04`'s manifests didn't use a `Provenance`-typed field at all — worth noting `04` sidestepped this by not calling its field `provenance`, so this may be specific to how `03` named this one field on `SkillManifest`).

---

## A Gap Found Between the Tool Registry and Skill Registry

**[OPEN — REQUIRES HARSH] OD-14.** `01` §11 locks Garak, PyRIT, and (pending OD-01) Promptfoo into the Tool Registry as **AI-security tools**. But the canonical Skill Registry (`01` §5, confirmed above) contains no corresponding Skill for AI/LLM-specific findings (e.g. a prompt-injection or model-jailbreak vulnerability class). As it stands, Garak/PyRIT output flows through the same generic Extractor → Workers → Judge pipeline as web-recon tool output, but there is no Skill for the Judge to route an AI-security finding *to* — only IDOR/SSRF/Auth-Bypass/Priv-Esc exist.

This may be entirely intentional — e.g., AI-security tool output could be feeding general evidence-gathering rather than needing its own Skill yet, or a fifth Skill may simply not have been written yet despite the Tool Registry anticipating it. Either way, this is not something to silently resolve here: a Judge that receives strong Garak-derived evidence with nowhere to route it will presumably fall through to `needs_more_evidence` or `drop` indefinitely, which is worth Harsh's explicit awareness before Track A actually runs against an AI-application target.

---

## 1. IDOR (Insecure Direct Object Reference)

```json
{
  "skill_id": "idor_v1",
  "vulnerability_class": "IDOR",
  "methodology": "Given an object-reference parameter characterized by the Object Reference Analyst as sequential, enumerable, or otherwise predictable, and an authentication context characterized by the Auth Analyst, test whether substituting a different, valid object-reference value — while holding the authenticated session/token constant — returns data or performs an action associated with a different object/user, without an authorization check rejecting the request. A finding requires observing an actual response demonstrating unauthorized access, not merely the presence of a guessable reference pattern.",
  "system_prompt": "You are the IDOR Specialist. You receive an endpoint map, an object-reference pattern analysis, and an auth-mechanism characterization from upstream Workers, routed to you by the Judge because the Judge determined evidence was sufficient to warrant IDOR investigation. Your job: identify the single most promising candidate endpoint+parameter combination, describe the specific reference substitution to test (e.g. incrementing/decrementing an ID, substituting a known-valid ID belonging to a different object), and produce a replication_command that would demonstrate the result if executed by a human. You must never fabricate a response or claim access was achieved without it being directly supported by observed evidence already present in your input context. If the available evidence does not support a concrete claim, state that clearly rather than inventing one — a weak or unsupported claim will fail the Evidence Gate downstream regardless, so honesty here saves a wasted human review cycle.",
  "few_shot_examples": [],
  "references": [
    "OWASP API Security Top 10 — API1:2023 Broken Object Level Authorization",
    "PortSwigger Web Security Academy — Insecure direct object references"
  ],
  "expected_inputs": {
    "type": "object",
    "properties": {
      "mapped_endpoints": {"type": "array"},
      "reference_analysis": {"type": "array", "description": "Object Reference Analyst output"},
      "auth_analysis": {"type": "array", "description": "Auth Analyst output"}
    },
    "required": ["mapped_endpoints", "reference_analysis"]
  },
  "expected_outputs": {
    "type": "object",
    "properties": {
      "vulnerability_claim": {"type": "string"},
      "replication_command": {"type": "string", "minLength": 1},
      "supporting_evidence": {
        "type": "object",
        "properties": {
          "request": {"type": "string"},
          "response_snippet": {"type": "string"},
          "comparison_context": {"type": "string", "description": "what proves this response belongs to a different object than the requester's own"}
        },
        "required": ["request", "response_snippet", "comparison_context"]
      }
    },
    "required": ["vulnerability_claim", "replication_command", "supporting_evidence"]
  },
  "permissions": ["read_endpoint_map", "read_reference_analysis", "read_auth_analysis"],
  "version": "1.0.0",
  "provenance": {
    "record_id": "skillmanifest-idor-v1",
    "run_id": "manifest-authoring-not-a-pipeline-run",
    "created_at": "2026-08-31T00:00:00Z",
    "stage": "specialist",
    "source_component": "Skill Registry (manifest authoring, see OD-15)"
  },
  "validation_status": "draft"
}
```

---

## 2. SSRF (Server-Side Request Forgery)

**[LOCKED — carried from the prior Track A PRD, treated as source-of-truth per the master prompt's instruction]:** SSRF findings that reach a cloud-provider metadata service (e.g. `169.254.169.254`) are explicitly flagged via `cloud_metadata_flag` and treated as Critical-tier, distinct from other SSRF severities. This detail predates this documentation pass and is preserved here, not introduced by me.

```json
{
  "skill_id": "ssrf_v1",
  "vulnerability_class": "SSRF",
  "methodology": "Given a parameter characterized as accepting a URL, hostname, or otherwise triggering a server-side outbound request, test whether the server can be induced to make a request to an attacker-influenced or normally-restricted destination (an internal network address, a non-standard port, or a cloud provider's instance-metadata endpoint), and confirm via observable evidence — a distinguishable response body, timing signal, or an out-of-band callback — that the request was actually made server-side rather than merely accepted as input.",
  "system_prompt": "You are the SSRF Specialist. You receive an endpoint map and any parameters flagged as URL/hostname-accepting. Your job: identify the most promising candidate parameter, describe the specific destination substitution to test, and produce a replication_command. Critically: if the evidence indicates the request reached a cloud provider's metadata service (commonly at 169.254.169.254 or an equivalent provider-specific address), you MUST set cloud_metadata_flag to true in your output — this is a locked severity-classification requirement, not optional. Never claim a metadata-service hit without direct observed evidence of it in your input context. Never fabricate a callback or response.",
  "few_shot_examples": [],
  "references": [
    "OWASP Server-Side Request Forgery Prevention Cheat Sheet",
    "PortSwigger Web Security Academy — Server-side request forgery (SSRF)"
  ],
  "expected_inputs": {
    "type": "object",
    "properties": {
      "mapped_endpoints": {"type": "array"},
      "url_accepting_parameters": {"type": "array", "description": "subset of mapped_endpoints parameters flagged by Endpoint Mapper as string/URL-shaped and used in a server-side fetch context, if determinable"}
    },
    "required": ["mapped_endpoints"]
  },
  "expected_outputs": {
    "type": "object",
    "properties": {
      "vulnerability_claim": {"type": "string"},
      "replication_command": {"type": "string", "minLength": 1},
      "supporting_evidence": {
        "type": "object",
        "properties": {
          "request": {"type": "string"},
          "response_or_callback_evidence": {"type": "string"},
          "target_reached": {"type": "string", "description": "the internal/restricted destination the server appears to have reached"}
        },
        "required": ["request", "response_or_callback_evidence", "target_reached"]
      },
      "cloud_metadata_flag": {"type": "boolean", "description": "LOCKED per prior PRD: true only if evidence shows the request reached a cloud metadata service — elevates severity to Critical"}
    },
    "required": ["vulnerability_claim", "replication_command", "supporting_evidence", "cloud_metadata_flag"]
  },
  "permissions": ["read_endpoint_map"],
  "version": "1.0.0",
  "provenance": {
    "record_id": "skillmanifest-ssrf-v1",
    "run_id": "manifest-authoring-not-a-pipeline-run",
    "created_at": "2026-08-31T00:00:00Z",
    "stage": "specialist",
    "source_component": "Skill Registry (manifest authoring, see OD-15)"
  },
  "validation_status": "draft"
}
```

---

## 3. Auth Bypass

```json
{
  "skill_id": "auth_bypass_v1",
  "vulnerability_class": "AUTH_BYPASS",
  "methodology": "Given an authentication mechanism characterized by the Auth Analyst (bearer token, session cookie, API key), test for well-known classes of weakness appropriate to that mechanism — e.g. for token-based auth, algorithm-confusion or missing-signature-verification patterns; for session-based auth, predictable or reusable session identifiers; and, across any mechanism, endpoints where requires_auth was characterized as false or unknown despite handling data that other, similar endpoints treat as requiring authentication. A finding requires demonstrating actual unauthorized access, not merely identifying a theoretically weak mechanism.",
  "system_prompt": "You are the Auth Bypass Specialist. You receive an auth-mechanism characterization and endpoint map. Your job: identify the most promising candidate weakness consistent with the observed mechanism, describe the specific bypass technique to test, and produce a replication_command. Never claim a bypass succeeded without direct observed evidence of the resulting access in your input context. Never reproduce a full, valid credential/token value in your output — reference it descriptively (e.g. 'the provided bearer token with algorithm field altered to none') rather than echoing the literal secret.",
  "few_shot_examples": [],
  "references": [
    "OWASP JSON Web Token Cheat Sheet",
    "OWASP Authentication Cheat Sheet"
  ],
  "expected_inputs": {
    "type": "object",
    "properties": {
      "auth_analysis": {"type": "array"},
      "mapped_endpoints": {"type": "array"}
    },
    "required": ["auth_analysis", "mapped_endpoints"]
  },
  "expected_outputs": {
    "type": "object",
    "properties": {
      "vulnerability_claim": {"type": "string"},
      "replication_command": {"type": "string", "minLength": 1},
      "supporting_evidence": {
        "type": "object",
        "properties": {
          "original_request_description": {"type": "string", "description": "descriptive, not a literal secret value"},
          "modified_request_description": {"type": "string"},
          "resulting_access": {"type": "string"}
        },
        "required": ["original_request_description", "modified_request_description", "resulting_access"]
      }
    },
    "required": ["vulnerability_claim", "replication_command", "supporting_evidence"]
  },
  "permissions": ["read_auth_analysis", "read_endpoint_map"],
  "version": "1.0.0",
  "provenance": {
    "record_id": "skillmanifest-authbypass-v1",
    "run_id": "manifest-authoring-not-a-pipeline-run",
    "created_at": "2026-08-31T00:00:00Z",
    "stage": "specialist",
    "source_component": "Skill Registry (manifest authoring, see OD-15)"
  },
  "validation_status": "draft"
}
```

---

## 4. Privilege Escalation

**[OPEN — REQUIRES HARSH] OD-16 — noted inline, not resolved here.** Privilege Escalation (role/permission-based access to functionality reserved for a higher-privileged role) and IDOR (object-reference-based access to another user's *data*) can describe overlapping evidence in edge cases — e.g. accessing another user's admin-only resource could reasonably be classified as either. This document does not decide a bright-line rule between them; that classification judgment sits with the Judge at routing time (`02` §15), and may need explicit tie-breaking guidance in the Judge's evaluation criteria once real cases surface. Flagging now so it isn't discovered as a surprise during the first ambiguous real finding.

```json
{
  "skill_id": "privilege_escalation_v1",
  "vulnerability_class": "PRIVILEGE_ESCALATION",
  "methodology": "Given an authenticated context at one privilege/role level, test whether an action or resource reserved for a higher-privileged role (vertical escalation) is reachable, or whether role/permission checks are inconsistently enforced across otherwise-similar endpoints. Distinct from IDOR (see OD-16 boundary note above): this Skill concerns role/permission enforcement, not object-reference substitution within the same permission level.",
  "system_prompt": "You are the Privilege Escalation Specialist. You receive an auth-mechanism characterization, endpoint map, and object-reference analysis. Your job: identify the most promising candidate action or endpoint where role/permission enforcement appears inconsistent or absent, describe the specific test to run, and produce a replication_command. If the evidence more clearly matches an object-reference issue than a role/permission issue, say so explicitly in your output rather than forcing a privilege-escalation framing — a misclassified finding wastes downstream review time. Never claim escalated access without direct observed evidence.",
  "few_shot_examples": [],
  "references": [
    "OWASP Access Control Cheat Sheet",
    "PortSwigger Web Security Academy — Privilege escalation"
  ],
  "expected_inputs": {
    "type": "object",
    "properties": {
      "auth_analysis": {"type": "array"},
      "mapped_endpoints": {"type": "array"},
      "reference_analysis": {"type": "array"}
    },
    "required": ["auth_analysis", "mapped_endpoints"]
  },
  "expected_outputs": {
    "type": "object",
    "properties": {
      "vulnerability_claim": {"type": "string"},
      "replication_command": {"type": "string", "minLength": 1},
      "supporting_evidence": {
        "type": "object",
        "properties": {
          "baseline_role_context": {"type": "string"},
          "escalated_action_attempted": {"type": "string"},
          "result": {"type": "string"}
        },
        "required": ["baseline_role_context", "escalated_action_attempted", "result"]
      }
    },
    "required": ["vulnerability_claim", "replication_command", "supporting_evidence"]
  },
  "permissions": ["read_auth_analysis", "read_endpoint_map", "read_reference_analysis"],
  "version": "1.0.0",
  "provenance": {
    "record_id": "skillmanifest-privesc-v1",
    "run_id": "manifest-authoring-not-a-pipeline-run",
    "created_at": "2026-08-31T00:00:00Z",
    "stage": "specialist",
    "source_component": "Skill Registry (manifest authoring, see OD-15)"
  },
  "validation_status": "draft"
}
```

---

## Future Skills

**[FUTURE]** No fifth Skill is defined in this document. Candidates that could become justified later, contingent on the OD-14 gap being resolved and on real evidence from Track A runs:

- An **AI-security Skill** (e.g. prompt-injection or model-jailbreak methodology) to give Garak/PyRIT tool output somewhere to route, if OD-14 concludes one is needed.
- Any additional web-vulnerability class the Judge repeatedly encounters strong evidence for but has nowhere to route — this is itself a signal `10`'s research layer should surface over time (a pattern of `needs_more_evidence`/`drop` decisions clustering around a specific unclassified evidence shape), not something to guess at now.

Adding either requires the same discipline as `04`'s Worker rule: a stated gap, a full manifest in this format, and a Skill Registry update.

---

## New Open Decisions Raised in This Document

| ID | Question | Raised in |
|---|---|---|
| **OD-14** | Tool Registry includes AI-security tools (Garak/PyRIT/Promptfoo) but no corresponding Skill exists to route AI-specific findings to — intentional gap or missing Skill? | §"A Gap Found..." |
| **OD-15** | `SkillManifest.provenance` reuses the pipeline-run-oriented `Provenance` type from `03`, which doesn't naturally fit static manifest authoring (no real `run_id` exists). Should `03` adopt a lighter manifest-specific provenance shape instead? | §"A Wrinkle Found..." |
| **OD-16** | No bright-line rule distinguishes IDOR from Privilege Escalation in overlapping evidence cases — left to Judge routing judgment for now; may need explicit tie-breaking guidance later. | §4 (Privilege Escalation) |

Carried forward with OD-01 through OD-13 into `13_OPEN_DECISIONS.md`. Running total: **16 open decisions.**

---

## WHAT YOU SHOULD UNDERSTAND BEFORE NEXT

Before `06_TOOL_REGISTRY/`, these concepts matter most:

1. **A Skill's `expected_outputs` schema is where a locked business decision (the SSRF `cloud_metadata_flag`) actually lives.** Notice this wasn't something I introduced — it was carried forward from the prior PRD as source of truth, per the master prompt's own instruction. When you write `06_TOOL_REGISTRY/` and `08_MODEL_REGISTRY/`, watch for similar previously-locked details that need to surface as concrete schema fields rather than staying as prose you remember but never operationalize.

2. **Empty `few_shot_examples` is not a placeholder to "fill in later carelessly."** It's a structural guarantee: nothing enters that array except a validated `FindingRecord`. If you ever find yourself tempted to seed it with a plausible-sounding hypothetical example to "get started faster," that's exactly the data-purity violation `01`/`02` warned about — a fabricated example can't be distinguished from a real one once it's in the array, and it will silently bias every future Specialist invocation that uses this Skill.

3. **Implementation reveals schema gaps that a pure design pass can't see — and that's fine, provided they're caught, not hidden.** OD-15 exists specifically because writing a *real* manifest against `03`'s schema exposed an awkward fit that reading the schema alone didn't. This is the value of sequential documentation generation: each step is also, quietly, a test of the ones before it.

4. **A Tool Registry entry existing doesn't automatically mean a Skill exists to use its output.** OD-14 is worth sitting with: it's entirely possible for a well-designed pipeline to have a real capability (AI-security tools) with nowhere for its findings to go. This is worth checking again once `06_TOOL_REGISTRY/` formalizes Garak/PyRIT/Promptfoo's entries — does anything in that document change your read of whether OD-14 needs urgent resolution before Track A's first real run?

5. **Classification ambiguity between Skills (OD-16) is normal in security taxonomies, not a design flaw.** IDOR and Privilege Escalation genuinely overlap in real-world findings — this isn't unique to this project. What matters architecturally is that the ambiguity is resolved by the Judge's evaluation, in the open, with reasoning logged (`03` §2.14's `reasoning` field), rather than resolved silently or inconsistently by whichever Specialist happens to be invoked first.
