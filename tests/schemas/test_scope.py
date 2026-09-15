from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.schemas.common import PipelineStage
from trackA.schemas.scope import Run, RunScope, ScopeAuthorization, ScopeDecision, ScopeRequest
from tests.conftest import make_provenance


def _request(run_id):
    return ScopeRequest(
        provenance=make_provenance(run_id, PipelineStage.SCOPE_GATE),
        target_identifier="*.example-bounty.com",
        authorization_reference="https://bugcrowd.com/example-program/scope",
        requested_by="harsh",
    )


def _run_scope(run_id, **overrides):
    data = {
        "run_id": run_id,
        "authorization_reference": "https://bugcrowd.com/example-program/scope",
        "allowed_domains": ["example.com"],
        "allowed_subdomains": ["*.example.com"],
        "established_by": "harsh",
    }
    data.update(overrides)
    return RunScope(**data)


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


def test_scope_authorization_pending_decision(run_id):
    req = _request(run_id)
    sa = ScopeAuthorization(request=req)
    assert sa.decision is None
    assert sa.is_authorized is False


def test_scope_authorization_authorized_when_allow(run_id):
    req = _request(run_id)
    decision = ScopeDecision(
        provenance=make_provenance(run_id, PipelineStage.SCOPE_GATE),
        request_record_id=req.provenance.record_id,
        decision="allow",
        reason="target matches authorized scope pattern",
        policy_version="scope-policy-v3",
    )
    sa = ScopeAuthorization(request=req, decision=decision)
    assert sa.is_authorized is True


def test_scope_authorization_rejects_mismatched_decision(run_id):
    req = _request(run_id)
    decision = ScopeDecision(
        provenance=make_provenance(run_id, PipelineStage.SCOPE_GATE),
        request_record_id="not-the-request-id",
        decision="allow",
        reason="x",
        policy_version="v1",
    )
    with pytest.raises(ValidationError):
        ScopeAuthorization(request=req, decision=decision)


def test_run_requires_matching_run_id(run_id):
    req = _request(run_id)
    sa = ScopeAuthorization(request=req)
    with pytest.raises(ValidationError):
        Run(run_id="a-different-run-id", scope=sa)


def test_run_valid(run_id):
    req = _request(run_id)
    sa = ScopeAuthorization(request=req)
    run = Run(run_id=run_id, scope=sa)
    assert run.started_at


def test_run_with_run_scope_matching_run_id(run_id):
    req = _request(run_id)
    sa = ScopeAuthorization(request=req)
    rs = _run_scope(run_id)
    run = Run(run_id=run_id, scope=sa, run_scope=rs)
    assert run.run_scope is rs


def test_run_rejects_mismatched_run_scope_run_id(run_id):
    req = _request(run_id)
    sa = ScopeAuthorization(request=req)
    rs = _run_scope("a-different-run-id")
    with pytest.raises(ValidationError):
        Run(run_id=run_id, scope=sa, run_scope=rs)


# --------------------------------------------------------------------------
# RunScope — the canonical, engagement-specific authorization object
# --------------------------------------------------------------------------


class TestRunScopeConstruction:
    def test_minimal_valid_run_scope(self, run_id):
        rs = _run_scope(run_id)
        assert rs.run_id == run_id
        assert rs.is_established is True

    def test_candidate_run_scope_not_established_by_default(self, run_id):
        rs = RunScope(
            run_id=run_id,
            authorization_reference="https://example.com/scope",
            allowed_domains=["example.com"],
        )
        assert rs.established_by is None
        assert rs.established_at is None
        assert rs.is_established is False

    def test_established_at_defaults_when_established_by_given(self, run_id):
        rs = _run_scope(run_id)
        assert rs.established_at

    def test_established_by_and_at_must_be_set_together(self, run_id):
        with pytest.raises(ValidationError):
            RunScope(
                run_id=run_id,
                authorization_reference="https://example.com/scope",
                allowed_domains=["example.com"],
                established_at="2026-01-01T00:00:00Z",
            )

    def test_empty_authorization_reference_rejected(self, run_id):
        with pytest.raises(ValidationError):
            RunScope(run_id=run_id, authorization_reference="")

    def test_extra_field_rejected(self, run_id):
        with pytest.raises(ValidationError):
            RunScope(
                run_id=run_id,
                authorization_reference="https://example.com/scope",
                unexpected_field="x",
            )

    def test_malformed_ip_entry_rejected(self, run_id):
        with pytest.raises(ValidationError):
            _run_scope(run_id, allowed_ips=["not-an-ip"])

    def test_malformed_excluded_ip_entry_rejected(self, run_id):
        with pytest.raises(ValidationError):
            _run_scope(run_id, excluded_ips=["999.999.999.999"])

    def test_port_out_of_range_rejected(self, run_id):
        with pytest.raises(ValidationError):
            _run_scope(run_id, allowed_ports=[70000])

    def test_port_zero_rejected(self, run_id):
        with pytest.raises(ValidationError):
            _run_scope(run_id, allowed_ports=[0])

    def test_valid_cidr_accepted(self, run_id):
        rs = _run_scope(run_id, allowed_ips=["10.0.0.0/24"])
        assert rs.allowed_ips == ["10.0.0.0/24"]

    def test_domains_normalized_lowercase_and_trailing_dot_stripped(self, run_id):
        rs = _run_scope(run_id, allowed_domains=["Example.COM."])
        assert rs.allowed_domains == ["example.com"]

    def test_protocols_normalized_lowercase(self, run_id):
        rs = _run_scope(run_id, allowed_protocols=["HTTPS", " Http "])
        assert rs.allowed_protocols == ["https", "http"]


