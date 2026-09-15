"""Scope schemas. Source: docs/03_DATA_SCHEMAS_README.md §2.1-2.2.

RunScope and Run are constructed convenience types — see their docstrings
for exactly what is documented vs. what is a reasoned aggregation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import model_validator

from trackA.schemas.base import HypermindModel
from trackA.schemas.common import Provenance, _new_uuid, _utc_now_iso  # noqa: F401


class ScopeRequest(HypermindModel):
    """docs/03 §2.1. Produced by: Human / Scope Gate caller."""

    provenance: Provenance
    target_identifier: str
    authorization_reference: str
    requested_by: str
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _stage_is_scope_gate(self) -> "ScopeRequest":
        from trackA.schemas.common import PipelineStage

        if self.provenance.stage != PipelineStage.SCOPE_GATE:
            raise ValueError("ScopeRequest.provenance.stage must be 'scope_gate'")
        return self


class ScopeDecision(HypermindModel):
    """docs/03 §2.2. Produced by: Scope Gate."""

    provenance: Provenance
    request_record_id: str
    decision: Literal["allow", "deny"]
    reason: str
    policy_version: str

    @model_validator(mode="after")
    def _stage_is_scope_gate(self) -> "ScopeDecision":
        from trackA.schemas.common import PipelineStage

        if self.provenance.stage != PipelineStage.SCOPE_GATE:
            raise ValueError("ScopeDecision.provenance.stage must be 'scope_gate'")
        return self


class RunScope(HypermindModel):
    """Composition of a ScopeRequest and its (possibly not-yet-made)
    ScopeDecision for one run.

    NOT a literally-named schema in docs/03 — docs/03 §2.1/§2.2 define
    ScopeRequest and ScopeDecision as two separate records correlated only
    via ScopeDecision.request_record_id. RunScope pairs them because a run
    cannot proceed past Stage 0 (docs/01_ARCHITECTURE.md §5) without both
    existing, and downstream code needs one thing to hold. Built only from
    the two documented schemas; no new fields invented.
    """

    request: ScopeRequest
    decision: Optional[ScopeDecision] = None

    @model_validator(mode="after")
    def _decision_correlates_to_request(self) -> "RunScope":
        if self.decision is not None:
            if self.decision.request_record_id != self.request.provenance.record_id:
                raise ValueError(
                    "RunScope.decision.request_record_id must reference "
                    "RunScope.request.provenance.record_id"
                )
        return self

    @property
    def is_authorized(self) -> bool:
        """True only once an explicit 'allow' ScopeDecision exists.

        Ambiguity/absence must never resolve to authorized — mirrors the
        default-deny principle stated repeatedly across docs/01 §4 and
        docs/09_SECURITY_POLICIES §1 (enforcing that principle at runtime
        is Scope Gate logic and out of scope here; this property only
        reflects the state already present on the object).
        """

        return self.decision is not None and self.decision.decision == "allow"


class Run(HypermindModel):
    """Minimal run-correlation record.

    UNRESOLVED AMBIGUITY: no document defines a standalone "Run" schema.
    docs/03_DATA_SCHEMAS_README.md §1.1 only establishes
    `Provenance.run_id` as the join key correlating every record produced
    during one target's run — there is no dedicated record type for the
    run itself. This type is a thin, explicitly-flagged convenience built
    only from already-documented, already-required fields (a run_id, the
    RunScope that authorizes it, and a start timestamp) so downstream
    code has something to construct before individual pipeline records
    exist. If a literal Run schema is later specified in the docs,
    replace this type rather than silently extend it.
    """

    run_id: str
    scope: RunScope
    started_at: str = ""

    @model_validator(mode="before")
    @classmethod
    def _apply_defaults(cls, data):
        if isinstance(data, dict):
            data = dict(data)
            data.setdefault("started_at", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        return data

    @model_validator(mode="after")
    def _scope_run_id_matches(self) -> "Run":
        if self.scope.request.provenance.run_id != self.run_id:
            raise ValueError("Run.scope.request.provenance.run_id must equal Run.run_id")
        if self.scope.decision is not None and self.scope.decision.provenance.run_id != self.run_id:
            raise ValueError("Run.scope.decision.provenance.run_id must equal Run.run_id")
        return self
