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
    """docs/03 §2.10, [LOCKED field list], FINAL per architecture-owner
    decision (Context-1 schema-decisions review — do not reopen).

    Two confirmed deviations from docs/03's original literal text:

    - The model-pointer field is `worker_role_binding`, not docs/03's
      `model` field (docs/03's `model` field is superseded). Per
      docs/04_WORKER_SKILL_CONTRACTS.md's design — "a POINTER, not a
      model identifier" — and docs/01_ARCHITECTURE.md §4 [LOCKED]'s
      general principle that a worker contract "does NOT hardcode which
      model fulfils it": the manifest must point to a worker *role*,
      never a concrete model identity. All of docs/03's other fields are
      kept as-is.
    - `provenance: ManifestProvenance` is added, per OD-15 (docs/13_OPEN_
      DECISIONS.md, [LOCKED] — see trackA/schemas/common.py's
      ManifestProvenance docstring). docs/03's WorkerManifest has no
      authorship-provenance field, only the unrelated
      `provenance_requirements` (what to log at *runtime*, kept below,
      unchanged).

    NOT implemented: docs/04's own, differently-shaped WorkerManifest
    sketch (role/input/task/output/evidence/limits/escalation/quality
    nested structure) — docs/03's flatter field set remains canonical;
    only the model-pointer field name was swapped for docs/04's.
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

    [FINAL per architecture-owner decision — do not reopen.] docs/03
    §2.12's shape is canonical, per docs/02_COMPONENT_SPECS.md §14's
    explicit citation of docs/03 as the schema authority for
    WorkerOutput. docs/04_WORKER_SKILL_CONTRACTS.md's differently-shaped
    inline "WorkerOutput Schema" sketch
    (worker_id/version/target/timestamp/findings[]/status/failure_reason)
    is marked superseded/stale in docs/04 itself and must not be
    implemented against.
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
