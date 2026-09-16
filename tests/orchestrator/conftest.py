"""Shared fixtures for the Context-5 orchestrator test suite.

`ScriptedAdapter` is the one new test double this suite needs beyond what
Context 2/4 already provide (`MockAdapter`): a queue of pre-built
`InferenceResult`s played back in order, with the last one repeated for
any call beyond the queue's length. This is what makes retry/refusal
semantics deterministically testable — "technical failure twice, then
success" or "refusal on the very first call" are exact, scripted
sequences, never timing- or randomness-dependent.
"""
from __future__ import annotations

from typing import List

import pytest

from tests.registries.conftest import model_manifest_data, skill_manifest_data, tool_manifest_data, worker_manifest_data
from trackA.execution.backends import MockToolBackend
from trackA.execution.tools import ToolExecutor
from trackA.models.runtime import InferenceAdapter, InferenceRequest, InferenceResult, MockAdapter, ModelBinding, RuntimeRegistry
from trackA.orchestrator.run import Orchestrator
from trackA.policy.scope_gate import ScopeGate
from trackA.registries.models import ModelRegistry
from trackA.registries.resolution import RoleResolver
from trackA.registries.skills import SkillRegistry
from trackA.registries.tools import ToolRegistry
from trackA.registries.workers import WorkerRegistry
from trackA.schemas.common import PipelineStage, Provenance
from trackA.schemas.orchestrator import OrchestratorAction
from trackA.schemas.scope import RunScope, ScopeAuthorization, ScopeDecision, ScopeRequest


class ScriptedAdapter(InferenceAdapter):
    backend = "scripted"

    def __init__(self, results: List[InferenceResult]):
        if not results:
            raise ValueError("ScriptedAdapter needs at least one scripted result")
        self._results = list(results)
        self.call_count = 0

    def infer(self, request: InferenceRequest, *, binding: ModelBinding) -> InferenceResult:
        self.call_count += 1
        index = min(self.call_count - 1, len(self._results) - 1)
        return self._results[index]


def refusal_result(message: str = "I cannot assist with that request.") -> InferenceResult:
    return InferenceResult(success=False, error=message, raw={"refusal": True})


def technical_failure_result(message: str = "connection reset") -> InferenceResult:
    return InferenceResult(success=False, error=message)


def structured_success(payload: dict) -> InferenceResult:
    return InferenceResult(success=True, output_text="ok", raw=payload)


@pytest.fixture
def run_id() -> str:
    return "55555555-5555-4555-8555-555555555555"


@pytest.fixture
def tool_registry():
    registry = ToolRegistry()
    registry.register_from_dict(tool_manifest_data())
    return registry


@pytest.fixture
def worker_registry():
    registry = WorkerRegistry()
    registry.register_from_dict(worker_manifest_data())
    return registry


@pytest.fixture
def skill_registry():
    registry = SkillRegistry()
    registry.register_from_dict(skill_manifest_data())
    return registry


@pytest.fixture
def model_registry():
    registry = ModelRegistry()
    registry.register_from_dict(
        model_manifest_data(candidate_id="cand-worker", intended_worker_role="endpoint_mapper", approval_status="approved")
    )
    registry.register_from_dict(
        model_manifest_data(candidate_id="cand-judge", intended_worker_role="judge", approval_status="approved")
    )
    registry.register_from_dict(
        model_manifest_data(candidate_id="cand-specialist", intended_worker_role="specialist", approval_status="approved")
    )
    return registry


@pytest.fixture
def role_resolver(model_registry):
    return RoleResolver(model_registry)


@pytest.fixture
def runtime_registry(model_registry):
    registry = RuntimeRegistry(model_registry=model_registry)
    registry.register_adapter(MockAdapter())
    for candidate_id in ("cand-worker", "cand-judge", "cand-specialist"):
        registry.bind(ModelBinding(candidate_id=candidate_id, backend="mock"))
    return registry


def runtime_registry_with_scripted(
    model_registry: ModelRegistry, *, candidate_id: str, results: List[InferenceResult]
) -> "tuple[RuntimeRegistry, ScriptedAdapter]":
    """A fresh `RuntimeRegistry` (independent of the shared `mock`-backed
    fixture above) with every one of `model_registry`'s three seeded
    candidates bound: `candidate_id` to a fresh `ScriptedAdapter` playing
    back `results` in order, every other candidate still to the ordinary
    `MockAdapter` (so a test that scripts, say, the Worker role doesn't
    also have to care about the Judge/Specialist roles it isn't
    exercising). Building a fresh registry per test — rather than
    mutating the shared `runtime_registry` fixture, which
    `RuntimeRegistry.bind`'s duplicate-id guard does not allow rebinding
    anyway — keeps each retry/refusal test's scripted sequence isolated
    from every other test.
    """
    registry = RuntimeRegistry(model_registry=model_registry)
    mock_adapter = MockAdapter()
    scripted_adapter = ScriptedAdapter(results)
    scripted_adapter.backend = f"scripted-{candidate_id}"
    registry.register_adapter(mock_adapter)
    registry.register_adapter(scripted_adapter)
    for other_id in ("cand-worker", "cand-judge", "cand-specialist"):
        if other_id == candidate_id:
            registry.bind(ModelBinding(candidate_id=other_id, backend=scripted_adapter.backend))
        else:
            registry.bind(ModelBinding(candidate_id=other_id, backend="mock"))
    return registry, scripted_adapter


