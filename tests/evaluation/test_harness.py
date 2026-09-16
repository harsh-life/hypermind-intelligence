from __future__ import annotations

import pytest

from trackA.evaluation.errors import NoCandidatesRegisteredError
from trackA.evaluation.harness import EvaluationHarness, build_request, classify_result
from trackA.models.runtime import InferenceResult
from trackA.registries.models import ModelRegistry
from trackA.schemas.common import PipelineStage


def make_case(case_store, case_id="idor-lab-001"):
    return case_store.lookup(case_id)


# --- classify_result ------------------------------------------------------


def test_classify_result_success():
    assert classify_result(InferenceResult(success=True, output_text="ok")) == "success"


def test_classify_result_technical_failure_by_default():
    assert classify_result(InferenceResult(success=False, error="timeout")) == "technical_failure"


def test_classify_result_refusal_requires_explicit_marker():
    result = InferenceResult(success=False, error="I cannot help with that", raw={"refusal": True})
    assert classify_result(result) == "refusal"


def test_classify_result_never_guesses_refusal_from_error_text_alone():
    """Task brief §12: do not interpret refusal as technical failure, and
    do not fabricate a refusal classification from unreliable text
    sniffing either — absence of the explicit marker must default to
    technical_failure (retryable), never to refusal (non-retryable)."""
    result = InferenceResult(success=False, error="I cannot help with that")
    assert classify_result(result) == "technical_failure"


# --- build_request: identical starting conditions --------------------------


def test_build_request_is_deterministic(case_store):
    case = make_case(case_store)
    r1 = build_request(case)
    r2 = build_request(case)
    assert r1.prompt == r2.prompt
    assert r1.role == case.role


# --- EvaluationHarness: same case, multiple candidates ----------------------


def test_run_experiment_uses_identical_starting_conditions_for_every_candidate(
    case_store, scripted_runtime, two_candidate_registry
):
    runtime, adapter = scripted_runtime
    case = make_case(case_store)
    adapter.script("cand-a", [InferenceResult(success=True, output_text="a", raw={"vulnerable": True})])
    adapter.script("cand-b", [InferenceResult(success=True, output_text="b", raw={"vulnerable": True})])

    harness = EvaluationHarness(runtime=runtime, model_registry=two_candidate_registry)
    trajectories = harness.run_experiment(
        case,
        experiment_id="exp-1",
        role_stage=PipelineStage.SPECIALIST,
        dataset_id="ds-track-a-bootstrap",
        dataset_version="v1",
    )

    assert len(trajectories) == 2
    assert trajectories[0].starting_inputs == trajectories[1].starting_inputs == case.starting_inputs
    assert {t.candidate_id for t in trajectories} == {"cand-a", "cand-b"}


def test_run_experiment_raises_when_no_candidates_for_role(case_store):
    case = make_case(case_store)
    empty_registry = ModelRegistry()
    from trackA.models.runtime import RuntimeRegistry

    runtime = RuntimeRegistry(model_registry=empty_registry)
    harness = EvaluationHarness(runtime=runtime, model_registry=empty_registry)
    with pytest.raises(NoCandidatesRegisteredError):
        harness.run_experiment(
            case,
            experiment_id="exp-1",
            role_stage=PipelineStage.SPECIALIST,
            dataset_id="ds-track-a-bootstrap",
            dataset_version="v1",
        )


# --- candidate identity / provenance / reproducibility ----------------------


