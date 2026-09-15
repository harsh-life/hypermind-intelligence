"""Serialization/deserialization and naming-crosswalk tests that exercise
the schema layer as a whole, rather than one schema at a time.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

import trackA.schemas as schemas
from trackA.schemas.common import PipelineStage, TrustClassification
from trackA.schemas.tools import RawToolOutput
from tests.conftest import make_provenance


def test_alias_crosswalk_points_at_canonical_classes():
    assert schemas.ToolRequest is schemas.ToolExecutionRequest
    assert schemas.ToolResult is schemas.ToolExecutionResult
    assert schemas.Observation is schemas.RawToolOutput
    assert schemas.CandidateFinding is schemas.SpecialistPoCOutput
    assert schemas.ValidatedFinding is schemas.FindingRecord
    assert schemas.ValidationEvent is schemas.ValidationOutcome
    assert schemas.JudgeEvaluationPackage is schemas.JudgeInput
    assert schemas.Trajectory is schemas.ToolSequenceRecord


def test_raw_tool_output_json_roundtrip(run_id):
    original = RawToolOutput(
        provenance=make_provenance(
            run_id, PipelineStage.TOOL_EXECUTION, tool_id="subfinder", tool_version="v2.6.3"
        ),
        content="sub1.example-bounty.com\nsub2.example-bounty.com\n",
        truncated=False,
    )
    as_json = original.model_dump_json()
    restored = RawToolOutput.model_validate_json(as_json)
    assert restored == original
    assert restored.trust_classification == TrustClassification.RAW_OBSERVATION


def test_specialist_poc_output_dict_roundtrip(run_id):
    from trackA.schemas.skills import SpecialistPoCOutput

    original = SpecialistPoCOutput(
        provenance=make_provenance(
            run_id, PipelineStage.SPECIALIST, model_id="specialist-model", model_version="v1"
        ),
        skill_id="idor_v1",
        vulnerability_claim="GET /api/v1/users/{id} leaks other users' data",
        replication_command="curl -H 'Authorization: Bearer TOKEN' https://target/api/v1/users/12346",
        supporting_evidence={"request": "...", "response_snippet": "..."},
        specialist_confidence=0.81,
    )
    as_dict = original.model_dump(mode="json")
    restored = SpecialistPoCOutput.model_validate(as_dict)
    assert restored == original


@pytest.mark.parametrize(
    "cls_name,extra_kwargs",
    [
        ("RawToolOutput", {"content": "x", "truncated": False}),
    ],
)
def test_extra_fields_are_rejected(run_id, cls_name, extra_kwargs):
    cls = getattr(schemas, cls_name)
    kwargs = dict(
        provenance=make_provenance(
            run_id, PipelineStage.TOOL_EXECUTION, tool_id="subfinder", tool_version="v2.6.3"
        ),
        **extra_kwargs,
        unexpected_field="should not be accepted",
    )
    with pytest.raises(ValidationError):
        cls(**kwargs)


def test_public_api_surface_matches_all():
    for name in schemas.__all__:
        assert hasattr(schemas, name), f"trackA.schemas.__all__ names {name} but it is not exported"
