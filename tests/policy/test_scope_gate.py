from __future__ import annotations

from trackA.policy.requests import NetworkOperationRequest
from trackA.policy.scope_gate import ScopeDenialReason, ScopeGate, decide_scope


def _req(run_id, **overrides):
    data = {"run_id": run_id, "hostname": "api.example.com", "protocol": "https", "port": 443}
    data.update(overrides)
    return NetworkOperationRequest(**data)


class TestClearlyAuthorized:
    def test_allowed_subdomain(self, run_id, run_scope_factory):
        rs = run_scope_factory()
        decision = decide_scope(_req(run_id), rs)
        assert decision.decision == "allow"
        assert decision.reason_code is None

    def test_allowed_exact_domain(self, run_id, run_scope_factory):
        rs = run_scope_factory(allowed_domains=["example.com"], allowed_subdomains=[])
        decision = decide_scope(_req(run_id, hostname="example.com"), rs)
        assert decision.decision == "allow"

    def test_allowed_ip(self, run_id, run_scope_factory):
        rs = run_scope_factory(allowed_domains=[], allowed_subdomains=[], allowed_ips=["10.0.0.0/24"])
        decision = decide_scope(_req(run_id, hostname=None, ip="10.0.0.5"), rs)
        assert decision.decision == "allow"

    def test_unrestricted_port_and_protocol_still_allows(self, run_id, run_scope_factory):
        rs = run_scope_factory(allowed_ports=[], allowed_protocols=[])
        decision = decide_scope(_req(run_id, port=9999, protocol="ftp"), rs)
        assert decision.decision == "allow"

    def test_matching_restricted_port_and_protocol(self, run_id, run_scope_factory):
        rs = run_scope_factory(allowed_ports=[443], allowed_protocols=["https"])
        decision = decide_scope(_req(run_id), rs)
        assert decision.decision == "allow"


