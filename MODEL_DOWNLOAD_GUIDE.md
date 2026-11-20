# Model Download Guide

How to download candidate models from Hugging Face, verify them, register them as Model Registry candidates, and connect them through the repository's inference abstraction.

**Checked: 2026-11-20.** Repo IDs, filenames and sizes below come from the Hugging Face Hub file listings on that date. All repositories listed are **ungated** (no login or license click-through needed). See [MODEL_CANDIDATES.md](MODEL_CANDIDATES.md) for why each model is a candidate and for license terms.

> **Ground rules**
> - **Nothing in this repository downloads weights.** Every command here is one you run by hand, on **Machine B only**, after a human decides which candidates to evaluate.
> - Weights live **outside the repository**. The repo's `.gitignore` does not exclude `*.gguf`, so never put weights inside the checkout.
> - Registering a candidate never approves it. `approval_status` starts at `"candidate"`, and promotion is a separate human decision after a docs/16 benchmark.

---

## 1. Install the Hugging Face CLI (Machine B)

The CLI command is now `hf` (it replaced the deprecated `huggingface-cli`). It ships with the `huggingface_hub` Python package. Install it **in its own environment**, not in the Track A venv. It is a tool, not a repository dependency.

```bash
# option A: pipx
pipx install huggingface_hub
# option B: uv
uv tool install huggingface_hub
# option C: a dedicated venv
python3 -m venv ~/.venvs/hf && ~/.venvs/hf/bin/pip install -U huggingface_hub && export PATH="$HOME/.venvs/hf/bin:$PATH"

hf --help          # confirm the command exists
```

No `hf auth login` is needed for the repos in this guide. (If you later pick a gated repo, log in with a **read-only** token and never commit it.)

## 2. Where weights are stored

Use one directory tree, mirroring the Hub repo IDs:

```bash
export HM_MODELS="$HOME/models"        # put this line in ~/.bashrc
mkdir -p "$HM_MODELS"
```

Layout: `$HM_MODELS/<org>/<repo>/<file>.gguf`, e.g. `$HM_MODELS/unsloth/Qwen3.5-4B-GGUF/Qwen3.5-4B-Q4_K_M.gguf`.

If you use Ollama's own pull (`ollama pull hf.co/...`), Ollama stores blobs in its own model directory (by default under `~/.ollama/models`). That is fine too, but use one approach per model so you don't download it twice.

## 3. Recommended quantization

| Format | Use when | Notes |
|---|---|---|
| **Q4_K_M** | default for every candidate on Machine B | Best size/quality trade-off for CPU inference. Most common quant, so results compare well |
| Q5_K_M | a model fits with room to spare and you suspect Q4 quality loss | ~15–20% larger |
| Q8_0 | Extractor-sized models (≤ 3B) only | near-lossless. Only affordable for small models on 16 GB |
| QAT Q4_0 (Gemma 4) | Gemma 4 | Google's quantization-aware-trained Q4 is the official quant. Use it instead of a post-hoc Q4_K_M |
| MXFP4 (gpt-oss) | gpt-oss-20b | the model's native format |

Compare candidates **at the same quantization level** where possible, so differences come from the model, not the compression (docs/16: comparable conditions).

## 4. Download commands

Each command downloads **exactly one file**. Pin a revision for reproducibility (§4.2). Approximate sizes are from the Hub listing.

### 4.1 Commands by role tier

