from __future__ import annotations

import pytest

from trackA.registries.errors import (
    ConflictError,
    DuplicateIdError,
    ManifestValidationError,
    NoApprovedCandidateError,
    UnknownIdError,
)
from trackA.registries.models import ModelRegistry
from tests.registries.conftest import SEED_DATA_DIR


def test_register_and_lookup(model_data):
    registry = ModelRegistry()
    registry.register_from_dict(model_data())
    assert registry.lookup("qwen2.5-1.5b-extractor").intended_worker_role == "extractor"
    assert "qwen2.5-1.5b-extractor" in registry


def test_lookup_unregistered_raises(model_data):
    registry = ModelRegistry()
    with pytest.raises(UnknownIdError):
        registry.lookup("nonexistent-candidate")


def test_duplicate_candidate_id_rejected(model_data):
    registry = ModelRegistry()
    registry.register_from_dict(model_data())
    with pytest.raises(DuplicateIdError):
        registry.register_from_dict(model_data())


def test_multiple_candidates_for_one_role_allowed_when_not_both_approved(model_data):
    registry = ModelRegistry()
    registry.register_from_dict(
        model_data(candidate_id="cand-a", intended_worker_role="specialist", approval_status="candidate")
    )
    registry.register_from_dict(
        model_data(candidate_id="cand-b", intended_worker_role="specialist", approval_status="candidate")
    )
    assert len(registry.list_candidates("specialist")) == 2


def test_two_approved_candidates_for_same_role_conflict(model_data):
    """docs/08_MODEL_REGISTRY.md [LOCKED]: 'exactly one is marked approved
    and active at a time per role.'"""
    registry = ModelRegistry()
    registry.register_from_dict(
        model_data(candidate_id="cand-a", intended_worker_role="specialist", approval_status="approved")
    )
    with pytest.raises(ConflictError):
        registry.register_from_dict(
            model_data(candidate_id="cand-b", intended_worker_role="specialist", approval_status="approved")
        )
    # the conflicting registration must not have been partially applied
    assert len(registry.list_candidates("specialist")) == 1


def test_approved_candidates_for_different_roles_do_not_conflict(model_data):
    registry = ModelRegistry()
    registry.register_from_dict(
        model_data(candidate_id="cand-a", intended_worker_role="specialist", approval_status="approved")
    )
    registry.register_from_dict(
        model_data(candidate_id="cand-b", intended_worker_role="judge", approval_status="approved")
    )
    assert registry.get_approved("specialist").candidate_id == "cand-a"
    assert registry.get_approved("judge").candidate_id == "cand-b"


def test_get_approved_raises_when_no_candidates_for_role(model_data):
    registry = ModelRegistry()
    with pytest.raises(NoApprovedCandidateError):
        registry.get_approved("report_polisher")


def test_get_approved_raises_when_role_has_only_unapproved_candidates(model_data):
    registry = ModelRegistry()
    registry.register_from_dict(model_data(approval_status="candidate"))
    with pytest.raises(NoApprovedCandidateError):
        registry.get_approved("extractor")


def test_same_model_identity_can_serve_two_roles_via_distinct_candidates(model_data):
    """Context-2 task brief §5: 'the same candidate model potentially
    being usable for multiple roles where the contract allows it' — no
    schema change required, just two ModelManifest entries."""
    registry = ModelRegistry()
    registry.register_from_dict(
        model_data(candidate_id="qwen3b-worker", model_identity="Qwen2.5-3B-Instruct", intended_worker_role="endpoint_mapper")
    )
    registry.register_from_dict(
        model_data(candidate_id="qwen3b-judge", model_identity="Qwen2.5-3B-Instruct", intended_worker_role="judge")
    )
    worker_candidate = registry.lookup("qwen3b-worker")
    judge_candidate = registry.lookup("qwen3b-judge")
    assert worker_candidate.model_identity == judge_candidate.model_identity
    assert worker_candidate.intended_worker_role != judge_candidate.intended_worker_role


def test_malformed_manifest_rejected_bad_execution_location(model_data):
    registry = ModelRegistry()
    with pytest.raises(ManifestValidationError):
        registry.register_from_dict(model_data(execution_location="containerized"))


def test_quality_metrics_out_of_range_rejected(model_data):
    registry = ModelRegistry()
    with pytest.raises(ManifestValidationError):
        registry.register_from_dict(
            model_data(quality_metrics={"structured_output_validity_rate": 1.5})
        )


def test_quality_metrics_never_fabricated_by_default(model_data):
    """docs/08 [ABSOLUTE RULE]: a null quality_metrics field means 'not
    yet measured' — never an estimate."""
    registry = ModelRegistry()
    manifest = registry.register_from_dict(model_data())
    assert manifest.quality_metrics.structured_output_validity_rate is None
    assert manifest.quality_metrics.useful_hypothesis_rate is None
    assert manifest.quality_metrics.false_positive_rate is None


def test_serialization_round_trip(model_data):
    registry = ModelRegistry()
    registry.register_from_dict(model_data())
    dumped = registry.to_dict()

    reloaded = ModelRegistry()
    for manifest_data in dumped.values():
        reloaded.register_from_dict(manifest_data)

    assert reloaded.lookup("qwen2.5-1.5b-extractor").model_dump(mode="json") == dumped[
        "qwen2.5-1.5b-extractor"
    ]


def test_from_directory_loads_real_seed_manifests_without_conflict():
    registry = ModelRegistry.from_directory(SEED_DATA_DIR / "models")
    assert len(registry) == 5
    assert registry.get_approved("extractor").candidate_id == "qwen2.5-1.5b-extractor"
    assert registry.get_approved("endpoint_mapper").candidate_id == "qwen2.5-3b-worker"
    with pytest.raises(NoApprovedCandidateError):
        registry.get_approved("specialist")
    with pytest.raises(NoApprovedCandidateError):
        registry.get_approved("judge")
