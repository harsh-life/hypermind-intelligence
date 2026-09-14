# 14_CONSISTENCY_AUDIT — Document Consistency Report
## Hypermind — Track A — Cross-Document Consistency Audit

**Document:** STEP 14 of 15 · Track A Documentation Package
**Status:** Audit report across `01`–`13`
**Method:** Each of the master prompt's 23 required checks evaluated against the actual content of all prior documents. Findings are graded **PASS** (holds cleanly), **PASS w/ NOTE** (holds, with a caveat worth recording), or **FINDING** (a real inconsistency, gap, or contradiction needing correction). This audit does not fix issues in place — it reports them, so corrections are made deliberately, not silently (consistent with the master prompt's rule against silent revision).

---

## Part 1 — The 23 Required Checks

| # | Check | Result | Detail |
|---|---|---|---|
| 1 | Every architecture component has a component spec | **PASS** | All 13 of `01` §19's deep-dive components, plus the registries (`01` §18), map to `02`'s 19-component index. `02` legitimately *expanded* the count by breaking out the Model Serving Layer and Policy Engine as first-class components — an elaboration, not a contradiction. |
| 2 | Every schema exists | **PASS w/ NOTE** | All 32 master-prompt-required schemas are defined in `03` (ValidationOutcome is dual-listed as both pipeline and research, giving 33 index entries). **Note:** `ModelManifest` is *correctly* absent from `03` (it was never in the master prompt's STEP 03 list) and correctly defined in `08` — but see FINDING-1, because `02` still contains a stale citation claiming it lives in `03`. |
| 3 | Every Worker has a manifest | **PASS** | `04` defines all three Workers named in `01` §5 (Endpoint Mapper, Object Reference Analyst, Auth Analyst). No orphan Workers, no un-manifested Workers. |
| 4 | Every Skill has a manifest | **PASS** | `05` defines all four Skills named in `01` §5 (IDOR, SSRF, Auth Bypass, Privilege Escalation). |
| 5 | Every Tool has a registry entry | **PASS** | `06` defines all eight tools named in `01` §11. Promptfoo is present but provisional (correctly gated on OD-01). |
| 6 | Every Tool has Docker requirements | **PASS** | `06` gives per-tool network/filesystem/resource values; `07` gives the enforcement mechanism. Every tool's `container_image` field points to `07`'s pinning policy. |
| 7 | Every Model has a registry entry | **PASS** | `08` covers all five roles. Extractor locked; the other four have candidate entries. No role is left without at least a candidate. |
| 8 | Every security boundary has policy | **PASS** | TB-A, TB-B, scope, authorization, isolation, redaction, submission, escalation all have policy statements consolidated in `09`. |
| 9 | Every important requirement has tests | **FINDING** | Broadly strong, but see FINDING-4: three registry-rejection basic-case tests (REG-TOOL/WORKER/SKILL-001) were found missing from `11` during `12`'s writing and supplied *in `12`* — they need to be relocated into `11`. Also RDI-006 (false-negative recording) is correctly blocked pending OD-25. |
| 10 | Every acceptance criterion is measurable | **PASS** | All 39 gates in `12` map to a specific test ID or a defined structural/code audit. None are vague ("mostly works"). Several are explicitly OD-dependent, which is correct — they specify "behavior matches configured policy," not a guessed value. |
| 11 | Every unresolved decision is recorded | **PASS** | All 26 live open decisions are consolidated in `13`. Cross-checked: every OD raised in `01`–`12`'s "New Open Decisions" sections appears in `13`. OD-07 correctly noted as reserved-into-OD-04, never a standalone item. |
| 12 | No documents contradict each other | **FINDING** | See FINDING-1 (ModelManifest citation), FINDING-2 (manifest provenance inconsistency), FINDING-3 (timeout field nesting ambiguity). |
| 13 | Track B has not leaked into Track A | **PASS** | Mem0 kept firmly in Track B throughout. The one place Track A needs persistence (dedup index, OD-04) was explicitly reasoned as *not* Mem0 and flagged for ratification. |
| 14 | Mem0 has not become live Track A memory | **PASS w/ NOTE** | Holds throughout. **Note:** OD-04's *resolution* must preserve this — if the dedup index were ever implemented as a general Mem0-style store (OD-04 option b), this check would flip to FINDING. The guardrail is documented; the risk lives in the unresolved decision, not the current docs. |
| 15 | Darwin has not entered MVP scope | **PASS** | Consistently deferred. `10` §9 Q21 is the highest-risk place it could have crept in (chaining research), and it correctly defines *only* data-structure groundwork, no chaining mechanism. |
| 16 | Workers and Skills remain separate | **PASS** | Separate registries (`02` §2, §3), separate documents (`04`, `05`), separate schemas (`03` §2.10, §2.15). The Skill Registry is structurally unreachable by non-Specialist callers. |
| 17 | Judge neutrality is preserved | **PASS w/ NOTE** | Enforced three ways: structural (`02` §3 unreachable registry), schema (`03` §2.13 `contains_skill_content: false`), and prompt (`12` AC-017). **Note:** a *fourth* dimension — model-family independence from the Specialist (OD-22) — is recommended but not gated by any test in `11`/`12`. Neutrality is strong at the prompt/structural layers but has an un-gated gap at the model layer. See RISK-2. |
| 18 | Human submission remains mandatory | **PASS** | The strongest guarantee in the package: `09` §5 / `12` AC-031 — no submission capability exists in the codebase at all. Verified by absence, not by a defeatable control. |
| 19 | Docker isolation remains mandatory | **PASS** | `12` AC-036 requires structural audit that no on-host execution path exists, backed by `07`'s full mechanism spec. |
| 20 | Research-data collection does not become operational control | **PASS** | The firewall (`10` §1, `02` §19 one-directional interface, `12` AC-032, `11` RDI-001). This is the most important discipline in the package and it holds cleanly across every document. |
| 21 | Validated findings distinguishable from model claims | **PASS** | `trust_classification` (`03` §1.2) carried through every schema and into the research store; `12` AC-034 gates it; one legitimate promotion path only. |
| 22 | Model benchmarking remains possible | **PASS w/ NOTE** | Architecturally intact (`08` + `03` §3.6/3.8 + `11` §12). **Note:** operationally blocked until OD-27 (bootstrap dataset) resolves — benchmarking is *possible by design* but cannot *begin* until a starting dataset exists. Not a contradiction; a sequencing dependency. |
| 23 | Future fine-tuning not a hidden MVP dependency | **PASS** | Consistently `[FUTURE, GATED]` across `01`, `08`, `10`. `03` §3.10's `ModelVersionRecord.training_data_reference` structurally enforces that any fine-tuned model traces to a validated `DatasetRecord`, never to the live MVP path. |

**Score: 20 PASS (5 with notes), 3 FINDING.** No check failed outright. The three FINDINGs are all correctable and none touch a locked safety principle — they are citation/structural/nesting issues, not violations of Track A's security or evidence discipline.

---

## Part 2 — Contradictions

### FINDING-1 — Stale `ModelManifest` citation in `02` (contradiction)
**What:** `02` §4's Schemas row states "ModelManifest — full fields in `03`." But `03` does not contain `ModelManifest` (correctly — it was never in the master prompt's STEP 03 list), and `08` §1 defines it and explicitly documented this citation as an error.
**Severity:** Low — the correct location is unambiguous (`08`), and `08` already flagged it. But `02`'s text is still wrong and will mislead an engineer reading `02` in isolation.
**Correction needed:** Edit `02` §4's Schemas row to read "ModelManifest — full fields in `08_MODEL_REGISTRY/`." This is a plain fix, not a decision for Harsh.

