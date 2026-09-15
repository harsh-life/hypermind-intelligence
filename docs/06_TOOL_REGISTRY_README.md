# 06_TOOL_REGISTRY/README.md
## Hypermind — Track A — Tool Registry

**Document:** STEP 06 of 15 · Track A Documentation Package
**Status:** Implementation-ready registry entries
**Depends on:** `01_ARCHITECTURE.md` §11, §17, §19.4 (WHAT/WHY of tool execution, Docker isolation principle), `02_COMPONENT_SPECS.md` §1, §12 (Tool Registry mechanism, Docker Tool Execution Engine), `03_DATA_SCHEMAS/README.md` §2.4 (the `ToolManifest` schema these entries conform to)
**Feeds forward to:** `07_DOCKER_SPEC/` (container specifics these entries reference but don't fully define), `08_MODEL_REGISTRY/` (the AI-security tools here produce output that later feeds Extractor/Worker models)

---

## How to Read This Document

This does not re-explain why tools are isolated in containers (`01` §17), how the Tool Registry mechanism works (`02` §1), or the `ToolManifest` field types (`03` §2.4). New content here: **eight concrete registry entries**, populated with real values for the tools already named in `01`'s locked pipeline. **[REQ]** No tool appears here that isn't already named in `01` §11 — "do not add random tools" is honored by construction, not by a separate check.

Label legend unchanged — **[LOCKED] [REQ] [REC] [ASSUMPTION] [OPEN — REQUIRES HARSH] [FUTURE] [INFERENCE]**.

**On version numbers and container digests:** exact current version numbers and container image digests are implementation-time facts that need live verification against the actual upstream projects at deployment time — asserting a specific digest or "latest version" here would risk documenting something stale or simply wrong. Every entry below uses a placeholder (`<PINNED_DIGEST_REQUIRED>`) for the digest and an illustrative version tag flagged **[ASSUMPTION — verify at deployment]**, consistent with `07_DOCKER_SPEC/`'s eventual job of enforcing real pinned digests.

---

## Registry State

**[LOCKED]** Eight tools, matching `01` §11 exactly:

| Category | Tools |
|---|---|
| Recon / web | Subfinder, Httpx, Katana, Ffuf |
| Vulnerability scan | Nuclei ("where explicitly supported" — see OD-17) |
| AI-security | Garak, PyRIT, Promptfoo (**provisional**, pending OD-01) |

**[REC]** `category` in `03` §2.4 was defined as a 3-value enum (`recon \| ai_security \| web_probe`). Nuclei doesn't fit any of those — it's a vulnerability-detection tool, not passive recon or a probe. `03` explicitly permits extending this enum "as needed via registry update, not a code change" (§2.4 note). This document exercises that permission and adds a fourth value: `vulnerability_scan`.

**On Promptfoo specifically:** its entry below is fully populated so it's ready to activate the moment OD-01 resolves, but it is marked `validation_status: provisional_pending_OD-01` and **must not be treated as authorized for use** until Harsh resolves whether to keep it, drop it, or pin a pre-acquisition fork (per `01` §11's original flag).

---

## 1. Subfinder

```json
{
  "tool_id": "subfinder",
  "name": "Subfinder",
  "version": "v2.6.3 (illustrative — verify current stable at deployment)",
  "purpose": "Passive subdomain enumeration using public sources — does not send requests to the target itself.",
  "category": "recon",
  "input_schema": {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]},
  "output_schema": {"type": "array", "items": {"type": "string"}, "description": "advisory — one discovered subdomain per entry"},
  "expected_output": "A list of subdomains believed to belong to the target domain, sourced from passive/public data — not confirmed live or reachable (that's Httpx's job downstream).",
  "container_image": "<PINNED_DIGEST_REQUIRED — see 07_DOCKER_SPEC>",
  "network_requirements": {"egress": "DNS + HTTPS to passive-source APIs only; no direct contact with the target's infrastructure since this tool is passive by design"},
  "filesystem_requirements": {"read_only_root": true, "scratch_space_mb": 50},
  "resource_limits": {"cpu": "1", "memory_mb": 512, "pid_limit": 64},
  "timeout_seconds": 120,
  "allowed_stages": ["tool_execution"],
  "risk_classification": "low",
  "failure_handling": "On timeout, treat any partial output as untrusted; do not auto-retry — a timeout on a passive lookup is usually a source outage, not a transient error worth retrying blindly.",
  "audit_requirements": "Log domain input and exit code. Full output list may be logged (non-sensitive, publicly-sourced subdomain names)."
}
```

