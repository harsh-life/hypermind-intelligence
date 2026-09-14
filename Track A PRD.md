# Hypermind : Cybersecurity Research Swarm

  

**Status:** Final execution-ready version. Supersedes all prior Track A drafts.

**Audience:** New ML/research contributors joining Track A. Self-contained — no prior cybersecurity background required to start. You do not need to understand every vulnerability class deeply. You need to understand the architecture, trust the tools, and follow the AI reasoning. This document tells you exactly what each tool does, what the AI does at each step, and what "working correctly" looks like.

**Owner:** Harsh (Product / Strategy), Pushpal (Live Execution Custody until handover protocol clears new members)

**Scope:** Phase 2a. Phase 1 (APK, Gateway, allowlist) is already shipped.

  

---

  

## 1. One-Paragraph Summary

  

Track A is a research track disguised as a revenue engine. The goal: prove that small (1–3B parameter), narrowly-scoped, task-specific models can perform a real, high-stakes technical job — finding a specific class of security vulnerability in live web applications — with near-zero hallucination, by following a fixed, mechanical workflow instead of reasoning freely. Revenue (bug bounty payouts) is real and matters — it funds Track B. The deeper deliverable is the *pattern*: narrow specialist models + neutral judge + human replication gate. Phase 3 reuses this exact pattern to build reliable finance, health, and education agents. You are proving the pattern, not just chasing bugs.

  

---

  

## 2. What You Actually Need To Know About Cybersecurity

  

Not much. Here is the mental model that matters:

  

Bug bounty programmes are companies paying researchers to find security holes in their own products before malicious attackers do. The programmes publish rules — what you're allowed to test, what tools you're allowed to use — and pay cash when you find something real and new that they haven't fixed yet.

  

A vulnerability is just a mistake in how a web application was built. Most mistakes fall into recognisable patterns — the same type of mistake gets made over and over by different developers. Track A's job is to build a pipeline that systematically checks for a specific type of mistake, at scale, across many applications. The tools we use (Subfinder, Nuclei, Garak, etc.) are well-established, widely-used, open-source tools that the security community has built over years to automate exactly this kind of systematic checking.

  

**Your job is not to be a hacker.** Your job is to build the AI architecture that takes the output of these tools, reasons about it correctly, generates a structured proof of the vulnerability, and hands everything to a human reviewer in a form they can verify in under two minutes. The tools do the scanning. The AI does the reasoning. The human does the judgment. You build the AI layer.

  

---

  

## 3. Goals

  

1. Build and prove a 4-stage pipeline against real, in-scope bug bounty targets — in order: IDOR, then SSRF, then Auth Bypass/JWT, then Privilege Escalation.

2. Generate at least two accepted bounty submissions across the first two vulnerability classes before declaring the architecture proven.

3. Document each pipeline precisely enough that adding a new vulnerability class is a configuration change, not a rebuild.

4. Reach a real revenue trend — baseline ₹40k–60k/month, realistic growth to ₹1L+/month once SSRF and Auth Bypass are contributing.

5. Do all of this without a single unauthorized action against an out-of-scope target. This goal overrides every other one, every time.

  

---

  

## 4. Explicit Non-Goals

  

- No auto-submission of any report. A human submits every single finding.

- No fine-tuning until Plan A (few-shot frontier LLM) proves it cannot get there alone AND 2,000+ proprietary validated examples exist.

- No live target access for new contributors until the ramp protocol (Section 9) is cleared.

- No consumer-facing anything — Track A is headless infrastructure only.

- No creative reasoning tasks (business logic flaws, race conditions) — these require understanding the application's intended behavior, which is outside the scope of what a narrow small model does reliably.

  

---

  

## 5. Why These Four Vulnerability Classes, In This Order

  

| Priority | Class | CVSS Range | Typical Payout | Why This Order |

|---|---|---|---|---|

| 1 | **IDOR / BOLA** | Medium–High (5.5–8.5) | $500–$5,000 | Most mechanical workflow. Lowest hallucination risk. Best architecture proof-of-concept. High prevalence means fast iteration feedback. Revenue ceiling is modest — this is the learning pipeline. |

| 2 | **SSRF** | High (7.5–9.0) | $1,000–$50,000+ | Mechanical but higher reasoning than IDOR. Critical upgrade: SSRF in cloud environments that reaches the metadata endpoint often triages as Critical ($10k–50k+). This is Track A's first real revenue driver. |

| 3 | **Auth Bypass / JWT / Broken Auth** | High–Critical (8.0–9.5) | $2,000–$15,000 | Checklist-based (specific token flaws, OAuth misconfigurations). Medium prevalence means less duplicate noise than IDOR. Consistent payout range. Separate pipeline from IDOR/SSRF — different tools, different specialist prompts. |

