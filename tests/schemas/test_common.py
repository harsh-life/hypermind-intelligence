from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.schemas.common import ManifestProvenance, PipelineStage, ScreenResult, TrustClassification
from tests.conftest import make_provenance


def test_provenance_valid_defaults(run_id):
    p = make_provenance(run_id, PipelineStage.EXTRACTOR, model_id="qwen2.5-1.5b", model_version="q4")
    assert p.record_id
    assert p.created_at
    assert p.model_id == "qwen2.5-1.5b"
    assert p.tool_id is None


def test_provenance_neither_model_nor_tool_is_valid(run_id):
    p = make_provenance(run_id, PipelineStage.EVIDENCE_GATE)
    assert p.model_id is None and p.tool_id is None


def test_provenance_rejects_both_model_and_tool(run_id):
    with pytest.raises(ValidationError):
        make_provenance(
            run_id,
            PipelineStage.TOOL_EXECUTION,
            model_id="m1",
            model_version="v1",
            tool_id="subfinder",
            tool_version="v2.6.3",
        )


def test_provenance_requires_model_version_with_model_id(run_id):
    with pytest.raises(ValidationError):
        make_provenance(run_id, PipelineStage.EXTRACTOR, model_id="m1")


def test_provenance_requires_tool_version_with_tool_id(run_id):
    with pytest.raises(ValidationError):
        make_provenance(run_id, PipelineStage.TOOL_EXECUTION, tool_id="subfinder")


def test_provenance_rejects_unknown_field(run_id):
    with pytest.raises(ValidationError):
        make_provenance(run_id, PipelineStage.EXTRACTOR, unexpected_field="oops")


def test_manifest_provenance_defaults_created_at():
    mp = ManifestProvenance(created_by="harsh", source_basis="doc", version="1.0.0")
    assert mp.created_at


def test_screen_result_cleared_with_no_reason():
    sr = ScreenResult(cleared=True)
    assert sr.reason is None


def test_screen_result_rejection_carries_reason():
    sr = ScreenResult(cleared=False, reason="pattern match: ignore previous instructions")
    assert sr.cleared is False
    assert "ignore previous instructions" in sr.reason


def test_trust_classification_ladder_values():
    assert [c.value for c in TrustClassification] == [
        "RAW_OBSERVATION",
        "MODEL_INTERPRETATION",
        "CANDIDATE_FINDING",
        "VALIDATED_FINDING",
    ]