## 2. Httpx

```json
{
  "tool_id": "httpx",
  "name": "Httpx",
  "version": "v1.6.x (illustrative — verify current stable at deployment)",
  "purpose": "Actively probe a list of hosts for HTTP/HTTPS liveness, status code, response headers, and basic technology fingerprinting.",
  "category": "recon",
  "input_schema": {"type": "object", "properties": {"hosts": {"type": "array", "items": {"type": "string"}}}, "required": ["hosts"]},
  "output_schema": {"type": "array", "items": {"type": "object"}, "description": "advisory — one object per probed host with status_code, title, tech fingerprint"},
  "expected_output": "For each input host: whether it responded, its status code, page title if HTML, and any detectable technology fingerprint. Read-only probing — no state-changing requests.",
  "container_image": "<PINNED_DIGEST_REQUIRED — see 07_DOCKER_SPEC>",
  "network_requirements": {"egress": "HTTP/HTTPS to the authorized target's hosts ONLY — see the cross-cutting network-scoping note below (OD-18)"},
  "filesystem_requirements": {"read_only_root": true, "scratch_space_mb": 50},
  "resource_limits": {"cpu": "1", "memory_mb": 256, "pid_limit": 32},
  "timeout_seconds": 90,
  "allowed_stages": ["tool_execution"],
  "risk_classification": "low",
  "failure_handling": "Per-host failures (unreachable, timeout) are recorded as such in the output, not treated as a whole-tool failure — a partial success across many hosts is the expected common case.",
  "audit_requirements": "Log host list input (count + hash, not necessarily every hostname if the list is large) and per-host response summary."
}
```

## 3. Katana

```json
{
  "tool_id": "katana",
  "name": "Katana",
  "version": "v1.1.x (illustrative — verify current stable at deployment)",
  "purpose": "Actively crawl the target web application to discover additional endpoints/URLs beyond passive recon.",
  "category": "recon",
  "input_schema": {"type": "object", "properties": {"start_url": {"type": "string"}, "max_depth": {"type": "integer", "minimum": 1}}, "required": ["start_url"]},
  "output_schema": {"type": "array", "items": {"type": "string"}, "description": "advisory — discovered URLs"},
  "expected_output": "A list of URLs discovered by crawling from start_url, up to max_depth. Read-only crawling — follows links, does not submit forms or otherwise mutate state.",
  "container_image": "<PINNED_DIGEST_REQUIRED — see 07_DOCKER_SPEC>",
  "network_requirements": {"egress": "HTTP/HTTPS to the authorized target's hosts ONLY — see OD-18"},
  "filesystem_requirements": {"read_only_root": true, "scratch_space_mb": 100},
  "resource_limits": {"cpu": "1", "memory_mb": 512, "pid_limit": 64},
  "timeout_seconds": 300,
  "allowed_stages": ["tool_execution"],
  "risk_classification": "medium",
  "failure_handling": "On timeout, capture whatever URLs were discovered before the cutoff as partial (still untrusted) output. `max_depth` exists specifically to bound crawl time and request volume — do not run unbounded.",
  "audit_requirements": "Log start_url, max_depth, request count issued, and duration. Request volume is the key audit signal here since an overly deep crawl can look like unintended load on the target."
}
```

## 4. Ffuf

```json
{
  "tool_id": "ffuf",
  "name": "Ffuf",
  "version": "v2.1.x (illustrative — verify current stable at deployment)",
  "purpose": "Fuzz for hidden endpoints/parameters against the target using a wordlist.",
  "category": "recon",
  "input_schema": {
    "type": "object",
    "properties": {
      "target_url_pattern": {"type": "string", "description": "URL containing a FUZZ placeholder"},
      "wordlist_id": {"type": "string"},
      "rate_limit_per_second": {"type": "integer", "minimum": 1, "maximum": 50}
    },
    "required": ["target_url_pattern", "wordlist_id", "rate_limit_per_second"]
  },
  "output_schema": {"type": "array", "items": {"type": "object"}, "description": "advisory — matched paths/parameters with status code"},
  "expected_output": "A list of wordlist entries that produced a non-default response (e.g. discovered a real endpoint or parameter), with their status code.",
  "container_image": "<PINNED_DIGEST_REQUIRED — see 07_DOCKER_SPEC>",
  "network_requirements": {"egress": "HTTP/HTTPS to the authorized target's hosts ONLY — see OD-18"},
  "filesystem_requirements": {"read_only_root": true, "scratch_space_mb": 100},
  "resource_limits": {"cpu": "1", "memory_mb": 512, "pid_limit": 64},
  "timeout_seconds": 300,
  "allowed_stages": ["tool_execution"],
  "risk_classification": "medium",
  "failure_handling": "On timeout, capture partial results. `rate_limit_per_second` is a **required** input, not optional — fuzzing without a rate cap risks looking like a denial-of-service attempt against the target, which is both an ethical and a scope concern, not just a technical one **[REQ]**.",
  "audit_requirements": "Log target_url_pattern (with the fuzzed value redacted from any logged match, since wordlist hits could incidentally reveal sensitive path names), wordlist_id, rate_limit_per_second used, and total requests issued."
}
```