| 4 | **Privilege Escalation** | High (7.0–9.0) | $1,500–$10,000 | Often chains naturally from IDOR findings. Requires slightly more contextual reasoning than the first three — add this pipeline once the first two are generating consistent, accepted findings. |

  

**Explicitly not targeted:** XSS (Very High prevalence = constant duplicates, $100–3k ceiling doesn't justify a pipeline), Business Logic (requires creative reasoning, wrong fit for small models), Clickjacking/Open Redirect/Rate Limiting (programs mark these informational or no-bounty constantly), RCE (incredible payout but requires multi-step creative reasoning that small models hallucinate badly — human expert domain, not a swarm's, at this stage).

  

---

  

## 6. System Architecture

  

### 6.1 Full Pipeline

  

```

┌──────────────────────────────────┐

│ TARGET SELECTION (Human) │

│ In-scope programme, scope rules │

│ confirmed before anything runs │

└─────────────┬────────────────────┘

▼

┌─────────────────────────────────────────────────────────────────────┐

│ STAGE 0 — SCOPE GATE │

│ Engine: OPA (Open Policy Agent), Rego policy │

│ Input: target domain/IP, programme scope rules │

│ What it does: checks the target is in-scope and automation is │

│ explicitly permitted by the programme's rules │

│ Output: PASS or BLOCK │

│ BLOCK = hard stop. Pipeline halts. No override. No exceptions. │

└────────────────────────────┬────────────────────────────────────────┘

▼ PASS only

┌─────────────────────────────────────────────────────────────────────┐

│ RECON TOOLS (run first, produce raw output) │

│ Subfinder: finds all subdomains of the target │

│ Httpx: probes each subdomain — which ones are actually live? │

│ Katana: crawls the live endpoints — what URLs exist? │

│ Nuclei: runs template-based checks — known patterns │

│ Garak: scans for AI/LLM-specific vulnerabilities (where relevant) │

│ All output flows into the Extractor Node │

└────────────────────────────┬────────────────────────────────────────┘

▼

┌─────────────────────────────────────────────────────────────────────┐

│ EXTRACTOR NODE (Qwen2.5-1.5B via Ollama — always running) │

│ Compresses noisy raw tool output into clean, schema-validated JSON │

│ GBNF grammar constrains output — model cannot hallucinate fields │

│ Feeds clean JSON to Stage 1 │

└────────────────────────────┬────────────────────────────────────────┘

▼

┌─────────────────────────────────────────────────────────────────────┐

│ STAGE 1 — PARALLEL RECON/ANALYSIS │

│ 3 independent 2–3B models run simultaneously, different angles: │

│ Model 1: endpoint enumeration and surface mapping │

│ Model 2: object-reference / parameter pattern detection │

│ Model 3: authentication and session structure analysis │

│ Each outputs a locked ReconOutput JSON (Section 7) │

└────────────────────────────┬────────────────────────────────────────┘

▼

┌─────────────────────────────────────────────────────────────────────┐

│ STAGE 2 — JUDGE & ROUTE │

│ Neutral model. Evaluates the 3 ReconOutputs. │

│ Classifies: IDOR_CANDIDATE / SSRF_CANDIDATE / │

│ AUTH_BYPASS_CANDIDATE / PRIVILEGE_ESC_CANDIDATE / DISCARD │

│ NEVER generates attacks or payloads — evidence evaluation only │

│ Never shares weights or prompts with Stage 3 │

│ Output: JudgeRoutingDecision JSON (Section 7) │

└────────────────────────────┬────────────────────────────────────────┘

▼

┌─────────────────────────────────────────────────────────────────────┐

│ STAGE 3 — SPECIALIST POC GENERATION │

│ Separate specialist per vulnerability class (see Section 7–10) │

│ Plan A (default): frontier LLM + 200–500 class-specific few-shot │

│ Plan B (fallback only): fine-tuned Qwen2.5-1.5B/3B │

│ Must output replication_command field — required, not optional │

│ Output: SpecialistPoCOutput JSON (Section 7) │

└────────────────────────────┬────────────────────────────────────────┘

▼

┌─────────────────────────────────────────────────────────────────────┐

│ STAGE 4 — DEDUPE + HUMAN REVIEW + SUBMISSION │

│ Confidence modifier: public duplicates hard-blocked │

│ Novel findings → HumanReviewPackage handed to Harsh │

│ Harsh runs the replication_command, verifies the finding manually │

│ Report Polisher (Claude/GPT-4): formats the final .md report │

│ — formatting ONLY, never reasoning or judging │

│ Harsh submits the report manually. No auto-submission. Ever. │

└─────────────────────────────────────────────────────────────────────┘

```

  

### 6.2 The Extractor Node — Why It Exists

  

Raw tool output is noisy, long, and inconsistently formatted. Subfinder returns hundreds of subdomains. Nuclei dumps pages of template results. Katana produces crawl trees. If you pass all of that directly to the reasoning models in Stage 1, you blow the context window, inflate API costs, and introduce garbage that corrupts reasoning.

  

