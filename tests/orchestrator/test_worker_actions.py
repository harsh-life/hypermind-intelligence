"""Worker-invocation actions: `worker_role_binding -> RoleResolver ->
RuntimeRegistry` resolution (task brief §7), refusal-vs-technical-failure
handling, and bounded retry against `WorkerManifest.retry_limit`."""
from __future__ import annotations

from tests.orchestrator.conftest import (
    refusal_result,
    runtime_registry_with_scripted,
    structured_success,
    technical_failure_result,
)


class TestWorkerResolutionAndInvocation:
    def test_authorized_worker_invocation_resolves_role_and_produces_output(self, run_context, action_factory):
        outcome = run_context.run_worker_action(
            action_factory(action_type="worker_invocation", target="endpoint_mapper_v1", parameters={}),
            payload={"entities": [{"type": "endpoint", "value": "/api/v1/users/1"}]},
            source_extractor_record_id="raw-1",
        )
        assert outcome.was_authorized
        assert outcome.output is not None
        assert outcome.output.worker_id == "endpoint_mapper_v1"
        # MockAdapter's `raw` dict (request/binding) is what the default
        # payload-extraction strategy uses when no scripted adapter
        # supplies a purpose-built structured response — proves the
        # worker_role_binding -> Model Registry -> runtime adapter chain
        # actually ran, without asserting anything backend-specific.
        assert "binding" in outcome.output.payload
        assert outcome.output.provenance.model_id == "cand-worker"

    def test_unregistered_worker_denied(self, run_context, action_factory):
        outcome = run_context.run_worker_action(
            action_factory(action_type="worker_invocation", target="nonexistent_worker", parameters={}),
            payload={},
            source_extractor_record_id="raw-1",
        )
        assert not outcome.was_authorized
        assert outcome.rejected.reason_code == "worker_registry_rejection"

    def test_worker_invocation_does_not_pass_through_scope_gate(self, run_context, action_factory, mock_tool_backend):
        # No network-capable operation here — the tool backend must never
        # be touched by a worker invocation.
        run_context.run_worker_action(
            action_factory(action_type="worker_invocation", target="endpoint_mapper_v1", parameters={}),
            payload={},
            source_extractor_record_id="raw-1",
        )
        assert mock_tool_backend.calls == []


class TestWorkerModelRefusal:
    def test_refusal_produces_failure_event_not_output(self, orchestrator_factory, run_id, scope_authorization, run_scope_factory, action_factory, model_registry):
        registry, adapter = runtime_registry_with_scripted(
            model_registry, candidate_id="cand-worker", results=[refusal_result()]
        )
        orch = orchestrator_factory(runtime_registry=registry)
        ctx = orch.start_run(run_id=run_id, scope=scope_authorization, run_scope=run_scope_factory())
        outcome = ctx.run_worker_action(
            action_factory(action_type="worker_invocation", target="endpoint_mapper_v1", parameters={}),
            payload={},
            source_extractor_record_id="raw-1",
        )
        assert outcome.output is None
        assert outcome.failure is not None
        assert outcome.failure.failure_type == "model_refusal"
        assert adapter.call_count == 1  # never retried

    def test_refusal_is_never_retried_even_with_retries_available(self, orchestrator_factory, run_id, scope_authorization, run_scope_factory, action_factory, model_registry):
        # WorkerManifest.retry_limit (seed data) is 2 — if refusal were
        # (incorrectly) retried like a technical failure, call_count would
        # be 3, not 1.
        registry, adapter = runtime_registry_with_scripted(
            model_registry, candidate_id="cand-worker", results=[refusal_result(), structured_success({"should": "never reach here"})]
        )
        orch = orchestrator_factory(runtime_registry=registry)
        ctx = orch.start_run(run_id=run_id, scope=scope_authorization, run_scope=run_scope_factory())
        outcome = ctx.run_worker_action(
            action_factory(action_type="worker_invocation", target="endpoint_mapper_v1", parameters={}),
            payload={},
            source_extractor_record_id="raw-1",
        )
        assert adapter.call_count == 1
        assert outcome.output is None


class TestWorkerTechnicalFailureRetry:
    def test_technical_failure_retried_then_succeeds(self, orchestrator_factory, run_id, scope_authorization, run_scope_factory, action_factory, model_registry):
        registry, adapter = runtime_registry_with_scripted(
            model_registry,
            candidate_id="cand-worker",
            results=[technical_failure_result(), structured_success({"mapped_endpoints": []})],
        )
        orch = orchestrator_factory(runtime_registry=registry)
        ctx = orch.start_run(run_id=run_id, scope=scope_authorization, run_scope=run_scope_factory())
        outcome = ctx.run_worker_action(
            action_factory(action_type="worker_invocation", target="endpoint_mapper_v1", parameters={}),
            payload={},
            source_extractor_record_id="raw-1",
        )
        assert adapter.call_count == 2
        assert outcome.output is not None
        assert outcome.retries_used == 1

    def test_technical_failure_exhausts_retry_limit_then_fails(self, orchestrator_factory, run_id, scope_authorization, run_scope_factory, action_factory, model_registry):
        # worker_manifest_data's retry_limit is 2 -> up to 3 total calls.
        registry, adapter = runtime_registry_with_scripted(
            model_registry, candidate_id="cand-worker", results=[technical_failure_result()]
        )
        orch = orchestrator_factory(runtime_registry=registry)
        ctx = orch.start_run(run_id=run_id, scope=scope_authorization, run_scope=run_scope_factory())
        outcome = ctx.run_worker_action(
            action_factory(action_type="worker_invocation", target="endpoint_mapper_v1", parameters={}),
            payload={},
            source_extractor_record_id="raw-1",
        )
        assert adapter.call_count == 3
        assert outcome.output is None
        assert outcome.failure.failure_type == "unreachable_dependency"
        assert outcome.retries_used == 2


class TestMalformedWorkerOutput:
    def test_non_dict_non_json_output_is_rejected_not_propagated(self, orchestrator_factory, run_id, scope_authorization, run_scope_factory, action_factory, model_registry):
        from trackA.models.runtime import InferenceResult

        registry, adapter = runtime_registry_with_scripted(
            model_registry,
            candidate_id="cand-worker",
            results=[InferenceResult(success=True, output_text="not json at all", raw=None)],
        )
        orch = orchestrator_factory(runtime_registry=registry)
        ctx = orch.start_run(run_id=run_id, scope=scope_authorization, run_scope=run_scope_factory())
        outcome = ctx.run_worker_action(
            action_factory(action_type="worker_invocation", target="endpoint_mapper_v1", parameters={}),
            payload={},
            source_extractor_record_id="raw-1",
        )
        assert outcome.output is None
        assert outcome.failure.failure_type == "schema_invalid"
