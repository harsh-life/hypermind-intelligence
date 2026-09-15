"""Cross-cutting audit/failure schemas.
Source: docs/03_DATA_SCHEMAS_README.md §2.22-2.23.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import model_validator

from trackA.schemas.base import HypermindModel
from trackA.schemas.common import Provenance


class AuditEvent(HypermindModel):
    """docs/03 §2.22. Produced by: any component.

    `event_type` is kept as an open `str`, not a closed enum: docs/03
    §2.22 explicitly says "Extend via registry update, not schema
    change [REC]", mirroring ToolManifest.category's treatment.
    Canonical values as of docs/03: authorized | rejected | gate_passed
    | gate_failed | human_decision | registry_lookup.
    """

    provenance: Provenance
    event_type: str
    detail: Dict[str, Any]
    related_record_ids: List[str]


class FailureEvent(HypermindModel):
    """docs/03 §2.23. Produced by: any component."""

    provenance: Provenance
    failure_type: Literal[
        "timeout",
        "crash",
        "resource_exhausted",
        "schema_invalid",
        "model_refusal",
        "unreachable_dependency",
    ]
    detail: str
    retry_count_at_failure: int

    @model_validator(mode="after")
    def _non_negative_retry(self) -> "FailureEvent":
        if self.retry_count_at_failure < 0:
            raise ValueError("FailureEvent.retry_count_at_failure must be >= 0")
        return self