The Extractor (Qwen2.5-1.5B-Instruct, running locally via Ollama) compresses each tool's output into a tight, schema-validated JSON object. GBNF grammar (Ollama's built-in output constraint mechanism) makes it structurally impossible for the model to return malformed output — it either matches the schema exactly or the grammar rejects it. Three failures escalate to a human; the pipeline never loops indefinitely.

  

Think of it as a translator: raw tool noise goes in, clean structured intelligence comes out. Every stage above the Extractor operates on clean data, not raw dumps.

  

---

  

## 7. Data Contracts — All JSON Schemas

  

Implement these exactly. Do not improvise field names. Every downstream stage depends on the upstream shape being stable. A schema change is a breaking change — version it.

  

**ExtractorJSON** (GBNF-constrained):

```json

{

"tool_source": "subfinder | httpx | katana | nuclei | garak",

"target": "example.com",

"extracted_entities": [

"api.example.com",

"/api/v1/orders/{id}",

"admin.example.com"

],

"observations": "brief structured summary of what the tool found",

"status": "SUCCESS | FAILED"

}

```

  

**ReconOutput** (Stage 1, one per model):

```json

{

"model_id": "recon-endpoint-enum-v1",

"target": "example.com",

"timestamp": "ISO8601",

"findings": [

{

"endpoint": "/api/v1/orders/{id}",

"observation": "sequential numeric object reference, no visible ownership check on GET",

"candidate_class": "IDOR | SSRF | AUTH_BYPASS | PRIVILEGE_ESC | UNKNOWN",

"confidence": 0.0

}

],

"status": "SUCCESS | PARTIAL | FAILED"

}

```

  

**JudgeRoutingDecision** (Stage 2):

```json

{

"target": "example.com",

"recon_inputs_evaluated": 3,

"classification": "IDOR_CANDIDATE | SSRF_CANDIDATE | AUTH_BYPASS_CANDIDATE | PRIVILEGE_ESC_CANDIDATE | DISCARD",

"reasoning_summary": "string — evidence-based only, no speculative language",

"routed_to": "stage3_idor | stage3_ssrf | stage3_auth_bypass | stage3_priv_esc | none",

"discard_reason": "null unless DISCARD — explain why"

}

```

  

**SpecialistPoCOutput** (Stage 3):

```json

{

"vulnerability_class": "IDOR | SSRF | AUTH_BYPASS | PRIVILEGE_ESC",

"target": "example.com",

"endpoint": "/api/v1/orders/1042",

"poc_steps": [

"Step 1: Create Account A and Account B",

"Step 2: ...",

"Step N: ..."

],

"evidence": {

"request": "full HTTP request string",

"response_expected": "what should have been returned",

"response_actual": "what was actually returned — this is the proof"

},

"replication_command": "curl -X GET https://target/api/v1/orders/1042 -H 'Authorization: Bearer ACCOUNT_B_TOKEN'",

"cloud_metadata_flag": false,

"plan_used": "PlanA_FewShot | PlanB_FineTuned",

"severity_estimate": "Low | Medium | High | Critical",

"confidence": 0.0

}

```

  

**Note on `replication_command`:** required, not optional. A `SpecialistPoCOutput` missing this field is incomplete — send it back to Stage 3. The human reviewer runs this command directly to verify the finding. Under 2 minutes, no reconstruction from prose.

  

**Note on `cloud_metadata_flag`:** for SSRF findings only — set to `true` if the replication command successfully reaches an internal endpoint known to expose cloud credentials (AWS: `169.254.169.254/latest/meta-data/iam/...`, GCP: `metadata.google.internal`, Azure: `169.254.169.254/metadata/instance`). A `true` flag means Harsh reviews this as a potential Critical, not a standard SSRF finding.

  

**HumanReviewPackage** (Stage 4 → human — assembled before any submission):

```json

{

"finding_id": "uuid",

"target": "example.com",

"vulnerability_class": "IDOR",

"replication_command": "...",

"poc_steps": ["..."],

"evidence": {

"request": "...",

"response_expected": "...",

"response_actual": "..."

},

"cloud_metadata_flag": false,

"is_duplicate": false,

"duplicate_check_source": "HackerOne disclosed reports, checked ISO8601",

"severity_estimate": "High",

"reviewer_action": "SUBMIT | DISCARD | NEEDS_MORE_EVIDENCE",

"reviewer_notes": "free text — Harsh fills this in"

}

```

  

`reviewer_action` must be set by a human. The pipeline cannot set it.

  

---

  

## 8. Pipeline 1 — IDOR (Insecure Direct Object Reference)

  

### What IDOR Is (Plain Language)