## 5. Nuclei

**[LOCKED — OD-17 resolved 2026-09-15, see `13_OPEN_DECISIONS.md`]** OD-17 is resolved as a **capability-oriented** model, not a pre-built static allowlist: the model may reason about what it needs, request a Nuclei capability dynamically, and that request passes through the Scope Gate/policy check before execution — the same MODEL DECIDES → POLICY/SCOPE AUTHORIZES → TOOL EXECUTES boundary every other tool follows. A specific template/capability restriction is defined only if a later implementation/security decision actually requires one, based on the real capability being implemented — not invented speculatively here. The entry below's `[REQ, blocking]` failure-handling note (requiring a curated allowlist before any activation) is **superseded** by this resolution; Nuclei is governed by the same authorization model as the rest of the registry, not held to a separate static-list precondition.

*(Original framing, retained for context only — no longer the operative constraint:)* The master prompt lists Nuclei as included "where explicitly supported" (`01` §11) — phrasing that implies a restriction exists but does not specify what it is. Nuclei's full public template library includes many templates far more intrusive than passive detection (some templates actively attempt exploitation to confirm a finding).

```json
{
  "tool_id": "nuclei",
  "name": "Nuclei",
  "version": "v3.x (illustrative — verify current stable at deployment)",
  "purpose": "Run a curated set of non-intrusive, detection-only vulnerability templates against the target.",
  "category": "vulnerability_scan",
  "input_schema": {
    "type": "object",
    "properties": {
      "target_url": {"type": "string"},
      "template_tags": {"type": "array", "items": {"type": "string"}, "description": "must reference only the curated, approved template subset — see OD-17"}
    },
    "required": ["target_url", "template_tags"]
  },
  "output_schema": {"type": "array", "items": {"type": "object"}, "description": "advisory — per-template match results"},
  "expected_output": "For each matched template: which template fired, on which URL, and the raw match evidence — this is RAW_OBSERVATION output like any other tool, not itself a validated finding.",
  "container_image": "<PINNED_DIGEST_REQUIRED — see 07_DOCKER_SPEC>",
  "network_requirements": {"egress": "HTTP/HTTPS to the authorized target's hosts ONLY — see OD-18"},
  "filesystem_requirements": {"read_only_root": true, "scratch_space_mb": 100},
  "resource_limits": {"cpu": "2", "memory_mb": 1024, "pid_limit": 128},
  "timeout_seconds": 300,
  "allowed_stages": ["tool_execution"],
  "risk_classification": "medium-high",
  "failure_handling": "On timeout, capture partial matches. Template/capability selection is authorized per-request through the Scope Gate (OD-17, resolved — see `13_OPEN_DECISIONS.md`), not gated on a pre-built static allowlist.",
  "audit_requirements": "Log target_url, exact template_tags used (this is the single most important audit field for this tool, given OD-17), and every match with its template ID."
}
```

## 6. Garak

```json
{
  "tool_id": "garak",
  "name": "Garak",
  "version": "current release (illustrative — verify at deployment)",
  "purpose": "Probe an AI/LLM-based target application for known failure modes — susceptibility to prompt injection, jailbreaks, and unsafe output generation — using automated probe suites.",
  "category": "ai_security",
  "input_schema": {"type": "object", "properties": {"target_endpoint": {"type": "string"}, "probe_suite": {"type": "array", "items": {"type": "string"}}}, "required": ["target_endpoint", "probe_suite"]},
  "output_schema": {"type": "array", "items": {"type": "object"}, "description": "advisory — per-probe pass/fail with the triggering prompt and observed response"},
  "expected_output": "For each probe in the suite: whether the target's response indicated the failure mode the probe tests for, plus the prompt/response pair as evidence.",
  "container_image": "<PINNED_DIGEST_REQUIRED — see 07_DOCKER_SPEC>",
  "network_requirements": {"egress": "HTTPS to the authorized target's AI/LLM API endpoint ONLY — see OD-18"},
  "filesystem_requirements": {"read_only_root": true, "scratch_space_mb": 200},
  "resource_limits": {"cpu": "1", "memory_mb": 512, "pid_limit": 32},
  "timeout_seconds": 600,
  "allowed_stages": ["tool_execution"],
  "risk_classification": "medium",
  "failure_handling": "Target rate-limiting or refusal responses are recorded as data, not tool failures. A full-suite timeout should preserve completed-probe results as partial output.",
  "audit_requirements": "Log probe_suite used, probe count, pass/fail summary. Note per OD-14: this tool's output currently has no dedicated Skill to route to — see `05_SKILL_MANIFESTS/`."
}
```

