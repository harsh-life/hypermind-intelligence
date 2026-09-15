from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.schemas.common import PipelineStage
from trackA.schemas.skills import SkillManifest, SpecialistPoCOutput
from tests.conftest import make_manifest_provenance, make_provenance


def _skill_manifest(**overrides):
    data = dict(
        skill_id="idor_v1",
        vulnerability_class="IDOR",
        methodology="Given an object-reference parameter characterized as sequential...",
        system_prompt="You are the IDOR Specialist.",
        few_shot_examples=[],
        references=["https://owasp.org/www-community/attacks/..."],
        expected_inputs={"type": "object"},
        expected_outputs={"type": "object", "required": ["replication_command"]},
        permissions=["read_endpoint_map", "read_reference_analysis"],
        version="1.0.0",
        provenance=make_manifest_provenance(),
        validation_status="draft",
    )
    data.update(overrides)
    return SkillManifest(**data)


def test_skill_manifest_defaults_to_generic_specialist_role_for_mvp():
    # Architecture-owner decision: MVP uses the generic "specialist" role
    # name for every skill, not a per-vulnerability role.
    manifest = _skill_manifest()
    assert manifest.specialist_role_binding == "specialist"


def test_skill_manifest_still_permits_explicit_per_vulnerability_override():
    # The field stays an open str (not a closed enum) specifically so a
    # future validated evaluation can justify a per-vulnerability role
    # without a schema change — but "specialist" remains the MVP default.
    manifest = _skill_manifest(specialist_role_binding="specialist_idor")
    assert manifest.specialist_role_binding == "specialist_idor"


def test_skill_manifest_rejects_bad_validation_status():
    with pytest.raises(ValidationError):
        _skill_manifest(validation_status="published")


def _poc(run_id, **overrides):
    data = dict(
        provenance=make_provenance(
            run_id, PipelineStage.SPECIALIST, model_id="specialist-model", model_version="v1"
        ),
        skill_id="idor_v1",
        vulnerability_claim="GET /api/v1/users/{id} returns other users' data",
        replication_command="curl -H 'Authorization: Bearer <token>' https://target/api/v1/users/12346",
        supporting_evidence={"request": "...", "response_snippet": "..."},
        specialist_confidence=0.81,
    )
    data.update(overrides)
    return SpecialistPoCOutput(**data)


def test_specialist_poc_output_valid(run_id):
    poc = _poc(run_id)
    assert poc.replication_command


def test_specialist_poc_output_rejects_empty_replication_command(run_id):
    with pytest.raises(ValidationError):
        _poc(run_id, replication_command="")


def test_specialist_poc_output_confidence_out_of_range(run_id):
    with pytest.raises(ValidationError):
        _poc(run_id, specialist_confidence=1.2)


def test_specialist_poc_output_requires_model_provenance(run_id):
    with pytest.raises(ValidationError):
        SpecialistPoCOutput(
            provenance=make_provenance(run_id, PipelineStage.SPECIALIST),
            skill_id="idor_v1",
            vulnerability_claim="...",
            replication_command="curl ...",
            supporting_evidence={},
            specialist_confidence=0.5,
        )
