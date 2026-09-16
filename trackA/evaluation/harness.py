"""The controlled evaluation harness. Context-4 task brief §3/§4/§12/§13/§14.

Runs one `BenchmarkCase` against every Model Registry candidate registered
for a role, one candidate at a time (task brief §14: "the evaluator should
support sequential candidate execution ... do not build a complicated
cluster scheduler"), through `trackA.models.runtime.RuntimeRegistry` (task
brief §13: "must use the runtime abstraction created in Context 2 ... do
NOT hardcode Ollama") — never touching a Docker container, a live network
target, or any of the excluded components in the task brief's §21 list.

Failure classification (task brief §12) uses the runtime layer's own
extension point rather than a new one: `InferenceAdapter.infer()`
(trackA.models.runtime, Context 2, unmodified) already returns a generic
`InferenceResult(success=False, error=...)` for *any* model-side failure
by design ("InferenceResult — raw model output ... schema validation is
the calling component's job" — the same reasoning applies to failure-mode
classification: it is this calling component's job, not the runtime
layer's). `InferenceResult.raw` is an open `Dict[str, Any]` for exactly
this kind of caller-specific extension. This module defines one small,
documented convention on it — `raw["refusal"] = True` — rather than
guessing at refusal from free-text `error` content (which the task brief
itself warns is unreliable: "do not interpret refusal as technical
failure"). An adapter that can positively identify a refusal (a real LLM
backend usually can, from a stop_reason/finish_reason field) sets this key
explicitly; an adapter that cannot make that distinction leaves it unset,
and every unset case is conservatively treated as a technical failure
(eligible for bounded retry) rather than silently assumed to be a refusal
— assuming refusal when the evidence does not support it would itself
be a form of confidence beyond what the evidence establishes, mirroring
the "evidence over confidence" instinct that runs through the wider Track
A architecture (docs/01_ARCHITECTURE.md §4).
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Literal, Optional

from trackA.evaluation.errors import NoCandidatesRegisteredError
from trackA.models.runtime import InferenceRequest, InferenceResult, RuntimeRegistry
from trackA.registries.models import ModelRegistry
from trackA.schemas.common import PipelineStage, Provenance
from trackA.schemas.evaluation import BenchmarkCase, EvaluationTrajectory, TrajectoryStep
from trackA.schemas.models import ModelManifest

ResultStatus = Literal["success", "technical_failure", "refusal"]

REFUSAL_MARKER_KEY = "refusal"


def classify_result(result: InferenceResult) -> ResultStatus:
    """See module docstring for the `raw["refusal"]` convention this relies on."""
    if result.success:
        return "success"
    if isinstance(result.raw, dict) and result.raw.get(REFUSAL_MARKER_KEY) is True:
        return "refusal"
    return "technical_failure"


def _default_trajectory_extractor(result: InferenceResult, next_index: int) -> List[TrajectoryStep]:
    """One step per adapter call, wrapping its raw output. A richer
    adapter/backend integration may supply its own `trajectory_extractor`
    that decomposes `result.raw` into multiple tool_request/tool_result/
    model_interpretation steps; this default makes no assumption about
    any particular backend's `raw` shape beyond the REFUSAL_MARKER_KEY
    convention above, staying usable for `MockAdapter` and any future
    backend alike."""
    status = classify_result(result)
    action_type: Literal["model_interpretation", "error", "refusal"]
    if status == "success":
        action_type = "model_interpretation"
        description = "candidate produced output"
    elif status == "refusal":
        action_type = "refusal"
        description = result.error or "candidate refused the request"
    else:
        action_type = "error"
        description = result.error or "technical failure calling candidate"
    return [
        TrajectoryStep(
            step_index=next_index,
            action_type=action_type,
            description=description,
            detail={"output_text": result.output_text, "raw": result.raw},
            is_untrusted_input=True,  # candidate-controlled content, never a directive
        )
    ]


def _default_objective_outcome_checker(
    case: BenchmarkCase, final_output: Optional[Dict[str, Any]]
) -> Optional[bool]:
    """Naive equality check between the case's known-correct outcome and
    the candidate's final output. Deliberately simple and overridable —
    a real controlled-lab case (e.g. a planted-vulnerability sandbox
    outcome) will usually need a case-specific checker; this default only
    covers the trivial "exact structured match" case so the harness is
    usable out of the box for synthetic transformation-style tasks."""
    if case.objective_outcome is None or final_output is None:
        return None
    return final_output == case.objective_outcome


TrajectoryExtractor = Callable[[InferenceResult, int], List[TrajectoryStep]]
ObjectiveOutcomeChecker = Callable[[BenchmarkCase, Optional[Dict[str, Any]]], Optional[bool]]


def build_request(case: BenchmarkCase, *, role: Optional[str] = None) -> InferenceRequest:
    """The exact same `InferenceRequest` every candidate for `case`
    receives (Context-4 task brief §3: "the same starting task/data/
    capabilities must be used for independently evaluated candidates").
    Built once per case (not per candidate) so this is structurally
    guaranteed, not merely intended — see
    `EvaluationHarness.run_experiment`, which constructs it exactly once
    per call and reuses it for every candidate in that experiment.

    `prompt` is a deterministic (sorted-key) JSON serialization of the
    task description and starting inputs — deterministic so the exact
    same request is reproducible from the case alone (Context-4 task
    brief §17), and so `starting_inputs`/its content is always carried as
    inert serialized data, never interpolated into anything resembling
    an instruction to the harness itself.
    """
    payload = {"task_description": case.task_description, "starting_inputs": case.starting_inputs}
    return InferenceRequest(
        role=role or case.role,
        prompt=json.dumps(payload, sort_keys=True),
        generation_policy={},
    )


class EvaluationHarness:
    """Runs a `BenchmarkCase` against every registered Model Registry
    candidate for a role, sequentially, and returns one `EvaluationTrajectory`
    per candidate. See module docstring for scope and failure-
    classification conventions.
    """

    def __init__(
        self,
        *,
        runtime: RuntimeRegistry,
        model_registry: ModelRegistry,
        max_retries: int = 2,
        trajectory_extractor: TrajectoryExtractor = _default_trajectory_extractor,
        objective_outcome_checker: ObjectiveOutcomeChecker = _default_objective_outcome_checker,
        include_runtime_config: bool = False,
    ) -> None:
        if max_retries < 0:
            raise ValueError("EvaluationHarness.max_retries must be >= 0")
        self._runtime = runtime
        self._model_registry = model_registry
        self._max_retries = max_retries
        self._trajectory_extractor = trajectory_extractor
        self._objective_outcome_checker = objective_outcome_checker
        # Default False: a ModelBinding.connection dict may carry API
        # keys/endpoints (trackA.models.runtime's own docstring —
        # "backend-specific connection config"). Recording it verbatim
        # into a persisted evaluation trajectory by default would risk
        # exactly the kind of credential leakage docs/09_SECURITY_
        # POLICIES_README.md §4 prohibits ("no exception for debug ...
        # logs"). A caller that has verified its bindings carry nothing
        # sensitive (e.g. local mock/Ollama configs) may opt in.
        #
        # Note the boundary this does NOT cover: `InferenceResult.raw`
        # (an adapter's own output) is stored into trajectory steps/
        # final_output as-is (see `_default_trajectory_extractor`) — if
        # a *specific* adapter implementation chooses to echo its own
        # binding/connection into `raw` (as `trackA.models.runtime.
        # MockAdapter` deliberately does, for debug/test visibility),
        # that content is not filtered here. Keeping `raw` untouched is
        # correct and unavoidable at this layer (the harness cannot know
        # which keys in an arbitrary adapter's raw payload are secret
        # without unreliable text-pattern guessing, the same category of
        # guess this module already refuses to make for refusal
        # detection); avoiding that leak is the responsibility of each
        # adapter implementation, not this harness.
        self._include_runtime_config = include_runtime_config

    def run_case_for_candidate(
        self,
        case: BenchmarkCase,
        candidate: ModelManifest,
        request: InferenceRequest,
        *,
        experiment_id: str,
        role_stage: PipelineStage,
        dataset_id: str,
        dataset_version: str,
    ) -> EvaluationTrajectory:
        """Run `request` (built once, shared across every candidate in the
        experiment via `build_request`) against a single `candidate`.

        Bounded retry applies only while the observed status is
        "technical_failure" (task brief §12); the very first "refusal" or
        "success" ends the loop immediately, so a refusal is never called
        again on this or any later attempt.
        """
        binding = self._runtime.get_binding(candidate.candidate_id)
        steps: List[TrajectoryStep] = []
        retries_used = 0
        result = self._runtime.invoke(candidate.candidate_id, request)
        status = classify_result(result)
        steps.extend(self._trajectory_extractor(result, len(steps)))
        while status == "technical_failure" and retries_used < self._max_retries:
            retries_used += 1
            result = self._runtime.invoke(candidate.candidate_id, request)
            status = classify_result(result)
            steps.extend(self._trajectory_extractor(result, len(steps)))

        final_output: Optional[Dict[str, Any]] = None
        if status == "success" and isinstance(result.raw, dict):
            final_output = result.raw

        objective_outcome_available = case.objective_outcome is not None
        objective_outcome_match = (
            self._objective_outcome_checker(case, final_output) if objective_outcome_available else None
        )

        completion_status: Literal["success", "technical_failure", "refusal"] = status
        failure_detail = None if status == "success" else (result.error or f"{status} with no error detail")

        return EvaluationTrajectory(
            provenance=Provenance(
                run_id=experiment_id,
                stage=role_stage,
                source_component="Evaluation Harness",
                model_id=candidate.candidate_id,
                model_version=candidate.version,
            ),
            case_id=case.case_id,
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            role=candidate.intended_worker_role,
            candidate_id=candidate.candidate_id,
            candidate_model_version=candidate.version,
            runtime_backend=binding.backend,
            runtime_config=binding.connection if self._include_runtime_config else {},
            starting_inputs=case.starting_inputs,
            capabilities_available=case.available_capabilities,
            steps=steps,
            final_output=final_output,
            objective_outcome_available=objective_outcome_available,
            objective_outcome_match=objective_outcome_match,
            completion_status=completion_status,
            failure_detail=failure_detail,
            retry_count=retries_used,
            latency_ms=result.latency_ms,
        )

    def run_experiment(
        self,
        case: BenchmarkCase,
        *,
        experiment_id: str,
        role_stage: PipelineStage,
        dataset_id: str,
        dataset_version: str,
        role: Optional[str] = None,
    ) -> List[EvaluationTrajectory]:
        """Every registered candidate for `role` (defaulting to
        `case.role`) attempts `case` independently, sequentially, under
        the identical `InferenceRequest` built once by `build_request`.
        """
        effective_role = role or case.role
        candidates = self._model_registry.list_candidates(effective_role)
        if not candidates:
            raise NoCandidatesRegisteredError(
                f"no Model Registry candidates are registered for role {effective_role!r}"
            )
        request = build_request(case, role=effective_role)
        return [
            self.run_case_for_candidate(
                case,
                candidate,
                request,
                experiment_id=experiment_id,
                role_stage=role_stage,
                dataset_id=dataset_id,
                dataset_version=dataset_version,
            )
            for candidate in candidates
        ]
