from __future__ import annotations

from pathlib import Path

from trackA.evaluation.cases import BenchmarkCaseStore, DatasetStore
from trackA.evaluation.harness import EvaluationHarness
from trackA.evaluation.judge import BenchmarkJudge
from trackA.evaluation.judge_package import assign_blind_labels, build_judge_package
from trackA.evaluation.results import build_experiment_record
from trackA.evaluation.storage import read_record, write_record
from trackA.models.runtime import InferenceResult, ModelBinding, RuntimeRegistry
from trackA.registries.models import ModelRegistry
from trackA.schemas.common import PipelineStage
from trackA.schemas.research import ExperimentRecord
from tests.evaluation.conftest import SEED_DATA_DIR, ScriptedAdapter, model_manifest_data


def test_full_pipeline_seed_data_to_persisted_experiment_record(tmp_path: Path):
    """Model Registry candidates (Context 2) -> Model Evaluation Lab
    (Context 4), end to end: load seed cases/dataset -> two competing
    candidates -> harness runs both under identical conditions -> blind
    -> Judge scores each -> fold into ExperimentRecord/
    ModelEvaluationRecord (Context 1) -> persist to local storage."""
    case_store = BenchmarkCaseStore.from_directory(SEED_DATA_DIR / "cases")
    dataset_store = DatasetStore()
    dataset_store.register_from_directory(SEED_DATA_DIR / "datasets")
    case = dataset_store.resolve_cases("ds-track-a-bootstrap", "v1", case_store)[0]
    assert case.case_id == "idor-lab-001"

    models = ModelRegistry()
    models.register_from_dict(model_manifest_data(candidate_id="cand-a"))
    models.register_from_dict(model_manifest_data(candidate_id="cand-b"))

    adapter = ScriptedAdapter()
    runtime = RuntimeRegistry(model_registry=models)
    runtime.register_adapter(adapter)
    runtime.bind(ModelBinding(candidate_id="cand-a", backend="scripted"))
    runtime.bind(ModelBinding(candidate_id="cand-b", backend="scripted"))
    adapter.script("cand-a", [InferenceResult(success=True, output_text="a", raw={"vulnerable": True})])
    adapter.script("cand-b", [InferenceResult(success=True, output_text="b", raw={"vulnerable": False})])

    harness = EvaluationHarness(runtime=runtime, model_registry=models)
    trajectories = harness.run_experiment(
        case,
        experiment_id="exp-integration-1",
        role_stage=PipelineStage.SPECIALIST,
        dataset_id="ds-track-a-bootstrap",
        dataset_version="v1",
    )
    assert len(trajectories) == 2

    labels = assign_blind_labels([t.candidate_id for t in trajectories], seed="exp-integration-1")
    judge = BenchmarkJudge()
    verdicts = {}
    for trajectory in trajectories:
        pkg = build_judge_package(
            trajectory,
            case,
            blinded_candidate_label=labels[trajectory.candidate_id],
            experiment_id="exp-integration-1",
        )
        # the package handed to the Judge never carries the real id
        assert trajectory.candidate_id not in str(pkg.model_dump(mode="json"))
        verdicts[trajectory.trajectory_id] = judge.evaluate(pkg, experiment_id="exp-integration-1")

    record = build_experiment_record(
        experiment_id="exp-integration-1",
        role_under_test="specialist",
        dataset_id="ds-track-a-bootstrap",
        dataset_version="v1",
        trajectories=trajectories,
        verdicts=verdicts,
    )
    assert isinstance(record, ExperimentRecord)
    assert record.winner_model_id is None  # never auto-decided

    # persist every trajectory + the experiment record locally
    for trajectory in trajectories:
        write_record(tmp_path, "trajectories", trajectory.trajectory_id, trajectory)
    write_record(tmp_path, "experiments", record.experiment_id, record)

    reloaded = read_record(tmp_path, "experiments", record.experiment_id, ExperimentRecord)
    assert reloaded == record

    # candidate manifests were never mutated by any of the above
    assert models.lookup("cand-a").approval_status == "candidate"
    assert models.lookup("cand-b").approval_status == "candidate"


def test_unapproved_candidates_are_still_eligible_for_evaluation(tmp_path: Path):
    """Task brief §11 / trackA.evaluation.errors.NoCandidatesRegisteredError
    docstring: benchmarking must be able to compete *unapproved*
    candidates -- that is the whole point of evaluation, unlike live
    pipeline resolution which requires an approved candidate
    (RoleResolver.resolve / ModelRegistry.get_approved)."""
    models = ModelRegistry()
    models.register_from_dict(model_manifest_data(candidate_id="cand-a", approval_status="candidate"))
    models.register_from_dict(model_manifest_data(candidate_id="cand-b", approval_status="candidate"))
    # neither candidate is "approved" -- get_approved would raise here
    import pytest
    from trackA.registries.errors import NoApprovedCandidateError

    with pytest.raises(NoApprovedCandidateError):
        models.get_approved("specialist")

    # but the evaluation harness competes both anyway
    assert len(models.list_candidates("specialist")) == 2
