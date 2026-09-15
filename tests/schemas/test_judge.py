from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.schemas.common import PipelineStage
from trackA.schemas.judge import JudgeInput, JudgeRoutingDecision
from tests.conftest import make_provenance


def test_judge_input_defaults_contains_skill_content_false(run_id):
    ji = JudgeInput(
        provenance=make_provenance(run_id, PipelineStage.JUDGE),
        worker_output_record_ids=["e1", "e2"],
        accumulated_evidence={"endpoints": ["/api/v1/users/{id}"]},
    )
    assert ji.contains_skill_content is False


def test_judge_input_cannot_be_constructed_with_skill_content_true(run_id):
    with pytest.raises(ValidationError):
        JudgeInput(
            provenance=make_provenance(run_id, PipelineStage.JUDGE),
            worker_output_record_ids=["e1"],
            accumulated_evidence={"idor_methodology": "try incrementing user IDs"},
            contains_skill_content=True,
        )


def test_judge_input_requires_at_least_one_worker_output(run_id):
    with pytest.raises(ValidationError):
        JudgeInput(
            provenance=make_provenance(run_id, PipelineStage.JUDGE),
            worker_output_record_ids=[],
            accumulated_evidence={},
        )


def _routing(run_id, **overrides):
    data = dict(
        provenance=make_provenance(
            run_id, PipelineStage.JUDGE, model_id="judge-model", model_version="v1"
        ),
        decision="route_to_skill",
        target_skill_id="idor_v1",
        reasoning="endpoint pattern consistent with IDOR prerequisites",
        confidence=0.78,
    )
    data.update(overrides)
    return JudgeRoutingDecision(**data)


def test_routing_decision_valid(run_id):
    decision = _routing(run_id)
    assert decision.target_skill_id == "idor_v1"


def test_routing_decision_requires_skill_id_when_routing(run_id):
    with pytest.raises(ValidationError):
        _routing(run_id, target_skill_id=None)


def test_routing_decision_confidence_out_of_range(run_id):
    with pytest.raises(ValidationError):
        _routing(run_id, confidence=1.5)


def test_routing_decision_requires_model_provenance(run_id):
    with pytest.raises(ValidationError):
        JudgeRoutingDecision(
            provenance=make_provenance(run_id, PipelineStage.JUDGE),
            decision="drop",
            reasoning="insufficient evidence",
            confidence=0.1,
        )
