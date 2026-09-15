from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.schemas.audit import AuditEvent, FailureEvent
from trackA.schemas.common import PipelineStage
from tests.conftest import make_provenance


def test_audit_event_accepts_documented_and_extended_event_types(run_id):
    for event_type in ["rejected", "gate_passed", "some_future_event_type"]:
        evt = AuditEvent(
            provenance=make_provenance(run_id, PipelineStage.ORCHESTRATOR),
            event_type=event_type,
            detail={"reason": "x"},
            related_record_ids=[],
        )
        assert evt.event_type == event_type


def test_failure_event_valid(run_id):
    fe = FailureEvent(
        provenance=make_provenance(run_id, PipelineStage.EXTRACTOR),
        failure_type="schema_invalid",
        detail="Extractor output did not conform to ExtractorJSON.v1",
        retry_count_at_failure=0,
    )
    assert fe.failure_type == "schema_invalid"


def test_failure_event_rejects_unknown_failure_type(run_id):
    with pytest.raises(ValidationError):
        FailureEvent(
            provenance=make_provenance(run_id, PipelineStage.EXTRACTOR),
            failure_type="oops",
            detail="something broke",
            retry_count_at_failure=0,
        )


def test_failure_event_rejects_negative_retry_count(run_id):
    with pytest.raises(ValidationError):
        FailureEvent(
            provenance=make_provenance(run_id, PipelineStage.EXTRACTOR),
            failure_type="timeout",
            detail="...",
            retry_count_at_failure=-1,
        )
