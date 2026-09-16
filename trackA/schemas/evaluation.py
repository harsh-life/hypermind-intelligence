"""Model-evaluation / competition schemas. Context 4.

No document in docs/01-18 names these types literally — docs/16_EVALUATION_
BENCHMARKING.md (per OD-27, docs/13_OPEN_DECISIONS.md, [LOCKED]) describes
the *method* ("trajectory-based ... controlled starting conditions ...
the actual trajectory, not just the final output shape") in prose, and
docs/03_DATA_SCHEMAS_README.md §3 already canonicalises the *aggregate*
research-tier records this method feeds (`ExperimentRecord`,
`ModelEvaluationRecord`, `DatasetRecord` — all in `trackA.schemas.research`,
reused here unmodified, not duplicated). What docs/03 does not define is a
schema for the trajectory *itself* — the step-by-step transcript of one
candidate attempting one controlled case — or for the controlled case/task
definition it attempts. Per the Context-4 task brief §25's own escalation
path (inspect docs -> inspect OD-13 -> inspect existing schemas -> confirm
Context 4 owns the gap -> smallest compatible extension -> tests -> report):
this is a genuine gap Context 4 owns (its explicit deliverable is "the
controlled evaluation system that compares model candidates against real
task trajectories"), so five new, purely additive schemas are introduced
here. Nothing in `trackA/schemas/research.py`, `common.py`, `judge.py`, or
any other existing module is modified.

Design choices, made explicit rather than silently assumed:

    Provenance reuse, not a new provenance type.
        `EvaluationTrajectory`/`EvaluationJudgePackage`/
        `EvaluationJudgeVerdict` all embed the existing pipeline
        `Provenance` (docs/03 §1.1), the same common type
        `ExperimentRecord`/`ModelEvaluationRecord`/`DatasetRecord` already
        use (see tests/schemas/test_research.py's existing
        `PipelineStage.JUDGE` convention for offline benchmarking
        records). `Provenance.stage` already has dedicated values for
        every role a candidate can be benchmarked in (EXTRACTOR, WORKER,
        JUDGE, SPECIALIST, REPORT_POLISHER — docs/02_COMPONENT_SPECS.md's
        component index), so no enum extension is needed either. A
        candidate's own model_id/model_version go in
        `EvaluationTrajectory.provenance` per docs/10_RESEARCH_DATA_
        PIPELINE.md §4 (Q8: "you can later ask how did the Judge perform
        when it was judge-model-a v1 versus v2 only because every
        judgment carries which model produced it" — the same reasoning
        applies to a benchmarked candidate's trajectory).
        `EvaluationJudgePackage` is assembled by deterministic harness
        code, not a model call, so its `provenance` sets neither
        model_id nor tool_id (mirroring the Evidence Gate's own
        documented convention, docs/03 §1.1). `BenchmarkCase` is static,
        human/config-authored test data (like a Tool/Worker/Skill
        manifest), so it uses `ManifestProvenance` (OD-15, [LOCKED]),
        not the pipeline `Provenance` type — same rationale as every
        other manifest in this codebase.

    Judge-package identity blinding is structural, not a validated rule.
        `EvaluationJudgePackage` has no `candidate_id`, `model_identity`,
        `runtime_backend`, or `runtime_config` field at all — "do not
        leak unnecessary candidate identity into the evaluation package"
        (Context-4 task brief §3/§8) is enforced by omission, the same
        pattern already used for the Skill Registry's Judge-unreachability
        (docs/02_COMPONENT_SPECS.md §3: "no interface exists ... enforced
        by omission, not just policy"). `contains_skill_content:
        Literal[False]` is copied onto both `EvaluationJudgePackage` and
        `EvaluationJudgeVerdict`, mirroring `JudgeInput`'s existing
        [LOCKED] pattern (trackA/schemas/judge.py) — the benchmarking
        Judge is held to the same structural neutrality guarantee as the
        live-pipeline Judge.

    Naming vs. the existing `JudgeEvaluationPackage` alias.
        trackA/schemas/__init__.py already aliases `JudgeEvaluationPackage
        = JudgeInput` for the *live-pipeline* Stage-2 Judge (docs/03
        §2.13: worker outputs -> routing decision). Docs/16's "Judge's
        Role in Benchmarking" is a different Judge invocation entirely
        (scoring a benchmark candidate's trajectory against a fixed
        rubric) with a structurally different input shape (no
        `worker_output_record_ids`, no `accumulated_evidence` — a
        trajectory, task requirements, and an optional objective
        outcome). Reusing `JudgeInput`'s locked field list for this would
        force fields that do not apply and blur two genuinely distinct
        concepts. This module therefore defines a separate
        `EvaluationJudgePackage`/`EvaluationJudgeVerdict` pair and leaves
        `JudgeInput`/`JudgeRoutingDecision`/the existing
        `JudgeEvaluationPackage` alias completely untouched.

    Role granularity: kept an open string, resolved by the caller.
        `ModelManifest.intended_worker_role` (docs/08, Context-1-locked)
        is granular (e.g. "endpoint_mapper"), while `ExperimentRecord.
        role_under_test`/`ModelEvaluationRecord.role` (docs/03 §3.6/§3.8)
        are a closed 5-value literal ("extractor"|"worker"|"judge"|
        "specialist"|"report_polisher"). `BenchmarkCase.role` and
        `EvaluationTrajectory.role` are deliberately left as an open
        `str` matching whatever key candidates are registered under in
        the Model Registry (docs/02 §4's `list_candidates(role)`) — no
        mapping table is invented here to bridge the two; the harness
        (trackA/evaluation/results.py) requires the coarse
        `role_under_test` value as an explicit, separate parameter when
        building the aggregate research records, rather than guessing it
        from the registry's role string.

    `evaluation_dataset_id` is a single string on the existing,
    unmodified `ExperimentRecord`/`ModelEvaluationRecord` (docs/03
    §3.6/§3.8) — there is no separate version field on those two schemas.
    Rather than editing docs/03's already-[LOCKED]-adjacent research
    schemas, trackA/evaluation/results.py documents and uses a composite
    string convention (`f"{dataset_id}@{version}"`) so "which dataset/
    version was used" (Context-4 task brief §5/§17) is still fully
    recorded without touching an existing contract. See that module's
    `dataset_ref`/`parse_dataset_ref` helpers.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import model_validator

from trackA.schemas.base import HypermindModel
from trackA.schemas.common import ManifestProvenance, Provenance, _new_uuid, _utc_now_iso


class BenchmarkCase(HypermindModel):
    """One controlled task/case a candidate model attempts.

    Static, human-authored test data — analogous to a Tool/Worker/Skill
    manifest, not a live-pipeline record, hence `ManifestProvenance`
    (see module docstring).

    `objective_outcome`: the known-correct result for a controlled/lab
    case (Context-4 task brief §6: "known controlled environment outcome
    ... known correct transformation/result"). `None` means no objective
    ground truth is available for this case — callers must not invent
    one; the distinction between an objectively-checkable case and a
    Judge-only case must stay visible downstream (§7: "make the
    distinction explicit rather than pretending the Judge is ground
    truth"), which is why `EvaluationTrajectory` below carries its own
    explicit `objective_outcome_available` flag rather than inferring it
    from whether this field happens to be truthy at trajectory-build
    time.

    `injection_probe`: marks a case whose `starting_inputs` deliberately
    embeds adversarial/injection-style content, for the prompt/tool-
    output injection-robustness evaluation the task brief §19 asks for.
    A case's own content is always treated as inert data by every
    consumer in this package — nothing here or in `trackA.evaluation`
    ever parses `starting_inputs` for embedded instructions.
    """

    case_id: str
    role: str
    task_description: str
    starting_inputs: Dict[str, Any]
    available_capabilities: List[str] = []
    objective_outcome: Optional[Dict[str, Any]] = None
    injection_probe: bool = False
    notes: str = ""
    provenance: ManifestProvenance

    @model_validator(mode="after")
    def _validate(self) -> "BenchmarkCase":
        for field_name in ("case_id", "role", "task_description"):
            if not getattr(self, field_name):
                raise ValueError(f"BenchmarkCase.{field_name} must be non-empty")
        return self


class TrajectoryStep(HypermindModel):
    """One step in a candidate's attempt at a `BenchmarkCase`
    (Context-4 task brief §4: "do not collapse the trajectory into only
    the final answer").

    `is_untrusted_input`: marks a step whose `detail` originates from
    case-supplied or candidate-controlled content (e.g. an
    `injection_probe` case's starting content, or a candidate's own
    claimed tool output) rather than from the harness's own deterministic
    bookkeeping — the same RAW_OBSERVATION-vs-instructions discipline
    already established for the live pipeline's Trust Boundary B (docs/
    01_ARCHITECTURE.md §6), restated at the evaluation-harness layer:
    `detail` is always data, never a directive to any consumer of this
    step, whatever this flag is set to. The flag exists for downstream
    auditing (which steps came from adversarial content), not to gate
    trust handling that the schema layer cannot itself enforce.
    """

    step_index: int
    action_type: Literal[
        "tool_request",
        "tool_result",
        "model_interpretation",
        "final_result",
        "error",
        "refusal",
    ]
    description: str
    detail: Dict[str, Any] = {}
    timestamp: str = ""
    is_untrusted_input: bool = False

    @model_validator(mode="before")
    @classmethod
    def _apply_defaults(cls, data):
        if isinstance(data, dict):
            data = dict(data)
            data.setdefault("timestamp", _utc_now_iso())
        return data

    @model_validator(mode="after")
    def _validate(self) -> "TrajectoryStep":
        if self.step_index < 0:
            raise ValueError("TrajectoryStep.step_index must be >= 0")
        return self


class EvaluationTrajectory(HypermindModel):
    """The full, reconstructable transcript of one candidate model
    attempting one `BenchmarkCase`, under the same starting conditions as
    every other candidate evaluated against that case (Context-4 task
    brief §3/§4).

    `retry_count` counts only *technical-failure* retries actually
    consumed (Context-4 task brief §12). It is not, by itself, proof that
    a refusal was never retried: a trajectory may legitimately show a
    technical failure retried once and *then* end in a refusal on that
    retry attempt — retrying a timeout is not "retrying to defeat a
    refusal." The rule this module actually needs to guarantee — the
    harness never calls a candidate again after observing a refusal, on
    that same attempt or any subsequent one — is a property of *how many
    times the harness invoked the candidate*, not of this final
    aggregate count, so it is enforced in `trackA.evaluation.harness`
    (never in a retry loop for a refusal) and proven by a dedicated test
    there (asserting the runtime adapter is invoked exactly once past
    the point a refusal is observed), not by a schema validator here.
    """

    provenance: Provenance
    trajectory_id: str = ""
    case_id: str
    dataset_id: str
    dataset_version: str
    role: str
    candidate_id: str
    candidate_model_version: str
    runtime_backend: str
    runtime_config: Dict[str, Any] = {}
    prompt_template_version: str = "v1"
    capabilities_available: List[str] = []
    starting_inputs: Dict[str, Any]
    steps: List[TrajectoryStep] = []
    final_output: Optional[Dict[str, Any]] = None
    objective_outcome_available: bool
    objective_outcome_match: Optional[bool] = None
    completion_status: Literal["success", "technical_failure", "refusal", "timeout", "partial"]
    failure_detail: Optional[str] = None
    retry_count: int = 0
    latency_ms: Optional[float] = None
    resource_usage: Dict[str, Any] = {}
    started_at: str = ""
    completed_at: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _apply_defaults(cls, data):
        if isinstance(data, dict):
            data = dict(data)
            data.setdefault("trajectory_id", _new_uuid())
            data.setdefault("started_at", _utc_now_iso())
        return data

    @model_validator(mode="after")
    def _validate(self) -> "EvaluationTrajectory":
        indices = [s.step_index for s in self.steps]
        if indices != sorted(indices):
            raise ValueError("EvaluationTrajectory.steps must be ordered by step_index")
        if self.completion_status != "success" and not self.failure_detail:
            raise ValueError(
                "EvaluationTrajectory.failure_detail is required when "
                "completion_status != 'success'"
            )
        if not self.objective_outcome_available and self.objective_outcome_match is not None:
            raise ValueError(
                "EvaluationTrajectory.objective_outcome_match must be None when "
                "objective_outcome_available is False (do not pretend the Judge "
                "or the harness is ground truth when no objective outcome exists)"
            )
        if self.retry_count < 0:
            raise ValueError("EvaluationTrajectory.retry_count must be >= 0")
        for field_name in (
            "case_id",
            "dataset_id",
            "dataset_version",
            "role",
            "candidate_id",
            "candidate_model_version",
            "runtime_backend",
        ):
            if not getattr(self, field_name):
                raise ValueError(f"EvaluationTrajectory.{field_name} must be non-empty")
        return self


class EvaluationJudgePackage(HypermindModel):
    """The minimum relevant package handed to a Judge scoring one
    candidate's trajectory (Context-4 task brief §7/§8; docs/16
    "The Judge's Role in Benchmarking": "It receives the minimum
    relevant evaluation package ... not the full original parsed/recon
    dataset").

    Deliberately has NO `candidate_id`, `model_identity`,
    `runtime_backend`, or `runtime_config` field — see the module
    docstring's "Judge-package identity blinding is structural" note.
    Any code that wants to hand a Judge the real candidate identity
    cannot do so through this type; it would have to invent a different
    one, which is exactly the friction this design intends.
    """

    provenance: Provenance
    package_id: str = ""
    trajectory_id: str
    blinded_candidate_label: str
    role: str
    task_requirements: str
    capabilities_available: List[str] = []
    actions_taken: List[Dict[str, Any]] = []
    evidence_produced: List[Dict[str, Any]] = []
    claimed_result: Optional[Dict[str, Any]] = None
    objective_outcome: Optional[Dict[str, Any]] = None
    resource_efficiency: Dict[str, Any] = {}
    contains_skill_content: Literal[False] = False

    @model_validator(mode="before")
    @classmethod
    def _apply_defaults(cls, data):
        if isinstance(data, dict):
            data = dict(data)
            data.setdefault("package_id", _new_uuid())
        return data

    @model_validator(mode="after")
    def _validate(self) -> "EvaluationJudgePackage":
        for field_name in ("trajectory_id", "blinded_candidate_label", "role", "task_requirements"):
            if not getattr(self, field_name):
                raise ValueError(f"EvaluationJudgePackage.{field_name} must be non-empty")
        return self


class EvaluationJudgeVerdict(HypermindModel):
    """A Judge's scoring of one `EvaluationJudgePackage`.

    `dimension_scores` is deliberately an open `Dict[str, float]`, not a
    fixed set of named fields — Context-4 task brief §9: "do not invent a
    universal numeric threshold ... do not create a single hardcoded
    score that automatically decides which model wins ... preserve
    enough structured results for the user to choose selection
    criteria." A closed schema of named metric fields would be exactly
    the kind of hardcoded rubric that instruction forbids; an open dict
    lets the harness/Judge report whichever of docs/16's/§9's many
    documented dimensions (task success, useful-hypothesis rate,
    evidence quality, false-positive rate, latency, cost, structured-
    output validity, injection robustness, reproducibility, ...) are
    actually applicable to a given role/case, without a schema change
    each time the set changes.

    This is scoring evidence only — nothing in this package (or anywhere
    else in Context 4) writes to `ModelManifest.approval_status`/
    `benchmark_status`. Promotion remains an explicit, separate human
    decision (task brief §11), never a side effect of constructing a
    verdict.
    """

    provenance: Provenance
    verdict_id: str = ""
    package_id: str
    blinded_candidate_label: str
    dimension_scores: Dict[str, float] = {}
    reasoning: str
    contains_skill_content: Literal[False] = False

    @model_validator(mode="before")
    @classmethod
    def _apply_defaults(cls, data):
        if isinstance(data, dict):
            data = dict(data)
            data.setdefault("verdict_id", _new_uuid())
        return data

    @model_validator(mode="after")
    def _validate(self) -> "EvaluationJudgeVerdict":
        for field_name in ("package_id", "blinded_candidate_label", "reasoning"):
            if not getattr(self, field_name):
                raise ValueError(f"EvaluationJudgeVerdict.{field_name} must be non-empty")
        return self
