from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.schemas.common import PipelineStage
from trackA.schemas.gates import CheckResult, DeduplicationResult, EvidenceGateResult
from tests.conftest import make_provenance


def test_evidence_gate_pass_with_no_reasons(run_id):
    result = EvidenceGateResult(
        provenance=make_provenance(run_id, PipelineStage.EVIDENCE_GATE),
        source_poc_record_id="g1",
        result="pass",
        checks_performed=[CheckResult(check_name="replication_command_present", passed=True)],
        reasons=[],
    )
    assert result.result == "pass"


def test_evidence_gate_fail_requires_reasons(run_id):
    with pytest.raises(ValidationError):
        EvidenceGateResult(
            provenance=make_provenance(run_id, PipelineStage.EVIDENCE_GATE),
            source_poc_record_id="g1",
            result="fail",
            checks_performed=[CheckResult(check_name="replication_command_present", passed=False)],
            reasons=[],
        )


def test_evidence_gate_rejects_model_or_tool_provenance(run_id):
    with pytest.raises(ValidationError):
        EvidenceGateResult(
            provenance=make_provenance(
                run_id, PipelineStage.EVIDENCE_GATE, model_id="x", model_version="v1"
            ),
            source_poc_record_id="g1",
            result="pass",
            checks_performed=[],
            reasons=[],
        )


def test_dedup_unique(run_id):
    result = DeduplicationResult(
        provenance=make_provenance(run_id, PipelineStage.DEDUPLICATION),
        source_poc_record_id="g1",
        result="unique",
    )
    assert result.matched_finding_id is None


def test_dedup_duplicate_requires_match_fields(run_id):
    with pytest.raises(ValidationError):
        DeduplicationResult(
            provenance=make_provenance(run_id, PipelineStage.DEDUPLICATION),
            source_poc_record_id="g1",
            result="duplicate",
            match_confidence=0.95,
        )


def test_dedup_duplicate_valid(run_id):
    result = DeduplicationResult(
        provenance=make_provenance(run_id, PipelineStage.DEDUPLICATION),
        source_poc_record_id="g1",
        result="duplicate",
        matched_finding_id="finding-123",
        match_confidence=0.95,
    )
    assert result.result == "duplicate"