def test_trajectory_carries_candidate_and_runtime_provenance(case_store, scripted_runtime, two_candidate_registry):
    runtime, adapter = scripted_runtime
    case = make_case(case_store)
    adapter.script("cand-a", [InferenceResult(success=True, output_text="a", raw={"vulnerable": True})])
    adapter.script("cand-b", [InferenceResult(success=True, output_text="b", raw={"vulnerable": True})])

    harness = EvaluationHarness(runtime=runtime, model_registry=two_candidate_registry)
    [trajectory] = [
        t
        for t in harness.run_experiment(
            case,
            experiment_id="exp-1",
            role_stage=PipelineStage.SPECIALIST,
            dataset_id="ds-track-a-bootstrap",
            dataset_version="v1",
        )
        if t.candidate_id == "cand-a"
    ]
    assert trajectory.provenance.model_id == "cand-a"
    assert trajectory.provenance.model_version == "v1"
    assert trajectory.runtime_backend == "scripted"
    assert trajectory.dataset_id == "ds-track-a-bootstrap"
    assert trajectory.dataset_version == "v1"
    assert trajectory.case_id == case.case_id


def test_runtime_config_excluded_by_default(case_store, scripted_runtime, two_candidate_registry):
    """Never leak ModelBinding.connection (may carry secrets) into the
    persisted trajectory unless the caller explicitly opts in.

    Uses ScriptedAdapter (not MockAdapter): MockAdapter is a Context-2
    debug/test stand-in that deliberately echoes its whole `binding`
    (connection included) into `InferenceResult.raw` for wiring
    visibility — that is MockAdapter's own documented behavior, not
    something trackA.evaluation.harness controls or should try to
    scrub generically (whether an arbitrary adapter's `raw` payload
    echoes secrets is that adapter's responsibility, the same way a
    real backend's response object must not itself echo request
    headers). ScriptedAdapter's scripted `raw` content is fully
    controlled here, isolating exactly what the harness itself
    controls: whether *it* copies `binding.connection` into
    `EvaluationTrajectory.runtime_config`.
    """
    runtime, adapter = scripted_runtime
    case = case_store.lookup("idor-lab-001")
    adapter.script("cand-a", [InferenceResult(success=True, output_text="a", raw={"vulnerable": True})])
    adapter.script("cand-b", [InferenceResult(success=True, output_text="b", raw={"vulnerable": False})])

    harness = EvaluationHarness(runtime=runtime, model_registry=two_candidate_registry)
    trajectories = harness.run_experiment(
        case,
        experiment_id="exp-1",
        role_stage=PipelineStage.SPECIALIST,
        dataset_id="ds-track-a-bootstrap",
        dataset_version="v1",
    )
    for t in trajectories:
        assert t.runtime_config == {}


def test_runtime_config_included_when_opted_in(case_store, two_candidate_registry):
    from trackA.models.runtime import ModelBinding, RuntimeRegistry
    from tests.evaluation.conftest import ScriptedAdapter

    adapter = ScriptedAdapter()
    runtime = RuntimeRegistry(model_registry=two_candidate_registry)
    runtime.register_adapter(adapter)
    runtime.bind(ModelBinding(candidate_id="cand-a", backend="scripted", connection={"endpoint": "local"}))
    runtime.bind(ModelBinding(candidate_id="cand-b", backend="scripted"))
    adapter.script("cand-a", [InferenceResult(success=True, output_text="a", raw={"vulnerable": True})])
    adapter.script("cand-b", [InferenceResult(success=True, output_text="b", raw={"vulnerable": False})])

    case = case_store.lookup("idor-lab-001")
    harness = EvaluationHarness(
        runtime=runtime, model_registry=two_candidate_registry, include_runtime_config=True
    )
    trajectories = harness.run_experiment(
        case,
        experiment_id="exp-1",
        role_stage=PipelineStage.SPECIALIST,
        dataset_id="ds-track-a-bootstrap",
        dataset_version="v1",
    )
    cand_a = next(t for t in trajectories if t.candidate_id == "cand-a")
    assert cand_a.runtime_config == {"endpoint": "local"}


# --- objective outcome recording --------------------------------------------