A web application gives users access to objects — orders, invoices, profile pages, documents — by an ID in the URL or request body (`/api/orders/1042`). An IDOR vulnerability means the application doesn't properly check whether the logged-in user actually owns that object. Account B asks for Account A's order — and gets it. That's the whole vulnerability.

  

### Why It's the First Pipeline

The test is entirely mechanical. You don't need to understand what the application does. You need two accounts and a list of object IDs. Swap the ID, swap the session token, compare responses. A model following a checklist can do this reliably, which makes it the lowest-risk first pipeline to prove the architecture.

  

### What the Tools Do

- **Subfinder + Httpx + Katana:** map the target's surface — subdomains, live endpoints, crawled URL patterns. You're looking for URLs with numeric or sequential IDs in the path or query string (`/orders/1042`, `?invoice_id=88`, `/users/profile/77`).

- **Nuclei:** runs IDOR-specific templates against discovered endpoints — checks for common patterns where object references appear without visible auth checks.

- **Extractor:** compresses all of this into `ExtractorJSON`, listing candidate endpoints with sequential IDs.

  

### What the AI Does

- **Stage 1 (Recon models):** three models each independently look at the Extractor output. Model 1 maps all endpoints with object references. Model 2 checks whether any of those endpoints have visible authentication on GET vs. POST vs. DELETE (a mismatch is a IDOR signal). Model 3 analyses whether the IDs are sequential/guessable vs. UUIDs (sequential = exploitable, UUID = much harder).

- **Stage 2 (Judge):** reviews all three ReconOutputs and decides whether there's a real IDOR candidate worth pursuing. Returns `IDOR_CANDIDATE` with the specific endpoint, or `DISCARD` with a reason.

- **Stage 3 (Specialist):** given a specific endpoint and two account tokens (Account A and Account B — both must be created manually on the real target by the team before the pipeline runs on it), the specialist generates the exact `replication_command`. It replays Account A's object IDs using Account B's session token and checks whether Account B receives Account A's data.

  

### What "Working Correctly" Looks Like

```

Account A token: eyJhbGci... (created manually)

Account B token: eyJhbGci... (created manually)

Account A order ID discovered by Katana crawl: 1042

  

replication_command:

curl -X GET https://api.target.com/v1/orders/1042 \

-H 'Authorization: Bearer ACCOUNT_B_TOKEN' \

-H 'Content-Type: application/json'

  

Expected response (no vulnerability): 403 Forbidden or empty

Actual response (vulnerability confirmed): 200 OK with Account A's order data

```

  

Harsh runs this command. Gets back Account A's data under Account B's token. That's the finding. Everything else (report formatting) is Stage 4.

  

### Plan A vs. Plan B for IDOR

Start with Plan A: a frontier LLM (Claude/GPT-4) given 200–500 few-shot examples of real, disclosed IDOR reports from HackerOne's public disclosure database. These examples teach the model what a valid IDOR PoC looks like without fine-tuning. Plan B (fine-tuning Qwen2.5-1.5B on 2,000+ proprietary IDOR examples) only happens if Plan A consistently fails to generate valid, accepted submissions — which we won't know until Plan A has run on real targets.

  

---

  

## 9. Pipeline 2 — SSRF (Server-Side Request Forgery)

  

### What SSRF Is (Plain Language)

Many web applications make HTTP requests on your behalf — "check if this URL is valid," "fetch the image from this link," "send a webhook to this endpoint." An SSRF vulnerability means the application doesn't properly restrict where it makes those requests. An attacker provides a URL that points somewhere internal — the company's own database, an admin panel, or (in cloud environments) the cloud provider's metadata endpoint which stores credentials. The server fetches it and returns the contents.

  

### Why It's the Second Pipeline and the Primary Revenue Driver

Two reasons:

  

1. SSRF in a cloud-hosted application that reaches the metadata endpoint (`169.254.169.254` on AWS, for example) can expose IAM credentials — effectively giving access to the company's entire cloud infrastructure. This is a Critical severity finding ($10k–50k+), not a standard SSRF finding ($1k–5k). The same underlying vulnerability type, dramatically different impact based on what it reaches. The `cloud_metadata_flag` field in `SpecialistPoCOutput` exists specifically to flag this so Harsh reviews it as a Critical.

2. SSRF is still mechanical: find URL/webhook parameters → probe internal endpoints → check responses. It's a checklist, not creative reasoning.

  

### What the Tools Do

- **Katana:** crawls for any parameter that accepts a URL (common patterns: `url=`, `target=`, `webhook=`, `fetch=`, `redirect=`, `image_url=`, `src=`, `path=`). These are your injection points.

- **Nuclei:** runs SSRF-specific templates — probes the discovered parameters with payloads pointing to known internal addresses (localhost, 127.0.0.1, internal subnet ranges, cloud metadata IPs).

- **Httpx:** validates which probe responses actually returned content (blind SSRF vs. full-response SSRF — the latter is higher value and easier to document).

