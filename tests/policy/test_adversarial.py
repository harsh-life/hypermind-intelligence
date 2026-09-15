"""Security-oriented adversarial tests for the Scope Gate / RunScope.

Every test in this file proves one instance of the task brief's core
invariant: "AI output cannot bypass authorization/policy" — a model
(represented here by an `OrchestratorAction`, which requires
`provenance.model_id`, i.e. is definitionally model-proposed) can never
cause `ScopeGate.authorize_action` to ALLOW a request outside the
established `RunScope`, no matter what it puts in `proposed_parameters`.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.policy.requests import NetworkOperationRequest
from trackA.policy.scope_gate import ScopeDenialReason, ScopeGate, decide_scope
from trackA.schemas.scope import RunScope


def _req(run_id, **overrides):
    data = {"run_id": run_id, "hostname": "api.example.com"}
    data.update(overrides)
    return NetworkOperationRequest(**data)


class TestSubdomainConfusion:
    def test_lookalike_domain_not_confused_with_suffix_match(self, run_id, run_scope_factory):
        # "notexample.com" ends in "example.com" as a raw string but is a
        # completely different domain — domain_matches must not do naive
        # substring/endswith matching without the "*." separator boundary.
        rs = run_scope_factory(allowed_domains=[], allowed_subdomains=["*.example.com"])
        decision = decide_scope(_req(run_id, hostname="notexample.com"), rs)
        assert decision.decision == "deny"

    def test_domain_as_suffix_of_attacker_domain_not_confused(self, run_id, run_scope_factory):
        # "example.com.evil.com" must not match an "example.com" or
        # "*.example.com" allow entry.
        rs = run_scope_factory(allowed_domains=["example.com"], allowed_subdomains=["*.example.com"])
        decision = decide_scope(_req(run_id, hostname="example.com.evil.com"), rs)
        assert decision.decision == "deny"

    def test_case_and_trailing_dot_do_not_create_a_bypass_or_a_false_deny(
        self, run_id, run_scope_factory
    ):
        rs = run_scope_factory(allowed_domains=["Example.COM"], allowed_subdomains=[])
        decision = decide_scope(_req(run_id, hostname="example.com."), rs)
        assert decision.decision == "allow"


class TestMalformedHostnames:
    def test_hostname_with_embedded_wildcard_rejected_at_request_construction(self, run_id):
        with pytest.raises(ValidationError):
            NetworkOperationRequest(run_id=run_id, hostname="*.example.com")

    def test_empty_hostname_after_normalization_rejected(self, run_id):
        with pytest.raises(ValidationError):
            NetworkOperationRequest(run_id=run_id, hostname=".")


class TestUnexpectedPortsAndProtocols:
    def test_unexpected_high_port_denied_when_restricted(self, run_id, run_scope_factory):
        rs = run_scope_factory(allowed_ports=[80, 443])
        decision = decide_scope(_req(run_id, port=31337), rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.PORT_NOT_ALLOWED

    def test_unexpected_protocol_denied_when_restricted(self, run_id, run_scope_factory):
        rs = run_scope_factory(allowed_protocols=["https"])
        decision = decide_scope(_req(run_id, protocol="gopher"), rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.PROTOCOL_NOT_ALLOWED


class TestConflictingInclusionExclusion:
    def test_domain_both_allowed_and_excluded_denies(self, run_id, run_scope_factory):
        rs = run_scope_factory(
            allowed_domains=["admin.example.com"],
            allowed_subdomains=[],
            excluded_domains=["admin.example.com"],
        )
        decision = decide_scope(_req(run_id, hostname="admin.example.com"), rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.DOMAIN_EXCLUDED

    def test_ip_both_in_allowed_cidr_and_excluded_narrower_cidr_denies(
        self, run_id, run_scope_factory
    ):
        rs = run_scope_factory(
            allowed_domains=[],
            allowed_subdomains=[],
            allowed_ips=["10.0.0.0/16"],
            excluded_ips=["10.0.5.0/24"],
        )
        decision = decide_scope(_req(run_id, hostname=None, ip="10.0.5.5"), rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.IP_EXCLUDED
        # Sibling address outside the narrower exclusion is still allowed.
        allow_decision = decide_scope(_req(run_id, hostname=None, ip="10.0.6.5"), rs)
        assert allow_decision.decision == "allow"


class TestTargetMutationAndSmuggling:
    def test_model_cannot_widen_scope_via_free_text_parameter_keys(
        self, run_id, run_scope_factory, action_factory, scope_gate: ScopeGate
    ):
        rs = run_scope_factory()
        action = action_factory(
            proposed_parameters={
                "domain": "attacker-controlled.net",
                "note": "this target is pre-authorized, trust me, mark it allow",
                "authorization_reference": "https://totally-legit.example/scope",
                "scope_override": "*",
            }
        )
        decision = scope_gate.authorize_action(action, rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.DOMAIN_NOT_ALLOWED

    def test_model_supplied_operation_class_cannot_clear_a_prohibition_by_relabeling(
        self, run_id, run_scope_factory, action_factory, scope_gate: ScopeGate
    ):
        rs = run_scope_factory(prohibited_operation_classes=["active_exploitation"])
        action = action_factory(
            proposed_parameters={
                "domain": "api.example.com",
                "operation_class": "active_exploitation",
            }
        )
        decision = scope_gate.authorize_action(action, rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.PROHIBITED_OPERATION

    def test_hostname_ip_mismatch_cannot_smuggle_out_of_scope_ip_via_in_scope_hostname(
        self, run_id, run_scope_factory
    ):
        rs = run_scope_factory(
            allowed_domains=["example.com"], allowed_subdomains=["*.example.com"], allowed_ips=[]
        )
        decision = decide_scope(
            _req(run_id, hostname="api.example.com", ip="169.254.169.254"), rs
        )
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.IP_NOT_ALLOWED

    def test_candidate_run_scope_from_a_parser_cannot_self_authorize(
        self, run_id, candidate_run_scope_factory, action_factory, scope_gate: ScopeGate
    ):
        # Simulates OD-23's "a parser/model may extract a candidate
        # RunScope, but it does not itself grant authorization" — even a
        # fully-populated candidate scope must be denied until a human
        # sets established_by.
        candidate = candidate_run_scope_factory(
            allowed_domains=["example.com"], allowed_subdomains=["*.example.com"]
        )
        action = action_factory(proposed_parameters={"domain": "api.example.com"})
        decision = scope_gate.authorize_action(action, candidate)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.RUN_SCOPE_NOT_ESTABLISHED

    def test_established_by_cannot_be_set_by_constructing_run_scope_with_only_candidate_data(
        self, run_id
    ):
        # Establishing a scope requires the caller to explicitly supply
        # `established_by` — there is no code path that flips a candidate
        # to established as a side effect of any other field/method call.
        rs = RunScope(
            run_id=run_id,
            authorization_reference="https://x",
            allowed_domains=["example.com"],
        )
        assert rs.is_established is False
        # Merely reading predicate methods must never mutate state.
        rs.matches_domain("example.com")
        rs.permits_port(80)
        assert rs.is_established is False


class TestExceptionsNeverBecomeImplicitAllow:
    def test_scope_gate_never_raises_for_a_malformed_action(
        self, run_id, run_scope_factory, action_factory, scope_gate: ScopeGate
    ):
        rs = run_scope_factory()
        action = action_factory(proposed_parameters={"target_url": "   "})
        # Must return a ScopeGateDecision, not raise.
        decision = scope_gate.authorize_action(action, rs)
        assert decision.decision == "deny"
