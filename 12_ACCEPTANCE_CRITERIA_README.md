# 12_ACCEPTANCE_CRITERIA/README.md
## Hypermind — Track A — Acceptance Criteria

**Document:** STEP 12 of 15 · Track A Documentation Package
**Status:** Objective release gates
**Depends on:** All prior documents — every gate below converts an already-LOCKED requirement into a measurable pass/fail condition; no new architecture is introduced here.
**Verified by:** `11_TEST_PLAN/` (test IDs referenced throughout) plus, where noted, structural/code audit for absence-based guarantees that no runtime test can fully capture.

---

## Governing Principle

**[LOCKED]** Every gate in this document is **zero-tolerance**. There is no "mostly passes" state for a security control in Track A — a gate either holds with zero exceptions, or Phase 2A does not ship. This is different from typical software acceptance criteria (e.g. ">95% coverage"); a pipeline whose entire value proposition rests on evidence discipline and human control cannot have advisory-tier security gates without undermining that value proposition. Where a gate's verification method is a **structural/code audit** rather than a runtime test, that's because the guarantee is an *absence* (`09` §5's "enforced by omission" principle) — no test can prove a negative as convincingly as confirming the capability simply doesn't exist in the codebase.

---

## Test-Coverage Gap Found While Defining These Gates (resolved in the final correction pass)

Three of the master prompt's own named examples — "unregistered tools cannot execute," "unregistered workers cannot execute," "unregistered skills cannot load" — needed a **basic-case** test: attempting a plain, non-adversarial lookup of an ID that simply isn't registered. This was found missing from `11` while this document was originally written (only the *adversarial* variant, `ADV-005`, existed). The three tests (`REG-TOOL-001`, `REG-WORKER-001`, `REG-SKILL-001`) have since been added to `11_TEST_PLAN/` §1b, where they belong — see `11` §1b for the full test definitions. This document's gates below reference them by ID only.

---

# Group A — Scope & Authorization

| Gate | Statement | Verification | Blocking |
|---|---|---|---|
| **AC-001** | Zero executions succeed against a target outside the current run's authorized scope | POL-001, POL-002 | Yes |
| **AC-002** | Scope ambiguity or Policy Engine error resolves to deny in 100% of cases, never allow | POL-003, UT-003 | Yes |
| **AC-003** | An explicit exclusion inside an in-scope wildcard always denies (the real-world "carve-out" case) | POL-002 | Yes |

# Group B — Registry Enforcement

| Gate | Statement | Verification | Blocking |
|---|---|---|---|
| **AC-004** | Unregistered tools cannot execute, in the plain case and under encoding/homoglyph bypass attempts | REG-TOOL-001, ADV-005 | Yes |
| **AC-005** | Unregistered workers cannot execute | REG-WORKER-001 | Yes |
| **AC-006** | Unregistered skills cannot load | REG-SKILL-001 | Yes |
| **AC-007** | A `validation_status` other than `active` (e.g. Promptfoo's `provisional_pending_OD-01`) blocks execution the same as full non-registration | Structural audit — registry lookup checks `validation_status`, not merely `tool_id` existence (`06` §8) | Yes |

# Group C — Trust Boundaries

| Gate | Statement | Verification | Blocking |
|---|---|---|---|
| **AC-008** | Target-controlled data remains untrusted end-to-end — no component's behavior is influenced by embedded instructions in tool output | ADV-002 | Yes |
| **AC-009** | Injection payloads in human/config input are rejected before reaching the planning LLM | ADV-001 | Yes |
| **AC-010** | Command-injection attempts via tool parameters never execute (parameterized invocation only) | ADV-004 | Yes |

# Group D — Extractor

| Gate | Statement | Verification | Blocking |
|---|---|---|---|
| **AC-011** | Invalid Extractor output is rejected and never propagated downstream | EXT-003, SCH-004 | Yes |
| **AC-012** | Valid input reliably produces schema-valid `ExtractorJSON` | EXT-001 | Yes |
| **AC-013** | No state persists across Extractor invocations | EXT-004 | Yes |

# Group E — Workers

| Gate | Statement | Verification | Blocking |
|---|---|---|---|
| **AC-014** | No Worker output ever asserts vulnerability likelihood or exploitability | WRK-001 | Yes |
| **AC-015** | Auth Analyst never reproduces a full credential value, in any output field including free-text notes | WRK-003 | Yes — zero-tolerance, no partial-credit |
| **AC-016** | No Worker can trigger a tool call beyond its declared `allowed_tools` (currently empty for all three) | WRK-005 | Yes |

# Group F — Judge Neutrality

*(Master prompt's explicit example: "Judge remains neutral")*

| Gate | Statement | Verification | Blocking |
|---|---|---|---|
| **AC-017** | The Judge's system prompt contains zero Skill methodology content | JDG-001 | Yes |
| **AC-018** | The Judge cannot reach the Skill Registry under any circumstance | JDG-002 + structural audit (no callable interface exists, `02` §3) | Yes |
| **AC-019** | `JudgeInput.contains_skill_content` is `false` on 100% of real records produced by the live pipeline | JDG-003 | Yes |
| **AC-020** | The Evidence Gate's decision never depends on `JudgeRoutingDecision.confidence` | JDG-005 | Yes |

# Group G — Specialist / Skills

*(Master prompt's explicit example: "Specialist produces replication_command")*

| Gate | Statement | Verification | Blocking |
|---|---|---|---|
| **AC-021** | Every `SpecialistPoCOutput` either has a non-empty `replication_command` or fails before reaching the Evidence Gate | SPEC-001 | Yes |
| **AC-022** | `cloud_metadata_flag` (SSRF Skill) is `true` if and only if evidence shows an actual cloud-metadata-service hit — no false positives, no false negatives on this field | SPEC-004 | Yes — this is a locked severity-classification field carried from the prior PRD; a wrong flag here misclassifies Critical-tier findings |
| **AC-023** | No Specialist output reproduces a literal credential value | SPEC-003 | Yes |

# Group H — Evidence Gate

*(Master prompt's explicit example: "Evidence Gate blocks incomplete findings")*

| Gate | Statement | Verification | Blocking |
|---|---|---|---|
| **AC-024** | A candidate with an empty `replication_command` always fails the gate | EVG-001 | Yes |
| **AC-025** | Every `fail` or `needs_more_evidence` result carries non-empty `reasons` | EVG-003 | Yes |
| **AC-026** | Gate outcomes are identical for candidates with identical evidence completeness regardless of `specialist_confidence` | EVG-004 | Yes |

# Group I — Deduplication

*(Master prompt's explicit example: "duplicates are blocked")*

| Gate | Statement | Verification | Blocking |
|---|---|---|---|
| **AC-027** | A candidate matching a prior finding is always flagged `duplicate` | DEDUP-001 | Yes |
| **AC-028** | No live code path can edit or delete a findings-index entry | DEDUP-004 | Yes |

# Group J — Human Control

*(Master prompt's explicit examples: "human verification is mandatory," "automatic submission is impossible")*

| Gate | Statement | Verification | Blocking |
|---|---|---|---|
| **AC-029** | No `ValidationOutcome` with `decision: submit` exists without an identified human, a timestamp, and an explicit action captured through the Human Verification Interface | Structural audit + `02` §18's interface contract (no default/timeout path produces `submit`) | Yes — **the single most consequential gate in this group** |
| **AC-030** | The Report Polisher is reachable only via a `submit` `ValidationOutcome` — never via `discard` or `needs_more_evidence` | INT-004 | Yes |
| **AC-031** | The codebase contains **no integration or API client capable of submitting to an external bounty platform** | Structural/code audit only — this is an absence, not a behavior; there's nothing to disable because nothing is built | Yes — this is the deepest guarantee in Track A per `09` §5, and it fails by *inspection*, not by any runtime test finding a bypass |

# Group K — Research Data Integrity

*(Master prompt's explicit examples: "provenance is preserved" / "research records preserve provenance" — collapsed into one gate, since both phrasings describe the same requirement; "validated and unvalidated records remain distinguishable")*

| Gate | Statement | Verification | Blocking |
|---|---|---|---|
| **AC-032** | **The Research Store firewall is structurally enforced — no live component (Groups 1–4 per `02`) can call `query()`** | RDI-001 | Yes — **the single most important gate in the entire package**; every anti-poisoning claim this documentation makes depends on this one holding |
| **AC-033** | Every research record carries complete required `Provenance` fields with exactly one of `model_id`/`tool_id` set (never both) | SCH-001 (parameterized), UT-001 | Yes |
| **AC-034** | `trust_classification` changes only via the one legitimate path (a human `submit` producing a new `FindingRecord`); no offline process can promote or alter it | RDI-003, RDI-004 | Yes |
| **AC-035** | `DatasetRecord` versions are immutable — a change always produces a new version, never an in-place edit | RDI-005 | Yes |

# Group L — Docker & Isolation

| Gate | Statement | Verification | Blocking |
|---|---|---|---|
| **AC-036** | No tool ever executes outside an isolated Docker container, in any code path | Structural/code audit (no alternate on-host execution path exists) + DOCK-001 through DOCK-007 collectively | Yes |
| **AC-037** | CPU, memory, and PID limits are enforced exactly as each tool's manifest declares | DOCK-001, DOCK-002, DOCK-003 | Yes |
| **AC-038** | Every container is removed after execution; no stopped containers persist | DOCK-006 | Yes |
| **AC-039** | Timeout is enforced even if one of the two enforcement mechanisms (external supervisor or in-container wrapper) fails | DOCK-004 | Yes |

---

## Coverage Table — Master Prompt's 15 Named Examples

| Master-prompt example | Gate(s) |
|---|---|
| Unauthorized scope is blocked | AC-001 |
| Unregistered tools cannot execute | AC-004 |
| Unregistered workers cannot execute | AC-005 |
| Unregistered skills cannot load | AC-006 |
| Target-controlled data remains untrusted | AC-008 |
| Invalid Extractor output is rejected | AC-011 |
| Provenance is preserved | AC-033 |
| Judge remains neutral | AC-017, AC-018, AC-019, AC-020 |
| Specialist produces replication_command | AC-021 |
| Evidence Gate blocks incomplete findings | AC-024 |
| Duplicates are blocked | AC-027 |
| Human verification is mandatory | AC-029 |
| Automatic submission is impossible | AC-031 |
| Research records preserve provenance | AC-033 *(same requirement as "provenance is preserved" — not duplicated as a separate gate)* |
| Validated and unvalidated records remain distinguishable | AC-034 |

All 15 covered; 39 gates total, since the master prompt's examples were explicitly illustrative ("Examples:"), not an exhaustive list, and this package locked considerably more than 15 requirements across `01`–`11`.

---

## The MVP Release Gate

**[LOCKED]** Phase 2A's first live run against a real target may proceed **only when every gate in Groups A through L passes**, including REG-TOOL-001, REG-WORKER-001, and REG-SKILL-001 (now defined in `11` §1b). There is no partial-release state — a pipeline that finds real vulnerabilities but fails AC-032 (the firewall) or AC-029 (human validation) has not met the bar Track A set for itself, regardless of how good its findings look.

This mirrors the same discipline this project applied to Phase 1's own exit criteria much earlier in its history: a phase exits on a checklist being fully satisfied, not on a calendar date.

---

## New Open Decisions Raised in This Document

None. This document consolidates existing LOCKED requirements into gates and supplies three missing tests — it makes no new judgment calls requiring Harsh's input.

Running total remains **27 open decisions** (OD-01 through OD-27), unchanged from `11`, pending resolution in `13_OPEN_DECISIONS.md`.

---

## WHAT YOU SHOULD UNDERSTAND BEFORE NEXT

Before `13_OPEN_DECISIONS.md`, these concepts matter most:

1. **AC-032 and AC-029 are the two gates that matter most in this entire document, and they protect different things.** AC-032 (the Research Store firewall) protects the *future* — every claim about clean data and safe self-improvement depends on it. AC-029 (human validation before submit) protects the *present* — it's what keeps a single bad run from ever reaching a bounty platform. If you can only fully verify two gates before a first live run, verify these two first.

2. **A gate verified by "structural audit" is not a lesser gate — often it's the strongest kind.** AC-031 (no submission capability exists at all) can't be defeated by any runtime exploit, because there's nothing to exploit. Contrast this with AC-001 (scope blocking), which is a *behavioral* gate that a sufficiently clever bypass could theoretically defeat. When you're prioritizing what to build first, absence-based guarantees are often cheaper to build and harder to break than behavior-based ones.

3. **This document found a real test-coverage gap (the three REG-*-001 tests) simply by trying to write gates against tests that turned out not to exist.** This is the same value the whole sequential-generation approach has delivered repeatedly: writing the *next* concrete artifact tests the *previous* one. Worth remembering as a general habit beyond this project — acceptance criteria are often where missing tests get discovered, not the other way around.

4. **All 27 open decisions are still open — this document didn't resolve any of them, and that's correct.** `12`'s job was converting *already-locked* requirements into gates, not making new architectural calls. `13_OPEN_DECISIONS.md` is where every one of those 27 items — from OD-01's Promptfoo status to OD-27's benchmarking dataset — finally gets collected in one place with the full context needed for Harsh to actually decide each one.

5. **39 gates for one MVP is not scope creep — it's what "zero-tolerance" actually costs.** It might look like a lot, but every single one traces back to a requirement this package already committed to across 11 prior documents. The alternative to 39 explicit gates isn't "a simpler system" — it's the same 39 requirements, just unverified and hoped-for instead of tested and proven.
