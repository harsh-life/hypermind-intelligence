"""Candidate-identity blinding + EvaluationJudgePackage construction.
Context-4 task brief §3/§7/§8.
"""
from __future__ import annotations

import random
from typing import Dict, List

from trackA.schemas.common import PipelineStage, Provenance
from trackA.schemas.evaluation import BenchmarkCase, EvaluationJudgePackage, EvaluationTrajectory


def assign_blind_labels(candidate_ids: List[str], *, seed: str) -> Dict[str, str]:
    """candidate_id -> "candidate_N" label, order randomized by a
    seeded RNG so the mapping is reproducible for a given `seed` (task
    brief §17: reproducibility) without leaking registration order,
    alphabetical order, or any other identity-correlated ordering to
    whoever sees the labels (task brief §3: "blinded to the Judge where
    practical"). Pass the experiment_id as `seed` so every package built
    within one experiment shares one consistent candidate_id<->label
    mapping, but a different experiment gets an independently-shuffled
    one.
    """
    ordered = sorted(set(candidate_ids))
    shuffled = ordered[:]
    random.Random(seed).shuffle(shuffled)
    return {candidate_id: f"candidate_{i + 1}" for i, candidate_id in enumerate(shuffled)}


def build_judge_package(
    trajectory: EvaluationTrajectory,
    case: BenchmarkCase,
    *,
    blinded_candidate_label: str,
    experiment_id: str,
) -> EvaluationJudgePackage:
    """Assembles the minimum relevant package for a Judge to score
    `trajectory` (docs/16_EVALUATION_BENCHMARKING.md: "the candidate's
    trajectory, actions performed, tool results the candidate itself
    produced, evidence generated, the candidate's claimed result, the
    objective outcome, and relevant resource/efficiency information").

    Never reads `trajectory.candidate_id`, `.candidate_model_version`,
    `.runtime_backend`, or `.runtime_config` — `EvaluationJudgePackage`
    has no field to put them in (trackA/schemas/evaluation.py), so this
    is a structural guarantee, not a discipline this function has to
    remember to uphold.
    """
    actions_taken = [
        {"action_type": step.action_type, "description": step.description} for step in trajectory.steps
    ]
    evidence_produced = [
        {"description": step.description, "detail": step.detail}
        for step in trajectory.steps
        if step.action_type in ("tool_result", "final_result")
    ]
    return EvaluationJudgePackage(
        provenance=Provenance(
            run_id=experiment_id,
            stage=PipelineStage.JUDGE,
            source_component="Judge Package Builder",
        ),
        trajectory_id=trajectory.trajectory_id,
        blinded_candidate_label=blinded_candidate_label,
        role=trajectory.role,
        task_requirements=case.task_description,
        capabilities_available=trajectory.capabilities_available,
        actions_taken=actions_taken,
        evidence_produced=evidence_produced,
        claimed_result=trajectory.final_output,
        objective_outcome=case.objective_outcome,
        resource_efficiency={"latency_ms": trajectory.latency_ms, "retry_count": trajectory.retry_count},
    )