## 7. PyRIT

```json
{
  "tool_id": "pyrit",
  "name": "PyRIT (Python Risk Identification Tool for generative AI)",
  "version": "current release (illustrative — verify at deployment)",
  "purpose": "Orchestrate structured, often multi-turn adversarial probing against generative AI systems.",
  "category": "ai_security",
  "input_schema": {"type": "object", "properties": {"target_endpoint": {"type": "string"}, "orchestrator_config": {"type": "object"}}, "required": ["target_endpoint", "orchestrator_config"]},
  "output_schema": {"type": "array", "items": {"type": "object"}, "description": "advisory — per-conversation-turn evidence of a targeted failure mode"},
  "expected_output": "A record of the adversarial conversation(s) run and whether the target's responses indicated the tested failure mode, with the full conversation as evidence.",
  "container_image": "<PINNED_DIGEST_REQUIRED — see 07_DOCKER_SPEC>",
  "network_requirements": {"egress": "HTTPS to the authorized target's AI/LLM API endpoint ONLY — see OD-18"},
  "filesystem_requirements": {"read_only_root": true, "scratch_space_mb": 200},
  "resource_limits": {"cpu": "1", "memory_mb": 512, "pid_limit": 32},
  "timeout_seconds": 600,
  "allowed_stages": ["tool_execution"],
  "risk_classification": "medium",
  "failure_handling": "Same as Garak — target refusals/rate-limits are data, not tool failure. Multi-turn runs should checkpoint so a timeout mid-conversation still yields the turns completed so far.",
  "audit_requirements": "Log orchestrator_config used, turn count, and pass/fail summary. Same OD-14 routing caveat as Garak applies."
}
```

## 8. Promptfoo — **PROVISIONAL, pending OD-01**

**[NOTE — OD-01 resolved 2026-09-15, see `13_OPEN_DECISIONS.md`]** Promptfoo is kept for MVP, but repositioned into the **model-evaluation/benchmarking toolchain** (`11` §12, `16`), not reinstated for this Tool-Registry use case (scanning third-party AI targets). This entry's `provisional_pending_OD-01` / inactive status for target-scanning use is therefore **unaffected by the resolution** pending Harsh's explicit confirmation — see `13_OPEN_DECISIONS.md` §3, item 2.

```json
{
  "tool_id": "promptfoo",
  "name": "Promptfoo",
  "version": "current release (illustrative — verify at deployment; also verify licensing/ownership status per OD-01 before any use)",
  "purpose": "Automated LLM output evaluation and red-teaming test-suite execution against a target AI application.",
  "category": "ai_security",
  "input_schema": {"type": "object", "properties": {"target_endpoint": {"type": "string"}, "test_suite_id": {"type": "string"}}, "required": ["target_endpoint", "test_suite_id"]},
  "output_schema": {"type": "array", "items": {"type": "object"}, "description": "advisory — per-test pass/fail with evidence"},
  "expected_output": "For each test in the suite: pass/fail against the configured assertion, with the prompt/response as evidence.",
  "container_image": "<PINNED_DIGEST_REQUIRED — see 07_DOCKER_SPEC; do not build/pull until OD-01 resolves>",
  "network_requirements": {"egress": "HTTPS to the authorized target's AI/LLM API endpoint ONLY — see OD-18"},
  "filesystem_requirements": {"read_only_root": true, "scratch_space_mb": 200},
  "resource_limits": {"cpu": "1", "memory_mb": 512, "pid_limit": 32},
  "timeout_seconds": 600,
  "allowed_stages": ["tool_execution"],
  "risk_classification": "medium",
  "failure_handling": "Same pattern as Garak/PyRIT.",
  "audit_requirements": "Log test_suite_id, test count, pass/fail summary. **[LOCKED — this entry is inactive]** the Tool Registry (`02` §1) must reject any invocation attempt against `promptfoo` until its `validation_status` is changed from `provisional_pending_OD-01` to `active` by an explicit, recorded decision."
}
```