- **Extractor:** compresses all of this into ExtractorJSON with a list of candidate URL parameters and the responses to initial probes.

  

### What the AI Does

- **Stage 1:** Model 1 maps all URL-accepting parameters. Model 2 checks for cloud infrastructure indicators (AWS instance metadata, GCP metadata, Azure IMDS patterns in error messages or response headers). Model 3 assesses whether the application uses internal microservices (common API gateway patterns, service mesh headers) — these are high-value SSRF targets because they reach internal services.

- **Stage 2:** Classifies `SSRF_CANDIDATE` and notes whether cloud metadata access looks possible (feeds directly into `cloud_metadata_flag` logic in Stage 3).

- **Stage 3:** Generates the replication command probing the specific parameter with the internal/metadata endpoint. If `cloud_metadata_flag` is true, the replication command must include a secondary probe of the IAM/credentials endpoint specifically.

  

### What "Working Correctly" Looks Like

  

Standard SSRF finding:

```

replication_command:

curl -X POST https://api.target.com/v1/fetch \

-H 'Authorization: Bearer YOUR_TOKEN' \

-d '{"url": "http://127.0.0.1:8080/admin"}'

  

Expected: blocked or error

Actual: 200 OK with internal admin panel content

severity_estimate: High

cloud_metadata_flag: false

```

  

Cloud metadata SSRF (Critical-tier finding):

```

replication_command:

curl -X POST https://api.target.com/v1/fetch \

-H 'Authorization: Bearer YOUR_TOKEN' \

-d '{"url": "http://169.254.169.254/latest/meta-data/iam/security-credentials/"}'

  

Expected: blocked

Actual: 200 OK with IAM role name returned

severity_estimate: Critical

cloud_metadata_flag: true

  

HARSH REVIEWS THIS AS CRITICAL BEFORE ANYTHING ELSE. DO NOT SUBMIT WITHOUT

VERBAL CONFIRMATION FROM HARSH THAT HE HAS REPLICATED THE METADATA ACCESS.

```

  

---

  

## 10. Pipeline 3 — Auth Bypass / JWT / Broken Auth

  

### What Auth Bypass Is (Plain Language)

Authentication is how a web application proves you are who you say you are — typically a session token or a JWT (JSON Web Token). Broken authentication means the application's implementation of this has specific, exploitable flaws. These flaws are not creative or unique to each application — they are well-documented patterns that developers repeatedly make when implementing authentication from scratch.

  

**JWT flaws specifically:** a JWT is a three-part token (header.payload.signature). The signature is supposed to prove the token hasn't been tampered with. Common flaws: the application accepts `"alg": "none"` (no signature at all — attacker just removes it), the application uses a weak or guessable secret for HMAC signing, or the application doesn't validate the signature at all. None of these require creative reasoning to test — they're a checklist.

  

**OAuth misconfigurations:** OAuth is the "Login with Google/GitHub" flow. Common flaws: state parameter not validated (enables CSRF on the OAuth flow), redirect_uri not strictly validated (enables token theft), implicit flow tokens leaking in referrer headers.

  

**Session fixation:** the application doesn't issue a new session token after login — a pre-login token remains valid post-login, which means an attacker who knows your pre-login token can hijack your session after you authenticate.

  

### What the Tools Do

- **Katana:** discovers all authentication endpoints (`/login`, `/oauth/authorize`, `/api/token`, `/refresh`, `/logout`), JWT-protected endpoints, and any redirect parameters in OAuth flows.

- **Nuclei:** runs JWT-specific templates — probes for `alg:none` acceptance, checks for common weak secrets (using a local wordlist from PayloadsAllTheThings), checks if refresh tokens are properly invalidated on logout.

- **A JWT manipulation library** (run as a script, not an interactive tool): generates modified tokens with `alg:none`, modified claims (escalating `role: user` to `role: admin`), and expired-timestamp bypasses. This is a Python script that wraps PyJWT — Pushpal builds this as part of the pipeline infrastructure.

- **Extractor:** compresses results into ExtractorJSON with candidate endpoints and specific token flaws observed.

  

### What the AI Does

- **Stage 1:** Model 1 maps all auth endpoints and token usage patterns. Model 2 checks whether JWTs use `alg:none` or symmetric vs. asymmetric algorithms (symmetric = potentially crackable if weak secret). Model 3 analyses OAuth flow parameters for common misconfigurations.

- **Stage 2:** Classifies `AUTH_BYPASS_CANDIDATE` and specifies which sub-type was detected (JWT_ALG_NONE / JWT_WEAK_SECRET / OAUTH_REDIRECT_URI / SESSION_FIXATION).

- **Stage 3:** Generates a replication command specific to the sub-type. For JWT flaws, this includes the modified token itself. For OAuth issues, it includes the exact modified authorization URL.

  

### What "Working Correctly" Looks Like

  

