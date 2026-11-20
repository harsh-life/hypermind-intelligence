# Model Candidates for the First IDOR Experiment

**Information checked: 2026-11-20**, against the Hugging Face Hub (repo metadata, model cards, `config.json`, `LICENSE`/`NOTICE` files, and GGUF file listings).

This document lists **candidates for evaluation**. It is **not** a selection.

- No model below has been benchmarked against a Track A contract. Every `quality_metrics` value in the registry stays `null` until a docs/16 trajectory benchmark measures it.
- Nothing here changes the Model Registry. Adding a candidate manifest and approving a candidate are separate, human decisions (docs/08, README §12).
- A model whose name or marketing says "cybersecurity", "pentest" or "uncensored" gets **no** credit for that. docs/08 records an independent study in which the most "offensive"-branded model performed worst on deceptive content.

### How to read this document

| Marker | Meaning |
|---|---|
| **[V]** | Verified on the Hugging Face Hub on 2026-11-20 (model card, config, license file, or file listing) |
| **[E]** | Estimate. Not measured on our hardware |
| **[R]** | My recommendation or assessment. Opinion, not fact |
| **[?]** | Not resolved. Check before relying on it |

**RAM estimate rule [E]:** practical RAM ≈ GGUF file size + 1–2 GB (KV cache at ~8K context plus runtime overhead), CPU-only. Longer contexts need more. Hybrid-attention models (Qwen3.5, Gemma 4, gpt-oss) grow their KV cache more slowly than dense-attention models.

**Machine budget [E]:**

- **Machine A** (4 GB host, ~2 GB VM): **no model**. Unit tests and mock evaluation only.
- **Machine B** (16 GB): OS ≈ 3 GB and Docker + Juice Shop ≈ 1 GB leave **≈ 10–11 GB for one model at a time**. The evaluation harness runs candidates sequentially, which fits this. Comfortable up to ~9B at Q4/Q5. 12B Q4 is feasible. 20B is borderline and only works with Docker stopped (or on a GPU with ≥ 16 GB VRAM).

**ARM64 and runtimes (applies to every GGUF below) [V/R]:** GGUF files run on llama.cpp and runtimes built on it (Ollama, LM Studio), on Linux aarch64 (CPU) and Apple Silicon (Metal). Safetensors weights run on Hugging Face Transformers and, for most of these, vLLM/SGLang (per their cards). Machine B's CPU architecture and GPU are not stated, so none of this was tested on it **[?]**.

---

## 1. Summary table

Sizes are exact file sizes from the Hub listing (1 GB = 10⁹ bytes).