```bash
cd "$HM_MODELS"

# --- Baselines already in the registry ---------------------------------------
# Extractor (approved, locked)               1.12 GB
hf download Qwen/Qwen2.5-1.5B-Instruct-GGUF qwen2.5-1.5b-instruct-q4_k_m.gguf \
  --local-dir Qwen/Qwen2.5-1.5B-Instruct-GGUF
# Worker endpoint_mapper (approved)          2.10 GB   ⚠ Qwen Research License
hf download Qwen/Qwen2.5-3B-Instruct-GGUF qwen2.5-3b-instruct-q4_k_m.gguf \
  --local-dir Qwen/Qwen2.5-3B-Instruct-GGUF

# --- Evaluate first (MODEL_CANDIDATES.md §5.1) ---------------------------------
# Worker / small Judge / Polisher            2.74 GB
hf download unsloth/Qwen3.5-4B-GGUF Qwen3.5-4B-Q4_K_M.gguf \
  --local-dir unsloth/Qwen3.5-4B-GGUF

# --- Evaluate second: IDOR Specialist comparison (§5.2) -----------------------
# Specialist, security-tuned                 4.92 GB
hf download mradermacher/Foundation-Sec-8B-Instruct-GGUF Foundation-Sec-8B-Instruct.Q4_K_M.gguf \
  --local-dir mradermacher/Foundation-Sec-8B-Instruct-GGUF
# Specialist, general-model control          5.68 GB
hf download unsloth/Qwen3.5-9B-GGUF Qwen3.5-9B-Q4_K_M.gguf \
  --local-dir unsloth/Qwen3.5-9B-GGUF
# Judge from a third family (pick one)       5.35 GB / 5.20 GB
hf download ibm-granite/granite-4.2-8b-GGUF granite-4.2-8b-Q4_K_M.gguf \
  --local-dir ibm-granite/granite-4.2-8b-GGUF
hf download mistralai/Ministral-3-8B-Instruct-2512-GGUF Ministral-3-8B-Instruct-2512-Q4_K_M.gguf \
  --local-dir mistralai/Ministral-3-8B-Instruct-2512-GGUF
```

Other candidates from MODEL_CANDIDATES.md, if a human selects them:

| Candidate | Command | Size |
|---|---|---|
| Foundation-Sec-8B-Reasoning (official Q4) | `hf download fdtn-ai/Foundation-Sec-8B-Reasoning-Q4_K_M-GGUF foundation-sec-8b-reasoning-q4_k_m.gguf --local-dir fdtn-ai/Foundation-Sec-8B-Reasoning-Q4_K_M-GGUF` | 4.92 GB |
| Foundation-Sec-8B-Instruct (official Q8) | `hf download fdtn-ai/Foundation-Sec-8B-Instruct-Q8_0-GGUF foundation-sec-8b-instruct-q8_0.gguf --local-dir fdtn-ai/Foundation-Sec-8B-Instruct-Q8_0-GGUF` | 8.54 GB |
| Qwen3.5-2B (Extractor challenger) | `hf download unsloth/Qwen3.5-2B-GGUF Qwen3.5-2B-Q4_K_M.gguf --local-dir unsloth/Qwen3.5-2B-GGUF` | 1.28 GB |
| Qwen2.5-Coder-7B (source-reading Worker) | `hf download Qwen/Qwen2.5-Coder-7B-Instruct-GGUF qwen2.5-coder-7b-instruct-q4_k_m.gguf --local-dir Qwen/Qwen2.5-Coder-7B-Instruct-GGUF` | 4.68 GB |
| granite-4.2-3b | `hf download ibm-granite/granite-4.2-3b-GGUF granite-4.2-3b-Q4_K_M.gguf --local-dir ibm-granite/granite-4.2-3b-GGUF` | 2.24 GB |
| Ministral-3-3B | `hf download mistralai/Ministral-3-3B-Instruct-2512-GGUF Ministral-3-3B-Instruct-2512-Q4_K_M.gguf --local-dir mistralai/Ministral-3-3B-Instruct-2512-GGUF` | 2.15 GB |
| gemma-4-E4B-it (QAT) | `hf download google/gemma-4-E4B-it-qat-q4_0-gguf gemma-4-E4B_q4_0-it.gguf --local-dir google/gemma-4-E4B-it-qat-q4_0-gguf` | 5.15 GB |
| gemma-4-12B-it (QAT) | `hf download google/gemma-4-12B-it-qat-q4_0-gguf gemma-4-12b-it-qat-q4_0.gguf --local-dir google/gemma-4-12B-it-qat-q4_0-gguf` | 6.98 GB |
| gpt-oss-20b | `hf download ggml-org/gpt-oss-20b-GGUF gpt-oss-20b-MXFP4.gguf --local-dir ggml-org/gpt-oss-20b-GGUF` | 12.11 GB |