def test_objective_outcome_match_recorded_when_available(case_store, scripted_runtime, two_candidate_registry):
    runtime, adapter = scripted_runtime
    case = make_case(case_store)  # objective_outcome = {"vulnerable": True}
    adapter.script("cand-a", [InferenceResult(success=True, output_text="a", raw={"vulnerable": True})])
    adapter.script("cand-b", [InferenceResult(success=True, output_text="b", raw={"vulnerable": False})])

    harness = EvaluationHarness(runtime=runtime, model_registry=two_candidate_registry)
    trajectories = {
        t.candidate_id: t
        for t in harness.run_experiment(
            case,
            experiment_id="exp-1",
            role_stage=PipelineStage.SPECIALIST,
            dataset_id="ds-track-a-bootstrap",
            dataset_version="v1",
        )
    }
    assert trajectories["cand-a"].objective_outcome_available is True
    assert trajectories["cand-a"].objective_outcome_match is True
    assert trajectories["cand-b"].objective_outcome_match is False


def test_objective_outcome_match_none_when_unavailable(case_store, scripted_runtime, two_candidate_registry):
    runtime, adapter = scripted_runtime
    case = case_store.lookup("injection-probe-001")  # objective_outcome = None
    adapter.script("cand-a", [InferenceResult(success=True, output_text="a", raw={"vulnerable": False})])
    adapter.script("cand-b", [InferenceResult(success=True, output_text="b", raw={"vulnerable": False})])

    harness = EvaluationHarness(runtime=runtime, model_registry=two_candidate_registry)
    trajectories = harness.run_experiment(
        case,
        experiment_id="exp-1",
        role_stage=PipelineStage.SPECIALIST,
        dataset_id="ds-track-a-bootstrap",
        dataset_version="v1",
    )
    for t in trajectories:
        assert t.objective_outcome_available is False
        assert t.objective_outcome_match is None


# --- bounded retry vs. refusal (task brief §12) -----------------------------


def test_technical_failure_is_retried_up_to_max_retries_then_succeeds(
    case_store, scripted_runtime, two_candidate_registry
):
    runtime, adapter = scripted_runtime
    case = make_case(case_store)
    adapter.script(
        "cand-a",
        [
            InferenceResult(success=False, error="timeout 1"),
            InferenceResult(success=False, error="timeout 2"),
            InferenceResult(success=True, output_text="ok", raw={"vulnerable": True}),
        ],
    )
    adapter.script("cand-b", [InferenceResult(success=True, output_text="ok", raw={"vulnerable": True})])

    harness = EvaluationHarness(runtime=runtime, model_registry=two_candidate_registry, max_retries=2)
    trajectories = {
        t.candidate_id: t
        for t in harness.run_experiment(
            case,
            experiment_id="exp-1",
            role_stage=PipelineStage.SPECIALIST,
            dataset_id="ds-track-a-bootstrap",
            dataset_version="v1",
        )
    }
    assert trajectories["cand-a"].completion_status == "success"
    assert trajectories["cand-a"].retry_count == 2
    assert adapter.call_count("cand-a") == 3


def test_technical_failure_exhausts_bounded_retries(case_store, scripted_runtime, two_candidate_registry):
    runtime, adapter = scripted_runtime
    case = make_case(case_store)
    adapter.script("cand-a", [InferenceResult(success=False, error="permanent backend error")])
    adapter.script("cand-b", [InferenceResult(success=True, output_text="ok", raw={"vulnerable": True})])

    harness = EvaluationHarness(runtime=runtime, model_registry=two_candidate_registry, max_retries=2)
    trajectories = {
        t.candidate_id: t
        for t in harness.run_experiment(
            case,
            experiment_id="exp-1",
            role_stage=PipelineStage.SPECIALIST,
            dataset_id="ds-track-a-bootstrap",
            dataset_version="v1",
        )
    }
    assert trajectories["cand-a"].completion_status == "technical_failure"
    assert trajectories["cand-a"].retry_count == 2
    # 1 initial attempt + 2 retries = 3 total calls, never unbounded
    assert adapter.call_count("cand-a") == 3
    assert trajectories["cand-a"].failure_detail


