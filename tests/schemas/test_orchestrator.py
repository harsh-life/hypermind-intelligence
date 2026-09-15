from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.schemas.common import PipelineStage
from trackA.schemas.orchestrator import OrchestratorAction
from tests.conftest import make_provenance


def _valid(run_id, **overrides):
    data = dict(
        provenance=make_provenance(
            run_id, PipelineStage.ORCHESTRATOR, model_id="planner-model", model_version="v1"
        ),
        proposed_action_type="tool_execution",
        target_registry_id="subfinder",
        proposed_parameters={"domain": "example-bounty.com"},
        session_action_count=1,
    )
    data.update(overrides)
    return OrchestratorAction(**data)


def test_valid_action(run_id):
    action = _valid(run_id)
    assert action.proposed_action_type == "tool_execution"


def test_rejects_invalid_action_type(run_id):
    with pytest.raises(ValidationError):
        _valid(run_id, proposed_action_type="delete_all_findings")


def test_requires_model_provenance(run_id):
    with pytest.raises(ValidationError):
        OrchestratorAction(
            provenance=make_provenance(run_id, PipelineStage.ORCHESTRATOR),
            proposed_action_type="tool_execution",
            target_registry_id="subfinder",
            proposed_parameters={},
            session_action_count=1,
        )


def test_session_action_count_must_be_positive(run_id):
    with pytest.raises(ValidationError):
        _valid(run_id, session_action_count=0)
