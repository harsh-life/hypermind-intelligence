from __future__ import annotations

import pytest

from trackA.registries.errors import (
    DuplicateIdError,
    InactiveEntryError,
    ManifestValidationError,
    StageNotAllowedError,
    UnknownIdError,
)
from trackA.registries.tools import ToolRegistry
from tests.registries.conftest import SEED_DATA_DIR


def test_register_and_lookup(tool_data):
    registry = ToolRegistry()
    registry.register_from_dict(tool_data())
    assert len(registry) == 1
    assert registry.lookup("subfinder").tool_id == "subfinder"
    assert "subfinder" in registry


def test_lookup_unregistered_raises(tool_data):
    registry = ToolRegistry()
    registry.register_from_dict(tool_data())
    with pytest.raises(UnknownIdError):
        registry.lookup("nuclei")


def test_lookup_resists_homoglyph_and_whitespace_variants(tool_data):
    """Registry-level half of docs/11_TEST_PLAN_README.md ADV-005: an
    exact-string-keyed lookup cannot be fooled by a lookalike id."""
    registry = ToolRegistry()
    registry.register_from_dict(tool_data())
    with pytest.raises(UnknownIdError):
        registry.lookup("subfinder ")  # trailing whitespace
    with pytest.raises(UnknownIdError):
        registry.lookup("subfindeг")  # Cyrillic "г" homoglyph for "r"


def test_duplicate_tool_id_rejected(tool_data):
    registry = ToolRegistry()
    registry.register_from_dict(tool_data())
    with pytest.raises(DuplicateIdError):
        registry.register_from_dict(tool_data())


def test_duplicate_rejected_even_with_different_content(tool_data):
    registry = ToolRegistry()
    registry.register_from_dict(tool_data())
    with pytest.raises(DuplicateIdError):
        registry.register_from_dict(tool_data(purpose="a different purpose entirely"))


def test_malformed_manifest_rejected_missing_required_field(tool_data):
    registry = ToolRegistry()
    data = tool_data()
    del data["container_image"]
    with pytest.raises(ManifestValidationError):
        registry.register_from_dict(data)
    assert len(registry) == 0


def test_malformed_manifest_rejected_bad_enum_value(tool_data):
    registry = ToolRegistry()
    with pytest.raises(ManifestValidationError):
        registry.register_from_dict(tool_data(risk_classification="extreme"))


def test_validation_status_defaults_active(tool_data):
    registry = ToolRegistry()
    registry.register_from_dict(tool_data())
    assert registry.is_active("subfinder")


def test_validate_invocation_passes_for_active_allowed_stage(tool_data):
    registry = ToolRegistry()
    registry.register_from_dict(tool_data())
    assert registry.validate_invocation("subfinder", stage="tool_execution") is True


def test_validate_invocation_rejects_inactive_entry(tool_data):
    """AC-007: a validation_status other than active blocks execution the
    same as full non-registration."""
    registry = ToolRegistry()
    registry.register_from_dict(
        tool_data(tool_id="promptfoo", validation_status="provisional_pending_OD-01")
    )
    assert not registry.is_active("promptfoo")
    with pytest.raises(InactiveEntryError):
        registry.validate_invocation("promptfoo", stage="tool_execution")


def test_validate_invocation_rejects_disallowed_stage(tool_data):
    registry = ToolRegistry()
    registry.register_from_dict(tool_data(allowed_stages=["tool_execution"]))
    with pytest.raises(StageNotAllowedError):
        registry.validate_invocation("subfinder", stage="ai_security")


def test_validate_invocation_unregistered_raises_unknown_not_inactive(tool_data):
    registry = ToolRegistry()
    with pytest.raises(UnknownIdError):
        registry.validate_invocation("nuclei", stage="tool_execution")


def test_serialization_round_trip(tool_data):
    registry = ToolRegistry()
    registry.register_from_dict(tool_data())
    dumped = registry.to_dict()

    reloaded = ToolRegistry()
    for manifest_data in dumped.values():
        reloaded.register_from_dict(manifest_data)

    assert reloaded.lookup("subfinder").model_dump(mode="json") == dumped["subfinder"]


def test_from_directory_loads_real_seed_manifests():
    registry = ToolRegistry.from_directory(SEED_DATA_DIR / "tools")
    assert {t.tool_id for t in registry.all()} == {"subfinder", "httpx"}
    for tool in registry.all():
        assert registry.is_active(tool.tool_id)


def test_from_directory_missing_directory_raises():
    with pytest.raises(ValueError):
        ToolRegistry.from_directory(SEED_DATA_DIR / "does_not_exist")
