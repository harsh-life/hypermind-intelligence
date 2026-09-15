from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.schemas.common import PipelineStage
from trackA.schemas.extraction import ExtractedEntity, ExtractorJSON
from tests.conftest import make_provenance


def _valid(run_id, **overrides):
    data = dict(
        provenance=make_provenance(
            run_id, PipelineStage.EXTRACTOR, model_id="qwen-extractor", model_version="1.5b-q4"
        ),
        source_raw_output_record_id="c1",
        entities=[ExtractedEntity(type="endpoint", value="/api/v1/users/{id}", confidence=0.94)],
    )
    data.update(overrides)
    return ExtractorJSON(**data)


def test_valid_extractor_json():
    doc = _valid("r1")
    assert doc.schema_valid is True


def test_entity_confidence_out_of_range_rejected():
    with pytest.raises(ValidationError):
        ExtractedEntity(type="endpoint", value="/api/v1/users/{id}", confidence=1.5)


def test_extractor_json_requires_model_provenance(run_id):
    with pytest.raises(ValidationError):
        ExtractorJSON(
            provenance=make_provenance(run_id, PipelineStage.EXTRACTOR),
            source_raw_output_record_id="c1",
            entities=[],
        )


def test_extractor_json_schema_valid_cannot_be_false(run_id):
    with pytest.raises(ValidationError):
        _valid(run_id, schema_valid=False)
