from __future__ import annotations

import ast
import inspect

import pytest

import trackA.evaluation.judge as judge_module
from trackA.evaluation.judge import BenchmarkJudge, objective_outcome_scorer
from trackA.registries.errors import AccessDeniedError
from trackA.registries.skills import SkillRegistry
from trackA.schemas.common import PipelineStage
from trackA.schemas.evaluation import EvaluationJudgePackage
from tests.conftest import make_manifest_provenance, make_provenance


def make_package(run_id, **overrides) -> EvaluationJudgePackage:
    data = dict(
        provenance=make_provenance(run_id, PipelineStage.JUDGE),
        trajectory_id="traj-1",
        blinded_candidate_label="candidate_1",
        role="specialist",
        task_requirements="Determine whether the endpoint is IDOR-vulnerable.",
        claimed_result={"vulnerable": True},
        objective_outcome={"vulnerable": True},
    )
    data.update(overrides)
    return EvaluationJudgePackage(**data)


# --- Judge / Skill Registry structural separation (task brief §7) ----------


def test_judge_module_never_imports_skill_registry():
    """Static check: the benchmarking Judge's own source file contains no
    *import* of the Skill Registry (or anything skill-related) — mirrors
    JDG-001's style (docs/11_TEST_PLAN_README.md: 'no substring match
    against any SkillManifest.methodology'). Deliberately checks only
    `import`/`from ... import` statements via the AST, not the whole
    source text: the module's own docstring legitimately *discusses* why
    no such import exists, and a raw substring search over that prose
    would trip on its own explanation."""
    source = inspect.getsource(judge_module)
    tree = ast.parse(source)
    imported_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_names.append(node.module)
            imported_names.extend(alias.name for alias in node.names)
    assert not any("skill" in name.lower() for name in imported_names), imported_names


def test_benchmark_judge_constructor_accepts_no_registry_parameter():
    """There is no parameter this class could even receive a
    SkillRegistry (or any registry) through."""
    params = inspect.signature(BenchmarkJudge.__init__).parameters
    assert set(params) <= {"self", "scorer", "reasoner", "judge_candidate_id", "judge_model_version"}


def test_skill_registry_still_rejects_a_caller_naming_itself_the_benchmark_judge():
    """Functional proof, independent of the static check above: even if
    a reference to the real SkillRegistry somehow reached this
    component, the registry's own existing caller allowlist
    (trackA.registries.skills, Context 2, unmodified) still rejects it —
    defense in depth, the same pattern already relied on for the
    live-pipeline Judge."""
    registry = SkillRegistry()
    registry.register_from_dict(
        {
            "skill_id": "idor_v1",
            "vulnerability_class": "IDOR",
            "methodology": "test",
            "system_prompt": "test",
            "few_shot_examples": [],
            "references": [],
            "expected_inputs": {},
            "expected_outputs": {},
            "permissions": [],
            "version": "1.0.0",
            "provenance": make_manifest_provenance().model_dump(mode="json"),
            "validation_status": "active",
        }
    )
    with pytest.raises(AccessDeniedError):
        registry.lookup("idor_v1", caller="benchmark_judge")


# --- scoring behavior --------------------------------------------------------


def test_objective_outcome_scorer_matches():
    pkg = make_package("r1", claimed_result={"vulnerable": True}, objective_outcome={"vulnerable": True})
    assert objective_outcome_scorer(pkg) == {"objective_outcome_match": 1.0}


def test_objective_outcome_scorer_mismatch():
    pkg = make_package("r1", claimed_result={"vulnerable": False}, objective_outcome={"vulnerable": True})
    assert objective_outcome_scorer(pkg) == {"objective_outcome_match": 0.0}


def test_objective_outcome_scorer_returns_empty_when_no_ground_truth():
    """Task brief §7: the Judge must not pretend to be ground truth when
    none is available -- the default scorer reports nothing at all
    rather than inventing a number."""
    pkg = make_package("r1", claimed_result={"vulnerable": True}, objective_outcome=None)
    assert objective_outcome_scorer(pkg) == {}


def test_benchmark_judge_evaluate_produces_verdict_with_matching_blinded_label():
    judge = BenchmarkJudge()
    pkg = make_package("r1")
    verdict = judge.evaluate(pkg, experiment_id="exp-1")
    assert verdict.blinded_candidate_label == pkg.blinded_candidate_label
    assert verdict.package_id == pkg.package_id
    assert verdict.contains_skill_content is False


def test_benchmark_judge_custom_scorer_is_pluggable():
    """Task brief §9: do not hardcode a single scoring rubric."""

    def custom_scorer(package: EvaluationJudgePackage):
        return {"custom_dimension": 0.42}

    judge = BenchmarkJudge(scorer=custom_scorer)
    verdict = judge.evaluate(make_package("r1"), experiment_id="exp-1")
    assert verdict.dimension_scores == {"custom_dimension": 0.42}


def test_benchmark_judge_requires_model_version_with_candidate_id():
    with pytest.raises(ValueError):
        BenchmarkJudge(judge_candidate_id="judge-cand-a")


def test_benchmark_judge_records_its_own_model_provenance_when_model_backed():
    judge = BenchmarkJudge(judge_candidate_id="judge-cand-a", judge_model_version="v1")
    verdict = judge.evaluate(make_package("r1"), experiment_id="exp-1")
    assert verdict.provenance.model_id == "judge-cand-a"
    assert verdict.provenance.model_version == "v1"


def test_benchmark_judge_never_declares_a_winner():
    """A single verdict scores one candidate only -- cross-candidate
    comparison/selection is explicitly not this class's job (task brief
    §11)."""
    judge = BenchmarkJudge()
    verdict = judge.evaluate(make_package("r1"), experiment_id="exp-1")
    assert not hasattr(verdict, "winner")
    assert not hasattr(verdict, "is_best")
