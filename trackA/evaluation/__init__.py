"""Model Evaluation / AI Competition Lab. Context 4.

Builds the controlled evaluation system that compares Model Registry
candidates (trackA.registries.models) against real task trajectories
(trackA.schemas.evaluation) and produces evaluation evidence — never a
side effect on registry approval state, never a live-pipeline decision.

    docs/16_EVALUATION_BENCHMARKING.md (OD-27, [LOCKED]): the method.
    trackA.schemas.evaluation: the trajectory/case/judge-package shapes.
    trackA.schemas.research: the aggregate, persisted results
        (ExperimentRecord, ModelEvaluationRecord, DatasetRecord) — reused
        unmodified, not duplicated.

Modules:

    cases       BenchmarkCaseStore, DatasetStore (versioned datasets)
    harness     EvaluationHarness — runs one case against every
                registered candidate for a role, sequentially, under
                identical starting conditions; bounded retry for
                technical failure, no retry for refusal
    judge_package
                Candidate-identity blinding + EvaluationJudgePackage
                construction
    judge       BenchmarkJudge — scores a blinded package; structurally
                cannot reach the Skill Registry (no import, no
                parameter, nothing to pass one through)
    results     Folds trajectories + verdicts into the existing
                ExperimentRecord/ModelEvaluationRecord schemas
    storage     Local, append-only JSON artifact persistence
    promptfoo   Optional, modular supplementary checks — zero coupling
                from every module above

Explicitly NOT implemented here (Context-4 task brief §21): Scope Gate,
authorization policy, real external network/tool execution, Docker
orchestration, Nuclei, human validation, Track B, Darwin, live research-
store feedback into decisions, autonomous model promotion, automatic
registry approval, a production dashboard, or a distributed evaluation
cluster.
"""
from __future__ import annotations

from trackA.evaluation.cases import BenchmarkCaseStore, DatasetStore
from trackA.evaluation.errors import (
    ArtifactAlreadyExistsError,
    DuplicateDatasetVersionError,
    EvaluationError,
    NoCandidatesRegisteredError,
    UnknownCaseError,
    UnknownDatasetError,
)
from trackA.evaluation.harness import EvaluationHarness, classify_result
from trackA.evaluation.judge import BenchmarkJudge
from trackA.evaluation.judge_package import assign_blind_labels, build_judge_package
from trackA.evaluation.results import (
    build_experiment_record,
    build_model_evaluation_record,
    dataset_ref,
    parse_dataset_ref,
)
from trackA.evaluation.storage import read_record, write_record

__all__ = [
    "EvaluationError",
    "UnknownCaseError",
    "UnknownDatasetError",
    "DuplicateDatasetVersionError",
    "NoCandidatesRegisteredError",
    "ArtifactAlreadyExistsError",
    "BenchmarkCaseStore",
    "DatasetStore",
    "EvaluationHarness",
    "classify_result",
    "assign_blind_labels",
    "build_judge_package",
    "BenchmarkJudge",
    "build_model_evaluation_record",
    "build_experiment_record",
    "dataset_ref",
    "parse_dataset_ref",
    "write_record",
    "read_record",
]
