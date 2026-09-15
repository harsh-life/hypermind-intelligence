"""Judge schemas. Source: docs/03_DATA_SCHEMAS_README.md §2.13-2.14.

"Judge Evaluation Package" (the task's requested name) = JudgeInput below
— see trackA/schemas/__init__.py for the alias.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import model_validator

from trackA.schemas.base import HypermindModel
from trackA.schemas.common import Provenance


class JudgeInput(HypermindModel):
    """docs/03 §2.13. Produced by: whatever assembles Worker outputs for
    the Judge (docs/02 §11->§15).

    [LOCKED] `contains_skill_content` must always be `False` — this is
    the schema-level enforcement of Judge neutrality
    (docs/01_ARCHITECTURE.md §19.7, docs/02_COMPONENT_SPECS.md §3/§15).
    Modelled as `Literal[False]` so a record with `true` simply cannot be
    constructed, matching docs/03's framing: "this record must never be
    constructible with this value."
    """

    provenance: Provenance
    worker_output_record_ids: List[str]
    accumulated_evidence: Dict[str, Any]
    contains_skill_content: Literal[False] = False

    @model_validator(mode="after")
    def _at_least_one_worker_output(self) -> "JudgeInput":
        if len(self.worker_output_record_ids) < 1:
            raise ValueError(
                "JudgeInput.worker_output_record_ids must contain at least one id"
            )
        return self


class JudgeRoutingDecision(HypermindModel):
    """docs/03 §2.14. Produced by: Neutral Judge."""

    provenance: Provenance
    decision: Literal["route_to_skill", "needs_more_evidence", "drop"]
    target_skill_id: Optional[str] = None
    reasoning: str
    confidence: float

    @model_validator(mode="after")
    def _validate(self) -> "JudgeRoutingDecision":
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("JudgeRoutingDecision.confidence must be within [0, 1]")
        if self.decision == "route_to_skill" and not self.target_skill_id:
            raise ValueError(
                "JudgeRoutingDecision.target_skill_id is required when "
                "decision == 'route_to_skill' (docs/03 §2.14)"
            )
        if not self.provenance.model_id:
            raise ValueError(
                "JudgeRoutingDecision.provenance.model_id is required (docs/03 §2.14)"
            )
        return self
