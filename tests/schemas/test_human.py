from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.schemas.common import PipelineStage
from trackA.schemas.human import HumanReviewPackage, Report, ValidationOutcome
from tests.conftest import make_provenance


def test_human_review_package_requires_nonempty_trail(run_id):
    with pytest.raises(ValidationError):
        HumanReviewPackage(
            provenance=make_provenance(run_id, PipelineStage.HUMAN_VERIFICATION),
            poc_record_id="g1",
            full_evidence_trail=[],
            evidence_gate_result_id="h1",
            deduplication_result_id="i1",
        )


def test_human_review_package_valid(run_id):
    pkg = HumanReviewPackage(
        provenance=make_provenance(run_id, PipelineStage.HUMAN_VERIFICATION),
        poc_record_id="g1",
        full_evidence_trail=["c1", "d1", "e1", "f1", "g1", "h1", "i1"],
        evidence_gate_result_id="h1",
        deduplication_result_id="i1",
    )
    assert len(pkg.full_evidence_trail) == 7


def test_validation_outcome_discard_requires_reason(run_id):
    with pytest.raises(ValidationError):
        ValidationOutcome(
            provenance=make_provenance(run_id, PipelineStage.HUMAN_VERIFICATION),
            human_review_package_id="k1",
            decision="discard",
            human_identity="harsh",
            decided_at="2026-08-31T11:00:00Z",
        )


def test_validation_outcome_no_default_decision_no_default_identity(run_id):
    # decision and human_identity have no defaults: omitting either fails.
    with pytest.raises(ValidationError):
        ValidationOutcome(
            provenance=make_provenance(run_id, PipelineStage.HUMAN_VERIFICATION),
            human_review_package_id="k1",
            decided_at="2026-08-31T11:00:00Z",
        )


def test_validation_outcome_submit_valid(run_id):
    outcome = ValidationOutcome(
        provenance=make_provenance(run_id, PipelineStage.HUMAN_VERIFICATION),
        human_review_package_id="k1",
        decision="submit",
        human_identity="harsh",
        decided_at="2026-08-31T11:00:00Z",
    )
    assert outcome.decision == "submit"


def test_report_requires_model_provenance(run_id):
    with pytest.raises(ValidationError):
        Report(
            provenance=make_provenance(run_id, PipelineStage.REPORT_POLISHER),
            validation_outcome_record_id="j1",
            formatted_title="IDOR in GET /api/v1/users/{id}",
            formatted_body="## Summary\n...",
            source_claims=["g1", "j1"],
        )


def test_report_valid(run_id):
    report = Report(
        provenance=make_provenance(
            run_id, PipelineStage.REPORT_POLISHER, model_id="polisher-model", model_version="v1"
        ),
        validation_outcome_record_id="j1",
        formatted_title="IDOR in GET /api/v1/users/{id}",
        formatted_body="## Summary\n...",
        source_claims=["g1", "j1"],
    )
    assert report.formatted_title