---

## Cross-Cutting Note: Network Scoping (OD-18 — RESOLVED, see `13_OPEN_DECISIONS.md`)

**[LOCKED — resolved 2026-09-15, see `13_OPEN_DECISIONS.md` OD-18]** Every active tool above (Httpx, Katana, Ffuf, Nuclei, Garak, PyRIT, Promptfoo) has its `network_requirements.egress` written as "the authorized target's hosts ONLY." This is enforced by the **Scope Gate**: every network-capable tool request a model/worker proposes is checked against the current run's authorized RunScope before the Orchestrator authorizes execution (`02` §11's existing scope-validation check). A tool request outside RunScope is never executed. This is *not* enforced by a network-layer proxy — `07` §4's forced-egress-proxy proposal is explicitly not adopted as an MVP requirement; it remains a possible future defense-in-depth addition, not a current one. Do not read any per-tool `network_requirements.egress` line below as describing an enforced network boundary in itself — the enforcement point is the Scope Gate check on the proposed action, not the manifest text.

---

## New Open Decisions Raised in This Document

| ID | Question | Raised in |
|---|---|---|
| **OD-17** | **RESOLVED 2026-09-15** — see `13_OPEN_DECISIONS.md`. Capability-oriented model; no static allowlist required. | §5 (Nuclei) |
| **OD-18** | **RESOLVED 2026-09-15** — see `13_OPEN_DECISIONS.md`. Scope Gate is the enforcement checkpoint; no proxy mandated. | Cross-cutting note above |
| **OD-19** | `03`'s `ToolManifest` schema (§2.4) omitted a distinct `expected_output` field that master-prompt STEP 06 explicitly lists separately from `output_schema`. This document added `expected_output` (free-text description) to every entry above to satisfy the master prompt's actual field list, but `03` itself doesn't yet define it as a schema field — should `03` be amended to add it formally? | Discovered while writing every entry in this document |

Carried forward with OD-01 through OD-16 into `13_OPEN_DECISIONS.md`. Running total: **19 open decisions.**

---

## WHAT YOU SHOULD UNDERSTAND BEFORE NEXT

Before `07_DOCKER_SPEC/`, these concepts matter most:

1. **"Where explicitly supported" was a real constraint hiding in plain sight.** The master prompt's own wording on Nuclei implied a restriction three documents ago, but nothing operationalized it until an actual registry entry had to specify `template_tags` and discovered there's no allowlist to reference. This is the same pattern as OD-14/OD-15/OD-16 in `05` — writing concrete instances is what surfaces gaps that reading prose doesn't.

2. **A manifest's stated network intent is not the same as an enforced network boundary.** OD-18 is the most operationally important open decision in this document: "egress to target hosts only" written in a manifest is a *promise*, not a *mechanism*. `07_DOCKER_SPEC/` needs to answer, concretely, how a container is actually prevented from reaching anything outside the current run's authorized scope — this is squarely a security-boundary question, not a formatting detail.

3. **Two schema gaps have now been found by instantiation (OD-15 in `05`, OD-19 here).** Both follow the same shape: `03` defined a schema before any real content was written against it, and both gaps were in fields the master prompt itself explicitly asked for but `03` didn't fully capture. Worth watching for a third occurrence when `08_MODEL_REGISTRY/` populates real `ModelManifest` instances — if the pattern holds, it's worth a dedicated pass reconciling `03` against `04`–`08` once all manifests exist, which is exactly what `14`'s cross-document consistency audit is for.

4. **Risk classification isn't just a label — it should predict review scrutiny.** Notice Nuclei is the only entry marked `medium-high` and the only one with a **[REQ, blocking]** failure-handling note. That's intentional: it's the tool with the most potential to cause real, unintended impact on a target if misconfigured, and its registry entry should read as more cautious than Subfinder's, not identically templated.

5. **A provisional registry entry (Promptfoo) is a legitimate registry state, not a contradiction.** The Tool Registry mechanism (`02` §1) needs to actually check `validation_status`, not just whether a `tool_id` exists — "registered but not authorized to run" is a real, intentional state this design supports, and it's worth confirming `02`'s registry-lookup interface (`lookup(tool_id) -> ToolManifest | RegistryRejection`) is understood to also reject a lookup where `validation_status != active`, not just where the `tool_id` is entirely unknown.
