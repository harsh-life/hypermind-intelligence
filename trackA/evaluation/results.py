"""Fold trajectories + verdicts into the existing, unmodified
ExperimentRecord/ModelEvaluationRecord schemas (trackA.schemas.research).
Context-4 task brief §5/§9/§11/§17/§18.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple

from trackA.schemas.common import PipelineStage, Provenance
from trackA.schemas.evaluation import EvaluationJudgeVerdict, EvaluationTrajectory
from trackA.schemas.research import ExperimentModelResult, ExperimentRecord, ModelEvaluationRecord

RoleUnderTest = Literal["extractor", "worker", "judge", "specialist", "report_polisher"]

_DATASET_REF_SEPARATOR = "@"


def dataset_ref(dataset_id: str, version: str) -> str:
    """Composite `dataset_id@version` string. See trackA/schemas/
    evaluation.py's module docstring for why this convention exists:
    `ExperimentRecord.evaluation_dataset_id` / `ModelEvaluationRecord.
    evaluation_dataset_id` (docs/03_DATA_SCHEMAS_README.md §3.6/§3.8,
    unmodified) are a single `str` field with no separate version field.
    """
    if _DATASET_REF_SEPARATOR in dataset_id or _DATASET_REF_SEPARATOR in version:
        raise ValueError(
            f"dataset_id/version must not themselves contain "
            f"{_DATASET_REF_SEPARATOR!r} (got dataset_id={dataset_id!r}, "
            f"version={version!r})"
        )
    return f"{dataset_id}{_DATASET_REF_SEPARATOR}{version}"


def parse_dataset_ref(ref: str) -> Tuple[str, str]:
    if _DATASET_REF_SEPARATOR not in ref:
        raise ValueError(f"not a dataset_ref (missing {_DATASET_REF_SEPARATOR!r}): {ref!r}")
    dataset_id, _, version = ref.partition(_DATASET_REF_SEPARATOR)
    return dataset_id, version


def build_model_evaluation_record(
    trajectory: EvaluationTrajectory,
    *,
    role_under_test: RoleUnderTest,
    verdict: Optional[EvaluationJudgeVerdict] = None,
    known_limitations: Optional[List[str]] = None,
) -> ModelEvaluationRecord:
    """One persisted evaluation result for one candidate against one case
    within one dataset version.

    `metrics` carries the verdict's `dimension_scores` (if any) plus a
    small set of harness-produced, underscore-prefixed reserved keys
    documenting the trajectory this record was derived from. This keeps
    `ModelEvaluationRecord`'s existing, open `metrics: Dict[str, Any]`
    field doing exactly the job docs/03 already gave it, with no schema
    change: `_trajectory_id`, `_completion_status`, `_retry_count`,
    `_objective_outcome_match` (only when available),
    `_judge_verdict_id`/`_judge_reasoning` (only when a verdict exists).

    Never sets or reads `ModelManifest.approval_status`/`benchmark_status`
    — this function only produces a persisted record; promoting a
    candidate on the strength of it is an explicit, separate human
    action (Context-4 task brief §11), never a side effect here.
    """
    metrics: Dict[str, Any] = dict(verdict.dimension_scores) if verdict is not None else {}
    metrics["_trajectory_id"] = trajectory.trajectory_id
    metrics["_completion_status"] = trajectory.completion_status
    metrics["_retry_count"] = trajectory.retry_count
    if trajectory.objective_outcome_match is not None:
        metrics["_objective_outcome_match"] = trajectory.objective_outcome_match
    if verdict is not None:
        metrics["_judge_verdict_id"] = verdict.verdict_id
        metrics["_judge_reasoning"] = verdict.reasoning

    return ModelEvaluationRecord(
        provenance=Provenance(
            run_id=trajectory.provenance.run_id,
            stage=PipelineStage.JUDGE,
            source_component="Evaluation Results Builder",
        ),
        model_id=trajectory.candidate_id,
        role=role_under_test,
        evaluation_dataset_id=dataset_ref(trajectory.dataset_id, trajectory.dataset_version),
        metrics=metrics,
        known_limitations=known_limitations or [],
    )


def build_experiment_record(
    *,
    experiment_id: str,
    role_under_test: RoleUnderTest,
    dataset_id: str,
    dataset_version: str,
    trajectories: List[EvaluationTrajectory],
    verdicts: Optional[Dict[str, EvaluationJudgeVerdict]] = None,
    winner_model_id: Optional[str] = None,
) -> ExperimentRecord:
    """One ExperimentRecord grouping every candidate's result for one
    case/dataset-version run.

    `verdicts` is keyed by `trajectory_id`.

    `winner_model_id` defaults to `None` and is NEVER computed by this
    function from the metrics it just assembled — task brief §11: "do
    not automatically declare a model best ... do not make the evaluator
    itself the final architecture-level authority for model selection."
    A caller may pass one in only if a human decision has already been
    made elsewhere; this function performs no cross-candidate comparison
    of any kind.
    """
    if not trajectories:
        raise ValueError("build_experiment_record requires at least one trajectory")
    verdicts = verdicts or {}
    results_per_model = [
        ExperimentModelResult(
            model_id=trajectory.candidate_id,
            metrics=build_model_evaluation_record(
                trajectory,
                role_under_test=role_under_test,
                verdict=verdicts.get(trajectory.trajectory_id),
            ).metrics,
        )
        for trajectory in trajectories
    ]
    return ExperimentRecord(
        provenance=Provenance(
            run_id=experiment_id,
            stage=PipelineStage.JUDGE,
            source_component="Evaluation Results Builder",
        ),
        experiment_id=experiment_id,
        role_under_test=role_under_test,
        candidate_model_ids=[t.candidate_id for t in trajectories],
        evaluation_dataset_id=dataset_ref(dataset_id, dataset_version),
        results_per_model=results_per_model,
        winner_model_id=winner_model_id,
    )
