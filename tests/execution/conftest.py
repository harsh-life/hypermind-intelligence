from __future__ import annotations

import pytest

from tests.registries.conftest import tool_manifest_data
from trackA.execution.backends import MockToolBackend
from trackA.execution.tools import ToolExecutor
from trackA.registries.tools import ToolRegistry
from trackA.schemas.common import PipelineStage, Provenance
from trackA.schemas.tools import ToolExecutionRequest


@pytest.fixture
def run_id() -> str:
    return "44444444-4444-4444-8444-444444444444"


@pytest.fixture
def tool_registry():
    registry = ToolRegistry()
    registry.register_from_dict(tool_manifest_data())
    return registry


@pytest.fixture
def mock_backend():
    return MockToolBackend()


@pytest.fixture
def tool_executor(tool_registry, mock_backend):
    return ToolExecutor(tool_registry=tool_registry, backend=mock_backend)


def make_tool_request(run_id: str, *, tool_id: str = "subfinder", **overrides) -> ToolExecutionRequest:
    data = dict(
        provenance=Provenance(run_id=run_id, stage=PipelineStage.ORCHESTRATOR, source_component="test"),
        tool_id=tool_id,
        parameters={"domain": "example.com"},
        authorized_by_action_id="a1",
    )
    data.update(overrides)
    return ToolExecutionRequest(**data)


@pytest.fixture
def tool_request_factory(run_id):
    def _factory(**overrides):
        return make_tool_request(run_id, **overrides)

    return _factory