| # | Repository ID | Params [V] | License [V] | Context [V] | Q4 GGUF size [V] | RAM [E] | Roles [R] |
|---|---|---|---|---|---|---|---|
| 1 | `Qwen/Qwen2.5-1.5B-Instruct` | 1.54 B | Apache-2.0 | 32,768 | 1.12 GB (Q4_K_M) | ~2–3 GB | Extractor *(registered, approved)* |
| 2 | `Qwen/Qwen2.5-3B-Instruct` | 3.09 B | **Qwen Research License (non-commercial)** | 32,768 | 2.10 GB (Q4_K_M) | ~3–4 GB | Worker *(registered, approved)*, Judge *(registered candidate)* |
| 3 | `Qwen/Qwen3.5-2B` | 2.27 B | Apache-2.0 | 262,144 [?] | 1.28 GB (Q4_K_M) | ~2–3 GB | Extractor challenger |
| 4 | `Qwen/Qwen3.5-4B` | 4.66 B | Apache-2.0 | 262,144 [?] | 2.74 GB (Q4_K_M) | ~4–5 GB | Worker, small Judge, Report Polisher |
| 5 | `Qwen/Qwen3.5-9B` | 9.65 B | Apache-2.0 | 262,144 | 5.68 GB (Q4_K_M) | ~7–8 GB | Specialist, Judge, Worker (medium) |
| 6 | `Qwen/Qwen2.5-Coder-7B-Instruct` | 7.62 B | Apache-2.0 | 32,768 (config) | 4.68 GB (Q4_K_M) | ~6–7 GB | Worker (source-code reading) |
| 7 | `fdtn-ai/Foundation-Sec-8B-Instruct` | 8.03 B | Llama 3.1 Community + Apache-2.0 (Cisco changes) | 131,072 (config) | 4.92 GB (Q4_K_M) | ~6–7 GB | Specialist |
| 8 | `fdtn-ai/Foundation-Sec-8B-Reasoning` | 8.03 B | Llama 3.1 Community + Apache-2.0 (Cisco changes) | 131,072 (config of sibling) [?] | 4.92 GB (Q4_K_M, official) | ~6–7 GB | Specialist |
| 9 | `ibm-granite/granite-4.2-3b` | 3.66 B | Apache-2.0 | 128K [?] | 2.24 GB (Q4_K_M, official) | ~3–4 GB | Worker / Extractor challenger (non-Qwen) |
| 10 | `ibm-granite/granite-4.2-8b` | 8.79 B | Apache-2.0 | 128K native (512K ext.) | 5.35 GB (Q4_K_M, official) | ~7–8 GB | Judge, Specialist |
| 11 | `mistralai/Ministral-3-3B-Instruct-2512` | 3.85 B | Apache-2.0 | 256K [?] | 2.15 GB (Q4_K_M, official) | ~3–4 GB | Worker (non-Qwen) |
| 12 | `mistralai/Ministral-3-8B-Instruct-2512` | 8.92 B | Apache-2.0 | 256K | 5.20 GB (Q4_K_M, official) | ~7–8 GB | Judge, Report Polisher |
| 13 | `google/gemma-4-E4B-it` | 8.0 B total / 4.5 B effective | Apache-2.0 | 128K | 5.15 GB (QAT Q4_0, official) | ~6–7 GB | Report Polisher, Judge |
| 14 | `google/gemma-4-12B-it` | 11.96 B | Apache-2.0 | 256K | 6.98 GB (QAT Q4_0, official) | ~9–10 GB | Judge / Specialist (larger) |
| 15 | `openai/gpt-oss-20b` | 20.9 B MoE (4 of 32 experts active) | Apache-2.0 | 131,072 (config) | 12.11 GB (MXFP4) | ~14 GB+ | Judge (largest that might fit) |
| — | `fdtn-ai/Foundation-Sec-8B` (base) | 8.03 B | Apache-2.0 | — | — | — | *registered as `cand-001`. Not instruction-tuned, see §3* |
| — | `WhiteRabbitNeo/Llama-3.1-WhiteRabbitNeo-2-8B` | 8.03 B | Llama 3.1 + WhiteRabbitNeo usage restrictions | — | ~4.9 GB [E] | ~6–7 GB | *registered as `cand-003`, see §3* |

---

## 2. Candidates by role

What each role needs, as I read the repository contracts **[R]**:

| Role | Contract in repo | What matters most |
|---|---|---|
| **Worker** (endpoint and app-behaviour analysis) | `endpoint_mapper_v1`: map endpoints containing object references, cite the source entity, **must not** assess exploitability | Faithful structured output, no over-claiming, following instructions over tool output |
| **Extractor** | `ExtractorJSON` (docs/02 §13), GBNF-constrained | Schema validity, zero hallucinated entities, speed. Reasoning depth matters little |
| **Specialist** (IDOR) | `idor_v1` skill: pick the most promising endpoint+parameter, describe the substitution, produce a `replication_command`, never fabricate access | Authorization-logic reasoning, evidence discipline, false-positive resistance |
| **Judge** | `JudgeInput` (never sees Skill content); `BenchmarkJudge` for evaluation | Independence from the Specialist, calibrated "insufficient evidence" verdicts, resistance to injected instructions |
| **Report Polisher** | `Report` schema; formatting only, after human validation | Faithfulness to validated evidence. Adds nothing |

