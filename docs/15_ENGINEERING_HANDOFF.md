# 15_ENGINEERING_HANDOFF.md
## Hypermind — Track A — Engineering Handoff Summary

**Document:** STEP 15 of 15 · Track A Documentation Package — final artifact
**Audience:** The engineer implementing Track A
**Companion documents:** `01`–`14` (this summary routes into them; it does not replace them)

---

## Read This First

**Your job is to implement this specification, not to redesign it.**

Every architectural decision in `01`–`14` was made deliberately, and many encode a security or evidence-discipline property that is not obvious from the code alone. Before you change *any* architectural decision — not a variable name or a library choice, but an actual architectural decision — check whether it's tagged `[LOCKED]` in the source document. If it is, it is not yours to change; raise it with Harsh. If you find yourself thinking "this would be simpler if I just…", that instinct is often correct about simplicity and wrong about safety — the complexity is usually load-bearing. When in doubt, ask; don't refactor a locked decision away.

There are exactly two things in this package you may treat as genuinely open to your engineering judgment: (1) items tagged `[REC]` (recommendations — sound defaults you can override *with justification*), and (2) the 26 open decisions in `13` (which are Harsh's to decide, but your input is wanted). Everything `[LOCKED]` is settled.

---

## 1. What We Are Building

An **AI-assisted cybersecurity research pipeline** (`01` §1). It takes a human-authorized target, runs reconnaissance and analysis through a chain of small specialized local models and containerized tools, and produces **evidence-backed, human-validated vulnerability findings** that a human then submits. It has a second, simultaneous purpose: every run emits clean, provenance-rich research data (`10`) that will later support model evaluation and improvement.

It is **not** autonomous, **not** a submission bot, **not** Track B, and **not** Darwin. See §16.

The governing principle everything serves: **MODEL PROPOSES → POLICY DECIDES → HUMAN VALIDATES** (`01` §4).

---

## 2. What Is Locked (the non-negotiables)

These are the decisions you must build *to*, not *around* (full context in the cited sections):

- **Local/open-weight-first models**, served via Ollama, selected by benchmarking not size (`01` §10, `08`).
- **Extractor = Qwen ~1.5B**, the one locked model (`08` §2).
- **Workers ≠ Skills**: separate registries, never merged (`01` §4, `04`, `05`).
- **Neutral Judge**: never receives Skill/offensive methodology, structurally cannot reach the Skill Registry (`02` §3, §15).
- **Dual trust boundaries**: TB-A screens input; TB-B marks all target output as untrusted data, never instructions, forever (`01` §6, `09` §2).
- **Docker isolation**: every tool in an isolated container, never on the host (`07`, `12` AC-036).
- **Human control at three points**: scope authorization, verification, submission — none bypassable (`01` §15, `09` §5).
- **No submission capability exists** in the codebase at all — automatic submission is impossible by *absence*, not by a control (`09` §5, `12` AC-031). **Do not build a submission integration.**
- **Research layer is observe-only**: write-only from the live pipeline; no read-path back into live decisions (`10` §1, `02` §19).
- **Evidence over confidence**: no confidence score is ever ground truth; only a human `submit` produces a `VALIDATED_FINDING` (`10` §10).

---

## 3. Component Map

19 components across 5 groups (full specs in `02`; architecture in `01` §7, §19):

```
INFRASTRUCTURE:  Tool Registry · Worker Registry · Skill Registry ·
                 Model Registry · Model Serving Layer (Ollama)
POLICY & GATING: Policy Engine (OPA/Rego) · Scope Gate · Trust Boundary A ·
                 Evidence Gate · Deduplication Engine
CORE PIPELINE:   Orchestrator/Planner · Docker Tool Execution Engine ·
                 Extractor · Worker Execution Framework · Neutral Judge ·
                 Specialist Executor · Report Polisher
HUMAN:           Human Verification Interface
DATA:            Research/Audit Store
```

Pipeline flow (canonical, `01` §5): Human → Scope Gate → TB-A → Orchestrator → Tools (Docker) → TB-B → Extractor → Workers → Judge → Skill/Specialist → Evidence Gate → Dedup → Human Verification → Report Polisher → Human Submission.

---

## 4. Repository Structure (recommended)

**[REC]** — a starting layout, adjust to your conventions:
```
trackA/
  orchestrator/        # Orchestrator, check chain (02 §11)
  registries/          # Tool/Worker/Skill/Model registries (02 §1-4)
                       #   ⚠ manifests git-tracked (OD-08 rec)
  models/              # Ollama serving integration (02 §5, 08)
  policy/              # OPA/Rego bundles (09 §1)
  gates/               # Scope, Evidence, Dedup, TB-A (02 §6-10)
  execution/           # Docker Tool Execution Engine (02 §12, 07)
  pipeline/            # Extractor, Workers, Judge, Specialist, Polisher
  research/            # Research Store — WRITE-ONLY from pipeline (02 §19, 10)
  human/               # Verification interface (02 §18, OD-06)
  schemas/             # All 03 schemas as validated types
  manifests/           # Worker (04), Skill (05), Tool (06), Model (08) instances
  tests/               # Mirrors 11's structure
  docker/              # Per-tool container specs (07)
```
**Note (`14` AMBIGUITY-2):** the `03`–`12` documents were delivered as consolidated READMEs; split them into per-schema / per-manifest files here if you want finer version-control granularity.

---

## 5. Implementation Order

Build in dependency order, not document order. Foundations first, because everything downstream asserts against them:

1. **Schemas (`03`)** — everything validates against these; build and test them first, including the `trust_classification` enforcement.
2. **Registries + manifest loading (`02` §1-4, `04`/`05`/`06`/`08`)** — the deterministic backbone.
3. **Policy Engine + Scope Gate (`09` §1, `02` §6-7)** — nothing runs against a target without this.
4. **Docker Tool Execution Engine + the egress proxy (`07`, OD-18)** — ⚠ **the egress proxy is a real build, not assembly; it gates 7 of 8 tools** (`14` RISK-1). Do this early; it's on the critical path.
5. **Extractor (`02` §13)** — first component past TB-B; the TB-B-holds test (EXT-002) must pass before trusting anything downstream.
6. **Orchestrator + check chain (`02` §11)** — the control spine.
7. **Workers → Judge → Specialist (`02` §14-16)** — the analysis core.
8. **Evidence Gate → Dedup → Human Verification → Report Polisher (`02` §9-10, §17-18).**
9. **Research Store (`02` §19, `10`)** — build the firewall as *structural impossibility* (`14` RISK), not convention.

---

## 6. Interface Contracts

The function-signature-level contracts are in `02` per component (e.g. `Orchestrator.propose_and_authorize()`, `Extractor.extract()`, `Judge.evaluate()`, `ResearchStore.record()` write-only). Every input/output type they reference is fully defined in `03`. Two contract rules override convenience:
- The Research Store exposes `record()` to the live pipeline and **no reachable `query()`** — enforce by construction (`02` §19, `14` implementation risk).
- The Skill Registry exposes `lookup()` to the Specialist Executor and **no reachable interface to the Judge** (`02` §3).

---

## 7. Model Responsibilities

Per role (`08` for candidates + generation policy; `01` §10 for the principle):

| Role | Job | Model status |
|---|---|---|
| Extractor | Parse/normalize untrusted output → structured JSON | **Locked**: Qwen ~1.5B |
| Worker | One narrow analytical job each | Candidates, benchmark (OD-27) |
| Judge | Neutrally evaluate evidence sufficiency | Candidates, benchmark; **see OD-22** |
| Specialist | Methodology-driven investigation per Skill | Candidates (local-primary locked) |
| Report Polisher | Format a validated finding — formatting only | Candidates, benchmark |

⚠ **OD-22 / `14` RISK-2:** strongly consider mandating that Judge and Specialist use *different* model families — a shared model means a shared blind spot that undermines the finder/judge separation, and no current test catches it.

---

## 8. Worker Responsibilities

Three Workers, all *characterize, never conclude* (`04`): **Endpoint Mapper** (API surface shape), **Object Reference Analyst** (reference-pattern classification), **Auth Analyst** (observed auth mechanism). All have `allowed_tools: []`. Full manifests with system prompts and MUST-NOTs in `04`. Enforce each Worker's `must_not` constraints **at the framework level, not just in the prompt** (`02` §14).

---

## 9. Skill Responsibilities

Four Skills defining *how* a vuln class is investigated (`05`): **IDOR, SSRF, Auth Bypass, Privilege Escalation**. Each produces a `SpecialistPoCOutput` with a mandatory non-empty `replication_command` (a *proposal for a human*, never auto-executed). `few_shot_examples` are empty and **must stay empty until real validated findings exist** (`05`, `10` §9). SSRF's `cloud_metadata_flag` is a locked severity field — get it right in both directions (`05` §2, `12` AC-022).

---

## 10. Tool Responsibilities

Eight tools (`06`): Subfinder, Httpx, Katana, Ffuf (recon); Nuclei (vuln scan — **blocked until OD-17 template allowlist exists**); Garak, PyRIT (AI-security); Promptfoo (**inactive until OD-01**). No tool runs unless registered *and* `validation_status: active`. No tool runs outside its container. No AI-security tool has a Skill to route to yet (OD-14).

---

## 11. Docker Requirements

Full spec in `07`. Non-negotiables: pinned digests (never `:latest`), fail-closed on digest mismatch, read-only rootfs, tmpfs scratch (no host bind-mounts), enforced CPU/memory/PID limits, dual timeout (external supervisor + in-container), `--rm` cleanup, and the per-run forced egress proxy (OD-18). Synchronous output capture = TB-B (`07` §7).

---

## 12. Security Requirements

`09` is the authority. The load-bearing ones: default-deny scope with exclusions-override-inclusions (`09` §1); TB-B holds end-to-end including at the human-review screen (`09` §2); the authorization matrix (`09` §3, especially the Judge row); credential-class data never logged *including in debug/exception paths* (`09` §4); the failure-escalation ladder — more consequential ⇒ more toward stopping (`09` §6); fail-closed everywhere on integrity/policy/scope failures.

---

## 13. Test Requirements

`11` is the full plan. Every test specifies ID/purpose/setup/input/expected/failure/pass-fail. Tests written to depend on open decisions (OD-10/13/18/23) verify *behavior matches configured policy*, not a guessed value — keep them that way. **Add the three REG-*-001 tests from `12` into `11`** (`14` FINDING-4). The single most important test is **RDI-001** (firewall structural impossibility) — treat its failure as release-blocking.

---

## 14. Acceptance Gates

`12` — 39 zero-tolerance gates. No partial-pass state for a security control. The two that matter most: **AC-032** (research firewall structurally enforced) protects the future; **AC-029** (no `submit` without an explicit identified human) protects the present. Gates verified by *structural/code audit* (e.g. AC-031, no submission capability) are the strongest kind — an absence can't be exploited.

---

## 15. Research-Data Requirements

`10` is the authority. Record everything with full provenance, synchronously, as the pipeline runs (`10` §2). Preserve the `trust_classification` ladder — only a human `submit` promotes to `VALIDATED_FINDING` (`10` §3). **Never delete false positives or false negatives** — they are the highest-value data (`10` §6). The firewall is the whole point: write-only from live, no read-back (`10` §1). Everything future — few-shot, LoRA, chaining — is groundwork recorded now, built never (in this MVP).

---

## 16. What MUST NOT Be Implemented

**[LOCKED]** Do not build any of these — their absence is a feature (`01` §21, `09` §5, `10` §9):
- Any capability to submit to a bounty platform (absence *is* the safety guarantee).
- Darwin / evolutionary chaining / any fitness-selection loop.
- Mem0 or any live memory that feeds Track A decisions.
- Any Track B / consumer / Jarvis component.
- Fine-tuning/LoRA in the MVP (record the data that would enable it later; don't train).
- Any read-path from the Research Store into a live decision.
- Any offensive methodology in the Judge.
- Any LLM with direct execution authority.
- Any auto-approval of a candidate without a human.
- Any Nuclei run without OD-17's template allowlist; any Promptfoo run before OD-01.

If a task seems to require one of these, stop — you've misread the spec or found a gap. Raise it; don't build it.

---

## 17. Open Decisions

**26 open decisions in `13`, plus 3 surfaced by `14`.** These — not the specs — are the actual pre-implementation worklist. Priority order for a first live run:

- **Highest leverage:** OD-18 (network egress scoping — unblocks 7 of 8 tools).
- **Full MVP blockers (13):** OD-02, 03, 04, 05, 06, 08, 10, 11, 13, 18, 23, 24, 27 (`13` §1).
- **Partial blockers (3):** OD-01 (Promptfoo), OD-14 (AI-security Skill gap), OD-17 (Nuclei allowlist) (`13` §2).
- **Non-blocking (10):** decide as you go; several are best decided with real data (`13` §3).
- **From `14`:** widen OD-15 to all manifests; ratify timeout nesting; decide on a model-diversity gate (RISK-2).

**Plain corrections (just make them):** fix `02`'s ModelManifest citation (FINDING-1); move REG-*-001 tests into `11` (FINDING-4); update `03`'s category enum note (AMBIGUITY-1).

---

## 18. Definition of Done

Track A's Phase 2A MVP is done — and only then may it run against a real target — when **all** of the following hold:

1. All 39 `12` acceptance gates pass (including the relocated REG-*-001 tests), with **zero** exceptions on any security gate.
2. Every full-MVP-blocker open decision (`13` §1) is resolved and its resolution implemented.
3. The three FINDING corrections from `14` are made.
4. **RDI-001 / AC-032 pass** — the research firewall is a structural impossibility, verified, not a convention.
5. **AC-029 / AC-031 pass** — no `submit` without an identified human; no submission capability exists in the codebase.
6. The egress proxy (OD-18) is built and DOCK-005 passes for every active tool.
7. A golden-path E2E run (E2E-001) succeeds against a controlled target with a planted vulnerability, **and** a clean-target run (E2E-002) produces no fabricated finding.
8. A human with genuine security expertise is in the validation loop (`14` RISK-3 — this is a staffing precondition, not a code one, but it is part of "done" because without it the entire evidence chain is hollow).

Phase 2A does not exit on a date. It exits when this list is fully satisfied — the same discipline this project applied to Phase 1's exit long before this document existed.

---

## The Four Things To Foreground (from the `14` audit)

If you internalize nothing else from the companion documents, internalize these:

1. **OD-18 is on the critical path** — the egress proxy gates most of the pipeline and is a real build. Start it early.
2. **The research firewall must be structural, not a rule** — build it so live code *cannot* read the store, and prove it with RDI-001.
3. **Two things need building, not assembling** — the egress proxy and the human-review interface. Everything else is largely assembly; these two aren't.
4. **The whole evidence chain rests on human security expertise** — the best pipeline in the world produces validated-looking garbage if the human at the SUBMIT gate can't tell a real finding from a plausible false positive.

---

## Closing Note

This package is thirteen specification documents, one audit, and this handoff. It is deliberately more rigorous than a Phase-2A MVP strictly needs to *run* — that rigor exists because Track A's entire value proposition is discipline: evidence over confidence, clean data, human control. A sloppily-built version of this pipeline would produce exactly the AI-generated noise the security industry spent 2026 building defenses against. A carefully-built one lands on the right side of that line. The specification is the difference between the two. Build it as specified; raise the open decisions; don't redesign what's locked.

*End of Track A Documentation Package.*