The Gemma 4 and Ministral 3 repos also contain `mmproj` files (vision/audio projectors). Track A is text-only, so you don't need them.

### 4.2 Pin the exact revision

Repos change. Record the commit you downloaded so a benchmark can be reproduced:

```bash
REPO=unsloth/Qwen3.5-4B-GGUF
SHA=$(curl -s "https://huggingface.co/api/models/$REPO" | python3 -c 'import json,sys; print(json.load(sys.stdin)["sha"])')
echo "$REPO@$SHA"
hf download "$REPO" Qwen3.5-4B-Q4_K_M.gguf --revision "$SHA" --local-dir "$HM_MODELS/$REPO"
```

Put `$REPO@$SHA` (and the filename) into the candidate manifest's `source_provider` / `version` fields (§6).

## 5. Verify downloaded files

Do all three checks for every file.

**(a) Size and GGUF magic bytes**

```bash
F="$HM_MODELS/unsloth/Qwen3.5-4B-GGUF/Qwen3.5-4B-Q4_K_M.gguf"
ls -l "$F"                       # compare with the size in §4.1
head -c 4 "$F"; echo             # must print: GGUF
```

**(b) SHA-256 against the Hub's own record.** The Hub API reports each large file's SHA-256 as `lfs.oid`:

```bash
REPO=unsloth/Qwen3.5-4B-GGUF; FILE=Qwen3.5-4B-Q4_K_M.gguf
EXPECTED=$(curl -s "https://huggingface.co/api/models/$REPO/tree/main" | \
  python3 -c "import json,sys; print(next(e['lfs']['oid'] for e in json.load(sys.stdin) if e['path']=='$FILE'))")
ACTUAL=$(sha256sum "$HM_MODELS/$REPO/$FILE" | cut -d' ' -f1)      # macOS: shasum -a 256
[ "$EXPECTED" = "$ACTUAL" ] && echo "OK  $FILE" || echo "MISMATCH  $FILE"
```

(If you pinned a revision, replace `main` in the URL with the commit SHA.)

**(c) It loads and answers.** This is a runtime smoke test, see §7.

GGUF files are data, not code, but treat community quantizations (`unsloth/`, `mradermacher/`, `bartowski/`…) as third-party artifacts. Prefer an official quant when one exists (Qwen, IBM, Mistral, Google, Cisco, ggml-org all publish some) and record the publisher in the manifest.

## 6. Register a model candidate

One manifest per (model, role). The same weights serving two roles need two manifests with different `candidate_id`s (README §12). Save as `trackA/registries/data/models/<candidate_id>.json`:

```json
{
  "candidate_id": "cand-qwen3.5-4b-endpoint-mapper",
  "model_identity": "Qwen/Qwen3.5-4B",
  "source_provider": "Hugging Face / unsloth/Qwen3.5-4B-GGUF@<commit-sha>, file Qwen3.5-4B-Q4_K_M.gguf",
  "version": "Q4_K_M",
  "intended_worker_role": "endpoint_mapper",
  "execution_location": "local",
  "runtime_requirements": {"min_ram_gb": 5, "min_vram_gb": 0, "quantization": "Q4_K_M"},
  "input_format": "chat template (Qwen3.5)",
  "output_schema_compatibility": "json_mode",
  "benchmark_status": "NOT_YET_BENCHMARKED",
  "quality_metrics": {},
  "known_limitations": "Not yet benchmarked in this repository. min_ram_gb is an estimate, not a measurement.",
  "security_suitability_notes": "Local only; served on 127.0.0.1 by Ollama on Machine B.",
  "approval_status": "candidate",
  "replacement_policy": "Benchmark per docs/16 before any promotion; promotion is a human decision."
}
```

Role names must match the code: `extractor`, `endpoint_mapper`, `judge`, `specialist`. Then confirm it loads, and that no role ended up with two approved candidates:

