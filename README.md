# Hypermind Track A

Hypermind Track A is an **AI-assisted, human-controlled security research pipeline**. Small local language models propose analysis steps. Deterministic code decides whether those steps are allowed, sandboxed tools execute them, and a human validates every finding before it counts.

This repository holds the **control spine** of that pipeline: schemas, registries, the Scope Gate, the Orchestrator check-chain, a pluggable model runtime, a pluggable tool-execution layer, and a model-evaluation harness. **It does not yet contain a real model backend, a real tool sandbox, or any component that touches a live target.** See [Implementation status](#6-implementation-status).

> Companion guides:
> [SETUP_GUIDE.md](SETUP_GUIDE.md) (step-by-step install) ·
> [MODEL_CANDIDATES.md](MODEL_CANDIDATES.md) (Hugging Face model research for the IDOR experiment) ·
> [MODEL_DOWNLOAD_GUIDE.md](MODEL_DOWNLOAD_GUIDE.md) (downloading and wiring model weights)
>
> Design documents: [`Track A PRD.md`](Track%20A%20PRD.md) and [`docs/01`–`docs/18`](docs/). They describe the **target** architecture. This README describes what the **code** does today.

---

## 1. What Track A is

Track A takes a **human-authorized** target (for the first experiment, an intentionally vulnerable lab app on your own machine). It runs analysis through a chain of narrow, replaceable model roles and containerized tools, and produces **evidence-backed candidate findings**. A human must validate each candidate before it becomes a finding.

It is explicitly **not**:

- an autonomous scanner or exploitation bot,
- a bug-bounty submission tool (no submission capability exists, by design),
- a system where any model output can authorize an action.

## 2. Purpose and architecture

Track A has two purposes (docs/01 §1, docs/15 §1):

1. Produce trustworthy, reproducible, human-validated security findings.
2. Emit clean, provenance-rich records that later support **controlled model evaluation**. Those records never feed back into live decisions.

The architecture separates **roles** (what a step does) from **models** (who currently does it). A Worker or Skill manifest points to a role name. The Model Registry decides which candidate model currently fills that role. Swapping a model therefore never requires changing a contract or the orchestrator.

## 3. Core execution flow

```
MODEL PROPOSES  →  POLICY / SCOPE DECIDES  →  TOOL EXECUTES  →  EVIDENCE  →  HUMAN VALIDATES
```

How each arrow maps to code that exists today:

| Step | What happens | Code |
|---|---|---|
| **Model proposes** | A model's suggested action arrives as an `OrchestratorAction` record. It is a *proposal*, never a command. | [`trackA/schemas/orchestrator.py`](trackA/schemas/orchestrator.py) |
| **Policy / Scope decides** | The Orchestrator runs a fixed check chain: run-ID correlation → **Scope Gate** (network actions only) → registry checks → action budget. Any failure produces an `OrchestratorRejection`, and nothing downstream runs. | [`trackA/orchestrator/run.py`](trackA/orchestrator/run.py), [`trackA/policy/scope_gate.py`](trackA/policy/scope_gate.py) |
| **Tool executes** | Only an `AuthorizedAction` reaches the `ToolExecutor`. The executor re-checks the Tool Registry and dispatches to a pluggable `ToolBackend`. Today the only backend is `MockToolBackend`. | [`trackA/execution/`](trackA/execution/) |
| **Evidence** | Tool output is captured as `RawToolOutput` (always untrusted data). Every step emits `AuditEvent`/`FailureEvent` records, collected into a `RunArtifact`. | [`trackA/schemas/tools.py`](trackA/schemas/tools.py), [`trackA/orchestrator/run_artifact.py`](trackA/orchestrator/run_artifact.py) |
| **Human validates** | `HumanReviewPackage` / `ValidationOutcome` schemas exist. **No human-review interface is implemented yet.** | [`trackA/schemas/human.py`](trackA/schemas/human.py) |

## 4. Major components in plain language

| Component | Plain-language job | Status |
|---|---|---|
| **Schemas** (`trackA/schemas/`) | The "forms" every component fills in, written as Pydantic models. Bad data is rejected at the boundary. Every record carries provenance (who, when, which run, which stage). | Implemented |
| **Tool Registry** | The list of tools that are allowed to exist, with their container image, resource limits, timeout, and permitted pipeline stages. Being registered is necessary for execution, but not sufficient. | Implemented (2 manifests: `httpx`, `subfinder`) |
| **Worker Registry** | Narrow analysis jobs ("map endpoints that contain object references"). Each worker points to a *role*, not a model. | Implemented (1 manifest: `endpoint_mapper_v1`) |
| **Skill Registry** | Vulnerability-specific methodology (e.g. IDOR). Only the Specialist Executor may read it. The Judge structurally cannot. | Implemented (1 manifest: `idor_v1`, status `draft`) |
| **Model Registry** | Candidate models per role. At most one is `approved` per role. `quality_metrics` stay `null` until actually measured. | Implemented (5 manifests) |
| **RoleResolver** | Follows a worker/skill's role pointer to the single approved model for that role. | Implemented |
| **Model runtime** (`trackA/models/runtime.py`) | `InferenceAdapter` is the plug for any backend (Ollama, llama.cpp server, cloud API…). `RuntimeRegistry` binds a registry candidate to a backend. | **Interface + `MockAdapter` only. No real backend.** |
| **Policy Engine** | A deterministic, in-process policy evaluator that fails closed when a policy raises. | Implemented as a Python stand-in. **No OPA/Rego.** |
| **Scope Gate** | Decides allow/deny for every network-capable request against the run's human-established `RunScope`. Exclusions beat inclusions, and a missing or unconfirmed scope always denies. | Implemented |
| **Orchestrator** | Runs the check chain above and invokes Worker/Judge/Specialist roles through the runtime. Refusals are never retried; technical failures get bounded retry. | Implemented (bounded check-chain, not a planning LLM) |
| **Tool Executor** | Turns an authorized request into a captured result through a `ToolBackend`. | **Interface + `MockToolBackend` only. No Docker backend.** |
| **Evaluation harness** (`trackA/evaluation/`) | Runs the same benchmark case against every candidate for a role, blinds candidate identities, scores with a neutral `BenchmarkJudge`, and folds results into an `ExperimentRecord` (`winner_model_id` is always `None`). | Implemented |

## 5. Repository structure

```
hypermind-intelligence/
├── README.md                 ← this file
├── SETUP_GUIDE.md            ← exact install/run commands (Kali ARM64 + 16 GB machine)
├── MODEL_CANDIDATES.md       ← Hugging Face model research for the IDOR experiment
├── MODEL_DOWNLOAD_GUIDE.md   ← how to download, verify and register model weights
├── requirements.txt          ← runtime dependencies (pydantic, PyYAML)
├── requirements-dev.txt      ← adds pytest
├── pyproject.toml            ← pytest configuration only (testpaths = ["tests"])
├── Track A PRD.md            ← product requirements (design intent)
├── docs/                     ← architecture & decision documents 01–18 (design intent)
├── trackA/
│   ├── schemas/              ← Pydantic contracts for every record type
│   ├── registries/           ← Tool/Worker/Skill/Model registries + RoleResolver
│   │   └── data/             ← git-tracked JSON manifests (tools/, workers/, skills/, models/)
│   ├── models/               ← InferenceAdapter / RuntimeRegistry / MockAdapter
│   ├── policy/               ← PolicyEngine, request normalization, Scope Gate
│   ├── execution/            ← ToolBackend / MockToolBackend / ToolExecutor
│   ├── orchestrator/         ← Orchestrator, RunContext, outcomes, RunArtifact storage
│   └── evaluation/           ← harness, blinding, BenchmarkJudge, results, storage
│       └── data/             ← benchmark cases + versioned dataset (all synthetic)
└── tests/                    ← 469 pytest tests mirroring trackA/ (no network, no Docker)
```

Directories that docs/15 §4 *recommends* but that **do not exist yet**: `gates/` (Evidence Gate, Dedup, Trust Boundary A), `pipeline/` (Extractor, Report Polisher), `research/` (Research Store), `human/` (verification UI), `docker/` (per-tool container specs).

## 6. Implementation status

Verified by reading the code and running the test suite on 2026-11-20.

### Implemented and tested

- All docs/03 schemas as Pydantic models, with validation and round-trip tests.
- Four manifest registries (JSON or YAML loading), duplicate/conflict detection, the one-approved-candidate-per-role rule, and Skill Registry caller-identity access control.
- Scope Gate and RunScope: domains, subdomains, IPs, ports, protocols, exclusions, prohibited operation classes, and fail-closed on every ambiguous case. Adversarial tests are included.
- Orchestrator check chain for `tool_execution`, `worker_invocation` and `specialist_investigation`. Judge invocation never receives Skill content.
- Evaluation harness: identical request per candidate, bounded retry, no retry on refusal, candidate blinding, neutral judge, experiment records, append-only local JSON storage.

### Mocked (contract exists, only a test double behind it)

| Contract | Only implementation | What a real one needs |
|---|---|---|
| `InferenceAdapter` | `MockAdapter` (echoes the prompt) | e.g. an Ollama or llama.cpp-server HTTP adapter. See [MODEL_DOWNLOAD_GUIDE.md §8](MODEL_DOWNLOAD_GUIDE.md#8-connect-a-candidate-through-the-inference-abstraction) |
| `ToolBackend` | `MockToolBackend` (canned output) | a Docker backend that enforces docs/07 (read-only rootfs, limits, timeouts, pinned digests) |
| `PromptfooAdapter` | `MockPromptfooAdapter` | a real promptfoo CLI integration (optional, supplementary) |
| `PolicyEngine` | in-process Python policy functions | (docs mention OPA/Rego. The code deliberately uses a stand-in) |

### Missing (only schemas exist, or nothing yet)

- Extractor, Trust Boundary A, Evidence Gate, Deduplication Engine
- Report Polisher
- Human Verification Interface
- Research/Audit Store (write-only firewall)
- Docker tool sandbox. Both tool manifests use `container_image: "<PINNED_DIGEST_REQUIRED>"`
- An HTTP request/replay tool suitable for IDOR testing (the registered `httpx` tool only probes liveness)
- A planning LLM that generates `OrchestratorAction`s (callers supply them today)

### Seed data you should know about

| Manifest | Role | `approval_status` | Note |
|---|---|---|---|
| `qwen2.5-1.5b-extractor` | extractor | approved | locked by architecture decision |
| `qwen2.5-3b-worker` | endpoint_mapper | approved | ⚠ Qwen2.5-3B-Instruct is under the **Qwen Research License**, not Apache-2.0 (see MODEL_CANDIDATES.md) |
| `qwen2.5-3b-judge` | judge | candidate | Judge identity intentionally undecided |
| `cand-001-foundation-sec-8b` | specialist | candidate | points at the **base** (non-instruct) Foundation-Sec-8B |
| `cand-003-whiterabbitneo` | specialist | candidate | marketed "uncensored". Independent study shows high trap susceptibility (docs/08) |

Because no `specialist` or `judge` candidate is approved, Orchestrator calls for those roles return a clean `NoApprovedCandidateError` failure. That is intended: approval is a human decision.

## 7. System prerequisites

| Requirement | Needed for | Notes |
|---|---|---|
| Linux (Kali ARM64), macOS, or Windows+WSL | everything | Development target is Kali ARM64 in UTM |
| **Python 3.12, 3.13 or 3.14** | everything | Test suite verified on CPython 3.12.13, 3.13.13 and 3.14.5 (arm64). Pinned wheels exist for `manylinux aarch64` on cp313 and cp314 |
| `git` | cloning | |
| ~200 MB disk | venv + repo | |
| Docker | **not needed today**. Later: the lab target (Juice Shop) and a future tool sandbox | |
| A local inference runtime (Ollama / llama.cpp) | **not needed today**. Later: real model evaluation | Needs a real `InferenceAdapter`, which does not exist yet |

## 8. Installation

```bash
git clone https://github.com/harsh-life/hypermind-intelligence.git
cd hypermind-intelligence
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt   # runtime + pytest
```

Runtime-only install (no tests): `python -m pip install -r requirements.txt`.

There is no packaging metadata (`pyproject.toml` only configures pytest), so the code is used **from the repository root**. Run commands from there, or set `PYTHONPATH` to the repo root.

Full, OS-specific steps are in [SETUP_GUIDE.md](SETUP_GUIDE.md).

## 9. Environment configuration

The code currently reads **no environment variables and no config files** besides the manifests under `trackA/registries/data/` and `trackA/evaluation/data/`. Configuration happens in Python, by constructing registries, `RunScope`s and runtime bindings.

Guidance for later (when a real adapter exists):

- Put endpoints and API keys in a local `.env` (already in `.gitignore`), never in manifests.
- `EvaluationHarness(include_runtime_config=False)` is the default, so `ModelBinding.connection` (which may hold secrets) is **not** written into trajectories. Keep it that way unless the binding holds nothing sensitive.

## 10. Running the unit tests

```bash
source .venv/bin/activate
python -m pytest            # whole suite: expect "469 passed"
python -m pytest -q tests/policy          # one area
python -m pytest -q -k scope_gate         # by keyword
```

The suite needs **no network, no Docker, and no model weights**. If you skip PyYAML, exactly one test fails (`test_from_directory_supports_yaml_manifests`).

## 11. Running the existing evaluation harness

There is no CLI. The harness is a Python API. The script below (from the repo root) runs the seed IDOR case `idor-lab-001` against **every registered `specialist` candidate** using `MockAdapter`:

```bash
python - <<'EOF'
from pathlib import Path
from trackA.evaluation import (BenchmarkCaseStore, BenchmarkJudge, DatasetStore, EvaluationHarness,
                               assign_blind_labels, build_experiment_record, build_judge_package)
from trackA.models import MockAdapter, ModelBinding, RuntimeRegistry
from trackA.registries import ModelRegistry
from trackA.schemas.common import PipelineStage

models = ModelRegistry.from_directory(Path("trackA/registries/data/models"))
cases = BenchmarkCaseStore.from_directory(Path("trackA/evaluation/data/cases"))
case = cases.lookup("idor-lab-001")

runtime = RuntimeRegistry(model_registry=models)
runtime.register_adapter(MockAdapter())
for m in models.list_candidates(case.role):
    runtime.bind(ModelBinding(candidate_id=m.candidate_id, backend="mock"))

exp = "exp-mock-smoke-1"
trajs = EvaluationHarness(runtime=runtime, model_registry=models).run_experiment(
    case, experiment_id=exp, role_stage=PipelineStage.SPECIALIST,
    dataset_id="ds-track-a-bootstrap", dataset_version="v1")
labels = assign_blind_labels([t.candidate_id for t in trajs], seed=exp)
judge = BenchmarkJudge()
verdicts = {t.trajectory_id: judge.evaluate(
    build_judge_package(t, case, blinded_candidate_label=labels[t.candidate_id], experiment_id=exp),
    experiment_id=exp) for t in trajs}
record = build_experiment_record(experiment_id=exp, role_under_test=case.role,
    dataset_id="ds-track-a-bootstrap", dataset_version="v1", trajectories=trajs, verdicts=verdicts)
for t in trajs:
    print(t.candidate_id, t.completion_status, "objective_match=", t.objective_outcome_match)
print("winner_model_id:", record.winner_model_id)
EOF
```

Expected output:

```
cand-001-foundation-sec-8b success objective_match= False
cand-003-whiterabbitneo success objective_match= False
winner_model_id: None
```

`objective_match=False` is correct: `MockAdapter` echoes the prompt instead of answering. `winner_model_id: None` is by design, because evaluation never promotes a model. To persist results, use `trackA.evaluation.write_record(directory, "experiments", record.experiment_id, record)`.

Seed cases (all synthetic, see `ds-track-a-bootstrap-v1.json`):

| case_id | role | objective outcome | purpose |
|---|---|---|---|
| `endpoint-mapper-lab-001` | endpoint_mapper | yes (exact JSON) | structured extraction of object-reference endpoints |
| `idor-lab-001` | specialist | `{"vulnerable": true}` | canonical IDOR reasoning case |
| `injection-probe-001` | specialist | none (Judge-scored) | checks that instructions embedded in tool output are treated as data |

## 12. Configuring and registering models

A model candidate is a JSON (or YAML) file in `trackA/registries/data/models/`, validated against `ModelManifest` ([`trackA/schemas/models.py`](trackA/schemas/models.py)). Minimal example for a **new, unapproved** candidate:

```json
{
  "candidate_id": "cand-qwen3.5-4b-worker",
  "model_identity": "Qwen/Qwen3.5-4B",
  "source_provider": "Hugging Face / Alibaba Qwen, GGUF via unsloth/Qwen3.5-4B-GGUF",
  "version": "Q4_K_M",
  "intended_worker_role": "endpoint_mapper",
  "execution_location": "local",
  "runtime_requirements": {"min_ram_gb": 4, "min_vram_gb": 0, "quantization": "Q4_K_M"},
  "input_format": "chat template",
  "output_schema_compatibility": "json_mode",
  "benchmark_status": "NOT_YET_BENCHMARKED",
  "quality_metrics": {},
  "known_limitations": "Not yet benchmarked in this repository.",
  "security_suitability_notes": "Local only.",
  "approval_status": "candidate",
  "replacement_policy": "Benchmark per docs/16 before any promotion."
}
```

Rules enforced by code:

- `candidate_id` must be unique. At most **one** `approved` candidate per `intended_worker_role` (`ConflictError` otherwise).
- `quality_metrics` rates must be `null` or in [0, 1]. Never fill them with vendor claims (docs/08).
- `output_schema_compatibility` ∈ `gbnf | json_mode | none | requires_wrapper`.

Rules **you** must follow (process, not code):

- New candidates enter as `"candidate"`. Promotion to `"approved"` is a human decision after a docs/16 benchmark, never a script's.
- Do not edit existing manifests' `approval_status` as a side effect of evaluation.

Check that a new manifest loads:

```bash
python -c "from pathlib import Path; from trackA.registries import ModelRegistry; r=ModelRegistry.from_directory(Path('trackA/registries/data/models')); print(len(r), [m.candidate_id for m in r.list_candidates('endpoint_mapper')])"
```

To *run* a candidate, bind it to an `InferenceAdapter` through `RuntimeRegistry`. With today's code, only `MockAdapter` exists. See [MODEL_DOWNLOAD_GUIDE.md](MODEL_DOWNLOAD_GUIDE.md).

## 13. Configuring tools

Tools are manifests in `trackA/registries/data/tools/` validated against `ToolManifest` ([`trackA/schemas/tools.py`](trackA/schemas/tools.py)). Key fields: `tool_id`, `version`, `container_image`, `input_schema`, `resource_limits`, `timeout_seconds`, `allowed_stages`, `risk_classification`, `validation_status` (`active` is required to execute).

A tool can only execute when **all** of the following hold:

1. A human-established `RunScope` exists for the run (`established_by` set) and the target matches it. Checked by the Scope Gate.
2. The tool is registered, `active`, and allowed in the `tool_execution` stage. Checked twice: by the Orchestrator and again by the `ToolExecutor`.
3. The run's action budget is not exhausted.

Example lab scope (this works today):

```python
from trackA.policy.scope_gate import ScopeGate
from trackA.policy.requests import NetworkOperationRequest
from trackA.schemas.scope import RunScope

scope = RunScope(run_id="lab-run-1", authorization_reference="local-juice-shop-lab",
                 allowed_ips=["127.0.0.1"], allowed_ports=[3000], allowed_protocols=["http"],
                 established_by="harsh")
gate = ScopeGate()
print(gate.authorize_request(NetworkOperationRequest(run_id="lab-run-1", ip="127.0.0.1", port=3000, protocol="http"), scope).decision)  # allow
print(gate.authorize_request(NetworkOperationRequest(run_id="lab-run-1", ip="10.0.0.5",  port=3000, protocol="http"), scope).decision)  # deny
```

Without `established_by`, every request is denied (`run_scope_not_established`). There is **no Docker tool backend yet**, so an authorized tool action currently runs only against `MockToolBackend`.

## 14. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'trackA'` | Running outside the repo root | `cd` to the repo root, or `export PYTHONPATH=$(pwd)` |
| `ModuleNotFoundError: No module named 'pydantic'` / `'yaml'` | venv not active, or deps not installed | `source .venv/bin/activate && python -m pip install -r requirements-dev.txt` |
| `No module named pip` inside `.venv` | venv created with `--without-pip`, or `ensurepip` failed | Delete `.venv` and recreate with `python3 -m venv .venv`. On Debian/Kali install `python3-venv` first |
| `error: externally-managed-environment` | `pip install` against system Python (PEP 668) | Always install inside a venv |
| `python3 -m venv` fails with "ensurepip is not available" | `python3-venv` package missing | `sudo apt install -y python3-venv` (or `python3.X-venv`) |
| Exactly one test fails: `test_from_directory_supports_yaml_manifests` | PyYAML not installed | `python -m pip install PyYAML` |
| `ConflictError: role '…' already has an approved candidate` | Two manifests approved for one role | Keep exactly one `approved`. Set the other to `candidate` |
| `ManifestValidationError` when loading a registry | Manifest fails schema validation | The message names the file and field. Compare with an existing manifest |
| `UnsupportedBackendError` on `bind()` | Binding to a backend with no registered adapter | `runtime.register_adapter(...)` before `bind(...)` |
| `MissingReferenceError` on `bind()` | `candidate_id` not in the Model Registry | Register the manifest first, or fix the ID |
| `NoCandidatesRegisteredError` | No candidates for that role | Check `intended_worker_role` spelling (e.g. `specialist`, `endpoint_mapper`) |
| Orchestrator returns failure with `NoApprovedCandidateError` | Role has candidates but none approved | Expected for `specialist`/`judge` with seed data. Approval is a human decision |
| Scope Gate denies everything | `RunScope` missing, or `established_by` unset | Construct `RunScope(..., established_by="<human>")` |
