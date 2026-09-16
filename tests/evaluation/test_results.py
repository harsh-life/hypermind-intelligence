from __future__ import annotations

import pytest

from trackA.evaluation.results import (
    build_experiment_record,
    build_model_evaluation_record,
    dataset_ref,
    parse_dataset_ref,
)
from trackA.models.runtime import InferenceResult
from trackA.evaluation.harness import EvaluationHarness
from trackA.evaluation.judge import BenchmarkJudge
from trackA.evaluation.judge_package import assign_blind_labels, build_judge_package
from trackA.schemas.common import PipelineStage


# --- dataset_ref / parse_dataset_ref -----------------------------------------


def test_dataset_ref_round_trip():
    ref = dataset_ref("ds-track-a-bootstrap", "v1")
    assert ref == "ds-track-a-bootstrap@v1"
    assert parse_dataset_ref(ref) == ("ds-track-a-bootstrap", "v1")


def test_dataset_ref_rejects_separator_in_components():
    with pytest.raises(ValueError):
        dataset_ref("ds@bad", "v1")


def test_parse_dataset_ref_rejects_malformed_input():
    with pytest.raises(ValueError):
        parse_dataset_ref("not-a-ref")


# --- build_model_evaluation_record / build_experiment_record ----------------


def _run(case_store, scripted_runtime, two_candidate_registry, experiment_id="exp-1"):
    runtime, adapter = scripted_runtime
    case = case_store.lookup("idor-lab-001")
    adapter.script("cand-a", [InferenceResult(success=True, output_text="a", raw={"vulnerable": True})])
    adapter.script("cand-b", [InferenceResult(success=True, output_text="b", raw={"vulnerable": False})])
    harness = EvaluationHarness(runtime=runtime, model_registry=two_candidate_registry)
    trajectories = harness.run_experiment(
        case,
        experiment_id=experiment_id,
        role_stage=PipelineStage.SPECIALIST,
        dataset_id="ds-track-a-bootstrap",
        dataset_version="v1",
    )
    return case, trajectories


def test_build_model_evaluation_record_carries_dataset_ref_and_reserved_keys(
    case_store, scripted_runtime, two_candidate_registry
):
    case, trajectories = _run(case_store, scripted_runtime, two_candidate_registry)
    trajectory = trajectories[0]
    record = build_model_evaluation_record(trajectory, role_under_test="specialist")
    assert record.evaluation_dataset_id == "ds-track-a-bootstrap@v1"
    assert record.model_id == trajectory.candidate_id
    assert record.metrics["_trajectory_id"] == trajectory.trajectory_id
    assert record.metrics["_completion_status"] == "success"


def test_build_model_evaluation_record_folds_in_verdict_scores(
    case_store, scripted_runtime, two_candidate_registry
):
    case, trajectories = _run(case_store, scripted_runtime, two_candidate_registry)
    trajectory = trajectories[0]
    labels = assign_blind_labels([t.candidate_id for t in trajectories], seed="exp-1")
    pkg = build_judge_package(
        trajectory, case, blinded_candidate_label=labels[trajectory.candidate_id], experiment_id="exp-1"
    )
    verdict = BenchmarkJudge().evaluate(pkg, experiment_id="exp-1")

    record = build_model_evaluation_record(trajectory, role_under_test="specialist", verdict=verdict)
    assert record.metrics["objective_outcome_match"] == 1.0
    assert record.metrics["_judge_verdict_id"] == verdict.verdict_id


def test_build_experiment_record_groups_every_candidate(case_store, scripted_runtime, two_candidate_registry):
    case, trajectories = _run(case_store, scripted_runtime, two_candidate_registry)
    record = build_experiment_record(
        experiment_id="exp-1",
        role_under_test="specialist",
        dataset_id="ds-track-a-bootstrap",
        dataset_version="v1",
        trajectories=trajectories,
    )
    assert set(record.candidate_model_ids) == {"cand-a", "cand-b"}
    assert record.evaluation_dataset_id == "ds-track-a-bootstrap@v1"
    assert len(record.results_per_model) == 2


def test_build_experiment_record_never_computes_a_winner_by_default(
    case_store, scripted_runtime, two_candidate_registry
):
    """Task brief §11: do not automatically declare a model best."""
    case, trajectories = _run(case_store, scripted_runtime, two_candidate_registry)
    record = build_experiment_record(
        experiment_id="exp-1",
        role_under_test="specialist",
        dataset_id="ds-track-a-bootstrap",
        dataset_version="v1",
        trajectories=trajectories,
    )
    assert record.winner_model_id is None


def test_build_experiment_record_only_sets_winner_when_caller_explicitly_provides_one(
    case_store, scripted_runtime, two_candidate_registry
):
    case, trajectories = _run(case_store, scripted_runtime, two_candidate_registry)
    record = build_experiment_record(
        experiment_id="exp-1",
        role_under_test="specialist",
        dataset_id="ds-track-a-bootstrap",
        dataset_version="v1",
        trajectories=trajectories,
        winner_model_id="cand-a",  # a human decision, passed in explicitly
    )
    assert record.winner_model_id == "cand-a"


def test_build_experiment_record_requires_at_least_one_trajectory():
    with pytest.raises(ValueError):
        build_experiment_record(
            experiment_id="exp-1",
            role_under_test="specialist",
            dataset_id="ds-track-a-bootstrap",
            dataset_version="v1",
            trajectories=[],
        )


def test_two_experiments_same_case_different_ids_remain_independently_identifiable(
    case_store, scripted_runtime, two_candidate_registry
):
    """Task brief §17/§18: historical experiments must remain
    identifiable, never silently replaced."""
    _, trajectories_1 = _run(case_store, scripted_runtime, two_candidate_registry, experiment_id="exp-1")
    record_1 = build_experiment_record(
        experiment_id="exp-1",
        role_under_test="specialist",
        dataset_id="ds-track-a-bootstrap",
        dataset_version="v1",
        trajectories=trajectories_1,
    )

    # a second, independent experiment run against the same case/dataset
    runtime, adapter = scripted_runtime
    adapter.script("cand-a", [InferenceResult(success=True, output_text="a2", raw={"vulnerable": True})])
    adapter.script("cand-b", [InferenceResult(success=True, output_text="b2", raw={"vulnerable": True})])
    harness = EvaluationHarness(runtime=runtime, model_registry=two_candidate_registry)
    case = case_store.lookup("idor-lab-001")
    trajectories_2 = harness.run_experiment(
        case,
        experiment_id="exp-2",
        role_stage=PipelineStage.SPECIALIST,
        dataset_id="ds-track-a-bootstrap",
        dataset_version="v1",
    )
    record_2 = build_experiment_record(
        experiment_id="exp-2",
        role_under_test="specialist",
        dataset_id="ds-track-a-bootstrap",
        dataset_version="v1",
        trajectories=trajectories_2,
    )

    assert record_1.experiment_id != record_2.experiment_id
    assert record_1.provenance.run_id == "exp-1"
    assert record_2.provenance.run_id == "exp-2"
    # each experiment's trajectory ids are its own, not shared/overwritten
    assert {t.trajectory_id for t in trajectories_1}.isdisjoint({t.trajectory_id for t in trajectories_2})
