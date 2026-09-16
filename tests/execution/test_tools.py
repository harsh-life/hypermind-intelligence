from __future__ import annotations

import pytest

from tests.registries.conftest import tool_manifest_data
from trackA.execution.backends import MockToolBackend, ToolBackendResult
from trackA.execution.tools import RegistryRejectedInvocation, ToolExecutor
from trackA.registries.tools import ToolRegistry
from trackA.schemas.common import TrustClassification


class TestRegisteredToolLookup:
    def test_authorized_invocation_produces_result_and_raw_output(
        self, tool_executor, tool_request_factory, mock_backend
    ):
        record = tool_executor.execute(tool_request_factory())
        assert record.result.exit_status == "success"
        assert record.raw_output is not None
        assert record.raw_output.trust_classification == TrustClassification.RAW_OBSERVATION
        assert record.raw_output.content == "mock tool output"
        assert record.result.raw_output_record_id == record.raw_output.provenance.record_id
        assert len(mock_backend.calls) == 1

    def test_provenance_carries_tool_identity_and_version(self, tool_executor, tool_request_factory):
        record = tool_executor.execute(tool_request_factory())
        assert record.result.provenance.tool_id == "subfinder"
        assert record.result.provenance.tool_version == "v2.6.3"
        assert record.result.provenance.model_id is None

    def test_result_references_the_originating_request(self, tool_executor, tool_request_factory):
        request = tool_request_factory()
        record = tool_executor.execute(request)
        assert record.result.request_record_id == request.provenance.record_id


class TestUnregisteredToolRejection:
    def test_unregistered_tool_id_is_rejected_and_backend_never_called(
        self, tool_executor, tool_request_factory, mock_backend
    ):
        request = tool_request_factory(tool_id="nmap-aggressive")
        with pytest.raises(RegistryRejectedInvocation):
            tool_executor.execute(request)
        assert mock_backend.calls == []

    def test_inactive_tool_is_rejected(self, mock_backend):
        registry = ToolRegistry()
        registry.register_from_dict(tool_manifest_data(validation_status="provisional_pending_OD-01"))
        executor = ToolExecutor(tool_registry=registry, backend=mock_backend)
        from trackA.schemas.common import PipelineStage, Provenance
        from trackA.schemas.tools import ToolExecutionRequest

        request = ToolExecutionRequest(
            provenance=Provenance(run_id="r1", stage=PipelineStage.ORCHESTRATOR, source_component="test"),
            tool_id="subfinder",
            parameters={"domain": "example.com"},
            authorized_by_action_id="a1",
        )
        with pytest.raises(RegistryRejectedInvocation):
            executor.execute(request)
        assert mock_backend.calls == []

    def test_tool_not_allowed_at_requested_stage_is_rejected(self, tool_executor, tool_request_factory, mock_backend):
        with pytest.raises(RegistryRejectedInvocation):
            tool_executor.execute(tool_request_factory(), stage="ai_security")
        assert mock_backend.calls == []


class TestFailureHandling:
    def test_backend_failure_produces_failed_result_with_no_raw_output(self, tool_request_factory):
        backend = MockToolBackend(failing_tools={"subfinder": ToolBackendResult(exit_status="timeout", error="deadline exceeded")})
        registry = ToolRegistry()
        registry.register_from_dict(tool_manifest_data())
        executor = ToolExecutor(tool_registry=registry, backend=backend)

        record = executor.execute(tool_request_factory())
        assert record.result.exit_status == "timeout"
        assert record.result.raw_output_record_id is None
        assert record.raw_output is None

    def test_backend_failure_never_raises(self, tool_request_factory):
        backend = MockToolBackend(failing_tools={"subfinder": ToolBackendResult(exit_status="crash", error="segfault")})
        registry = ToolRegistry()
        registry.register_from_dict(tool_manifest_data())
        executor = ToolExecutor(tool_registry=registry, backend=backend)
        # Should not raise — a tool-level failure is data, not an exception.
        record = executor.execute(tool_request_factory())
        assert record.result.exit_status == "crash"
