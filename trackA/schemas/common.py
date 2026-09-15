"""Common types shared across the Track A schema layer.

Source: docs/03_DATA_SCHEMAS_README.md §1 (Provenance, TrustClassification),
docs/02_COMPONENT_SPECS.md §8 (ScreenResult, referenced as OD-09 in
docs/13_OPEN_DECISIONS.md), and docs/13_OPEN_DECISIONS.md OD-15 /
docs/14_CONSISTENCY_AUDIT.md FINDING-2 (ManifestProvenance).
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import model_validator

from trackA.schemas.base import HypermindModel


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_uuid() -> str:
    return str(uuid4())


class TrustClassification(str, Enum):
    """The observation -> validated ladder. docs/03 §1.2. [LOCKED]

    No code path may set VALIDATED_FINDING except the Human Verification
    Interface writing a ValidationOutcome with decision="submit" — that
    rule is enforced above the schema layer (it requires knowing *how* a
    record was produced, not just its shape) and is out of scope for this
    context (orchestration/human-validation-API are explicitly excluded).
    """

    RAW_OBSERVATION = "RAW_OBSERVATION"
    MODEL_INTERPRETATION = "MODEL_INTERPRETATION"
    CANDIDATE_FINDING = "CANDIDATE_FINDING"
    VALIDATED_FINDING = "VALIDATED_FINDING"


class PipelineStage(str, Enum):
    """Provenance.stage enum. docs/03 §1.1."""

    SCOPE_GATE = "scope_gate"
    TRUST_BOUNDARY_A = "trust_boundary_a"
    ORCHESTRATOR = "orchestrator"
    TOOL_EXECUTION = "tool_execution"
    EXTRACTOR = "extractor"
    WORKER = "worker"
    JUDGE = "judge"
    SPECIALIST = "specialist"
    EVIDENCE_GATE = "evidence_gate"
    DEDUPLICATION = "deduplication"
    HUMAN_VERIFICATION = "human_verification"
    REPORT_POLISHER = "report_polisher"


class Provenance(HypermindModel):
    """docs/03 §1.1. Embedded in nearly every pipeline schema.

    [LOCKED] validation rule: exactly one of model_id/tool_id may be set
    for any given record, or neither — never both.

    record_id/created_at are given ergonomic defaults (a fresh UUIDv4 and
    the current UTC timestamp) since the docs specify their *format* and
    *requiredness* but not who supplies the value; both remain fully
    overridable, and deserializing an existing record always uses the
    supplied value, never the default.
    """

    record_id: str = ""
    run_id: str
    created_at: str = ""
    stage: PipelineStage
    source_component: str
    model_id: Optional[str] = None
    model_version: Optional[str] = None
    tool_id: Optional[str] = None
    tool_version: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _apply_defaults(cls, data):
        if isinstance(data, dict):
            data = dict(data)
            data.setdefault("record_id", _new_uuid())
            data.setdefault("created_at", _utc_now_iso())
        return data

    @model_validator(mode="after")
    def _exactly_one_of_model_or_tool(self) -> "Provenance":
        if self.model_id and self.tool_id:
            raise ValueError(
                "Provenance: model_id and tool_id must never both be set "
                "(docs/03 §1.1, [LOCKED])"
            )
        if self.model_id and not self.model_version:
            raise ValueError("Provenance.model_version is required when model_id is set")
        if self.tool_id and not self.tool_version:
            raise ValueError("Provenance.tool_version is required when tool_id is set")
        return self


class ManifestProvenance(HypermindModel):
    """Authorship/versioning metadata for a *manifest* (static config authored
    once by a human), as distinct from the pipeline-run-oriented Provenance
    above.

    This type does not exist as such in docs/03 today. It implements the
    *recommended* (not yet Harsh-ratified) resolution to OD-15
    (docs/13_OPEN_DECISIONS.md) as widened by FINDING-2
    (docs/14_CONSISTENCY_AUDIT.md): "define a single lightweight
    ManifestProvenance type ({created_by, created_at, source_basis,
    version}) and apply it uniformly to ToolManifest, WorkerManifest, and
    SkillManifest." Implemented here because the calling task explicitly
    named ManifestProvenance as a required contract — flagged in the
    schema-layer report as an open-decision recommendation, not a locked
    architectural fact.
    """

    created_by: str
    created_at: str = ""
    source_basis: str
    version: str

    @model_validator(mode="before")
    @classmethod
    def _apply_defaults(cls, data):
        if isinstance(data, dict):
            data = dict(data)
            data.setdefault("created_at", _utc_now_iso())
        return data


class ScreenResult(HypermindModel):
    """Trust Boundary A (input guard) screening result.

    Shape is `{cleared: bool, reason: Optional[str]}` per
    docs/02_COMPONENT_SPECS.md §8's interface definition
    (`screen(input) -> ScreenResult`), referenced (not redefined) by
    OD-09 in docs/13_OPEN_DECISIONS.md, which recommends formalising it
    as a docs/03 schema but has not yet done so. docs/02 was not one of
    this context's required-reading documents, but it is the only place
    this shape is defined and docs/13 points directly at it, so it is
    used here rather than guessed.
    """

    cleared: bool
    reason: Optional[str] = None
