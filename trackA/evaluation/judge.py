"""BenchmarkJudge — scores a blinded EvaluationJudgePackage. Context-4
task brief §7/§9.

[Structural guarantee] This module never imports
`trackA.registries.skills` / `SkillRegistry`, and `BenchmarkJudge` accepts
no such registry (or anything resembling one) as a constructor or method
parameter — there is no path through this class that could reach the
Skill Registry even if a caller wanted one, mirroring the "enforced by
omission" pattern docs/02_COMPONENT_SPECS.md §3 already documents for the
live-pipeline Judge. `tests/evaluation/test_judge.py` proves this two
ways: statically (no `skills` reference anywhere in this file's source)
and functionally (the real `SkillRegistry.lookup` still rejects a caller
identifying itself as this benchmarking Judge, per its own existing
caller allowlist).

The Judge here answers "how well did the candidate perform?", never "what
is actually true?" (task brief §7) — `scorer`/`reasoner` are pluggable
precisely so this class never hardcodes what "good" means; the one
built-in default (`objective_outcome_scorer`) only ever compares a
candidate's claimed result against a case's own pre-existing objective
outcome, and returns no score at all when none exists rather than
inventing one.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional

from trackA.schemas.common import PipelineStage, Provenance
from trackA.schemas.evaluation import EvaluationJudgePackage, EvaluationJudgeVerdict

Scorer = Callable[[EvaluationJudgePackage], Dict[str, float]]
Reasoner = Callable[[EvaluationJudgePackage, Dict[str, float]], str]


def objective_outcome_scorer(package: EvaluationJudgePackage) -> Dict[str, float]:
    """Default scorer: the only signal it ever reports is whether the
    candidate's claimed result matches the case's own objective outcome —
    never a judgment about a case with no objective outcome at all (task
    brief §7: "do not make the Judge the sole source of truth when
    objective evaluation is available" — and, symmetrically, do not let
    it invent one when it is not)."""
    if package.objective_outcome is None:
        return {}
    matched = package.claimed_result == package.objective_outcome
    return {"objective_outcome_match": 1.0 if matched else 0.0}


def _default_reasoner(package: EvaluationJudgePackage, scores: Dict[str, float]) -> str:
    if package.objective_outcome is not None:
        matched = package.claimed_result == package.objective_outcome
        return (
            f"Objective outcome {'matched' if matched else 'did not match'} the "
            f"candidate's claimed result. scores={scores}"
        )
    return f"No objective outcome available for this case; scores={scores}"


class BenchmarkJudge:
    """Scores one `EvaluationJudgePackage` at a time. Holds no reference
    to any Model/Tool/Worker/Skill registry, any trajectory store, or any
    other candidate's package — see module docstring."""

    def __init__(
        self,
        *,
        scorer: Scorer = objective_outcome_scorer,
        reasoner: Reasoner = _default_reasoner,
        judge_candidate_id: Optional[str] = None,
        judge_model_version: Optional[str] = None,
    ) -> None:
        if judge_candidate_id and not judge_model_version:
            raise ValueError(
                "BenchmarkJudge: judge_model_version is required when "
                "judge_candidate_id is set (mirrors Provenance's own "
                "model_id/model_version pairing rule)"
            )
        self._scorer = scorer
        self._reasoner = reasoner
        self._judge_candidate_id = judge_candidate_id
        self._judge_model_version = judge_model_version

    def evaluate(self, package: EvaluationJudgePackage, *, experiment_id: str) -> EvaluationJudgeVerdict:
        scores = self._scorer(package)
        reasoning = self._reasoner(package, scores)
        return EvaluationJudgeVerdict(
            provenance=Provenance(
                run_id=experiment_id,
                stage=PipelineStage.JUDGE,
                source_component="Benchmark Judge",
                model_id=self._judge_candidate_id,
                model_version=self._judge_model_version,
            ),
            package_id=package.package_id,
            blinded_candidate_label=package.blinded_candidate_label,
            dimension_scores=scores,
            reasoning=reasoning,
        )
