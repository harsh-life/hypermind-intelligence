from __future__ import annotations

import pytest

from trackA.registries.errors import (
    AccessDeniedError,
    DuplicateIdError,
    ManifestValidationError,
    UnknownIdError,
)
from trackA.registries.skills import SPECIALIST_EXECUTOR, SkillRegistry
from tests.registries.conftest import SEED_DATA_DIR


def test_register_and_lookup_by_allowed_caller(skill_data):
    registry = SkillRegistry()
    registry.register_from_dict(skill_data())
    assert registry.lookup("idor_v1", caller=SPECIALIST_EXECUTOR).skill_id == "idor_v1"


def test_lookup_rejects_judge_caller(skill_data):
    """[LOCKED, docs/02 §3]: the Judge must never reach the Skill
    Registry. This is the single most security-critical behavior of this
    registry."""
    registry = SkillRegistry()
    registry.register_from_dict(skill_data())
    with pytest.raises(AccessDeniedError):
        registry.lookup("idor_v1", caller="judge")


def test_lookup_rejects_arbitrary_unknown_caller(skill_data):
    registry = SkillRegistry()
    registry.register_from_dict(skill_data())
    with pytest.raises(AccessDeniedError):
        registry.lookup("idor_v1", caller="orchestrator")


def test_all_rejects_judge_caller(skill_data):
    registry = SkillRegistry()
    registry.register_from_dict(skill_data())
    with pytest.raises(AccessDeniedError):
        registry.all(caller="judge")
    assert len(registry.all(caller=SPECIALIST_EXECUTOR)) == 1


def test_lookup_unregistered_raises_for_allowed_caller(skill_data):
    registry = SkillRegistry()
    with pytest.raises(UnknownIdError):
        registry.lookup("ssrf_v1", caller=SPECIALIST_EXECUTOR)


def test_duplicate_skill_id_rejected(skill_data):
    registry = SkillRegistry()
    registry.register_from_dict(skill_data())
    with pytest.raises(DuplicateIdError):
        registry.register_from_dict(skill_data())


def test_malformed_manifest_missing_replication_command_requirement(skill_data):
    """docs/03 §2.15's invalid example: expected_outputs not requiring
    replication_command violates the reproducibility requirement — this
    is advisory JSON-schema content on the manifest, not itself enforced
    by SkillManifest's own Pydantic validation, so this test documents
    that boundary rather than asserting a rejection that doesn't exist at
    this layer (enforcement happens at the Evidence Gate on the
    Specialist's actual *output*, out of scope for Context 2)."""
    registry = SkillRegistry()
    manifest = registry.register_from_dict(
        skill_data(expected_outputs={"type": "object"})
    )
    assert "replication_command" not in manifest.expected_outputs.get("required", [])


def test_malformed_manifest_bad_validation_status_rejected(skill_data):
    registry = SkillRegistry()
    with pytest.raises(ManifestValidationError):
        registry.register_from_dict(skill_data(validation_status="published"))


def test_specialist_role_binding_defaults_to_generic_specialist(skill_data):
    data = skill_data()
    assert "specialist_role_binding" not in data
    registry = SkillRegistry()
    manifest = registry.register_from_dict(data)
    assert manifest.specialist_role_binding == "specialist"


def test_serialization_round_trip(skill_data):
    registry = SkillRegistry()
    registry.register_from_dict(skill_data())
    dumped = registry.to_dict()

    reloaded = SkillRegistry()
    for manifest_data in dumped.values():
        reloaded.register_from_dict(manifest_data)

    assert reloaded.lookup("idor_v1", caller=SPECIALIST_EXECUTOR).model_dump(
        mode="json"
    ) == dumped["idor_v1"]


def test_from_directory_loads_real_seed_manifests():
    registry = SkillRegistry.from_directory(SEED_DATA_DIR / "skills")
    assert {s.skill_id for s in registry.all(caller=SPECIALIST_EXECUTOR)} == {"idor_v1"}
