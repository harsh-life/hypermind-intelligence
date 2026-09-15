"""Evidence Gate / Deduplication schemas.
Source: docs/03_DATA_SCHEMAS_README.md §2.18-2.19.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import model_validator

from trackA.schemas.base import HypermindModel
from trackA.schemas.common import Provenance


class CheckResult(HypermindModel):
    """EvidenceGateResult.checks_performed[] item shape, docs/03 §2.18."""

    check_name: str
    passed: bool


class EvidenceGateResult(HypermindModel):
    """docs/03 §2.18. Produced by: Evidence Gate (deterministic — no
    model/tool provenance per docs/02_COMPONENT_SPECS.md §9).
    """

    provenance: Provenance
    source_poc_record_id: str
    result: Literal["pass", "fail", "needs_more_evidence"]
    checks_performed: List[CheckResult]
    reasons: List[str]

    @model_validator(mode="after")
    def _validate(self) -> "EvidenceGateResult":
        if self.provenance.model_id or self.provenance.tool_id:
            raise ValueError(
                "EvidenceGateResult.provenance must set neither model_id "
                "nor tool_id — the Evidence Gate is deterministic "
                "(docs/02_COMPONENT_SPECS.md §9)"
            )
        if self.result in ("fail", "needs_more_evidence") and not self.reasons:
            raise ValueError(
                "EvidenceGateResult.reasons must be non-empty when result "
                "is 'fail' or 'needs_more_evidence' (docs/03 §2.18)"
            )
        return self


class DeduplicationResult(HypermindModel):
    """docs/03 §2.19. Produced by: Deduplication Engine."""

    provenance: Provenance
    source_poc_record_id: str
    result: Literal["unique", "duplicate"]
    matched_finding_id: Optional[str] = None
    match_confidence: Optional[float] = None

    @model_validator(mode="after")
    def _validate(self) -> "DeduplicationResult":
        if self.result == "duplicate":
            if not self.matched_finding_id:
                raise ValueError(
                    "DeduplicationResult.matched_finding_id is required "
                    "when result == 'duplicate' (docs/03 §2.19)"
                )
            if self.match_confidence is None:
                raise ValueError(
                    "DeduplicationResult.match_confidence is required "
                    "when result == 'duplicate' (docs/03 §2.19)"
                )
        if self.match_confidence is not None and not (0.0 <= self.match_confidence <= 1.0):
            raise ValueError("DeduplicationResult.match_confidence must be within [0, 1]")
        return self
