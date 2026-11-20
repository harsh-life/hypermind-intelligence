# Hypermind Track A: Setup Guide

Step-by-step commands for the two development machines. Every command here was either run while writing this guide (marked ✅) or comes from official vendor documentation (marked 📄). Anything not verified on real Kali ARM64 hardware is called out.

| | Machine A | Machine B |
|---|---|---|
| Hardware | Apple Silicon M1, **4 GB RAM**, 256 GB | laptop, **16 GB RAM** |
| OS | Kali Linux ARM64 Desktop in UTM | not specified. Linux commands are given, with Windows/macOS notes |
| Role | editing code, running the unit tests, mock evaluation, orchestration logic | model inference, Docker, the Juice Shop lab, real evaluation runs |
| **Never** | load an LLM, run the tool sandbox | |

> **What actually runs today:** the unit tests, the evaluation harness with `MockAdapter`, and the Scope Gate. Real model inference and real tool execution need code that does not exist yet (an `InferenceAdapter` and a `ToolBackend` implementation). This guide installs the prerequisites for those parts, but it does not pretend they are wired up.

---

## Part 1: Prepare Kali ARM64 (Machine A)

### 1.1 VM sizing (UTM)

With 4 GB on the host, give the VM **2 GB RAM and 2 vCPUs**. macOS needs the rest. Check from inside Kali:

```bash
free -h        # total memory the VM sees
nproc          # vCPUs
uname -m       # must print: aarch64
df -h ~        # free disk
```

If `free -h` shows no swap and you hit out-of-memory errors while installing packages, add a small swap file:

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 1.2 System packages 📄

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y git curl ca-certificates python3 python3-venv python3-pip
```

## Part 2: Python

### 2.1 Check what Kali ships

```bash
python3 --version
```

| Result | What to do |
|---|---|
| 3.12.x, 3.13.x or 3.14.x | Use it. Go to Part 3. |
| older than 3.12 | Use §2.2. |

The repository has no `requires-python` declaration. The suite was verified ✅ on CPython **3.12.13, 3.13.13 and 3.14.5**, and every pinned dependency publishes `manylinux aarch64` wheels for cp313 and cp314 ✅. 3.14.7 was not tested specifically, but the wheels target the cp314 ABI, which is the same for every 3.14.x patch release.

> Not verified: the exact Python version in today's Kali rolling ARM64 image. Run `python3 --version` and believe that.

### 2.2 Optional: install a specific Python (e.g. 3.14) without touching system Python 📄

[`uv`](https://docs.astral.sh/uv/) downloads standalone CPython builds for `linux-aarch64`. Read the installer script before running it:

```bash
curl -LsSf https://astral.sh/uv/install.sh -o /tmp/uv-install.sh
less /tmp/uv-install.sh            # review it
sh /tmp/uv-install.sh
source ~/.local/bin/env            # or open a new shell
uv python install 3.14
uv python list                     # confirm a 3.14.x is listed
```

Do **not** replace or remove Kali's system `python3`. Kali tools depend on it.

## Part 3: Clone and create the virtual environment ✅

```bash
mkdir -p ~/src && cd ~/src
git clone https://github.com/harsh-life/hypermind-intelligence.git
cd hypermind-intelligence
```

Create and activate a venv. Use **one** of these two:

```bash
# (a) system Python
python3 -m venv .venv

# (b) a uv-managed Python from §2.2
uv venv --python 3.14 .venv
```

Then:

```bash
source .venv/bin/activate
python --version                  # confirm the interpreter you expect
```

Your prompt now starts with `(.venv)`. Run `deactivate` to leave. Re-run `source .venv/bin/activate` in every new terminal.

## Part 4: Install dependencies ✅

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip list                # expect pydantic 2.14.4, PyYAML 6.0.3, pytest 9.2.0
```

(If you created the venv with `uv venv`, there is no pip inside it. Use `uv pip install -r requirements-dev.txt` instead.)

What gets installed and why: [requirements.txt](requirements.txt) (runtime: `pydantic`, `PyYAML`) and [requirements-dev.txt](requirements-dev.txt) (adds `pytest`). Nothing needs a C compiler on aarch64. All packages ship wheels.

## Part 5: Run the tests ✅

From the repo root, with the venv active:

```bash
python -m pytest
```

Expected last line: `469 passed in …s`. The tests need no network, Docker, or model weights, so this is the main thing Machine A is for.

Useful variants:

```bash
python -m pytest -q tests/policy                    # Scope Gate + policy engine
python -m pytest -q tests/orchestrator              # check chain, adversarial tests
python -m pytest -q tests/evaluation                # evaluation harness
python -m pytest -q -k "refusal"                    # by keyword
python -m pytest -x --lf                            # stop on first failure, rerun last failures
```