### FINDING-2 — Manifest provenance handled inconsistently across the three manifest types (contradiction)
**What:** The three manifest schemas treat authorship/provenance metadata three different ways:
- `ToolManifest` (`03` §2.4): has `audit_requirements` (free text), no provenance field.
- `WorkerManifest` (`03` §2.10): has `provenance_requirements` (free text), no provenance field.
- `SkillManifest` (`03` §2.15): has a full `provenance` field typed as the pipeline `Provenance` common type — which is itself the awkward fit flagged as OD-15.
**Severity:** Medium — it's not a safety issue, but three inconsistent approaches to "who authored this manifest and when" will confuse implementation and undermine the manifests' own auditability.
**Correction needed:** This is best resolved *together with* OD-15. Recommendation: define a single lightweight `ManifestProvenance` type ({created_by, created_at, source_basis, version}) and apply it uniformly to all three manifest types, replacing SkillManifest's misfitted `provenance` and standardizing what ToolManifest/WorkerManifest currently express as ad-hoc free text. Because this changes `03`, it's a deliberate amendment requiring Harsh's sign-off (it's already partly captured as OD-15; this finding widens OD-15's scope from "SkillManifest only" to "all three manifests").

### FINDING-3 — Timeout field nesting is ambiguous across three schemas (contradiction/ambiguity)
**What:** `timeout_seconds` appears in `WorkerManifest` (`04`/`03`), `ToolManifest` (`06`/`03`), and `ModelManifest` (`08`). `08` flagged the model-vs-worker overlap but the full three-way relationship was never stated.
**The correct nesting (proposed, needs ratification):**
- A **model inference call** has a timeout (`ModelManifest.timeout_seconds`) — the innermost bound.
- A **Worker invocation** that uses a model has its own timeout (`WorkerManifest.timeout_seconds`) which must be **≥** the model timeout, since a worker invocation *contains* a model call plus framework overhead.
- A **tool execution** has a timeout (`ToolManifest.timeout_seconds`) that is **independent** — tools don't invoke models, so tool and model timeouts never nest.
**Severity:** Medium — if implemented without this nesting understood, a worker timeout shorter than its model timeout would cause the worker to abort mid-inference in a way that looks like a model failure but isn't.
**Correction needed:** State this nesting rule explicitly (best added to `02` §5's Consistency Note, which already raised the two-way version). Ties to OD-02 (the actual numeric values), so resolve together.

---

## Part 3 — Ambiguities

### AMBIGUITY-1 — Category enum now has four values, but `03` still documents three
**What:** `03` §2.4 defined `ToolManifest.category` as a 3-value enum (`recon | ai_security | web_probe`); `06` added `vulnerability_scan` for Nuclei, using `03`'s own explicitly-granted permission to extend the enum via registry update. This is *permitted*, not a contradiction — but `03`'s written enum is now stale relative to the canonical set.
**Severity:** Low — documentation hygiene. Correction: update `03` §2.4's enum note to reflect the current 4-value canonical set, or (cleaner) state that the enum's canonical source is the registry itself, not `03`'s inline list.

### AMBIGUITY-2 — Folder-structure documents delivered as single README files
**What:** The master prompt specified several steps as folders (`03_DATA_SCHEMAS/`, `04_WORKER_MANIFESTS/`, etc., "README.md + specifications"). These were delivered as single consolidated README files containing all content, rather than a README plus separate per-schema/per-manifest files.
**Severity:** Low — all required content is present; only the physical file layout differs. Correction: when this package is committed to a repo, an engineer should split each consolidated README into the intended directory structure (README + individual files) if per-file granularity is wanted for version-control diffing. Flagged so it's a conscious choice, not an accident.

---

## Part 4 — Missing Dependencies

### FINDING-4 — Three tests live in `12` but belong in `11`
**What:** REG-TOOL-001, REG-WORKER-001, REG-SKILL-001 (basic-case registry-rejection tests) were discovered missing during `12`'s writing and supplied there. `12`'s gates AC-004/005/006 reference them. Until relocated, these tests exist in the acceptance-criteria document rather than the test-plan document.
**Severity:** Low — the tests exist and are correct; they're just filed in the wrong document.
**Correction needed:** Move the three test definitions into `11` (§1 for the two component-level ones, §5.2/§5.4 as appropriate), leaving `12` to reference them. Plain fix, no decision needed.

### DEPENDENCY-NOTE-1 — RDI-006 correctly blocked on OD-25
Not a finding — flagged as correct. The false-negative-recording test cannot be written until OD-25 defines the mechanism. This is a properly-tracked forward dependency, not a gap.

### DEPENDENCY-NOTE-2 — Three storage decisions must not silently converge
OD-04 (dedup index), OD-08 (registry manifests), OD-11 (research store) are three distinct storage needs. `02` and `13` both warn against merging them for convenience. Not a current inconsistency, but a live risk during implementation — recorded here so `15`'s handoff carries the warning to the implementing engineer.

---

## Part 5 — Assumptions Register (consolidated from all documents)

Every `[ASSUMPTION]`-tagged item across `01`–`13`, gathered so none is forgotten:

| Source | Assumption | Risk if wrong |
|---|---|---|
| `01` §7 | Tools grouped into container-sets (recon vs AI-security) — grouping vs per-tool container deferred to `07` | Low — `07` can decide either way |
| `01` §16 | VM access via SSH/VPN | Low — standard |
| `04` | All three Workers target the same 4 vuln classes; Worker output is generic evidence, not class-specific | Medium — if a Worker needs class-specificity, the Judge's synthesis burden assumptions change |
| `06` (all entries) | Version numbers/digests are illustrative, need deployment-time verification | Medium — stale versions could introduce known CVEs; `07` §1's provisioning workflow mitigates |
| `07` §2 | `pid_limit: 64` default where a manifest omits it | Low |
| `07` §6 | No tool needs an injected secret at MVP scope (Subfinder OSINT keys off) | Low — accepts reduced recon coverage |
| `08` §7 | All five model roles resident in memory simultaneously (drives the 13–17 GB estimate) | Medium — directly affects OD-03 hardware sizing |

---

## Part 6 — Architectural Risk Register

### RISK-1 (High) — OD-18 gates 7 of 8 tools
Until network egress scoping (OD-18) is resolved and built, seven of eight registered tools cannot safely execute against a real target — only passive Subfinder is unaffected. This is the single largest architectural bottleneck to a first live run. Mitigation: `07` §4 already proposes a concrete mechanism; needs Harsh's confirmation and real engineering effort (which a small team may underestimate — see RISK-4).

### RISK-2 (Medium) — Judge neutrality's model-layer gap
Neutrality is enforced at the prompt and structural layers (checks 17), but the recommendation that Judge and Specialist use *different model families* (OD-22) is not gated by any test. If both roles benchmark to the same model, a shared reasoning blind spot could undermine the finder/judge separation *without any test detecting it*. Mitigation: either mandate model diversity as policy (OD-22 recommendation) or add a `12` gate checking role model-family independence.

### RISK-3 (Medium, from project reality, not the docs themselves) — The security-expertise dependency
Every evidence-discipline mechanism in this package (Evidence Gate, human validation, the whole "evidence over confidence" spine) ultimately depends on the *human validator having real security expertise*. The documents correctly place a human at the SUBMIT gate, but no document can supply the expertise itself. If the human validator can't reliably distinguish a real finding from a plausible-looking false positive, the pipeline produces validated-*looking* garbage and the entire evidence chain is hollow. This is consistent with what this project's own prior feasibility analysis identified as Track A's #1 gating constraint. Recorded here because a consistency audit should check the docs against *reality*, not only against each other.

### RISK-4 (Medium) — "Assemble, don't build" understates the custom-build items
The project's philosophy is to assemble existing components. But two items require genuine custom building, not assembly: the forced egress proxy (OD-18/`07` §4) and the human-verification interface with inert-rendering (OD-06/`09` §2). A small team estimating effort as "mostly assembly" could underestimate these. Recorded so `15`'s handoff sets realistic expectations.

---

## Part 7 — Implementation Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| The three storage backends (OD-04/08/11) get merged for convenience, quietly violating the Mem0 boundary | Medium | `15` handoff must carry the "keep separate" warning prominently |
| GBNF-constrained decoding for the Extractor (`02` §13 REC) is skipped in favor of weaker post-hoc validate-and-retry | Medium | `12` AC-011 tests the *outcome* (invalid output rejected) regardless of method, but grammar-constrained decoding is the more robust path and should be the default |
| The observe-only firewall (`10` §1) is implemented as a *convention* (a rule engineers follow) rather than a *structural* impossibility (no callable path) | High | `11` RDI-001 / `12` AC-032 must test structural impossibility, not mere convention — this is the difference between a real guarantee and a hoped-for one |
| Provisional Promptfoo entry accidentally activated before OD-01 resolves | Low | `06` §8 requires the registry to check `validation_status != active` and reject; `12` AC-007 gates it |
| Redaction (`09` §4) implemented for normal logs but forgotten in debug/exception paths | Medium | `09` §4 explicitly states "no exception for debug or failure logs"; `11` WRK-003/SPEC-003 test output for credential leakage |

---

## Part 8 — Items Requiring Harsh's Decision

Two categories: (a) the 26 open decisions already consolidated in `13` — unchanged by this audit; and (b) new items this audit *surfaced* that warrant Harsh's attention:

| New item | Nature | Relates to |
|---|---|---|
| Widen OD-15 → all three manifest types get a uniform `ManifestProvenance` (FINDING-2) | Amendment to `03` | OD-15 |
| Ratify the three-way timeout nesting rule (FINDING-3) | Clarification, ties to OD-02 | OD-02 |
| Decide whether to add a `12` gate for Judge/Specialist model-family independence (RISK-2) | New potential gate | OD-22 |

**Plain corrections needing no decision (an engineer should just make them):** FINDING-1 (fix `02`'s citation), FINDING-4 (move three tests to `11`), AMBIGUITY-1 (update `03`'s category enum note), AMBIGUITY-2 (split READMEs into folders at commit time).

---

## Part 9 — Overall Assessment

The package is **internally consistent on every locked safety and discipline principle** — checks 13 through 23, which are the ones that actually protect Track A's integrity (Track B separation, Mem0 boundary, Darwin deferral, Workers/Skills separation, Judge neutrality, mandatory human submission, Docker isolation, the research firewall, validated-vs-claim distinguishability, benchmarking viability, and no-hidden-fine-tuning), all **PASS**.

The three FINDINGs are confined to citation accuracy, manifest-metadata uniformity, and timeout nesting — all correctable, none touching the security model. The most important thing this audit confirms is that **the observe-only firewall and the human-submission guarantee — the two deepest safety properties — hold cleanly across all thirteen documents with no contradiction.**

The largest *real* risks are not documentation inconsistencies at all: they are OD-18 (unbuilt network scoping gating most tools), the model-layer neutrality gap (RISK-2), and the meta-dependency on human security expertise (RISK-3) that no document can resolve. These are correctly the things `15`'s handoff should foreground.

---

## WHAT YOU SHOULD UNDERSTAND BEFORE NEXT

Before `15`'s Engineering Handoff, these matter most:

1. **A clean audit isn't one with zero findings — it's one where the findings are all in the right places.** Every FINDING here is a citation, structural-uniformity, or nesting issue. *None* is a violation of a locked safety principle. That distribution is exactly what you want: the discipline held where it mattered (checks 13–23), and the imperfections landed in low-stakes bookkeeping. An audit that found a Mem0 leak or a Darwin-in-MVP creep would be a very different report.

2. **The three deepest safety properties survived thirteen documents intact — verify they survive implementation too.** The research firewall (check 20), human-submission-by-absence (check 18), and validated-vs-claim distinguishability (check 21) are consistent in the *docs*. RISK's implementation register flags that the firewall specifically must be built as structural impossibility, not convention — the docs being right doesn't guarantee the code will be, and RDI-001/AC-032 are what bridge that gap.

3. **The biggest risks are not in the documents — they're in what the documents can't control.** OD-18 (unbuilt), the model-layer neutrality gap (untested), and human security expertise (unsuppliable by any spec) are the real threats to Track A working. A consistency audit that only checked docs-against-docs would have missed all three; checking docs-against-reality is what surfaced them. `15` should lead with these, not bury them.

4. **Two things need building, not assembling — set the expectation now.** The egress proxy and the human-review interface are genuine custom work. The "Lego bricks" philosophy is right for most of the system but doesn't cover these two, and a handoff that implies "just wire up existing tools" would set the implementing engineer up for a surprise.

5. **`13`'s 26 open decisions plus this audit's 3 new surfaced items are the actual pre-implementation worklist.** Everything else in `01`–`12` is buildable as specified. When `15` defines "definition of done" and "implementation order," these ~29 items — not the specs themselves — are what stands between the current package and a first live run.
