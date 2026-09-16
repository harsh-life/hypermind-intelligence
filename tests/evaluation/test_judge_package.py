from __future__ import annotations

from trackA.evaluation.judge_package import assign_blind_labels, build_judge_package
from trackA.models.runtime import InferenceResult
from trackA.evaluation.harness import EvaluationHarness
from trackA.schemas.common import PipelineStage


# --- assign_blind_labels -----------------------------------------------------


def test_assign_blind_labels_deterministic_for_same_seed():
    ids = ["cand-a", "cand-b", "cand-c"]
    labels1 = assign_blind_labels(ids, seed="exp-1")
    labels2 = assign_blind_labels(ids, seed="exp-1")
    assert labels1 == labels2


def test_assign_blind_labels_differs_across_seeds_eventually():
    ids = [f"cand-{i}" for i in range(8)]
    labels_a = assign_blind_labels(ids, seed="exp-1")
    labels_b = assign_blind_labels(ids, seed="exp-2")
    assert labels_a != labels_b  # extremely unlikely to collide with 8! orderings


def test_assign_blind_labels_covers_every_candidate_exactly_once():
    ids = ["cand-a", "cand-b", "cand-c"]
    labels = assign_blind_labels(ids, seed="exp-1")
    assert set(labels.keys()) == set(ids)
    assert sorted(labels.values()) == ["candidate_1", "candidate_2", "candidate_3"]


# --- build_judge_package: minimum-relevant-package / no identity leak -------


def _make_trajectory(case_store, scripted_runtime, two_candidate_registry):
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
    return case, {t.candidate_id: t for t in trajectories}


def test_judge_package_never_contains_real_candidate_id(case_store, scripted_runtime, two_candidate_registry):
    case, trajectories = _make_trajectory(case_store, scripted_runtime, two_candidate_registry)
    trajectory = trajectories["cand-a"]
    pkg = build_judge_package(
        trajectory, case, blinded_candidate_label="candidate_1", experiment_id="exp-1"
    )
    dumped = pkg.model_dump(mode="json")
    # the real candidate_id must not appear anywhere in the serialized
    # package, under any key
    assert "cand-a" not in str(dumped)
    assert "cand-b" not in str(dumped)


def test_judge_package_carries_no_runtime_identity_fields(case_store, scripted_runtime, two_candidate_registry):
    case, trajectories = _make_trajectory(case_store, scripted_runtime, two_candidate_registry)
    trajectory = trajectories["cand-a"]
    pkg = build_judge_package(
        trajectory, case, blinded_candidate_label="candidate_1", experiment_id="exp-1"
    )
    assert not hasattr(pkg, "candidate_id")
    assert not hasattr(pkg, "runtime_backend")
    assert not hasattr(pkg, "runtime_config")
    assert not hasattr(pkg, "candidate_model_version")


def test_judge_package_carries_task_requirements_and_objective_outcome(
    case_store, scripted_runtime, two_candidate_registry
):
    case, trajectories = _make_trajectory(case_store, scripted_runtime, two_candidate_registry)
    trajectory = trajectories["cand-a"]
    pkg = build_judge_package(
        trajectory, case, blinded_candidate_label="candidate_1", experiment_id="exp-1"
    )
    assert pkg.task_requirements == case.task_description
    assert pkg.objective_outcome == case.objective_outcome
    assert pkg.claimed_result == trajectory.final_output


def test_judge_package_excludes_unrelated_context_not_on_the_trajectory(
    case_store, scripted_runtime, two_candidate_registry
):
    """The package is built only from the trajectory + case being judged
    -- nothing pulls in any other candidate's trajectory, any other
    case's data, or the full raw recon context (task brief §7/§8: do NOT
    automatically give the Judge the entire raw reconnaissance
    context)."""
    case, trajectories = _make_trajectory(case_store, scripted_runtime, two_candidate_registry)
    trajectory = trajectories["cand-a"]
    pkg = build_judge_package(
        trajectory, case, blinded_candidate_label="candidate_1", experiment_id="exp-1"
    )
    assert pkg.contains_skill_content is False
    # only this trajectory's own steps feed evidence_produced/actions_taken
    assert len(pkg.actions_taken) == len(trajectory.steps)
