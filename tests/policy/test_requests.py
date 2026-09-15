from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.policy.requests import NetworkOperationRequest, NormalizationError, from_orchestrator_action
from tests.policy.conftest import make_orchestrator_action


class TestNetworkOperationRequestConstruction:
    def test_minimal_valid(self, run_id):
        req = NetworkOperationRequest(run_id=run_id, hostname="example.com")
        assert req.hostname == "example.com"

    def test_no_target_is_constructible_but_flagged_downstream(self, run_id):
        # Deliberately NOT rejected at construction — see NetworkOperationRequest
        # docstring: this is the well-defined "insufficiently specified"
        # state the Scope Gate denies with a specific reason code.
        req = NetworkOperationRequest(run_id=run_id)
        assert req.hostname is None and req.ip is None

    def test_hostname_normalized_lowercase(self, run_id):
        req = NetworkOperationRequest(run_id=run_id, hostname="API.Example.COM")
        assert req.hostname == "api.example.com"

    def test_wildcard_hostname_rejected(self, run_id):
        with pytest.raises(ValidationError):
            NetworkOperationRequest(run_id=run_id, hostname="*.example.com")

    def test_blank_hostname_rejected(self, run_id):
        with pytest.raises(ValidationError):
            NetworkOperationRequest(run_id=run_id, hostname="   ")

    def test_hostname_with_whitespace_rejected(self, run_id):
        with pytest.raises(ValidationError):
            NetworkOperationRequest(run_id=run_id, hostname="example .com")

    def test_valid_ip_accepted(self, run_id):
        req = NetworkOperationRequest(run_id=run_id, ip="10.0.0.5")
        assert req.ip == "10.0.0.5"

    def test_cidr_rejected_as_request_ip(self, run_id):
        with pytest.raises(ValidationError):
            NetworkOperationRequest(run_id=run_id, ip="10.0.0.0/24")

    def test_malformed_ip_rejected(self, run_id):
        with pytest.raises(ValidationError):
            NetworkOperationRequest(run_id=run_id, ip="not-an-ip")

    def test_port_out_of_range_rejected(self, run_id):
        with pytest.raises(ValidationError):
            NetworkOperationRequest(run_id=run_id, hostname="example.com", port=99999)

    def test_protocol_normalized(self, run_id):
        req = NetworkOperationRequest(run_id=run_id, hostname="example.com", protocol="HTTPS")
        assert req.protocol == "https"

    def test_extra_field_rejected(self, run_id):
        with pytest.raises(ValidationError):
            NetworkOperationRequest(run_id=run_id, hostname="example.com", unexpected="x")


class TestFromOrchestratorAction:
    def test_url_with_scheme_and_port(self, action_factory):
        action = action_factory(proposed_parameters={"target_url": "https://api.example.com:8443/v1"})
        req = from_orchestrator_action(action)
        assert req.hostname == "api.example.com"
        assert req.protocol == "https"
        assert req.port == 8443

    def test_bare_domain_no_scheme(self, action_factory):
        action = action_factory(proposed_parameters={"domain": "example-bounty.com"})
        req = from_orchestrator_action(action)
        assert req.hostname == "example-bounty.com"
        assert req.protocol is None
        assert req.port is None

    def test_start_url_katana(self, action_factory):
        action = action_factory(proposed_parameters={"start_url": "https://example.com/"})
        req = from_orchestrator_action(action)
        assert req.hostname == "example.com"

    def test_target_endpoint_garak(self, action_factory):
        action = action_factory(proposed_parameters={"target_endpoint": "https://ai.example.com/api"})
        req = from_orchestrator_action(action)
        assert req.hostname == "ai.example.com"

    def test_ip_colon_port_ssrf_style(self, action_factory):
        action = action_factory(proposed_parameters={"target_url": "127.0.0.1:8080"})
        req = from_orchestrator_action(action)
        assert req.ip == "127.0.0.1"
        assert req.port == 8080

    def test_single_element_hosts_list_ok(self, action_factory):
        action = action_factory(proposed_parameters={"hosts": ["example.com"]})
        req = from_orchestrator_action(action)
        assert req.hostname == "example.com"

    def test_multi_element_hosts_list_raises(self, action_factory):
        action = action_factory(proposed_parameters={"hosts": ["a.example.com", "b.example.com"]})
        with pytest.raises(NormalizationError):
            from_orchestrator_action(action)

    def test_no_recognized_key_raises(self, action_factory):
        action = action_factory(proposed_parameters={"nonsense_field": "value"})
        with pytest.raises(NormalizationError):
            from_orchestrator_action(action)

    def test_ffuf_fuzz_placeholder_raises(self, action_factory):
        action = action_factory(
            proposed_parameters={"target_url_pattern": "https://example.com/FUZZ"}
        )
        with pytest.raises(NormalizationError):
            from_orchestrator_action(action)

    def test_source_action_id_set(self, action_factory):
        action = action_factory(proposed_parameters={"domain": "example.com"})
        req = from_orchestrator_action(action)
        assert req.source_action_id == action.provenance.record_id
        assert req.run_id == action.provenance.run_id

    def test_operation_class_override_passed_through(self, action_factory):
        action = action_factory(
            proposed_parameters={"domain": "example.com", "operation_class": "passive_recon"}
        )
        req = from_orchestrator_action(action)
        assert req.operation_class == "passive_recon"

    def test_unparseable_target_raises(self, action_factory):
        action = action_factory(proposed_parameters={"domain": "   "})
        with pytest.raises(NormalizationError):
            from_orchestrator_action(action)
