# 13_OPEN_DECISIONS.md
## Hypermind — Track A — Open Decisions

**Document:** STEP 13 of 15 · Track A Documentation Package
**Status:** Complete consolidation — every unresolved decision from `01`–`12`
**Purpose:** Unlike every other document in this package, this one does **not** point elsewhere for its core content. It exists so Harsh can work through every unresolved decision in one place, without reconstructing context from eleven other documents. Each entry is written to stand alone.

---

## How This Document Is Organized

26 live decisions (OD-01 through OD-27; OD-07 was reserved into OD-04's scope and never became a separate item — noted for numbering continuity, not a gap). Grouped by **blocking severity**, since that's what determines what Harsh should look at first:

- **§1 — Full MVP blockers** (12 items): Phase 2A cannot launch its first live run until these resolve. *(Updated in the final correction pass — OD-05 moved out to §3 as an over-classification correction; see its entry.)*
- **§2 — Partial blockers** (3 items): block one specific capability, not the MVP generally.
- **§3 — Non-blocking** (11 items): can be decided on a more relaxed timeline, several with a natural trigger for revisiting rather than a hard date.

Within each group, entries are in OD-number order for easy cross-reference back to the document that raised them.

---

# §1 — Full MVP Blockers

## OD-02 — Retry counts, timeout seconds, resource limit values
**Question:** What are the final numeric values for retries, timeouts, and resource limits across every component?
**Why it matters:** Prevents infinite loops or unbounded resource consumption (`01` §14) — components cannot execute without real numbers.
**Options:** (a) Ratify the per-component defaults already proposed throughout `04`/`06`/`08` (Worker: 30s/2 retries; per-tool timeouts in `06`; per-role model timeouts in `08`) as the initial baseline. (b) Derive different values independently. (c) Leave fully configurable/tunable, decide nothing now.
**Tradeoffs:** (a) is fast and already reasoned through per component; (b) requires re-deriving justification with no new information; (c) adds config-management complexity before any real data exists to justify specific tuning.
**Recommendation:** (a) — ratify the existing per-component recommendations as the initial locked baseline; revisit after first real runs show whether any are too tight or loose.
**Owner:** Harsh · **Deadline:** before Phase 2A's first live run · **Blocking:** Yes, full MVP
**Origin:** `01` §14, elaborated `04`/`06`/`07`/`08`

## OD-03 — Host hardware profile
**Question:** What hardware specification does the Track A VM need?
**Why it matters:** Serving five model roles locally has real RAM implications — `08` §7 computed a rough aggregate estimate of ~13–17.4 GB if one candidate per role loads simultaneously.
**Options:** (a) Provision generously (e.g. 32 GB) for headroom. (b) Provision tightly matched to the smallest candidates (~13 GB). (c) Cloud-elastic, scale as needed.
**Tradeoffs:** (a) costs more but avoids OOM risk if larger candidates win benchmarking; (b) cheaper but risks instability; (c) avoids fixed cost but adds real operational complexity for a small team.
**Recommendation:** (a) — 32 GB, giving comfortable headroom above `08`'s high-end estimate.
**Owner:** Harsh · **Deadline:** before VM provisioning begins · **Blocking:** Yes, full MVP
**Origin:** `01` §16, concretized in `08` §7

## OD-04 — Deduplication findings index: what it is, and its boundary from Mem0
**Question:** What technical form does the dedup findings index take, and how is it kept structurally distinct from Mem0/research memory?
**Why it matters:** This is the one live-pipeline component that legitimately needs cross-run persisted state — getting the boundary wrong risks Track A quietly becoming stateful in a way that violates the Mem0-belongs-to-Track-B principle.
**Options:** (a) A narrow, purpose-built findings-only index (fingerprint/hash of key finding attributes). (b) Fold into a general Mem0-like store for convenience. (c) No persistence — rely purely on human review to catch duplicates.
**Tradeoffs:** (a) preserves the architectural statelessness principle while solving a real need; (b) directly violates a locked project boundary; (c) raises real risk of duplicate submissions reaching a human or platform.
**Recommendation:** (a), as already reasoned in `02` §10 and reaffirmed as an `[INFERENCE]` pending this ratification.
**Owner:** Harsh · **Deadline:** before Deduplication Engine implementation · **Blocking:** Yes, full MVP
**Origin:** `01`/`02` §10, revisited `03` §2.19

## OD-06 — Human Verification Interface mechanism
**Question:** CLI, local web dashboard, or another mechanism for the mandatory human-review interface?
**Why it matters:** This is one of the three mandatory human-control points (`01` §15) — the MVP cannot ship without it built, and it now also carries a policy constraint from `09` §2 (must render untrusted evidence content inertly).
**Options:** (a) A simple CLI tool. (b) A local web dashboard. (c) Another async mechanism (e.g. a bot-style interaction).
**Tradeoffs:** (a) fastest to build, weaker for reviewing a multi-part evidence trail; (b) better UX for `HumanReviewPackage`'s linked-record trail, more build effort, must honor the inert-rendering requirement; (c) unknown effort/benefit.
**Recommendation:** (b) — a local web dashboard, since evidence trails are genuinely easier to review visually, provided inert rendering is built in from day one, not retrofitted.
**Owner:** Harsh · **Deadline:** before Human Verification Interface implementation · **Blocking:** Yes, full MVP
**Origin:** `02` §18, policy constraint added in `09` §2

## OD-08 — Registry manifest storage mechanism
**Question:** How are Tool/Worker/Skill/Model Registry manifests stored?
**Why it matters:** Registries need a persistence layer; this is one of three distinct storage questions (alongside OD-04 and OD-11) that shouldn't share a backend without an explicit decision.
**Options:** (a) Versioned files in the repo (git-tracked YAML/JSON). (b) A lightweight config database. (c) A full registry service.
**Tradeoffs:** (a) simplest, git gives free versioning/audit trail for free, fits the project's small-team philosophy; (b) more robust for runtime queries at real scale, more setup; (c) overkill at MVP scale.
**Recommendation:** (a) — git-tracked manifest files; manifests are read-mostly and updated rarely, by humans, deliberately, so git's own history satisfies most of the auditability requirement already stated for tool manifests.
**Owner:** Harsh · **Deadline:** before registry implementation · **Blocking:** Yes, full MVP
**Origin:** `02` §1–4

## OD-10 — Deduplication index unavailability: fail closed vs. fail open
**Question:** If the dedup index is down, does the pipeline block all submissions, or proceed with a warning flag?
**Why it matters:** A real availability-vs-safety tradeoff at a concrete operational failure point.
**Options:** (a) Fail closed — block until restored. (b) Fail open with a human warning flag during the outage.
**Tradeoffs:** (a) zero duplicate-submission risk during an outage, but blocks legitimate work; (b) preserves throughput but risks a duplicate reaching a human or platform during the outage window.
**Recommendation:** (a) — consistent with the fail-safe principle applied everywhere else in this package; an index outage should be rare and short, and the cost of a brief block is much lower than a duplicate submission's reputational cost.
**Owner:** Harsh · **Deadline:** before Deduplication Engine implementation · **Blocking:** Yes, full MVP
**Origin:** `02` §10

## OD-11 — Research/Audit Store storage technology
**Question:** What storage technology backs the Research/Audit Store, distinct from OD-08 and OD-04's storage?
**Why it matters:** This store is write-heavy, long-retention, and — per `10` §8 — the single largest long-term sensitive-data accumulation in the system. Its storage choice carries real security/compliance weight.
**Options:** (a) A simple self-hosted append-only structured store (e.g. SQLite or a document store). (b) A dedicated time-series/event store. (c) A managed cloud data warehouse.
**Tradeoffs:** (a) simplest, easiest to encrypt at rest, fits current scale; (b) better suited to eventual large-scale offline analytics; (c) offloads ops burden but raises data-residency/third-party-exposure questions given this store's sensitivity.
**Recommendation:** (a) for MVP, self-hosted (consistent with the self-hosting philosophy already applied to Mem0 elsewhere in this project) — migrate to (b) only if real data volume later justifies it.
**Owner:** Harsh · **Deadline:** before Research Store implementation · **Blocking:** Yes, full MVP
**Origin:** `02` §19

## OD-13 — RawToolOutput truncation cap
**Question:** What is the exact size limit for capturing raw tool output before truncating?
**Why it matters:** Prevents an unbounded record from a flood or misconfigured tool.
**Options:** (a) Confirm `07`'s proposed 10 MB cap. (b) Choose a different value once real tool output profiles are observed.
**Tradeoffs:** (a) fast, reasonable starting point with no data to contradict it yet; (b) requires empirical data that doesn't exist before a first real run.
**Recommendation:** (a) — confirm 10 MB as the MVP starting value, revisit once real output volumes are observed.
**Owner:** Harsh · **Deadline:** before Docker Tool Execution Engine implementation · **Blocking:** Yes, full MVP
**Origin:** `03` §2.7, proposal given `07` §7

## OD-18 — Network egress scoping mechanism
**Question:** How is a tool container's network egress dynamically confined to the current run's authorized target?
**Why it matters:** Without this, every active tool's manifest states "egress to target only" as an unenforced promise — a container could technically reach out-of-scope infrastructure. This is the highest-priority open decision from an operational-security standpoint: it blocks 7 of the 8 registered tools' safe activation (only Subfinder, which is purely passive, is unaffected).
**Options:** (a) `07`'s proposed forced egress proxy — per-run, DNS-inclusive, fail-closed, works regardless of tool cooperation. (b) Simpler static iptables rules generated per run, without a full proxy container. (c) Rely on tool-level `HTTP_PROXY` environment variables only.
**Tradeoffs:** (a) most auditable and universally enforced, more build/maintenance effort; (b) lighter-weight but harder to make fully DNS-inclusive and auditable; (c) simplest but insecure — not all tools honor proxy env vars, and this shouldn't be relied on.
**Recommendation:** (a), specifically because it doesn't depend on tool cooperation.
**Owner:** Harsh · **Deadline:** before any active-tool execution (Httpx, Katana, Ffuf, Nuclei, Garak, PyRIT, Promptfoo all depend on this) · **Blocking:** Yes, full MVP — and specifically the highest-leverage single decision in this table, since it unblocks the most downstream capability at once
**Origin:** `06` cross-cutting note, proposal `07` §4

## OD-23 — authorization_reference: presence-only or validated?
**Question:** Does the MVP validate that an `authorization_reference` corresponds to a live, current authorization, or only check that it's present?
**Why it matters:** Presence-only is simpler and safer to build (no new attack surface) but leans harder on the human having genuinely confirmed authorization; validation is a harder problem since it means fetching and parsing external, inherently untrusted content.
**Options:** (a) Presence-only. (b) Fetch-and-parse validation against the actual scope source. (c) A periodic manual re-confirmation process outside the pipeline.
**Tradeoffs:** (a) simple but purely trusts the human; (b) stronger guarantee, introduces a new untrusted-content-fetching surface and real engineering effort; (c) middle ground, adds process overhead but no new attack surface.
**Recommendation:** (a) for MVP, paired with a strong human-process expectation (documented in operator runbooks, not in the pipeline itself) that scope is manually reconfirmed before each run. Defer (b) until presence-only proves insufficient in practice.
**Owner:** Harsh · **Deadline:** before Scope Gate implementation · **Blocking:** Yes, full MVP
**Origin:** `09` §1

## OD-24 — Log and research-store retention/encryption
**Question:** What retention period and encryption-at-rest requirements apply to audit/failure logs and, separately but more urgently, to the Research Store?
**Why it matters:** Real compliance and operational-security implications — the research store specifically is the largest long-term sensitive-data accumulation in the entire system (`10` §8), because retention is its whole purpose.
**Options:** (a) Short retention + mandatory encryption everywhere. (b) Indefinite retention (serves the research flywheel) + encryption. (c) Tiered — short retention for transient logs, long/indefinite retention with strong encryption specifically for the research store.
**Tradeoffs:** (a) minimizes exposure but discards research value prematurely; (b) maximizes research value but maximizes exposure if encryption alone isn't sufficient; (c) most correct, most complex to implement and operate.
**Recommendation:** (c) — the research store's purpose is long-term accumulation, making short retention self-defeating specifically for it, while transient audit logs have no similar need for indefinite retention.
**Owner:** Harsh · **Deadline:** before Research Store and audit-logging implementation · **Blocking:** Yes, full MVP
**Origin:** `09` §7, extended `10` §8

## OD-27 — Model benchmarking bootstrap dataset
**Question:** What evaluation dataset lets model benchmarking begin before Track A has produced enough real validated findings?
**Why it matters:** `08`'s entire premise — models earn `primary` status through benchmarking, not preference — needs *some* dataset to start from; without one, every non-Extractor role stays `candidate_untested` indefinitely.
**Options:** (a) Public labs with documented ground truth. (b) Hand-constructed synthetic test cases. (c) Wait for real field data.
**Tradeoffs:** (a)+(b) enable benchmarking immediately but risk lab/synthetic bias not matching real-world evidence shapes; (c) most realistic eventual data, but delays all model selection indefinitely — which defeats the benchmarking premise entirely.
**Recommendation:** (a)+(b) combined, explicitly labeled non-field-validated in `DatasetRecord.purity_notes` so it's never later confused with real field data.
**Owner:** Harsh · **Deadline:** before the first benchmarking experiment runs · **Blocking:** Yes, full MVP — blocks any role from ever earning `primary` status
**Origin:** `11` §12

---

# §2 — Partial Blockers (block a specific capability, not the whole MVP)

## OD-01 — Promptfoo: keep, drop, or pin a fork?
**Question:** Given Promptfoo's reported OpenAI acquisition (March 2026), should it stay in the Tool Registry, be dropped, or be pinned to a pre-acquisition fork?
**Why it matters:** The master prompt's canonical pipeline names it, but prior project research flagged it's no longer a neutral, independent component — a genuine conflict between two source documents.
**Options:** (a) Keep as-is. (b) Drop entirely. (c) Pin a pre-acquisition fork.
**Tradeoffs:** (a) risks using a commercially-entangled tool; (b) loses the AI-red-team evaluation capability it offered; (c) preserves capability but locks to a stale, unmaintained version.
**Recommendation:** `06` already registered it as `provisional_pending_OD-01` (inactive) — that's the sensible interim state regardless of final answer; decide before it's ever needed for a real run.
**Owner:** Harsh · **Deadline:** before Promptfoo's entry is ever activated · **Blocking:** Promptfoo only — does not block MVP launch, since Garak/PyRIT cover baseline AI-security tooling
**Origin:** `01` §11

## OD-14 — Tool Registry / Skill Registry gap for AI-security findings
**Question:** Garak/PyRIT/Promptfoo exist in the Tool Registry, but no Skill exists to route AI-specific findings to. Intentional, or a missing Skill?
**Why it matters:** A Judge with strong Garak-derived evidence currently has nowhere to route it — it would cycle through `needs_more_evidence`/`drop` indefinitely.
**Options:** (a) Add a fifth "AI Security" Skill now. (b) Treat AI-security tool output as general evidence feeding the four existing Skills for now, no dedicated Skill yet. (c) Defer AI-security tool activation entirely until a Skill exists.
**Tradeoffs:** (a) closes the gap but adds scope before any real run has proven the need; (b) keeps MVP scope tight but risks wasted Garak/PyRIT effort with no routing destination; (c) simplest, but delays a capability the Tool Registry already anticipated.
**Recommendation:** (b) as an interim position — revisit adding a dedicated Skill once real Garak/PyRIT runs show whether findings cluster into a pattern needing its own methodology, consistent with `05`'s "justified by observed gaps, not speculation" principle for new Skills.
**Owner:** Harsh · **Deadline:** before any live run targets an AI/LLM application specifically · **Blocking:** AI-application-target runs only, not web-app-only MVP runs
**Origin:** `05`

## OD-17 — Nuclei's curated template allowlist
**Question:** Which specific Nuclei template categories/tags are approved, given the full public library includes intrusive/exploitative templates?
**Why it matters:** Registering "Nuclei" without this allowlist means registering whatever the unrestricted upstream template set contains — a direct conflict with the rest of the registry's least-harm posture. Nuclei's entry is currently blocked from activation pending this.
**Options:** (a) Curate a specific allowlist of detection-only, non-intrusive tags. (b) Allow the full default set, relying on human review of results before any action. (c) Drop Nuclei from Track A entirely.
**Tradeoffs:** (a) safest, requires security-expertise-driven curation effort; (b) faster to start but risks unintended target impact from an aggressive template; (c) loses a capable, widely-used vulnerability-detection tool.
**Recommendation:** (a) — start from Nuclei's own informational/non-intrusive detection tag categories, expand deliberately as specific templates are reviewed and approved.
**Owner:** Harsh (requires the security expertise flagged elsewhere in this project as the #1 gating constraint on Track A generally) · **Deadline:** before Nuclei's entry is activated · **Blocking:** Nuclei only
**Origin:** `06` §5

---

# §3 — Non-Blocking (defer without holding up MVP launch)

## OD-05 — Observability/logging stack **(reclassified from full-MVP-blocker in the final correction pass — see note)**
**Question:** What structured logging framework and metrics backend does the project standardize on?
**Why it matters:** Every component has an Observability requirement (`02`); none specify concrete tooling.
**Options:** (a) Lightweight structured JSON logging + a simple metrics exporter. (b) A heavier observability platform. (c) Minimal ad-hoc logging now, formalize later.
**Tradeoffs:** (a) balances rigor and simplicity, fits the project's "assemble, don't build infra" philosophy; (b) more capable but more setup/maintenance for a small team; (c) fastest to ship but risks inconsistent logs that the research/audit layers depend on.
**Recommendation:** (a) — adopt a structured-JSON logging convention; it can be executed in an afternoon and refined later, and doesn't block building schemas, registries, or the pipeline itself.
**Owner:** Harsh (or delegated to the implementer once the convention is confirmed) · **Deadline:** before first component implementation, but does not gate the start of implementation · **Blocking:** No
**Reclassification note:** originally filed as a full MVP blocker. On re-review during the final correction pass, this was over-classified — it's a `[REC]` convention an engineer can simply adopt, not an architectural decision requiring Harsh's judgment before anything else can proceed. Reclassified to non-blocking.
**Origin:** `02` (implicit across all Observability rows)

## OD-09 — Formalize TB-A's ScreenResult as a schema?
**Recommendation:** Yes, for consistency with the "every rejection is logged" requirement (`09` §7) — but MVP can launch with an ad-hoc log format for this one case and formalize later.
**Owner:** Harsh · **Deadline:** flexible, ideally alongside `14`'s audit · **Blocking:** No
**Origin:** `02` §8

## OD-12 — SkillManifest.vulnerability_class: closed enum vs. open string
**Recommendation:** Open string, registry-validated, as already given in `03` — preserves extensibility, doesn't block the current 4 Skills either way.
**Owner:** Harsh · **Deadline:** before Skill Registry implementation, low urgency · **Blocking:** No
**Origin:** `03` §2.15

## OD-15 — Manifest provenance/authorship metadata is handled inconsistently across all three manifest types **(widened in the final correction pass — see note)**
**Recommendation:** Amend `03` with a single lightweight `ManifestProvenance` type ({created_by, created_at, source_basis, version}) and apply it **uniformly to `ToolManifest`, `WorkerManifest`, and `SkillManifest`** — not just `SkillManifest`. The current stopgap for `SkillManifest.provenance` works fine in the meantime.
**Widening note:** originally scoped to `SkillManifest.provenance`'s awkward fit with the pipeline-run `Provenance` type. The final correction pass's consistency check (`14` FINDING-2) found the inconsistency is broader: `ToolManifest` expresses this as free-text `audit_requirements`, `WorkerManifest` as free-text `provenance_requirements`, and `SkillManifest` alone uses a full typed (and ill-fitting) `Provenance` object. All three should converge on one lightweight type.
**Owner:** Harsh · **Deadline:** before Skill Registry implementation locks formats, or during a `03` reconciliation pass · **Blocking:** No
**Origin:** `05`; widened `14`

## OD-16 — No bright-line rule between IDOR and Privilege Escalation
**Recommendation:** Accept case-by-case Judge reasoning for MVP; only add explicit tie-breaking guidance if real findings show the ambiguity is actually causing inconsistent routing in practice.
**Owner:** Harsh · **Deadline:** revisit after ~10–20 real routed candidates across these two Skills, not before · **Blocking:** No
**Origin:** `05` §4

## OD-19 — 03's ToolManifest missing the expected_output field
**Recommendation:** Amend `03` to formally add `expected_output: string`, matching what `06`'s instances already include in practice — a documentation-cleanliness fix, not a functional gap.
**Owner:** Harsh · **Deadline:** during `14`'s cross-document audit · **Blocking:** No
**Origin:** `06`

## OD-20 — Cryptographic image signature verification beyond digest pinning
**Recommendation:** (b) as proposed in `07` — mandatory digest pinning baseline, opportunistic signature verification added per tool where available, never blocking on universal availability.
**Owner:** Harsh · **Deadline:** can be added incrementally per tool, not blocking · **Blocking:** No
**Origin:** `07` §1

## OD-21 — Third-party OSINT provider API keys for Subfinder
**Recommendation:** No keys for MVP launch — zero secrets-management complexity now; revisit only if real runs show passive-source coverage is actually a limiting factor.
**Owner:** Harsh · **Deadline:** revisit post-launch based on real coverage data · **Blocking:** No
**Origin:** `07` §6

## OD-22 — Should Judge and Specialist use different model families? **(re-examined and confirmed in the final correction pass, not rejected)**
**Recommendation:** Mandate diversity as standing policy — the cost (fewer model choices per role) is low, and the risk being guarded against (undermining the entire finder/judge separation) is architecturally central to Track A's credibility. Note: neither `11`'s tests nor `12`'s gates currently check for this, so if diversity isn't mandated, the correlated-blind-spot risk would go entirely undetected.
**Re-examination note:** during the final correction pass, this was specifically checked for over-engineering (per that review's Rule 0) rather than accepted on the strength of having been raised before. It was confirmed as a genuine risk to a *stated core principle* (the finder/judge separation, `01` §19.7), not a speculative enhancement — kept as-is.
**Owner:** Harsh · **Deadline:** before benchmarking begins, so it shapes which candidates are even considered together · **Blocking:** No — MVP can launch with same-family candidates and this applied retroactively at primary-selection time, but earlier is better
**Origin:** `08` §5

## OD-25 — No mechanism for retroactive false-negative annotation
**Recommendation:** Represent via a specially-typed `ResearchEvent` (extending `event_category`) rather than a new dedicated schema — reuses existing infrastructure, avoids over-designing before a real case shows the pattern's actual shape.
**Owner:** Harsh · **Deadline:** unpredictable (before the first real false-negative case, which can't be scheduled) · **Blocking:** No — blocks only the specific deferred test `RDI-006`, not general MVP launch
**Origin:** `10` §6

## OD-26 — Dataset pruning policy for later-discovered contamination
**Recommendation:** Annotate-and-exclude-going-forward for MVP simplicity — at current small data volume, the added judgment overhead of a severity-based hybrid approach isn't yet justified. Revisit if the dataset corpus grows large enough that contamination becomes a recurring, not rare, event.
**Owner:** Harsh · **Deadline:** unpredictable (before the first real contamination case) · **Blocking:** No
**Origin:** `10` §11

---

## Summary Table (Quick Reference)

| ID | Short title | Group | Owner | Blocking |
|---|---|---|---|---|
| OD-01 | Promptfoo status | §2 | Harsh | Promptfoo only |
| OD-02 | Retry/timeout/resource values | §1 | Harsh | Full MVP |
| OD-03 | Host hardware profile | §1 | Harsh | Full MVP |
| OD-04 | Dedup index vs. Mem0 boundary | §1 | Harsh | Full MVP |
| OD-05 | Observability/logging stack | §3 | Harsh | No *(reclassified — see entry)* |
| OD-06 | Human Verification interface | §1 | Harsh | Full MVP |
| OD-08 | Registry manifest storage | §1 | Harsh | Full MVP |
| OD-09 | ScreenResult schema | §3 | Harsh | No |
| OD-10 | Dedup outage: fail closed/open | §1 | Harsh | Full MVP |
| OD-11 | Research Store storage tech | §1 | Harsh | Full MVP |
| OD-12 | vulnerability_class enum shape | §3 | Harsh | No |
| OD-13 | Output truncation cap | §1 | Harsh | Full MVP |
| OD-14 | AI-security Skill gap | §2 | Harsh | AI-app targets only |
| OD-15 | SkillManifest.provenance fit | §3 | Harsh | No |
| OD-16 | IDOR/PrivEsc boundary | §3 | Harsh | No |
| OD-17 | Nuclei template allowlist | §2 | Harsh | Nuclei only |
| OD-18 | Network egress scoping mechanism | §1 | Harsh | Full MVP (highest leverage) |
| OD-19 | ToolManifest.expected_output gap | §3 | Harsh | No |
| OD-20 | Image signature verification | §3 | Harsh | No |
| OD-21 | OSINT provider API keys | §3 | Harsh | No |
| OD-22 | Judge/Specialist model diversity | §3 | Harsh | No |
| OD-23 | authorization_reference validation depth | §1 | Harsh | Full MVP |
| OD-24 | Log/research-store retention & encryption | §1 | Harsh | Full MVP |
| OD-25 | Retroactive false-negative mechanism | §3 | Harsh | No (blocks one test) |
| OD-26 | Dataset contamination pruning policy | §3 | Harsh | No |
| OD-27 | Benchmarking bootstrap dataset | §1 | Harsh | Full MVP |

**12 full blockers, 3 partial blockers, 11 non-blocking** (updated in the final correction pass: OD-05 was reclassified from full-blocker to non-blocking as an over-classification correction — see its entry in §3). OD-07 was reserved into OD-04 and never became a standalone item.

---

## WHAT YOU SHOULD UNDERSTAND BEFORE NEXT

Before `14`'s cross-document consistency audit, these concepts matter most:

1. **Every recommendation in this document is a recommendation, not a decision.** Nothing here is `[LOCKED]` — that's the entire point of the document existing. `14`'s audit should treat every item as still open when checking for consistency, not assume any of these recommendations have been silently accepted just because they're written down with reasoning.

2. **OD-18 (network egress scoping) is the single highest-leverage item on this list.** It's the one decision that, once resolved, unblocks seven of eight registered tools simultaneously. If Harsh can only prioritize one full-blocker decision first, this is the one with the widest downstream effect.

3. **Three items (OD-15, OD-19, and implicitly the ModelManifest correction from `08`) are the same underlying pattern: a schema defined before any real instance existed against it.** Once all of `04`–`08`'s concrete manifests exist, `14`'s audit is exactly the right moment to do one consolidated pass reconciling `03` against everything that was actually built on top of it, rather than patching these piecemeal.

4. **Several non-blocking items share a common shape: "revisit once a specific real-world trigger occurs" rather than "revisit by a date."** OD-16, OD-21, OD-25, and OD-26 are all like this — they're not being deferred out of neglect, they're genuinely better decided with real data than speculatively now. Resist the urge to force a premature decision on these just to close the list out.

5. **This document is a snapshot, not a static artifact.** As `14` and `15` proceed, and certainly once real implementation begins, new open decisions will surface the same way they did at every step from `01` through `12` — that's a healthy sign the documentation process is doing its job, not a failure of this document to be complete. `13` should be revisited and appended to, not treated as frozen the moment it's written.