JWT `alg:none` bypass:

```

replication_command:

# Step 1: Take your valid JWT and decode the payload

# Step 2: Modify payload (e.g., change "role":"user" to "role":"admin")

# Step 3: Re-encode with alg:none (no signature)

# Modified token: eyJhbGciOiJub25lIn0.eyJ1c2VyX2lkIjoiMTIzIiwicm9sZSI6ImFkbWluIn0.

curl -X GET https://api.target.com/v1/admin/users \

-H 'Authorization: Bearer eyJhbGciOiJub25lIn0.eyJ1c2VyX2lkIjoiMTIzIiwicm9sZSI6ImFkbWluIn0.'

  

Expected: 401 Unauthorized (token has no signature)

Actual: 200 OK with admin user list

severity_estimate: Critical

```

  

---

  

## 11. Pipeline 4 — Privilege Escalation

  

### What It Is (Plain Language)

Privilege escalation means a user with a lower level of access doing something that only a higher-privilege user should be able to do. *Horizontal* escalation: Account A accessing Account B's data (this overlaps significantly with IDOR). *Vertical* escalation: a regular user performing admin actions. Track A targets vertical privilege escalation specifically as a separate pipeline — an endpoint that's supposed to require admin privileges but doesn't properly verify the role claim.

  

### When This Pipeline Gets Built

**After IDOR and SSRF are generating consistent, accepted findings.** Privilege escalation often chains naturally from IDOR (you find an IDOR, realise the object reference also controls permissions, and escalate to admin). Don't build this pipeline in parallel with Pipelines 1–2. Sequence it for when the architecture is proven and the team has bandwidth.

  

### What It Will Look Like

The same 4-stage structure as IDOR and SSRF. The specialist model for this class needs different few-shot examples (role manipulation, parameter tampering for privilege boundaries, GraphQL introspection for hidden admin mutations). The replication command will typically involve modifying a role/permission parameter in a request and verifying the response grants elevated access.

  

---

  

## 12. Infrastructure

  

