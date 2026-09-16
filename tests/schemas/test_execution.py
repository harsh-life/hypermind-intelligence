"""Tests for the Context-5 schema gap fill: AuthorizedAction / OrchestratorRejection.
See trackA/schemas/execution.py's module docstring for why these exist.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.conftest import make_provenance
from trackA.schemas.common import PipelineStage
from trackA.schemas.execution import AuthorizedAction, OrchestratorRejection
from trackA.schemas.gates import CheckResult


def _prov(run_id, **overrides):
    return make_provenance(run_id, PipelineStage.ORCHESTRATOR, **overrides)


class TestAuthorizedAction:
    def test_valid(self, run_id):
        action = AuthorizedAction(
            provenance=_prov(run_id),
            source_action_id="a1",
            action_type="tool_execution",
            target_registry_id="subfinder",
            authorized_parameters={"domain": "example.com"},
            checks_performed=[CheckResult(check_name="scope_gate", passed=True)],
        )
        assert action.action_type == "tool_execution"

    def test_rejects_model_or_tool_provenance(self, run_id):
        with pytest.raises(ValidationError):
            AuthorizedAction(
                provenance=_prov(run_id, model_id="planner", model_version="v1"),
                source_action_id="a1",
                action_type="tool_execution",
                target_registry_id="subfinder",
                authorized_parameters={},
                checks_performed=[],
            )

    def test_rejects_a_failing_check(self, run_id):
        with pytest.raises(ValidationError):
            AuthorizedAction(
                provenance=_prov(run_id),
                source_action_id="a1",
                action_type="tool_execution",
                target_registry_id="subfinder",
                authorized_parameters={},
                checks_performed=[CheckResult(check_name="scope_gate", passed=False)],
            )

    def test_rejects_wrong_stage(self, run_id):
        with pytest.raises(ValidationError):
            AuthorizedAction(
                provenance=make_provenance(run_id, PipelineStage.TOOL_EXECUTION),
                source_action_id="a1",
                action_type="tool_execution",
                target_registry_id="subfinder",
                authorized_parameters={},
                checks_performed=[],
            )


class TestOrchestratorRejection:
    def test_valid(self, run_id):
        rejection = OrchestratorRejection(
            provenance=_prov(run_id),
            source_action_id="a1",
            checks_performed=[CheckResult(check_name="scope_gate", passed=False)],
            reason="target not in scope",
            reason_code="domain_not_allowed",
        )
        assert rejection.reason_code == "domain_not_allowed"

    def test_requires_at_least_one_failing_check(self, run_id):
        with pytest.raises(ValidationError):
            OrchestratorRejection(
                provenance=_prov(run_id),
                source_action_id="a1",
                checks_performed=[CheckResult(check_name="scope_gate", passed=True)],
                reason="x",
                reason_code="x",
            )

    def test_requires_reason_and_code(self, run_id):
        with pytest.raises(ValidationError):
            OrchestratorRejection(
                provenance=_prov(run_id),
                source_action_id="a1",
                checks_performed=[CheckResult(check_name="scope_gate", passed=False)],
                reason="",
                reason_code="",
            )
