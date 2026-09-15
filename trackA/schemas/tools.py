"""Tool schemas. Source: docs/03_DATA_SCHEMAS_README.md §2.4-2.7,
docs/06_TOOL_REGISTRY_README.md (expected_output field, OD-19),
docs/13_OPEN_DECISIONS.md OD-15/OD-19.

ToolRequest/ToolResult/Observation are the task-requested names for
ToolExecutionRequest/ToolExecutionResult/RawToolOutput — see aliases in
trackA/schemas/__init__.py.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import model_validator

from trackA.schemas.base import HypermindModel
from trackA.schemas.common import ManifestProvenance, Provenance, TrustClassification


class ToolManifest(HypermindModel):
    """docs/03 §2.4, [LOCKED field list]. Registry entries: docs/06.

    Two deliberate deviations from docs/03's literal text, both flagged:

    - `category` is kept as an open `str`, not a closed enum. docs/03 §2.4
      explicitly permits extending this value set "via registry update,
      not a code change" (docs/06 already exercised that permission by
      adding "vulnerability_scan" for Nuclei). Canonical values as of
      docs/06: recon | ai_security | web_probe | vulnerability_scan.
    - `expected_output` is added. docs/03's ToolManifest omitted it, but
      docs/06 populates it on every instantiated entry and OD-19
      (docs/13_OPEN_DECISIONS.md) records this as a documentation gap
      that should be closed — "a documentation-cleanliness fix, not a
      functional gap." Included here since the task explicitly names
      `ToolManifest.expected_output`.
    - `provenance: ManifestProvenance` is added per OD-15 (docs/13_OPEN_
      DECISIONS.md, [LOCKED] — see trackA/schemas/common.py's
      ManifestProvenance docstring) — docs/03's ToolManifest has no
      authorship-provenance field at all, only the unrelated
      `audit_requirements` (what to log at *runtime*, kept below,
      unchanged).
    - `validation_status` is added (Context 2, registries scope). Neither
      docs/03 §2.4 nor docs/06's illustrative JSON instances literally
      define this as a manifest field, yet docs/06 §8's prose ("marked
      `validation_status: provisional_pending_OD-01`") and
      docs/12_ACCEPTANCE_CRITERIA_README.md AC-007 ("A `validation_status`
      other than `active` ... blocks execution the same as full
      non-registration") both require the Tool Registry to track and gate
      on exactly this field. This is the same class of gap OD-19 already
      resolved for `expected_output` — an instance/prose-level requirement
      docs/03's schema never formalised — so the same resolution applies:
      add the field to the canonical schema rather than inventing a
      second, parallel "registry state" representation of it. Kept as an
      open `str` (default `"active"`), mirroring `category`'s existing
      open-string precedent, since future tools may need arbitrary
      provisional-pending states (as Promptfoo does for OD-01) that a
      small closed enum can't anticipate. `SkillManifest.validation_status`
      (docs/03 §2.15) remains its own, separately-defined closed enum —
      not reused here, since its three values (draft/active/deprecated)
      don't cover the Promptfoo-style provisional state this field must
      represent.

    [FINAL per architecture-owner decision — do not reopen.]
    `risk_classification` stays the closed `low | medium | high` enum
    from docs/03 §2.4; it is NOT expanded. docs/06's Nuclei entry, which
    previously instantiated the out-of-enum value `"medium-high"`, has
    been corrected to `"high"` to match this enum.
    """

    tool_id: str
    name: str
    version: str
    purpose: str
    category: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None
    expected_output: str
    container_image: str
    network_requirements: Dict[str, Any]
    filesystem_requirements: Dict[str, Any]
    resource_limits: Dict[str, Any]
    timeout_seconds: int
    allowed_stages: List[str]
    risk_classification: Literal["low", "medium", "high"]
    failure_handling: str
    audit_requirements: str
    provenance: ManifestProvenance
    validation_status: str = "active"

    @model_validator(mode="after")
    def _positive_timeout(self) -> "ToolManifest":
        if self.timeout_seconds <= 0:
            raise ValueError("ToolManifest.timeout_seconds must be > 0")
        return self


class ToolExecutionRequest(HypermindModel):
    """docs/03 §2.5. Produced by: Orchestrator."""

    provenance: Provenance
    tool_id: str
    parameters: Dict[str, Any]
    authorized_by_action_id: str


class ToolExecutionResult(HypermindModel):
    """docs/03 §2.6. Produced by: Docker Tool Execution Engine."""

    provenance: Provenance
    request_record_id: str
    exit_status: Literal["success", "timeout", "crash", "resource_exhausted"]
    duration_ms: int
    raw_output_record_id: Optional[str] = None

    @model_validator(mode="after")
    def _validate(self) -> "ToolExecutionResult":
        if self.duration_ms < 0:
            raise ValueError("ToolExecutionResult.duration_ms must be >= 0")
        if not self.provenance.tool_id:
            raise ValueError(
                "ToolExecutionResult.provenance.tool_id is required "
                "(docs/03 §2.6)"
            )
        if self.exit_status == "success" and not self.raw_output_record_id:
            raise ValueError(
                "ToolExecutionResult.raw_output_record_id is required "
                "when exit_status == 'success' (docs/03 §2.6)"
            )
        return self


class RawToolOutput(HypermindModel):
    """docs/03 §2.7. Produced by: Docker Tool Execution Engine.

    This is Trust Boundary B, physically (docs/07_DOCKER_SPEC_README.md
    §7, [LOCKED]): the moment output is captured it becomes this record,
    permanently marked RAW_OBSERVATION. `content` must never be parsed as
    instructions by any downstream consumer.
    """

    provenance: Provenance
    trust_classification: Literal[TrustClassification.RAW_OBSERVATION] = (
        TrustClassification.RAW_OBSERVATION
    )
    content: str
    truncated: bool