def test_refusal_is_never_retried(case_store, scripted_runtime, two_candidate_registry):
    """Task brief §12: a refusal must NOT be repeatedly retried solely to
    defeat it. Scripted with a *second* entry that would succeed if
    called — the assertion that call_count stays at 1 proves the harness
    never reaches it."""
    runtime, adapter = scripted_runtime
    case = make_case(case_store)
    adapter.script(
        "cand-a",
        [
            InferenceResult(success=False, error="I cannot assist with this", raw={"refusal": True}),
            InferenceResult(success=True, output_text="would have succeeded", raw={"vulnerable": True}),
        ],
    )
    adapter.script("cand-b", [InferenceResult(success=True, output_text="ok", raw={"vulnerable": True})])

    harness = EvaluationHarness(runtime=runtime, model_registry=two_candidate_registry, max_retries=5)
    trajectories = {
        t.candidate_id: t
        for t in harness.run_experiment(
            case,
            experiment_id="exp-1",
            role_stage=PipelineStage.SPECIALIST,
            dataset_id="ds-track-a-bootstrap",
            dataset_version="v1",
        )
    }
    assert trajectories["cand-a"].completion_status == "refusal"
    assert trajectories["cand-a"].retry_count == 0
    assert adapter.call_count("cand-a") == 1  # never called a second time


def test_harness_rejects_negative_max_retries(two_candidate_registry):
    from trackA.models.runtime import RuntimeRegistry

    runtime = RuntimeRegistry(model_registry=two_candidate_registry)
    with pytest.raises(ValueError):
        EvaluationHarness(runtime=runtime, model_registry=two_candidate_registry, max_retries=-1)


# --- trajectory step ordering / preservation --------------------------------


def test_trajectory_steps_are_recorded_and_ordered(case_store, scripted_runtime, two_candidate_registry):
    runtime, adapter = scripted_runtime
    case = make_case(case_store)
    adapter.script(
        "cand-a",
        [
            InferenceResult(success=False, error="timeout"),
            InferenceResult(success=True, output_text="ok", raw={"vulnerable": True}),
        ],
    )
    adapter.script("cand-b", [InferenceResult(success=True, output_text="ok", raw={"vulnerable": True})])

    harness = EvaluationHarness(runtime=runtime, model_registry=two_candidate_registry)
    trajectories = {
        t.candidate_id: t
        for t in harness.run_experiment(
            case,
            experiment_id="exp-1",
            role_stage=PipelineStage.SPECIALIST,
            dataset_id="ds-track-a-bootstrap",
            dataset_version="v1",
        )
    }
    steps = trajectories["cand-a"].steps
    assert len(steps) == 2
    assert [s.step_index for s in steps] == [0, 1]
    assert steps[0].action_type == "error"
    assert steps[1].action_type == "model_interpretation"


# --- regression: Model Registry candidates are never mutated ----------------


def test_running_an_experiment_never_mutates_registered_manifests(
    case_store, scripted_runtime, two_candidate_registry
):
    runtime, adapter = scripted_runtime
    case = make_case(case_store)
    adapter.script("cand-a", [InferenceResult(success=True, output_text="a", raw={"vulnerable": True})])
    adapter.script("cand-b", [InferenceResult(success=True, output_text="b", raw={"vulnerable": False})])

    before = {m.candidate_id: m.model_dump(mode="json") for m in two_candidate_registry.all()}
    harness = EvaluationHarness(runtime=runtime, model_registry=two_candidate_registry)
    harness.run_experiment(
        case,
        experiment_id="exp-1",
        role_stage=PipelineStage.SPECIALIST,
        dataset_id="ds-track-a-bootstrap",
        dataset_version="v1",
    )
    after = {m.candidate_id: m.model_dump(mode="json") for m in two_candidate_registry.all()}
    assert before == after
