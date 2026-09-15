"""Shared fixtures/factories for the policy-layer test suite."""
from __future__ import annotations

import pytest

from trackA.policy.scope_gate import ScopeGate
from trackA.schemas.common import PipelineStage, Provenance
from trackA.schemas.orchestrator import OrchestratorAction
from trackA.schemas.scope import RunScope


@pytest.fixture
def run_id() -> str:
    return "22222222-2222-4222-8222-222222222222"


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


def make_candidate_run_scope(run_id: str, **overrides) -> RunScope:
    """A RunScope with real content but no `established_by` — the "a
    parser/model normalized this but a human hasn't confirmed it yet"
    state from docs/13 OD-23."""

    data = {
        "run_id": run_id,
        "authorization_reference": "https://bugcrowd.com/example-program/scope",
        "allowed_domains": ["example.com"],
    }
    data.update(overrides)
    data.pop("established_by", None)
    data.pop("established_at", None)
    return RunScope(**data)


def make_orchestrator_action(run_id: str, *, proposed_parameters: dict, **overrides) -> OrchestratorAction:
    provenance_data = {
        "run_id": run_id,
        "stage": PipelineStage.ORCHESTRATOR,
        "source_component": "Orchestrator (test)",
        "model_id": "planner-model",
        "model_version": "v1",
    }
    provenance_data.update(overrides.pop("provenance_overrides", {}))
    data = {
        "provenance": Provenance(**provenance_data),
        "proposed_action_type": "tool_execution",
        "target_registry_id": "httpx",
        "proposed_parameters": proposed_parameters,
        "session_action_count": 1,
    }
    data.update(overrides)
    return OrchestratorAction(**data)


@pytest.fixture
def run_scope_factory(run_id):
    def _factory(**overrides):
        return make_run_scope(run_id, **overrides)

    return _factory


@pytest.fixture
def candidate_run_scope_factory(run_id):
    def _factory(**overrides):
        return make_candidate_run_scope(run_id, **overrides)

    return _factory


@pytest.fixture
def action_factory(run_id):
    def _factory(**kwargs):
        return make_orchestrator_action(run_id, **kwargs)

    return _factory


@pytest.fixture
def scope_gate() -> ScopeGate:
    return ScopeGate()
