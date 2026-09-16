from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.execution.backends import MockToolBackend, ToolBackendResult


class TestMockToolBackend:
    def test_default_success(self):
        backend = MockToolBackend()
        result = backend.execute(
            tool_id="subfinder", container_image="sha256:abc", parameters={"domain": "example.com"}, timeout_seconds=120
        )
        assert result.exit_status == "success"
        assert result.output == "mock tool output"

    def test_canned_output_per_tool(self):
        backend = MockToolBackend(canned_outputs={"subfinder": "sub1.example.com"})
        result = backend.execute(tool_id="subfinder", container_image="x", parameters={}, timeout_seconds=1)
        assert result.output == "sub1.example.com"

    def test_failing_tool_returns_configured_failure(self):
        failure = ToolBackendResult(exit_status="timeout", error="deadline exceeded")
        backend = MockToolBackend(failing_tools={"nuclei": failure})
        result = backend.execute(tool_id="nuclei", container_image="x", parameters={}, timeout_seconds=1)
        assert result.exit_status == "timeout"
        assert result.error == "deadline exceeded"

    def test_records_every_call_including_failing_ones(self):
        failure = ToolBackendResult(exit_status="crash", error="boom")
        backend = MockToolBackend(failing_tools={"nuclei": failure})
        backend.execute(tool_id="nuclei", container_image="x", parameters={"a": 1}, timeout_seconds=5)
        assert len(backend.calls) == 1
        assert backend.calls[0]["tool_id"] == "nuclei"
        assert backend.calls[0]["parameters"] == {"a": 1}


class TestToolBackendResult:
    def test_error_required_on_non_success(self):
        with pytest.raises(ValidationError):
            ToolBackendResult(exit_status="crash")

    def test_negative_duration_rejected(self):
        with pytest.raises(ValidationError):
            ToolBackendResult(exit_status="success", duration_ms=-1)