- **Host:** headless Ubuntu VM (developer's machine or a low-cost VPS), behind a VPN. Move to a real VPS once bounty revenue is flowing — the laptop-hosted approach is fine for Phase 2a's early weeks, not permanently.

- **Isolation:** Docker, strict flags on every container:

- `--memory 512m` — cap memory per container

- `--cpus 0.5` — cap CPU per container

- `--network=none` for the Extractor and Stage 1–2 models (they don't need internet)

- `--network host` (temporarily) only for Recon tools against confirmed in-scope targets, removed immediately after

- **Scheduler:** APScheduler, 2 AM daily scan trigger against the current confirmed in-scope target list. One function call to register a job — don't build a cron wrapper.

- **Mem0 integration:** bounty findings written to Mem0 via the `/store_memory` Gateway endpoint (built in Phase 1). Use the config in Appendix A — do not let Mem0 default to OpenAI.

- **Routing:** LiteLLM proxy handles all cloud LLM calls — free-tier-first (DeepSeek/Qwen), paid (Claude/GPT-4) as reserved fallback for Stage 3 and the Report Polisher only.

  

**Live verification rule:** any tool not already in this document must be run against a real test target and confirmed working before it's added to the pipeline. No exceptions.

  

---

  

## 13. AI Model Allocation

  

| Role | Model | Notes |

|---|---|---|

| Extractor | Qwen2.5-1.5B-Instruct (Ollama, local) | GBNF-constrained. Compression only, not reasoning. |

| Recon models (×3, Stage 1) | 2–3B general-purpose models | Run in parallel. Different system prompts, different analysis angles. |

| Judge (Stage 2) | Neutral evaluator — model TBD, must not share weights/prompts with Stage 3 | Classification only. No payload generation. |

| Specialist, Plan A (Stage 3) | Frontier LLM (Claude/GPT-4) + class-specific few-shot examples | Default. Costs money. Cap usage via LiteLLM. |

| Specialist, Plan B (Stage 3) | Fine-tuned Qwen2.5-1.5B or 3B per vulnerability class | Fallback only, gated behind 2,000+ proprietary examples + Plan A proven insufficient. |

| Report Polisher (Stage 4) | High-parameter model (Claude/GPT-4) | Formatting only. Never reasoning. Separate call, separate system prompt. |

  

**Bulk / low-risk work** (test harness code, mock data, documentation): DeepSeek/Qwen APIs, free tier first.

**High-risk work** (Stage 0–4 pipeline code, OPA policy, anything touching live execution): Claude Code, mandatory human review before any merge touching this code runs on a real device or target.

  

---

  

## 14. Team & Ramp Protocol

  

### Why This Protocol Exists

Stage 0–4 touches live external systems. An out-of-scope scan is a violation of the bug bounty programme's terms — accounts get banned, and in some jurisdictions, unauthorized scanning has legal consequences. The ramp protocol is not a formality. It is the minimum time required to prove you understand the safety culture before you get access to the thing that can cause real damage.

  

### The Protocol

| Stage | Duration | What You Do | Access |

|---|---|---|---|

| 1 | Week 1 | Read documentation. Read existing pipeline code. Contribute to non-critical work: test harnesses, mock data generation, model architecture design on historical/public disclosed reports. | No live execution code. |

| 2 | Weeks 2–3 | Shadow Pushpal or Harsh on live Stage 0–4 operations. Watch every decision get made. Ask questions. Do not touch execution. | Observer only. |

| 3 | Week 4 | Run 3 independent test cycles against a sandbox target (a deliberately vulnerable app like DVWA or Juice Shop, hosted locally or on a disposable VPS). Zero scope gate violations, zero allowlist violations. | Sandbox only. |

| 4 | Days 30–60 | Pushpal and Harsh co-sign every merge touching Stage 0–4. You cannot merge unilaterally. | Live, co-signed. |

| 5 | Month 3+ | Founders shift focus to Phase 3. You operate independently. | Full. |

  

**Your model/architecture research is not gated by this.** The Extractor build, Stage 1 prompt architecture, fine-tuning experiments on historical data — all of this starts Week 1. The ramp applies specifically to live execution against real targets.

  

---

  

## 15. Budget

  

| Item | Cost | Funded by |

|---|---|---|

| Phase 2a build, worst case | ~$330 / ₹27,500 (data cleaning $50–100, GPU $60–90, CA consultation $120) | Personal or first bounty payout |

| Ongoing infra (VPS, Docker) | ~$10–20/month | Bounty revenue once flowing |

| Fine-tuning, Plan B — IDOR pipeline (if triggered) | ~$20–30 (RunPod/Modal, Qwen2.5-1.5B or 3B) | First bounty income only. Never fronted. |

| Fine-tuning, Plan B — SSRF pipeline (if triggered) | ~$20–30 | Same gate as IDOR Plan B. |

| Dataset labeling (Plan B dependency) | ~$1,500–3,000 for 2,000 examples — get real quotes, this is an estimate | Bounty income only |

| LiteLLM Stage 3 Plan A (frontier LLM calls) | Capped by LiteLLM budget config | Check weekly. Hard cap enforced in code. |

  

---

  

## 16. Open Decisions

  

1. Judge model identity (Stage 2) — must be confirmed distinct from Stage 3 specialist. Not yet locked.

2. VPS vs. laptop hosting — revisit once first bounty revenue arrives.

3. Which specific bounty programmes to target first — requires live research against current programme scope pages, not a decision made in this document.

4. Dataset sourcing for Plan B — HackerOne's public disclosure archive is the primary source, but volume per class needs a real count before Plan B is even on the table.

  

---

  

## 17. Risk Register

  

| Priority | Risk | Impact | Mitigation | Owner |

|---|---|---|---|---|

| 1 | Out-of-scope action executed | CRITICAL — legal + platform ban | OPA Stage 0 hard block. No override. Human target selection every time. | Execution custody holder (Section 14) |

| 2 | New contributor touches live execution before ramp clears | CRITICAL | Section 14 enforced literally. No "trusted-seeming" shortcuts. | Pushpal + Harsh |

| 3 | Judge contaminated by Specialist bias | HIGH — neutral evaluation fails | Strict model + prompt separation between Stage 2 and Stage 3. Never shared. | Pipeline architect |

| 4 | SSRF cloud_metadata_flag finding submitted without Harsh verbal confirmation | CRITICAL — this is a potential Critical-tier finding, review cannot be skipped | `cloud_metadata_flag: true` → Harsh reviews in person before submission, not just in the queue | Harsh |

| 5 | Extractor produces malformed JSON | HIGH — corrupts everything downstream | GBNF grammar constraint. 3-strike human escalation. | Extractor owner |

| 6 | Fine-tuning triggered before gate conditions met | MEDIUM — wasted cost | Hard gate: 2,000+ examples AND Plan A proven insufficient. Harsh sign-off required. | Harsh |

| 7 | Duplicate finding submitted | MEDIUM — wastes goodwill with programme | Stage 4 dedupe check against public disclosure sources before HumanReviewPackage is assembled. | Stage 4 owner |

| 8 | Unverified tool added to stack | MEDIUM — unknown failure modes in production | Live-verification rule. No exceptions. | Whoever proposes the tool |

| 9 | Pipeline 3 (Auth Bypass) built before Pipelines 1–2 proven | MEDIUM — splits attention before architecture is validated | Sequential pipeline build. Pipeline 3 does not start until Pipeline 1 has at least 2 accepted findings. | Harsh |

  

---

  

## 18. Implementation Timeline (First 10 Weeks)

  

| Week | Focus |

|---|---|

| 1 | Onboarding (Section 14, Stage 1). Extractor: GBNF schema design, Ollama setup. Study 20–30 public IDOR disclosures from HackerOne (read the reports, understand the pattern). |

| 2–3 | Shadow live operations. Stage 1 Recon model prompt architecture designed against historical/public data. Sandbox environment (DVWA or Juice Shop) set up locally. |

| 4 | Stage 1 built and tested against sandbox. Stage 2 Judge logic built — IDOR classification only for now. All tests against sandbox. Section 14 Stage 3 clearance cycle. |

| 5 | Stage 3 IDOR Specialist built. Plan A: frontier LLM + first batch of few-shot examples loaded. `replication_command` generation tested on known-vulnerable sandbox endpoints. |

| 6 | Stage 4 dedupe + HumanReviewPackage assembly. Full pipeline integration test on sandbox. Harsh runs `replication_command` on a known sandbox finding — does he verify it under 2 minutes? |

| 7 | First real in-scope target selected (human decision). Full pipeline run under Harsh/Pushpal co-sign. Stage 0 Scope Gate confirmed working on real target. |

| 8 | First real IDOR submission attempt. Outcome (accepted / rejected / duplicate) informs all next decisions. |

| 9 | SSRF pipeline build begins. Stage 2 updated to route SSRF_CANDIDATE. Stage 3 SSRF Specialist built. `cloud_metadata_flag` logic implemented. |

| 10 | SSRF pipeline integration test. Both pipelines running in parallel on separate in-scope targets. |

  

---

  

## 19. Appendix A — Mem0 Configuration (Required)

  

Mem0 defaults to OpenAI if not explicitly configured. This will silently hit the API and blow the budget. Every service in Track A that writes to memory (the Extractor's output storage, Stage 4's finding logging) must import from this shared config file (`mem0_config.py`).

  

```python

import os

from mem0 import AsyncMemory

from mem0.configs.base import MemoryConfig

  

config = MemoryConfig(

llm={

"provider": "litellm",

"config": {

"model": "deepseek/deepseek-chat",

"api_key": os.getenv("DEEPSEEK_API_KEY")

}

},

embedder={

"provider": "huggingface",

"config": {

"model": "BAAI/bge-small-en-v1.5"

}

},

vector_store={

"provider": "chroma",

"config": {

"collection_name": "hypermind_memories",

"path": "./mem0_storage"

}

}

)

  

memory = AsyncMemory(config=config)

```

  

Verified against current Mem0 docs. `AsyncMemory`, `MemoryConfig`, and all three providers confirmed real and correctly structured.

  

**Gateway note:** Track A and Track B endpoints run as modular FastAPI routers within the same Phase 1 Gateway instance — not separate deployments. Splitting into microservices is overkill for Phase 2a/2b; revisit only if Phase 3 load demands it.

  

---

  

## 20. Glossary

  

- **IDOR / BOLA:** Broken Object Level Authorization — accessing another user's data by manipulating an object reference (e.g., changing an order ID in a URL from 1042 to 1043 and getting back someone else's order).

- **SSRF:** Server-Side Request Forgery — tricking a server into making requests to internal or unintended destinations. Critical when it reaches cloud provider metadata endpoints.

- **Cloud metadata endpoint:** a special internal IP address (`169.254.169.254` on AWS/Azure, `metadata.google.internal` on GCP) that cloud-hosted servers can query to retrieve their own IAM credentials. If an SSRF finding reaches this, it's likely Critical severity.

- **JWT:** JSON Web Token — a three-part encoded token (header.payload.signature) used for authentication. Common flaws: `alg:none` (no signature), weak secret, unvalidated claims.

- **Auth Bypass:** any mechanism by which an attacker proves they are someone they are not, or gains privileges they shouldn't have, through a flaw in the application's authentication implementation.

- **Privilege Escalation:** gaining higher privileges than your account is supposed to have. Vertical: regular user → admin. Horizontal: Account A → Account B's data (overlaps with IDOR).

- **GBNF:** grammar format used by llama.cpp/Ollama to constrain model output to a strict, parseable schema. Prevents hallucinated field names from corrupting the pipeline.

- **OPA (Open Policy Agent):** declarative policy engine using Rego. Used here exclusively for Stage 0's Scope Gate — nowhere else in Track A.

- **Plan A / Plan B:** few-shot frontier-LLM prompting (default, no training cost) vs. fine-tuning a small Qwen model (fallback — gated on proven necessity and 2,000+ validated examples).

- **Duplicate:** a vulnerability finding that has already been submitted and disclosed by another researcher. Hard-blocked at Stage 4 — submitting a known duplicate damages the programme relationship and wastes everyone's time.

- **replication_command:** a copy-pasteable shell command (typically `curl`) in the `SpecialistPoCOutput` that lets the human reviewer verify the finding directly in under 2 minutes. Required in every finding. Not optional.