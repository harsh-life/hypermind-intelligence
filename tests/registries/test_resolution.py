from __future__ import annotations

import pytest

from trackA.registries.errors import NoApprovedCandidateError
from trackA.registries.models import ModelRegistry
from trackA.registries.resolution import RoleResolver
from trackA.schemas.skills import SkillManifest
from trackA.schemas.workers import WorkerManifest


def _models_with(model_data, *rows):
    registry = ModelRegistry()
    for row in rows:
        registry.register_from_dict(model_data(**row))
    return registry


def test_resolve_returns_approved_candidate_for_role(model_data):
    models = _models_with(
        model_data,
        dict(candidate_id="qwen3b-worker", intended_worker_role="endpoint_mapper", approval_status="approved"),
    )
    resolver = RoleResolver(models)
    assert resolver.resolve("endpoint_mapper").candidate_id == "qwen3b-worker"


def test_resolve_raises_when_role_never_registered(model_data):
    models = ModelRegistry()
    resolver = RoleResolver(models)
    with pytest.raises(NoApprovedCandidateError):
        resolver.resolve("report_polisher")


def test_resolve_raises_when_role_has_only_candidates(model_data):
    models = _models_with(
        model_data,
        dict(candidate_id="cand-a", intended_worker_role="specialist", approval_status="candidate"),
    )
    resolver = RoleResolver(models)
    with pytest.raises(NoApprovedCandidateError):
        resolver.resolve("specialist")


def test_resolve_for_worker_follows_role_binding_pointer(model_data, worker_data):
    models = _models_with(
        model_data,
        dict(candidate_id="qwen3b-worker", intended_worker_role="endpoint_mapper", approval_status="approved"),
    )
    resolver = RoleResolver(models)
    worker = WorkerManifest(**worker_data())
    assert worker.worker_role_binding == "endpoint_mapper"
    resolved = resolver.resolve_for_worker(worker)
    assert resolved.candidate_id == "qwen3b-worker"


def test_resolve_for_skill_follows_specialist_role_binding_pointer(model_data, skill_data):
    models = _models_with(
        model_data,
        dict(candidate_id="cand-approved-specialist", intended_worker_role="specialist", approval_status="approved"),
    )
    resolver = RoleResolver(models)
    skill = SkillManifest(**skill_data())  # specialist_role_binding defaults to "specialist"
    resolved = resolver.resolve_for_skill(skill)
    assert resolved.candidate_id == "cand-approved-specialist"


def test_worker_contract_survives_a_model_swap_unmodified(model_data, worker_data):
    """docs/01_ARCHITECTURE.md §4 [LOCKED]: 'the worker contract must
    survive a model swap unmodified.' Swapping the Model Registry's
    approved candidate for a role must change what RoleResolver returns
    without any edit to the WorkerManifest itself."""
    worker = WorkerManifest(**worker_data())

    models_v1 = _models_with(
        model_data,
        dict(candidate_id="qwen1.5b", intended_worker_role="endpoint_mapper", approval_status="approved"),
    )
    assert RoleResolver(models_v1).resolve_for_worker(worker).candidate_id == "qwen1.5b"

    models_v2 = _models_with(
        model_data,
        dict(candidate_id="qwen3b", intended_worker_role="endpoint_mapper", approval_status="approved"),
    )
    assert RoleResolver(models_v2).resolve_for_worker(worker).candidate_id == "qwen3b"


def test_list_candidates_returns_all_statuses_for_benchmarking_view(model_data):
    models = _models_with(
        model_data,
        dict(candidate_id="cand-a", intended_worker_role="specialist", approval_status="approved"),
        dict(candidate_id="cand-b", intended_worker_role="specialist", approval_status="candidate"),
        dict(candidate_id="cand-c", intended_worker_role="specialist", approval_status="rejected"),
    )
    resolver = RoleResolver(models)
    ids = {m.candidate_id for m in resolver.list_candidates("specialist")}
    assert ids == {"cand-a", "cand-b", "cand-c"}
