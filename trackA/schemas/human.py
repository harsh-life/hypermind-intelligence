"""Human verification / reporting schemas.
Source: docs/03_DATA_SCHEMAS_README.md §2.20-2.21, §3.5.

ValidationEvent (the task's requested name) = ValidationOutcome below —
see trackA/schemas/__init__.py for the alias. This is the only path that
may ever produce a VALIDATED_FINDING (docs/03 §1.2, [LOCKED]); the
Human Validation API that would actually capture a human's decision is
explicitly out of scope for this context — only its data shape is
implemented here.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import model_validator

from trackA.schemas.base import HypermindModel
from trackA.schemas.common import PipelineStage, Provenance


class HumanReviewPackage(HypermindModel):
    """docs/03 §2.20. Produced by: Deduplication Engine, for the human.

    Referential checks that require looking up other stored records
    (e.g. confirming `evidence_gate_result_id` really does reference an
    EvidenceGateResult with result == "pass") are out of scope for this
    schema layer — they require a data store / registry, both explicitly
    excluded from this context. Only the shape and the fields that are
    locally checkable are validated here.
    """

    provenance: Provenance
    poc_record_id: str
    full_evidence_trail: List[str]
    evidence_gate_result_id: str
    deduplication_result_id: str

    @model_validator(mode="after")
    def _stage_and_trail(self) -> "HumanReviewPackage":
        if self.provenance.stage != PipelineStage.HUMAN_VERIFICATION:
            raise ValueError(
                "HumanReviewPackage.provenance.stage must be 'human_verification'"
            )
        if len(self.full_evidence_trail) < 1:
            raise ValueError("HumanReviewPackage.full_evidence_trail must not be empty")
        return self


class ValidationOutcome(HypermindModel):
    """docs/03 §2.28 / §3.5 (dual pipeline+research schema). Produced by:
    Human Verification Interface.

    [LOCKED] No default/timeout-based decision is permitted
    (docs/02_COMPONENT_SPECS.md §18) — `decision` and `human_identity`
    are both required with no defaults, so a record cannot be constructed
    without an explicit choice and an identified human.
    """

    provenance: Provenance
    human_review_package_id: str
    decision: Literal["submit", "discard", "needs_more_evidence"]
    human_identity: str
    decided_at: str
    discard_reason: Optional[str] = None

    @model_validator(mode="after")
    def _validate(self) -> "ValidationOutcome":
        if self.provenance.stage != PipelineStage.HUMAN_VERIFICATION:
            raise ValueError(
                "ValidationOutcome.provenance.stage must be 'human_verification'"
            )
        if not self.human_identity:
            raise ValueError("ValidationOutcome.human_identity must not be empty")
        if self.decision == "discard" and not self.discard_reason:
            raise ValueError(
                "ValidationOutcome.discard_reason is required when "
                "decision == 'discard' (docs/03 §3.5)"
            )
        return self


class Report(HypermindModel):
    """docs/03 §2.21. Produced by: Report Polisher.

    [LOCKED] must reference a ValidationOutcome with decision == "submit"
    (docs/02_COMPONENT_SPECS.md §17). The referential check itself
    (does `validation_outcome_record_id` really point at a submit
    outcome?) requires a data store and is out of scope here; only the
    shape is validated.
    """

    provenance: Provenance
    validation_outcome_record_id: str
    formatted_title: str
    formatted_body: str
    source_claims: List[str]

    @model_validator(mode="after")
    def _stage_is_report_polisher(self) -> "Report":
        if self.provenance.stage != PipelineStage.REPORT_POLISHER:
            raise ValueError("Report.provenance.stage must be 'report_polisher'")
        if not self.provenance.model_id:
            raise ValueError("Report.provenance.model_id is required (docs/03 §2.21)")
        return self