Note: grammar/JSON-schema constrained decoding (llama.cpp GBNF, Ollama's `format` field) is a **runtime** feature that works with any GGUF model. That makes the "gbnf" requirement in the registry achievable for every candidate below.

### 2.1 Worker: endpoint and application-behaviour analysis

| Tier | Candidate | Why consider it [R] | Watch for [R] |
|---|---|---|---|
| Baseline | **Qwen2.5-3B-Instruct** (registered, approved) | Already the approved implementation, so it is the comparison baseline | Research-only license (§3). Older generation |
| Small | **Qwen3.5-4B** | Newest small Qwen, Apache-2.0, long context for big HAR/proxy logs, 2.7 GB | Hybrid architecture needs a recent runtime. Multimodal weights (vision tower unused here). Thinking mode must be controlled [?] |
| Small (other family) | **granite-4.2-3b** / **Ministral-3-3B-Instruct-2512** | Non-Qwen comparison points. Granite advertises tool calling and switchable thinking. Ministral advertises native JSON output | Unknown structured-output reliability on our schema until benchmarked |
| Medium | **Qwen2.5-Coder-7B-Instruct** | Juice Shop is open source, so a coder model can read route and handler code to find where ownership checks *should* be | Code skill ≠ authorization reasoning. 32K default context |
| Medium | **Qwen3.5-9B** | Strongest general model that comfortably fits Machine B | 5.7 GB at Q4. Slow on CPU [E] |

### 2.2 Extractor: structured extraction of observations

`qwen2.5-1.5b-extractor` is **locked by an architecture decision** (docs/08, docs/15 §2). Its manifest says replacement requires "an explicit architecture-level decision, not an automatic re-benchmark". The challengers below are for a human to consider only if that decision is revisited.

| Tier | Candidate | Why consider it [R] |
|---|---|---|
| Locked | **Qwen2.5-1.5B-Instruct** | Apache-2.0, 1.1 GB, fast. With GBNF constraints, schema validity comes mostly from the grammar |
| Challenger | **Qwen3.5-2B** | Same size class, newer generation, 1.3 GB |
| Challenger (other family) | **granite-4.2-3b** | Different training lineage, so it is useful for checking whether extraction errors are model-specific |

### 2.3 Specialist: IDOR reasoning and validation

| Tier | Candidate | Why consider it [R] | Watch for [R] |
|---|---|---|---|
| Medium | **Foundation-Sec-8B-Instruct** | Security-domain continued pre-training (Cisco) plus instruction tuning. Intended for local deployment. Llama-3.1 backbone | Vendor benchmarks are threat-intel focused (CTI, CVE→CWE), **not** web authorization logic. Its card lists "autonomous security decision-making without human review" as out of scope, which matches our human-validation rule |
| Medium | **Foundation-Sec-8B-Reasoning** | Same base with reasoning traces. May help with multi-step ownership reasoning | Reasoning traces cost latency on CPU. Same family as the Instruct model, so don't use one as the other's Judge |
| Medium (general) | **Qwen3.5-9B** | Strong general reasoner. A necessary control: if a general model matches the security-tuned one, branding added nothing | Not security-tuned |
| Larger | **gemma-4-12B-it** | Largest dense candidate that fits Machine B [E]. Apache-2.0 | ~7 GB at Q4. Expect slow CPU inference |
| Registered | `cand-003-whiterabbitneo` | Registered candidate. Evaluate only under the same protocol | See §3: independent trap-susceptibility evidence, and its card recommends refusal-bypass seeding |

### 2.4 Judge: independent assessment of candidate findings

Rules from the repository: the Judge never receives Skill content (structurally enforced). The judge manifest says Judge and Specialist must not share weights or prompts **in the same run**. Family diversity is *not* mandated (OD-22 reversed), but **[R]** I recommend it for the first experiment, so the Judge does not share the Specialist's blind spots.

| If the Specialist is… | Judge candidates [R] |
|---|---|
| Foundation-Sec (Llama 3.1 family) | Qwen3.5-9B, granite-4.2-8b, Ministral-3-8B, gemma-4-12B-it |
| Qwen3.5-9B | granite-4.2-8b, Ministral-3-8B, gemma-4-12B-it |
| Small-model smoke tests | Qwen3.5-4B, gemma-4-E4B-it |
| Largest that might fit | gpt-oss-20b (12.1 GB MXFP4). Only with Docker stopped or on a ≥ 16 GB GPU [E] |

docs/08 says the *initial* Judge is meant to be "a heavyweight cloud model". No cloud adapter exists in the repo, and calling one would send evidence off-machine. That is a human decision. The local options above are for local experiments.

### 2.5 Report Polisher: evidence-grounded report generation

Formatting-only, after human validation. Faithfulness matters more than capability **[R]**.

| Tier | Candidate | Why [R] |
|---|---|---|
| Small | **Qwen3.5-4B** | Good writing quality for its size. Cheap |
| Medium | **gemma-4-E4B-it**, **Ministral-3-8B-Instruct-2512** | Strong instruction following and system-prompt adherence per their cards |
| Larger | **gemma-4-12B-it** | Best quality that fits. Use when the report matters more than latency |

---

## 3. Findings about the existing registry (no changes made)

1. **`qwen2.5-3b-worker` (approved) and `qwen2.5-3b-judge` use a non-commercial license. [V]** The `LICENSE` file of `Qwen/Qwen2.5-3B-Instruct` is the *Qwen RESEARCH LICENSE AGREEMENT*: "FOR NON-COMMERCIAL PURPOSES ONLY … If you are commercially using the Materials, you shall request a license." The 1.5B and 7B siblings are Apache-2.0. docs/08 makes licensing a user decision. This note makes sure the decision is informed.
2. **`cand-001-foundation-sec-8b` points to the base model. [V]** `fdtn-ai/Foundation-Sec-8B` is the continued-pre-training **base** model. Cisco's Instruct card describes the Instruct variant as extending that base "with instruction-following capabilities". Yet the manifest says `input_format: "chat template"`. For chat/JSON roles the relevant repos are `Foundation-Sec-8B-Instruct` (Aug 2025) and `Foundation-Sec-8B-Reasoning` (Jan 2026). Note the license difference: the **base** is Apache-2.0, while **Instruct/Reasoning** are Llama 3.1 Community License plus Apache-2.0 for Cisco's changes (per their `NOTICE.md`).
3. **`cand-003-whiterabbitneo` is ambiguous. [V]** "WhiteRabbitNeo-2 / v2" most likely means `WhiteRabbitNeo/Llama-3.1-WhiteRabbitNeo-2-8B` (Llama 3.1 license + WhiteRabbitNeo usage restrictions). A 70B variant also exists. The newer `WhiteRabbitNeo-2.5-Qwen-2.5-Coder-7B` card tells users to **pre-seed the assistant turn to get past refusals**. That conflicts with docs/08: "The pipeline never jailbreaks its own models." **[R]** If this candidate is evaluated, do not use that seeding.
4. **Manifest RAM figures are authored, not measured.** E.g. the specialist manifests say `min_ram_gb: 16, quantization: fp16`. At Q4_K_M the same 8B models are ~4.9 GB files. Updating those numbers is a registry edit, which is out of scope here.
5. **Role naming:** docs/08 uses `specialist_idor`, while code and manifests use `specialist`. Candidate manifests must use the code's names (`extractor`, `endpoint_mapper`, `judge`, `specialist`).

---

## 4. Candidate cards (all fields)

Every card: checked 2026-11-20. Runtimes: GGUF → llama.cpp / Ollama / LM Studio; safetensors → Transformers (and vLLM/SGLang where the card says so). ARM64: GGUF runs on aarch64 CPU and Apple Metal; not tested on Machine B **[?]**.

### 4.1 `Qwen/Qwen2.5-1.5B-Instruct` · <https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct>
- **Size [V]:** 1,543.7 M params · architecture `qwen2` (dense transformer) · instruction-tuned.
- **License [V]:** Apache-2.0.
- **Quantized [V]:** official `Qwen/Qwen2.5-1.5B-Instruct-GGUF`: q4_0 1.07 GB, **q4_k_m 1.12 GB**, q8_0 1.89 GB.
- **Context [V]:** 32,768.
- **RAM [E]:** ~2–3 GB.
- **Strengths [R]:** tiny and fast, the registry's locked Extractor. Works well under grammar constraints.
- **Limitations [R]:** weak at multi-step reasoning. Not for Specialist or Judge.

### 4.2 `Qwen/Qwen2.5-3B-Instruct` · <https://huggingface.co/Qwen/Qwen2.5-3B-Instruct>
- **Size [V]:** 3,085.9 M · `qwen2` · instruction-tuned.
- **License [V]:** **Qwen Research License, non-commercial only** (see §3.1).
- **Quantized [V]:** official `Qwen/Qwen2.5-3B-Instruct-GGUF`: q4_0 2.00 GB, **q4_k_m 2.10 GB**, q8_0 3.62 GB.
- **Context [V]:** 32,768.
- **RAM [E]:** ~3–4 GB.
- **Strengths [R]:** the approved Worker baseline. Small and well understood.
- **Limitations [R]:** license; older generation; limited reasoning for Judge use.

### 4.3 `Qwen/Qwen3.5-2B` · <https://huggingface.co/Qwen/Qwen3.5-2B>
- **Size [V]:** 2,274.1 M (includes vision encoder) · `qwen3_5`: hybrid Gated DeltaNet + gated attention, vision-language · post-trained (chat).
- **License [V]:** Apache-2.0.
- **Quantized [V]:** `unsloth/Qwen3.5-2B-GGUF`: Q4_K_S 1.22 GB, **Q4_K_M 1.28 GB**, Q8_0 2.01 GB. Also `lmstudio-community/Qwen3.5-2B-GGUF` and `bartowski/Qwen_Qwen3.5-2B-GGUF`.
- **Context:** 262,144 is stated on the 9B card for the family **[?]** for 2B specifically.
- **RAM [E]:** ~2–3 GB.
- **Strengths [R]:** newest-generation small model. Candidate Extractor challenger.
- **Limitations [R]:** needs a recent llama.cpp/Ollama. Thinking-mode default not checked **[?]**.

### 4.4 `Qwen/Qwen3.5-4B` · <https://huggingface.co/Qwen/Qwen3.5-4B>
- **Size [V]:** 4,659.9 M (includes vision encoder) · `qwen3_5` hybrid · post-trained.
- **License [V]:** Apache-2.0.
- **Quantized [V]:** `unsloth/Qwen3.5-4B-GGUF`: IQ4_XS 2.48 GB, **Q4_K_M 2.74 GB**, Q5_K_M 3.14 GB, Q8_0 4.48 GB. Ollama library lists a `qwen3.5:4b` tag (third-party search result, not checked on ollama.com) **[?]**.
- **Context:** 262,144 (family) **[?]**.
- **RAM [E]:** ~4–5 GB.
- **Strengths [R]:** best size/capability trade-off for Worker, small Judge and Polisher. Long context for large request logs. Apache-2.0.
- **Limitations [R]:** small model, so expect more false positives on authorization reasoning than 8–9B models. Thinking mode control **[?]**.

### 4.5 `Qwen/Qwen3.5-9B` · <https://huggingface.co/Qwen/Qwen3.5-9B>
- **Size [V]:** 9,653.1 M · `qwen3_5` hybrid (32 layers: 3× Gated DeltaNet per 1× gated attention) · post-trained.
- **License [V]:** Apache-2.0.
- **Quantized [V]:** `unsloth/Qwen3.5-9B-GGUF`: IQ4_XS 5.17 GB, **Q4_K_M 5.68 GB**, Q5_K_M 6.58 GB, Q8_0 9.53 GB. Also lmstudio-community and bartowski.
- **Context [V]:** 262,144 native (card says extensible to ~1M).
- **RAM [E]:** ~7–8 GB at Q4_K_M.
- **Strengths [R]:** strongest general model that fits comfortably. Useful as Specialist control or as Judge for a Llama-family Specialist.
- **Limitations [R]:** CPU latency. Not security-tuned.

### 4.6 `Qwen/Qwen2.5-Coder-7B-Instruct` · <https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct>
- **Size [V]:** 7,615.6 M · `qwen2` · instruction-tuned, code-specialised.
- **License [V]:** Apache-2.0.
- **Quantized [V]:** official `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF`: **q4_k_m 4.68 GB** (single file, or 2-part split), q5_k_m 5.44 GB.
- **Context:** 32,768 in `config.json`; the card documents YaRN extension to 128K **[?]** in GGUF runtimes.
- **RAM [E]:** ~6–7 GB.
- **Strengths [R]:** reading route/controller code to locate missing ownership checks (Juice Shop source is public).
- **Limitations [R]:** code fluency is not authorization judgement. Keep it to Worker/analysis, not verdicts.

### 4.7 `fdtn-ai/Foundation-Sec-8B-Instruct` · <https://huggingface.co/fdtn-ai/Foundation-Sec-8B-Instruct>
- **Size [V]:** 8,031.3 M · `llama` (Llama-3.1-8B backbone, security continued pre-training) · instruction-tuned. Released 2025-08-01.
- **License [V]:** `NOTICE.md`: Llama 3.1 Community License (Meta) + Apache-2.0 for Cisco's changes. Card lists out-of-scope uses, including autonomous security decisions without human review.
- **Quantized [V]:** official `fdtn-ai/Foundation-Sec-8B-Instruct-Q8_0-GGUF` (8.54 GB); community `mradermacher/Foundation-Sec-8B-Instruct-GGUF`: IQ4_XS 4.49 GB, **Q4_K_M 4.92 GB**, Q5_K_M 5.73 GB, Q8_0 8.54 GB.
- **Context [V]:** `max_position_embeddings` 131,072 (Llama-3.1 RoPE scaling).
- **RAM [E]:** ~6–7 GB at Q4_K_M; ~10 GB at Q8_0.
- **Strengths [R]:** security vocabulary and concepts. Designed for local deployment. The most credible "security-tuned" candidate.
- **Limitations [R]:** vendor evaluation centres on threat intel, not web-app authorization. Community quant (not official) at Q4.

### 4.8 `fdtn-ai/Foundation-Sec-8B-Reasoning` · <https://huggingface.co/fdtn-ai/Foundation-Sec-8B-Reasoning>
- **Size [V]:** 8,030.4 M · `llama` · instruction + reasoning-trace tuned. Released 2026-01-28.
- **License [V]:** same `NOTICE.md` terms as 4.7.
- **Quantized [V]:** official `fdtn-ai/Foundation-Sec-8B-Reasoning-Q4_K_M-GGUF` (**4.92 GB**) and `fdtn-ai/Foundation-Sec-8B-Reasoning-Q8_0-GGUF`; community mradermacher, DevQuasar.
- **Context:** assumed 131,072 like its siblings **[?]**.
- **RAM [E]:** ~6–7 GB at Q4_K_M.
- **Strengths [R]:** official Q4 quant. Reasoning may help with "who owns this object" chains.
- **Limitations [R]:** long reasoning traces on CPU. Reasoning text must be stripped before schema validation.

### 4.9 `ibm-granite/granite-4.2-3b` · <https://huggingface.co/ibm-granite/granite-4.2-3b>
- **Size [V]:** 3,659.7 M · `granite` dense, reasoning (`<think>`), tool calling. Base: granite-4.1-3b-base.
- **License [V]:** Apache-2.0.
- **Quantized [V]:** official `ibm-granite/granite-4.2-3b-GGUF`: Q4_0 2.13 GB, **Q4_K_M 2.24 GB**, Q8_0 3.89 GB.
- **Context:** 128K stated on the 8B card **[?]** for 3B.
- **RAM [E]:** ~3–4 GB.
- **Strengths [R]:** non-Qwen small model with official quants. Switchable thinking.
- **Limitations [R]:** unbenchmarked on our schemas.

### 4.10 `ibm-granite/granite-4.2-8b` · <https://huggingface.co/ibm-granite/granite-4.2-8b>
- **Size [V]:** 8,791.6 M · `granite` dense reasoning model. Released 2026-08-25.
- **License [V]:** Apache-2.0.
- **Quantized [V]:** official `ibm-granite/granite-4.2-8b-GGUF`: Q4_0 5.06 GB, **Q4_K_M 5.35 GB**, Q5_K_M 6.25 GB, Q8_0 9.35 GB.
- **Context [V]:** 128K native, 512K with long-context extension. Thinking modes: full (default), non-thinking, low-effort.
- **RAM [E]:** ~7–8 GB.
- **Strengths [R]:** good Judge candidate: different lineage from both Qwen and Llama, and controllable reasoning depth.
- **Limitations [R]:** default full-thinking mode is slow on CPU. Use low-effort or non-thinking for smoke tests.

### 4.11 `mistralai/Ministral-3-3B-Instruct-2512` · <https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512>
- **Size [V]:** 3,849.1 M (language model + vision encoder) · `mistral3` · instruct (safetensors repo is FP8).
- **License [V]:** Apache-2.0.
- **Quantized [V]:** official `mistralai/Ministral-3-3B-Instruct-2512-GGUF`: **Q4_K_M 2.15 GB**, Q5_K_M 2.47 GB, Q8_0 3.65 GB, BF16 6.87 GB.
- **Context:** 256K stated on the 8B card **[?]** for 3B.
- **RAM [E]:** ~3–4 GB.
- **Strengths [R]:** native JSON output and function calling per the family card. Third model family for diversity.
- **Limitations [R]:** the card recommends temperature < 0.1 for production. Keep generation deterministic.

### 4.12 `mistralai/Ministral-3-8B-Instruct-2512` · <https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512>
- **Size [V]:** 8,918.0 M (8.4 B LM + 0.4 B vision) · `mistral3` · instruct.
- **License [V]:** Apache-2.0.
- **Quantized [V]:** official `mistralai/Ministral-3-8B-Instruct-2512-GGUF`: **Q4_K_M 5.20 GB**, Q5_K_M 6.06 GB, Q8_0 9.03 GB.
- **Context [V]:** 256K.
- **RAM [E]:** ~7–8 GB.
- **Strengths [R]:** strong system-prompt adherence per its card. Judge or Polisher from a non-Qwen, non-Llama family.
- **Limitations [R]:** unbenchmarked here.

### 4.13 `google/gemma-4-E4B-it` · <https://huggingface.co/google/gemma-4-E4B-it>
- **Size [V]:** 7,996.2 M total (4.5 B "effective", per card) · `gemma4` (sliding-window + global attention, multimodal: text, image, audio) · instruction-tuned, configurable thinking.
- **License [V]:** Apache-2.0 (Gemma 4 moved to Apache-2.0; earlier Gemma 3 used custom terms and gated access).
- **Quantized [V]:** official `google/gemma-4-E4B-it-qat-q4_0-gguf`: **5.15 GB** (+ optional 0.99 GB mmproj for images/audio, not needed here).
- **Context [V]:** 128K.
- **RAM [E]:** ~6–7 GB.
- **Strengths [R]:** quantization-aware-trained Q4 from Google (usually less quality loss than post-hoc Q4). Good writer, so a Polisher candidate.
- **Limitations [R]:** total weights are 8 B even though compute is ~4.5 B, so memory is like an 8B model.

### 4.14 `google/gemma-4-12B-it` · <https://huggingface.co/google/gemma-4-12B-it>
- **Size [V]:** 11,959.7 M · `gemma4_unified` (encoder-free multimodal) · instruction-tuned.
- **License [V]:** Apache-2.0.
- **Quantized [V]:** official `google/gemma-4-12B-it-qat-q4_0-gguf`: **6.98 GB** (+ 0.18 GB mmproj).
- **Context [V]:** 256K.
- **RAM [E]:** ~9–10 GB, which is near the Machine B budget. Run with Docker stopped if tight.
- **Strengths [R]:** largest dense model that plausibly fits. Judge or "larger Specialist" tier.
- **Limitations [R]:** slow on CPU. Little memory headroom.

### 4.15 `openai/gpt-oss-20b` · <https://huggingface.co/openai/gpt-oss-20b>
- **Size [V]:** 20,914.8 M · `gpt_oss` MoE (32 experts, 4 per token; alternating sliding/full attention) · instruction-tuned reasoning model.
- **License [V]:** Apache-2.0.
- **Quantized [V]:** weights ship natively in MXFP4. `ggml-org/gpt-oss-20b-GGUF`: **MXFP4 12.11 GB**.
- **Context [V]:** 131,072.
- **RAM [E]:** ~14 GB+. **Not practical on Machine B with Docker running.** Only if Machine B has a GPU with ≥ 16 GB VRAM, or you run it alone.
- **Strengths [R]:** a strong Judge candidate for its memory class. MoE with only 4 of 32 experts active per token, so it decodes faster than a dense 20B model once loaded.
- **Limitations [R]:** memory. Expects its own chat format ("harmony"); runtimes handle it but adapters must not hand-roll prompts.

---

## 5. Recommendations [R]

### 5.1 Evaluate first: `Qwen/Qwen3.5-4B` (Q4_K_M, 2.74 GB)

Why this one first:

1. **It tests the plumbing, not just a model.** No real `InferenceAdapter` exists yet. The first goal is to prove one end-to-end path: download → runtime → adapter → `RuntimeRegistry` → `EvaluationHarness` → `ExperimentRecord`. A 2.7 GB model makes that loop fast on Machine B, with plenty of RAM left for Docker and Juice Shop.
2. **It has an objective comparison ready.** Registered as an `endpoint_mapper` candidate, it can run `endpoint-mapper-lab-001` (the one seed case with an exact, machine-checkable `objective_outcome`) next to the approved `qwen2.5-3b-worker` baseline, under identical inputs.
3. **License.** Apache-2.0. If it matches the baseline, it gives the human decision-maker a non-research-license alternative to Qwen2.5-3B.
4. **Reuse.** The same download can be registered separately as a small Judge and as a Polisher candidate, one manifest per role.

### 5.2 Evaluate second (first security-specific comparison)

On `idor-lab-001` and `injection-probe-001` (`specialist` role):

- `fdtn-ai/Foundation-Sec-8B-Instruct` Q4_K_M (4.92 GB) vs.
- `Qwen/Qwen3.5-9B` Q4_K_M (5.68 GB) as the general-model control,
- judged by a model from a **third** family (`ibm-granite/granite-4.2-8b` or `mistralai/Ministral-3-8B-Instruct-2512`).

The question this answers: does security-domain tuning beat a general model of the same size on *our* contract, once grounded evidence and injection resistance are scored? That is the decision docs/08 says must come from benchmarking, not branding.

### 5.3 Defer

- `gpt-oss-20b`, until you know Machine B's GPU/VRAM.
- `WhiteRabbitNeo`, unless you explicitly want it in the comparison. If so, use the same protocol and no refusal-bypass seeding.
- Any model larger than ~12B: it doesn't fit the stated hardware.

### 5.4 Before any of this produces meaningful numbers

- A real `InferenceAdapter` (MODEL_DOWNLOAD_GUIDE.md §8).
- Juice Shop-derived `BenchmarkCase`s with real `objective_outcome`s, from the human observation protocol in SETUP_GUIDE.md Part 9. The three seed cases are synthetic and too few to rank models.
- Per docs/16: results inform a **human** approval decision. `winner_model_id` stays `None`.