```bash
python -c "
from pathlib import Path
from trackA.registries import ModelRegistry
r = ModelRegistry.from_directory(Path('trackA/registries/data/models'))
for role in ('extractor','endpoint_mapper','judge','specialist'):
    print(role, [(m.candidate_id, m.approval_status) for m in r.list_candidates(role)])
"
python -m pytest -q        # the suite must still pass
```

Adding a manifest file is a repository change. Commit it through a normal reviewed branch and pull request. Do **not** edit the `approval_status` of existing manifests as part of this.

## 7. Smoke-test a model in a runtime (before touching Track A code)

**Ollama, letting Ollama download directly from Hugging Face:**

```bash
ollama pull hf.co/unsloth/Qwen3.5-4B-GGUF:Q4_K_M
ollama run  hf.co/unsloth/Qwen3.5-4B-GGUF:Q4_K_M 'Reply with exactly this JSON and nothing else: {"ok": true}'
curl -s http://127.0.0.1:11434/api/chat -d '{
  "model": "hf.co/unsloth/Qwen3.5-4B-GGUF:Q4_K_M",
  "messages": [{"role":"user","content":"Return {\"ok\": true}"}],
  "format": "json", "stream": false, "options": {"temperature": 0}
}'
```

**llama.cpp, using the file you downloaded and verified:**

```bash
llama-server -m "$HM_MODELS/unsloth/Qwen3.5-4B-GGUF/Qwen3.5-4B-Q4_K_M.gguf" \
  --host 127.0.0.1 --port 8080 -c 8192
# OpenAI-compatible endpoint: http://127.0.0.1:8080/v1/chat/completions
```

Unresolved **[?]**:

- Whether a given Ollama or llama.cpp version supports the `qwen3_5` and `gemma4` architectures. Update the runtime if you see "unknown model architecture".
- How each thinking-capable model (Qwen3.5, Granite 4.2, Gemma 4, Foundation-Sec-Reasoning) is best switched to non-thinking mode in your runtime version. Ollama's `/api/chat` accepts a `think` field for thinking models. Check that your version honours it.

## 8. Connect a candidate through the inference abstraction

### 8.1 What exists

`trackA/models/runtime.py` defines the seam:

- `InferenceAdapter`: abstract class with `backend: ClassVar[str]` and `infer(request, *, binding) -> InferenceResult`.
- `ModelBinding(candidate_id, backend, connection)`: per-candidate runtime wiring. `connection` is a free-form dict (endpoint, model tag…).
- `RuntimeRegistry`: `register_adapter(adapter)`, then `bind(binding)` (checks the candidate exists in the Model Registry), then `invoke(candidate_id, request)`.
- **Only `MockAdapter` ships.** There is no Ollama, llama.cpp or cloud adapter in the repository.

### 8.2 Contract a real adapter must honour (from the code)

1. **Never raise for model-side failures** (timeout, connection refused, refusal, malformed output). Return `InferenceResult(success=False, error="…")`. The harness and Orchestrator retry those as technical failures (bounded).
2. Set `raw["refusal"] = True` **only** when the backend positively signals a refusal. Never guess from text. Refusals are never retried.
3. Put the **parsed model JSON** in `raw` when the output is a JSON object. The harness uses `raw` as the candidate's `final_output` (compared with `objective_outcome`), and the Orchestrator uses it as the structured payload. Put the raw text in `output_text`.
4. **Never copy `binding.connection` into `raw`.** The harness records `raw` verbatim into trajectories, while it keeps `connection` out unless `include_runtime_config=True` is set.
5. Generation settings come from `InferenceRequest.generation_policy` (a dict). The harness currently sends `{}`, so the adapter must supply deterministic defaults (temperature 0).
6. The model's output is **untrusted data**. The adapter returns it, and schema validation is the calling component's job. Nothing in the output can authorize an action.

### 8.3 Example adapter (illustration only, not in the repository)

The class below is an **example of the future work**. It was exercised on 2026-11-20 against a **stub** HTTP server that imitates Ollama's `/api/chat` (not a real Ollama), end-to-end through `RuntimeRegistry` and `EvaluationHarness`:

