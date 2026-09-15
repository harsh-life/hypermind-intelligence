from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.schemas.common import PipelineStage
from trackA.schemas.scope import Run, RunScope, ScopeDecision, ScopeRequest
from tests.conftest import make_provenance


def _request(run_id):
    return ScopeRequest(
        provenance=make_provenance(run_id, PipelineStage.SCOPE_GATE),
        target_identifier="*.example-bounty.com",
        authorization_reference="https://bugcrowd.com/example-program/scope",
        requested_by="harsh",
    )


def test_scope_request_wrong_stage_rejected(run_id):
    with pytest.raises(ValidationError):
        ScopeRequest(
            provenance=make_provenance(run_id, PipelineStage.ORCHESTRATOR),
            target_identifier="*.example.com",
            authorization_reference="https://example.com/scope",
            requested_by="harsh",
        )


def test_scope_decision_deny_reason_required_field_present(run_id):
    req = _request(run_id)
    decision = ScopeDecision(
        provenance=make_provenance(run_id, PipelineStage.SCOPE_GATE),
        request_record_id=req.provenance.record_id,
        decision="deny",
        reason="ambiguous target match",
        policy_version="scope-policy-v3",
    )
    assert decision.decision == "deny"


def test_scope_decision_rejects_invalid_decision_value(run_id):
    with pytest.raises(ValidationError):
        ScopeDecision(
            provenance=make_provenance(run_id, PipelineStage.SCOPE_GATE),
            request_record_id="x",
            decision="maybe",
            reason="unclear",
            policy_version="v1",
        )


def test_runscope_pending_decision(run_id):
    req = _request(run_id)
    rs = RunScope(request=req)
    assert rs.decision is None
    assert rs.is_authorized is False


def test_runscope_authorized_when_allow(run_id):
    req = _request(run_id)
    decision = ScopeDecision(
        provenance=make_provenance(run_id, PipelineStage.SCOPE_GATE),
        request_record_id=req.provenance.record_id,
        decision="allow",
        reason="target matches authorized scope pattern",
        policy_version="scope-policy-v3",
    )
    rs = RunScope(request=req, decision=decision)
    assert rs.is_authorized is True


def test_runscope_rejects_mismatched_decision(run_id):
    req = _request(run_id)
    decision = ScopeDecision(
        provenance=make_provenance(run_id, PipelineStage.SCOPE_GATE),
        request_record_id="not-the-request-id",
        decision="allow",
        reason="x",
        policy_version="v1",
    )
    with pytest.raises(ValidationError):
        RunScope(request=req, decision=decision)


def test_run_requires_matching_run_id(run_id):
    req = _request(run_id)
    rs = RunScope(request=req)
    with pytest.raises(ValidationError):
        Run(run_id="a-different-run-id", scope=rs)


def test_run_valid(run_id):
    req = _request(run_id)
    rs = RunScope(request=req)
    run = Run(run_id=run_id, scope=rs)
    assert run.started_at