@pytest.fixture
def mock_tool_backend():
    return MockToolBackend(canned_outputs={"subfinder": "sub1.example.com"})


@pytest.fixture
def tool_executor(tool_registry, mock_tool_backend):
    return ToolExecutor(tool_registry=tool_registry, backend=mock_tool_backend)


@pytest.fixture
def scope_gate():
    return ScopeGate()


@pytest.fixture
def orchestrator(tool_registry, worker_registry, skill_registry, model_registry, role_resolver, runtime_registry, scope_gate, tool_executor):
    return Orchestrator(
        tool_registry=tool_registry,
        worker_registry=worker_registry,
        skill_registry=skill_registry,
        model_registry=model_registry,
        role_resolver=role_resolver,
        runtime_registry=runtime_registry,
        scope_gate=scope_gate,
        tool_executor=tool_executor,
    )


def make_run_scope(run_id: str, **overrides) -> RunScope:
    data = {
        "run_id": run_id,
        "authorization_reference": "https://bugcrowd.com/example-program/scope",
        "allowed_domains": ["example.com"],
        "allowed_subdomains": ["*.example.com"],
        "established_by": "harsh",
    }
    data.update(overrides)
    return RunScope(**data)


def make_scope_authorization(run_id: str) -> ScopeAuthorization:
    request = ScopeRequest(
        provenance=Provenance(run_id=run_id, stage=PipelineStage.SCOPE_GATE, source_component="test"),
        target_identifier="example.com",
        authorization_reference="https://bugcrowd.com/example-program/scope",
        requested_by="harsh",
    )
    decision = ScopeDecision(
        provenance=Provenance(run_id=run_id, stage=PipelineStage.SCOPE_GATE, source_component="test"),
        request_record_id=request.provenance.record_id,
        decision="allow",
        reason="in scope",
        policy_version="v1",
    )
    return ScopeAuthorization(request=request, decision=decision)


@pytest.fixture
def run_scope_factory(run_id):
    def _factory(**overrides):
        effective_run_id = overrides.pop("run_id", run_id)
        return make_run_scope(effective_run_id, **overrides)

    return _factory


@pytest.fixture
def scope_authorization(run_id):
    return make_scope_authorization(run_id)


@pytest.fixture
def orchestrator_factory(tool_registry, worker_registry, skill_registry, model_registry, role_resolver, scope_gate, tool_executor):
    """For tests that need a non-default `runtime_registry` (scripted
    refusal/retry sequences) or non-default operational bounds
    (`max_actions_per_run` etc.) while reusing every other shared
    fixture as-is."""

    def _factory(*, runtime_registry, **overrides):
        kwargs = dict(
            tool_registry=tool_registry,
            worker_registry=worker_registry,
            skill_registry=skill_registry,
            model_registry=model_registry,
            role_resolver=role_resolver,
            runtime_registry=runtime_registry,
            scope_gate=scope_gate,
            tool_executor=tool_executor,
        )
        kwargs.update(overrides)
        return Orchestrator(**kwargs)

    return _factory


@pytest.fixture
def run_context(orchestrator, run_id, scope_authorization, run_scope_factory):
    return orchestrator.start_run(run_id=run_id, scope=scope_authorization, run_scope=run_scope_factory())


def make_action(run_id: str, *, action_type: str = "tool_execution", target: str = "subfinder", parameters=None, **overrides) -> OrchestratorAction:
    provenance_data = {
        "run_id": run_id,
        "stage": PipelineStage.ORCHESTRATOR,
        "source_component": "planner (test)",
        "model_id": "planner-model",
        "model_version": "v1",
    }
    provenance_data.update(overrides.pop("provenance_overrides", {}))
    data = {
        "provenance": Provenance(**provenance_data),
        "proposed_action_type": action_type,
        "target_registry_id": target,
        "proposed_parameters": parameters if parameters is not None else {"domain": "example.com"},
        "session_action_count": 1,
    }
    data.update(overrides)
    return OrchestratorAction(**data)


@pytest.fixture
def action_factory(run_id):
    def _factory(**kwargs):
        return make_action(run_id, **kwargs)

    return _factory