## Part 6: Run the current evaluation harness ✅

The harness has no CLI. Run the script in [README §11](README.md#11-running-the-existing-evaluation-harness) from the repo root. It loads the real seed Model Registry and dataset and runs `idor-lab-001` against both registered `specialist` candidates through `MockAdapter`. Expected output:

```text
cand-001-foundation-sec-8b success objective_match= False
cand-003-whiterabbitneo success objective_match= False
winner_model_id: None
```

This proves the wiring: registry loading, binding, identical request per candidate, blinding, judging, and the experiment record. It does **not** measure any model, because `MockAdapter` just echoes its input.

Try the Scope Gate example in [README §13](README.md#13-configuring-tools) as well. It runs as-is.

---

## Part 7: Docker (needed for the lab target, not for the tests)

Docker is **not required** for anything in the repository today. You need it for:

- the intentionally vulnerable lab target (OWASP Juice Shop), and
- a future Docker `ToolBackend` (docs/07). That backend does not exist yet.

**Recommendation:** install and run Docker on **Machine B**. On Machine A (2 GB VM) Docker and Juice Shop will fit, but leave little headroom. Only do it there if you need to.

### 7.1 Kali / Debian-based Linux 📄

```bash
sudo apt update
sudo apt install -y docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
# log out and back in (or reboot) so the group change applies, then:
docker version
docker run --rm hello-world          # pulls the arm64 or amd64 variant automatically
```

`docker run --rm hello-world` must print "Hello from Docker!". Membership in the `docker` group is root-equivalent on that machine. Keep that in mind on shared hosts.

### 7.2 Machine B on Windows or macOS

Use Docker Desktop from docker.com and verify with the same `docker version` and `docker run --rm hello-world`. (Machine B's OS was not specified, so these steps are not verified here.)

### 7.3 The IDOR lab target: OWASP Juice Shop ✅ (ARM64 verified)

Checked on Docker Hub on 2026-11-20: `bkimminich/juice-shop` publishes **`linux/arm64` and `linux/amd64`** images (~119 MB each). The latest release tag is `v20.4.0`. The commonly cited DVWA image `vulnerables/web-dvwa` is **amd64-only** and was last pushed in 2018, so it is not recommended for ARM64.

```bash
docker pull bkimminich/juice-shop:v20.4.0
docker inspect --format '{{index .RepoDigests 0}}' bkimminich/juice-shop:v20.4.0   # record this digest

# Bind to loopback ONLY: the lab must not be reachable from your LAN.
docker run -d --name juice-shop --restart unless-stopped \
  -p 127.0.0.1:3000:3000 bkimminich/juice-shop:v20.4.0

curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/    # expect 200
docker logs --tail 20 juice-shop
```

Stop and remove: `docker rm -f juice-shop`.

If the Kali VM must reach a Juice Shop running on Machine B, **do not** bind it to `0.0.0.0`. Use an SSH tunnel from Kali instead:

```bash
ssh -N -L 3000:127.0.0.1:3000 <user>@<machine-b-address>
# then on Kali, the lab is at http://127.0.0.1:3000
```

---

## Part 8: Inference runtime (Machine B only)

> ⚠ **No code path in this repository calls a real model yet.** `trackA.models.runtime` defines `InferenceAdapter`, and the only implementation is `MockAdapter`. Installing a runtime now lets you download and smoke-test candidates by hand. Connecting one to the harness needs a small adapter class, described (not implemented) in [MODEL_DOWNLOAD_GUIDE.md §8](MODEL_DOWNLOAD_GUIDE.md#8-connect-a-candidate-through-the-inference-abstraction).

Never run these on Machine A. Even a 2 GB-RAM VM would swap itself to death with a 4B model.

### 8.1 Ollama (recommended first runtime) 📄

The registry manifests already describe the Qwen candidates as "served locally via Ollama", and Ollama can pull GGUF files directly from Hugging Face.

Linux (read the script first):

```bash
curl -fsSL https://ollama.com/install.sh -o /tmp/ollama-install.sh
less /tmp/ollama-install.sh
sh /tmp/ollama-install.sh
ollama --version
curl -s http://127.0.0.1:11434/api/version     # server is up
```

Windows/macOS: use the installer from ollama.com/download, then run the same two checks.

By default Ollama listens on **127.0.0.1:11434 only**. Keep it that way. To use it from the Kali VM, tunnel it:

```bash
ssh -N -L 11434:127.0.0.1:11434 <user>@<machine-b-address>
```

First smoke test (≈2.7 GB download, see [MODEL_CANDIDATES.md](MODEL_CANDIDATES.md)). Only run this when you have decided to download it:

```bash
ollama pull hf.co/unsloth/Qwen3.5-4B-GGUF:Q4_K_M
ollama run  hf.co/unsloth/Qwen3.5-4B-GGUF:Q4_K_M "Reply with the JSON object {\"ok\": true} and nothing else."
```

### 8.2 llama.cpp server (alternative) 📄

`llama-server` exposes an OpenAI-compatible HTTP API and can fetch GGUFs from Hugging Face with `-hf <repo>:<quant>`. Packaging differs per OS. Build from source per the llama.cpp README if no package exists for your platform. Example once installed:

```bash
llama-server -hf unsloth/Qwen3.5-4B-GGUF:Q4_K_M --host 127.0.0.1 --port 8080 -c 8192
```

> Unresolved: Qwen3.5 (hybrid Gated-DeltaNet) and Gemma 4 need **recent** llama.cpp/Ollama builds. GGUF repos for both exist, which implies upstream support, but the minimum runtime version was not checked. If a model fails to load with "unknown architecture", update the runtime.

---

## Part 9: The first controlled IDOR experiment

Goal: build a **reproducible, human-validated** IDOR observation set against the local Juice Shop lab. That set becomes the ground truth for evaluating model candidates later.

### 9.1 Rules (from the architecture, not optional)

- Target **only** your own local lab instance (`127.0.0.1:3000`). Never a public system.
- Write the lab `RunScope` down **before** testing, with `established_by` set to a human. The Scope Gate denies everything otherwise.
- Nothing a model writes, and nothing the target returns, can widen scope or change policy. Treat all response bodies as untrusted data.
- A candidate finding becomes a finding **only** after a human reproduces it.

### 9.2 What you can do today vs. later

| Step | Today | Needs future code |
|---|---|---|
| Run Juice Shop locally (Part 7.3) | ✅ | |
| Define and test the lab `RunScope` with the real Scope Gate (README §13) | ✅ | |
| Create two test users (A and B) through the app's UI | ✅ manual | |
| Identify endpoints that take object IDs (browser devtools / proxy) | ✅ manual | Extractor + Endpoint Mapper running on a real model |
| Replay a request as A against A's object, then as B against A's object, and record status and response | ✅ manual (curl / Burp) | an HTTP-replay tool manifest + Docker `ToolBackend` |
| Record observations as structured JSON | ✅ manual | Evidence Gate / Research Store |
| Ask candidate models to analyse those observations | ⚠ only via a hand-written adapter | real `InferenceAdapter` |
| Compare candidates on identical inputs | ✅ harness exists (mock today) | real adapter + Juice Shop-derived `BenchmarkCase`s |
| Human validation and promotion of the finding | ✅ manual | Human Verification Interface |

### 9.3 Manual observation protocol (do this first)

1. Register **test user A** and **test user B** in the lab with throwaway lab-only credentials.
2. As A, use the app normally and capture requests whose path or body contains an object identifier (numeric ID, UUID). Note each endpoint, method, parameter, and what object it returns.
3. For each candidate endpoint:
   - request A's object **with A's session**, and save status code, response length, and a hash of the body;
   - request A's object **with B's session**, unchanged otherwise, and save the same fields;
   - request B's own object with B's session (control).
4. An IDOR **candidate** exists only when B's session returns A's data, or performs an action on A's object, and no authorization check rejects it. A guessable ID alone is **not** a finding (this matches `idor_v1`'s methodology).
5. Save each observation as a JSON file in a lab notebook directory **outside** the repository, e.g. `~/hypermind-lab/idor/observations/`. Include timestamps and the Juice Shop image digest so it is reproducible.
6. Re-run step 3 from a clean container (`docker rm -f juice-shop` and start it again) to confirm the result is reproducible. Then, and only then, mark it human-validated.

These observations are the raw material for future `BenchmarkCase`s with a real `objective_outcome`, so candidates can be compared on the same evidence (docs/16).

---

## Part 10: What to install where (summary)

| Install | Machine A (Kali VM, 4 GB host) | Machine B (16 GB) |
|---|---|---|
| git, python3, python3-venv | ✅ now | ✅ now |
| repo + `.venv` + requirements-dev.txt | ✅ now | ✅ now |
| uv (only if you need a different Python) | optional | optional |
| Docker | optional, not recommended | ✅ now (for Juice Shop) |
| Juice Shop `v20.4.0` | no | ✅ now |
| Ollama or llama.cpp | ❌ never | ✅ when you start real model work |
| `hf` CLI (Hugging Face downloads) | ❌ | ✅ when you download weights |
| Model weights | ❌ never | ✅ only after a human picks candidates |