class TestRunScopeDomainMatching:
    def test_exact_domain_matches_itself(self, run_id):
        rs = _run_scope(run_id, allowed_domains=["example.com"], allowed_subdomains=[])
        assert rs.matches_domain("example.com") is True

    def test_exact_domain_does_not_match_subdomain(self, run_id):
        rs = _run_scope(run_id, allowed_domains=["example.com"], allowed_subdomains=[])
        assert rs.matches_domain("api.example.com") is False

    def test_wildcard_matches_subdomain(self, run_id):
        rs = _run_scope(run_id, allowed_domains=[], allowed_subdomains=["*.example.com"])
        assert rs.matches_domain("api.example.com") is True
        assert rs.matches_domain("a.b.example.com") is True

    def test_wildcard_does_not_match_bare_apex(self, run_id):
        rs = _run_scope(run_id, allowed_domains=[], allowed_subdomains=["*.example.com"])
        assert rs.matches_domain("example.com") is False

    def test_wildcard_does_not_match_unrelated_domain(self, run_id):
        rs = _run_scope(run_id, allowed_domains=[], allowed_subdomains=["*.example.com"])
        assert rs.matches_domain("example.com.evil.com") is False
        assert rs.matches_domain("notexample.com") is False

    def test_domain_matching_case_insensitive(self, run_id):
        rs = _run_scope(run_id, allowed_domains=["Example.com"], allowed_subdomains=[])
        assert rs.matches_domain("EXAMPLE.COM") is True

    def test_no_match_when_no_patterns(self, run_id):
        rs = _run_scope(run_id, allowed_domains=[], allowed_subdomains=[])
        assert rs.matches_domain("example.com") is False

    def test_excluded_domain_detected(self, run_id):
        rs = _run_scope(run_id, excluded_domains=["admin.example.com"])
        assert rs.is_domain_excluded("admin.example.com") is True
        assert rs.is_domain_excluded("api.example.com") is False

    def test_excluded_domain_supports_wildcard(self, run_id):
        rs = _run_scope(run_id, excluded_domains=["*.internal.example.com"])
        assert rs.is_domain_excluded("db.internal.example.com") is True


class TestRunScopeIpMatching:
    def test_exact_ip_matches(self, run_id):
        rs = _run_scope(run_id, allowed_ips=["10.0.0.5"])
        assert rs.matches_ip("10.0.0.5") is True
        assert rs.matches_ip("10.0.0.6") is False

    def test_cidr_membership(self, run_id):
        rs = _run_scope(run_id, allowed_ips=["10.0.0.0/24"])
        assert rs.matches_ip("10.0.0.200") is True
        assert rs.matches_ip("10.0.1.1") is False

    def test_malformed_request_ip_never_matches(self, run_id):
        rs = _run_scope(run_id, allowed_ips=["10.0.0.0/24"])
        assert rs.matches_ip("not-an-ip") is False

    def test_excluded_ip_detected(self, run_id):
        rs = _run_scope(run_id, excluded_ips=["10.0.0.5"])
        assert rs.is_ip_excluded("10.0.0.5") is True

    def test_excluded_cidr_membership(self, run_id):
        rs = _run_scope(run_id, excluded_ips=["10.0.0.0/28"])
        assert rs.is_ip_excluded("10.0.0.5") is True
        assert rs.is_ip_excluded("10.0.1.5") is False


class TestRunScopePortsProtocols:
    def test_empty_allowed_ports_is_permissive(self, run_id):
        rs = _run_scope(run_id, allowed_ports=[])
        assert rs.permits_port(80) is True
        assert rs.permits_port(None) is True

    def test_nonempty_allowed_ports_restricts(self, run_id):
        rs = _run_scope(run_id, allowed_ports=[443])
        assert rs.permits_port(443) is True
        assert rs.permits_port(80) is False
        assert rs.permits_port(None) is False

    def test_empty_allowed_protocols_is_permissive(self, run_id):
        rs = _run_scope(run_id, allowed_protocols=[])
        assert rs.permits_protocol("https") is True
        assert rs.permits_protocol(None) is True

    def test_nonempty_allowed_protocols_restricts(self, run_id):
        rs = _run_scope(run_id, allowed_protocols=["https"])
        assert rs.permits_protocol("https") is True
        assert rs.permits_protocol("http") is False

    def test_protocol_matching_case_insensitive(self, run_id):
        rs = _run_scope(run_id, allowed_protocols=["https"])
        assert rs.permits_protocol("HTTPS") is True


class TestRunScopeProhibitedOperations:
    def test_no_prohibited_operations_by_default(self, run_id):
        rs = _run_scope(run_id)
        assert rs.is_operation_prohibited("active_exploitation") is False

    def test_prohibited_operation_detected(self, run_id):
        rs = _run_scope(run_id, prohibited_operation_classes=["active_exploitation"])
        assert rs.is_operation_prohibited("active_exploitation") is True
        assert rs.is_operation_prohibited("ACTIVE_EXPLOITATION") is True

    def test_none_operation_class_never_prohibited(self, run_id):
        rs = _run_scope(run_id, prohibited_operation_classes=["active_exploitation"])
        assert rs.is_operation_prohibited(None) is False
