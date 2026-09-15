"""Extractor schemas. Source: docs/03_DATA_SCHEMAS_README.md §2.8-2.9."""
from __future__ import annotations

from typing import List, Literal

from pydantic import model_validator

from trackA.schemas.base import HypermindModel
from trackA.schemas.common import Provenance, TrustClassification


class ExtractorInput(HypermindModel):
    """docs/03 §2.8. Produced by: Docker Tool Execution Engine (pointer)."""

    provenance: Provenance
    raw_output_record_id: str
    extraction_target_schema: str


class ExtractedEntity(HypermindModel):
    """The object shape of ExtractorJSON.entities[] per docs/03 §2.9."""

    type: str
    value: str
    confidence: float

    @model_validator(mode="after")
    def _confidence_in_range(self) -> "ExtractedEntity":
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("ExtractedEntity.confidence must be within [0, 1]")
        return self


class ExtractorJSON(HypermindModel):
    """docs/03 §2.9. Produced by: Extractor (Qwen ~1.5B, GBNF-constrained
    per docs/08_MODEL_REGISTRY.md).

    NOTE: this is the schema-of-record. It differs from the earlier,
    informal "ExtractorJSON" sketch in `Track A PRD.md`
    (tool_source/target/extracted_entities/observations/status), which
    is explicitly superseded by docs/01_ARCHITECTURE.md.
    """

    provenance: Provenance
    trust_classification: Literal[TrustClassification.MODEL_INTERPRETATION] = (
        TrustClassification.MODEL_INTERPRETATION
    )
    source_raw_output_record_id: str
    entities: List[ExtractedEntity]
    schema_valid: Literal[True] = True

    @model_validator(mode="after")
    def _requires_model_provenance(self) -> "ExtractorJSON":
        if not self.provenance.model_id:
            raise ValueError(
                "ExtractorJSON.provenance.model_id is required (docs/03 §2.9)"
            )
        return self