- The success path produced `objective_outcome_match=True` on `idor-lab-001`.
- An unreachable endpoint came back as `technical_failure` after 2 retries.
- `runtime_config` stayed empty.

It uses only the standard library, so it needs no new dependency. Adding it to `trackA/models/` (with tests) is a code change for a reviewed pull request. This guide does not make that change.

```python
import json, time, urllib.error, urllib.request
from trackA.models.runtime import InferenceAdapter, InferenceRequest, InferenceResult, ModelBinding

class OllamaAdapter(InferenceAdapter):
    backend = "ollama"

    def infer(self, request: InferenceRequest, *, binding: ModelBinding) -> InferenceResult:
        conn = binding.connection
        base_url = conn.get("base_url", "http://127.0.0.1:11434").rstrip("/")
        if "model" not in conn:   # adapter-usage error: allowed to raise
            raise ValueError("ModelBinding.connection['model'] is required for the ollama backend")
        body = {
            "model": conn["model"],
            "messages": [{"role": "user", "content": request.prompt}],
            "stream": False,
            "options": {"temperature": 0, **request.generation_policy.get("options", {})},
        }
        if "format" in request.generation_policy:   # "json" or a JSON-schema dict
            body["format"] = request.generation_policy["format"]
        if "think" in request.generation_policy:    # thinking models: True/False
            body["think"] = request.generation_policy["think"]
        started = time.monotonic()
        try:
            req = urllib.request.Request(f"{base_url}/api/chat", data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=conn.get("timeout_s", 300)) as resp:
                payload = json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            return InferenceResult(success=False, error=f"ollama call failed: {exc}",
                                   latency_ms=(time.monotonic() - started) * 1000)
        text = (payload.get("message") or {}).get("content", "")
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
        return InferenceResult(success=True, output_text=text,
                               raw=parsed if isinstance(parsed, dict) else None,
                               latency_ms=(time.monotonic() - started) * 1000)
```

Wiring it to a registered candidate and running the existing harness:

```python
from pathlib import Path
from trackA.evaluation import BenchmarkCaseStore, EvaluationHarness
from trackA.models import ModelBinding, RuntimeRegistry
from trackA.registries import ModelRegistry
from trackA.schemas.common import PipelineStage

models = ModelRegistry.from_directory(Path("trackA/registries/data/models"))
case = BenchmarkCaseStore.from_directory(Path("trackA/evaluation/data/cases")).lookup("endpoint-mapper-lab-001")

runtime = RuntimeRegistry(model_registry=models)
runtime.register_adapter(OllamaAdapter())
runtime.bind(ModelBinding(candidate_id="qwen2.5-3b-worker", backend="ollama",
    connection={"model": "hf.co/Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M"}))
runtime.bind(ModelBinding(candidate_id="cand-qwen3.5-4b-endpoint-mapper", backend="ollama",
    connection={"model": "hf.co/unsloth/Qwen3.5-4B-GGUF:Q4_K_M"}))

trajectories = EvaluationHarness(runtime=runtime, model_registry=models).run_experiment(
    case, experiment_id="exp-endpoint-mapper-001", role_stage=PipelineStage.WORKER,
    dataset_id="ds-track-a-bootstrap", dataset_version="v1")
```

Every candidate registered for the role must be bound, because `run_experiment` runs all of them. Continue with blinding, judging and `build_experiment_record` exactly as in README §11. The resulting `ExperimentRecord.winner_model_id` is always `None`. Reading the results and deciding what to approve is a human task.

> `role_stage=PipelineStage.WORKER` is the stage value for worker-role cases. Check `trackA/schemas/common.py` (`PipelineStage`) for the full list.

## 9. Removing a model

```bash
ollama rm hf.co/unsloth/Qwen3.5-4B-GGUF:Q4_K_M                 # Ollama-managed copy
rm "$HM_MODELS/unsloth/Qwen3.5-4B-GGUF/Qwen3.5-4B-Q4_K_M.gguf"  # hf-downloaded copy
```

Removing weights does not remove the registry manifest. Set its `approval_status` to `deprecated` or `rejected` through a reviewed change if the candidate is retired.
