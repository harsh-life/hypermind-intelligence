"""Worker schemas. Source: docs/03_DATA_SCHEMAS_README.md §2.10-2.12,
reconciled against docs/04_WORKER_SKILL_CONTRACTS.md and the [LOCKED]
role/implementation separation in docs/01_ARCHITECTURE.md §4.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import model_validator

from trackA.schemas.base import HypermindModel
from trackA.schemas.common import ManifestProvenance, PipelineStage, Provenance, TrustClassification


class WorkerManifest(HypermindModel):
    """docs/03 §2.10, [LOCKED field list], RECONCILED.

    Two deliberate deviations from docs/03's literal text, both flagged:

    - docs/03 §2.10 names the model-pointer field `model` ("references a
      Model Registry role/model_id"). docs/04_WORKER_SKILL_CONTRACTS.md
      instead specifies `worker_role_binding` — "a POINTER, not a model
      identifier" — with an explicit rationale: the worker contract must
      survive a model swap unmodified, so it names a *role*, never a
      model. docs/01_ARCHITECTURE.md §4 [LOCKED] states the same
      principle generally ("the worker contract... does NOT hardcode
      which model fulfils it"). Since the calling task requires
      preserving "model-role vs model-identity separation" and docs/04
      is one of its named authoritative documents, this implementation
      uses `worker_role_binding` (docs/04's field), not `model`
      (docs/03's field), for the same slot. All of docs/03's other
      fields are kept as-is.
    - `provenance: ManifestProvenance` is added, per OD-15/FINDING-2 (see
      trackA/schemas/common.py's ManifestProvenance docstring). docs/03's
      WorkerManifest has no authorship-provenance field, only the
      unrelated `provenance_requirements` (what to log at *runtime*,
      kept below, unchanged).

    NOT implemented: docs/04's own, differently-shaped WorkerManifest
    sketch (role/input/task/output/evidence/limits/escalation/quality
    nested structure). docs/03 is the schema actually cited by
    docs/02_COMPONENT_SPECS.md §2 as the canonical shape; docs/04's
    sketch appears to be an earlier, unreconciled draft. Flagged in the
    schema-layer report as an unresolved cross-document inconsistency.
    """

    worker_id: str
    purpose: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    worker_role_binding: str
    system_prompt: str
    allowed_tools: List[str]
    timeout_seconds: int
    retry_limit: int
    resource_limits: Dict[str, Any]
    success_criteria: str
    failure_criteria: str
    must_not: List[str]
    provenance_requirements: str
    provenance: ManifestProvenance

    @model_validator(mode="after")
    def _validate(self) -> "WorkerManifest":
        if self.timeout_seconds <= 0:
            raise ValueError("WorkerManifest.timeout_seconds must be > 0")
        if self.retry_limit < 0:
            raise ValueError("WorkerManifest.retry_limit must be >= 0")
        return self


class WorkerInput(HypermindModel):
    """docs/03 §2.11. Produced by: Worker Execution Framework."""

    provenance: Provenance
    worker_id: str
    payload: Dict[str, Any]
    source_extractor_record_id: str

    @model_validator(mode="after")
    def _stage_is_worker(self) -> "WorkerInput":
        if self.provenance.stage != PipelineStage.WORKER:
            raise ValueError("WorkerInput.provenance.stage must be 'worker'")
        return self


class WorkerOutput(HypermindModel):
    """docs/03 §2.12. Produced by: Worker Execution Framework.

    NOTE: docs/04_WORKER_SKILL_CONTRACTS.md's "WorkerOutput Schema"
    section defines a materially different shape
    (worker_id/version/target/timestamp/findings[]/status/failure_reason)
    from this one. This implementation follows docs/03 §2.12 (the
    canonical schema, cited directly by docs/02_COMPONENT_SPECS.md §14
    and consistent with the general Provenance/trust_classification
    pattern used everywhere else in docs/03). docs/04's sketch is treated
    as an earlier, unreconciled draft — flagged in the schema-layer
    report; this conflict was not caught by docs/14_CONSISTENCY_AUDIT.md.
    """

    provenance: Provenance
    trust_classification: Literal[TrustClassification.MODEL_INTERPRETATION] = (
        TrustClassification.MODEL_INTERPRETATION
    )
    worker_id: str
    payload: Dict[str, Any]
    retry_count: int

    @model_validator(mode="after")
    def _validate(self) -> "WorkerOutput":
        if self.retry_count < 0:
            raise ValueError("WorkerOutput.retry_count must be >= 0")
        if not self.provenance.model_id:
            raise ValueError(
                "WorkerOutput.provenance.model_id is required (docs/03 §2.12)"
            )
        return self