class TestClearlyUnauthorized:
    def test_out_of_scope_domain(self, run_id, run_scope_factory):
        rs = run_scope_factory()
        decision = decide_scope(_req(run_id, hostname="totally-different.org"), rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.DOMAIN_NOT_ALLOWED

    def test_out_of_scope_ip(self, run_id, run_scope_factory):
        rs = run_scope_factory(allowed_ips=["10.0.0.0/24"])
        decision = decide_scope(_req(run_id, hostname=None, ip="192.168.1.1"), rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.IP_NOT_ALLOWED

    def test_excluded_domain_wins_over_wildcard_inclusion(self, run_id, run_scope_factory):
        rs = run_scope_factory(excluded_domains=["admin.example.com"])
        decision = decide_scope(_req(run_id, hostname="admin.example.com"), rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.DOMAIN_EXCLUDED

    def test_excluded_ip_wins_over_cidr_inclusion(self, run_id, run_scope_factory):
        rs = run_scope_factory(allowed_ips=["10.0.0.0/24"], excluded_ips=["10.0.0.5"])
        decision = decide_scope(_req(run_id, hostname=None, ip="10.0.0.5"), rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.IP_EXCLUDED

    def test_prohibited_operation_denies_even_when_target_in_scope(self, run_id, run_scope_factory):
        rs = run_scope_factory(prohibited_operation_classes=["active_exploitation"])
        decision = decide_scope(_req(run_id, operation_class="active_exploitation"), rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.PROHIBITED_OPERATION

    def test_disallowed_port(self, run_id, run_scope_factory):
        rs = run_scope_factory(allowed_ports=[443])
        decision = decide_scope(_req(run_id, port=8080), rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.PORT_NOT_ALLOWED

    def test_disallowed_protocol(self, run_id, run_scope_factory):
        rs = run_scope_factory(allowed_protocols=["https"])
        decision = decide_scope(_req(run_id, protocol="http"), rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.PROTOCOL_NOT_ALLOWED


class TestAmbiguousOrMissing:
    def test_missing_run_scope_denies(self, run_id):
        decision = decide_scope(_req(run_id), None)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.MISSING_RUN_SCOPE

    def test_unestablished_candidate_run_scope_denies(self, run_id, candidate_run_scope_factory):
        rs = candidate_run_scope_factory()
        assert rs.is_established is False
        decision = decide_scope(_req(run_id), rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.RUN_SCOPE_NOT_ESTABLISHED

    def test_no_target_specified_denies(self, run_id, run_scope_factory):
        rs = run_scope_factory()
        decision = decide_scope(NetworkOperationRequest(run_id=run_id), rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.NO_TARGET_SPECIFIED

    def test_both_hostname_and_ip_must_each_pass(self, run_id, run_scope_factory):
        # hostname in scope, ip not listed at all -> deny (AND semantics,
        # not OR — see decide_scope's design notes).
        rs = run_scope_factory(allowed_ips=[])
        decision = decide_scope(_req(run_id, hostname="api.example.com", ip="8.8.8.8"), rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.IP_NOT_ALLOWED

    def test_both_hostname_and_ip_excluded_ip_denies_even_if_hostname_ok(
        self, run_id, run_scope_factory
    ):
        rs = run_scope_factory(allowed_ips=["8.8.8.8"], excluded_ips=["8.8.8.8"])
        decision = decide_scope(_req(run_id, hostname="api.example.com", ip="8.8.8.8"), rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.IP_EXCLUDED


class TestDeterminism:
    def test_same_inputs_same_decision(self, run_id, run_scope_factory):
        rs = run_scope_factory()
        req = _req(run_id)
        d1 = decide_scope(req, rs)
        d2 = decide_scope(req, rs)
        assert d1.decision == d2.decision
        assert d1.reason_code == d2.reason_code
        assert d1.reason == d2.reason


class TestScopeGateAuthorizeAction:
    def test_dynamic_capability_request_still_requires_authorization(
        self, run_id, run_scope_factory, action_factory, scope_gate: ScopeGate
    ):
        rs = run_scope_factory()
        action = action_factory(proposed_parameters={"domain": "api.example.com"})
        decision = scope_gate.authorize_action(action, rs)
        assert decision.decision == "allow"

    def test_dynamic_capability_request_out_of_scope_denied(
        self, run_id, run_scope_factory, action_factory, scope_gate: ScopeGate
    ):
        rs = run_scope_factory()
        action = action_factory(proposed_parameters={"domain": "attacker-controlled.net"})
        decision = scope_gate.authorize_action(action, rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.DOMAIN_NOT_ALLOWED

    def test_missing_run_scope_denies_every_action(
        self, run_id, action_factory, scope_gate: ScopeGate
    ):
        action = action_factory(proposed_parameters={"domain": "example.com"})
        decision = scope_gate.authorize_action(action, None)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.MISSING_RUN_SCOPE

    def test_unnormalizable_action_fails_safely_as_malformed(
        self, run_id, run_scope_factory, action_factory, scope_gate: ScopeGate
    ):
        rs = run_scope_factory()
        action = action_factory(proposed_parameters={"no_recognized_key": "x"})
        decision = scope_gate.authorize_action(action, rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.MALFORMED_REQUEST

    def test_multi_host_action_fails_safely_rather_than_checking_first_only(
        self, run_id, run_scope_factory, action_factory, scope_gate: ScopeGate
    ):
        rs = run_scope_factory()
        action = action_factory(
            proposed_parameters={"hosts": ["api.example.com", "attacker-controlled.net"]}
        )
        decision = scope_gate.authorize_action(action, rs)
        assert decision.decision == "deny"
        assert decision.reason_code == ScopeDenialReason.MALFORMED_REQUEST


class TestScopeGateCheckScope:
    def test_authorized_pattern_matches(self, scope_gate: ScopeGate):
        assert scope_gate.check_scope(
            "api.example-bounty.com", authorized_scope_patterns=["*.example-bounty.com"]
        ) is True

    def test_unauthorized_pattern_denies(self, scope_gate: ScopeGate):
        assert scope_gate.check_scope(
            "api.other.com", authorized_scope_patterns=["*.example-bounty.com"]
        ) is False

    def test_exclusion_overrides_wildcard_inclusion(self, scope_gate: ScopeGate):
        assert scope_gate.check_scope(
            "admin.example-bounty.com",
            authorized_scope_patterns=["*.example-bounty.com"],
            explicitly_excluded=["admin.example-bounty.com"],
        ) is False

    def test_empty_target_denies(self, scope_gate: ScopeGate):
        assert scope_gate.check_scope(
            "", authorized_scope_patterns=["*.example-bounty.com"]
        ) is False

    def test_no_authorized_patterns_denies(self, scope_gate: ScopeGate):
        assert scope_gate.check_scope("example.com", authorized_scope_patterns=[]) is False
