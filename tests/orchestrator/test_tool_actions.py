"""Tool-execution actions: the Scope Gate integration (task brief §5) and
`execute_tool_action`'s full check chain (task brief §3/§4)."""
from __future__ import annotations

from trackA.orchestrator.outcomes import ToolActionOutcome
from trackA.schemas.common import TrustClassification


class TestAuthorizedToolExecution:
    def test_in_scope_action_executes_and_captures_raw_output(self, run_context, action_factory, mock_tool_backend):
        outcome = run_context.execute_tool_action(action_factory())
        assert outcome.was_authorized
        assert outcome.invocation.result.exit_status == "success"
        assert outcome.invocation.raw_output.trust_classification == TrustClassification.RAW_OBSERVATION
        assert outcome.invocation.raw_output.content == "sub1.example.com"
        assert len(mock_tool_backend.calls) == 1

    def test_authorized_action_records_all_passing_checks(self, run_context, action_factory):
        outcome = run_context.execute_tool_action(action_factory())
        check_names = {c.check_name for c in outcome.authorized.checks_performed}
        assert {"schema_validation", "run_correlation", "scope_gate", "tool_registry", "resource_check"} <= check_names
        assert all(c.passed for c in outcome.authorized.checks_performed)

    def test_scope_decision_is_attached_and_allowed(self, run_context, action_factory):
        outcome = run_context.execute_tool_action(action_factory())
        assert outcome.scope_decision is not None
        assert outcome.scope_decision.is_allowed

    def test_outcome_recorded_in_run_context(self, run_context, action_factory):
        run_context.execute_tool_action(action_factory())
        assert len(run_context.tool_actions) == 1
        assert isinstance(run_context.tool_actions[0], ToolActionOutcome)


class TestOutOfScopeDenial:
    def test_out_of_scope_domain_denied_and_executor_never_called(self, run_context, action_factory, mock_tool_backend):
        outcome = run_context.execute_tool_action(
            action_factory(parameters={"domain": "not-authorized.org"})
        )
        assert not outcome.was_authorized
        assert outcome.rejected.reason_code == "domain_not_allowed"
        assert outcome.invocation is None
        assert mock_tool_backend.calls == []

    def test_excluded_subdomain_denied_even_inside_wildcard(self, orchestrator_factory, run_id, scope_authorization, action_factory, mock_tool_backend, runtime_registry):
        from tests.orchestrator.conftest import make_run_scope

        orch = orchestrator_factory(runtime_registry=runtime_registry)
        run_scope = make_run_scope(run_id, excluded_domains=["admin.example.com"])
        ctx = orch.start_run(run_id=run_id, scope=scope_authorization, run_scope=run_scope)
        outcome = ctx.execute_tool_action(action_factory(target="httpx", parameters={"target_url": "https://admin.example.com"}))
        assert not outcome.was_authorized
        assert outcome.rejected.reason_code == "domain_excluded"
        assert mock_tool_backend.calls == []

    def test_missing_run_scope_denies_every_tool_action(self, orchestrator, run_id, scope_authorization, action_factory, mock_tool_backend):
        ctx = orchestrator.start_run(run_id=run_id, scope=scope_authorization, run_scope=None)
        outcome = ctx.execute_tool_action(action_factory())
        assert not outcome.was_authorized
        assert outcome.rejected.reason_code == "missing_run_scope"
        assert mock_tool_backend.calls == []

    def test_unestablished_run_scope_denies(self, orchestrator, run_id, scope_authorization, action_factory, mock_tool_backend):
        from trackA.schemas.scope import RunScope

        candidate_scope = RunScope(
            run_id=run_id,
            authorization_reference="https://bugcrowd.com/example-program/scope",
            allowed_domains=["example.com"],
        )
        assert candidate_scope.is_established is False
        ctx = orchestrator.start_run(run_id=run_id, scope=scope_authorization, run_scope=candidate_scope)
        outcome = ctx.execute_tool_action(action_factory())
        assert not outcome.was_authorized
        assert outcome.rejected.reason_code == "run_scope_not_established"
        assert mock_tool_backend.calls == []


class TestRegistryEnforcement:
    def test_unregistered_tool_denied_and_executor_never_called(self, run_context, action_factory, mock_tool_backend):
        outcome = run_context.execute_tool_action(action_factory(target="nmap-aggressive"))
        assert not outcome.was_authorized
        assert outcome.rejected.reason_code == "tool_registry_rejection"
        assert mock_tool_backend.calls == []

    def test_registry_membership_alone_does_not_imply_authorization(self, run_context, action_factory, mock_tool_backend):
        # subfinder IS registered and active — but the target is still
        # out of scope, and that must still deny. Registry membership and
        # scope authorization are independent checks; passing one never
        # substitutes for the other.
        outcome = run_context.execute_tool_action(action_factory(parameters={"domain": "not-authorized.org"}))
        assert not outcome.was_authorized
        assert mock_tool_backend.calls == []


class TestMalformedRequest:
    def test_malformed_target_denies_via_scope_gate_normalization_failure(self, run_context, action_factory, mock_tool_backend):
        outcome = run_context.execute_tool_action(
            action_factory(target="ffuf", parameters={"target_url_pattern": "https://example.com/FUZZ"})
        )
        assert not outcome.was_authorized
        assert outcome.rejected.reason_code == "malformed_request"
        assert mock_tool_backend.calls == []

    def test_no_recognizable_target_field_denies(self, run_context, action_factory, mock_tool_backend):
        outcome = run_context.execute_tool_action(action_factory(parameters={"unexpected_key": "value"}))
        assert not outcome.was_authorized
        assert outcome.rejected.reason_code == "malformed_request"
        assert mock_tool_backend.calls == []


class TestToolExecutionFailure:
    def test_backend_failure_surfaces_without_crashing_the_run(self, orchestrator_factory, run_id, scope_authorization, run_scope_factory, action_factory, runtime_registry):
        from trackA.execution.backends import MockToolBackend, ToolBackendResult
        from trackA.execution.tools import ToolExecutor
        from trackA.registries.tools import ToolRegistry
        from tests.registries.conftest import tool_manifest_data

        registry = ToolRegistry()
        registry.register_from_dict(tool_manifest_data())
        backend = MockToolBackend(failing_tools={"subfinder": ToolBackendResult(exit_status="timeout", error="deadline exceeded")})
        orch = orchestrator_factory(runtime_registry=runtime_registry, tool_registry=registry, tool_executor=ToolExecutor(tool_registry=registry, backend=backend))
        ctx = orch.start_run(run_id=run_id, scope=scope_authorization, run_scope=run_scope_factory())
        outcome = ctx.execute_tool_action(action_factory())
        assert outcome.was_authorized
        assert outcome.invocation.result.exit_status == "timeout"
        assert outcome.invocation.raw_output is None
