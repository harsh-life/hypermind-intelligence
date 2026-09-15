from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.schemas.common import PipelineStage, TrustClassification
from trackA.schemas.research import (
    CandidateFindingRecord,
    DatasetRecord,
    ExperimentModelResult,
    ExperimentRecord,
    FindingRecord,
    ModelEvaluationRecord,
    ModelVersionRecord,
    ReplicationRecord,
    ResearchEvent,
    ToolSequenceEntry,
    ToolSequenceRecord,
)
from tests.conftest import make_provenance


def test_research_event_validation_category_requires_validated_trust(run_id):
    with pytest.raises(ValidationError):
        ResearchEvent(
            provenance=make_provenance(run_id, PipelineStage.HUMAN_VERIFICATION),
            event_category="validation",
            payload={"...": "..."},
            trust_classification=TrustClassification.CANDIDATE_FINDING,
        )


def test_research_event_validation_category_valid(run_id):
    evt = ResearchEvent(
        provenance=make_provenance(run_id, PipelineStage.HUMAN_VERIFICATION),
        event_category="validation",
        payload={"...": "a ValidationOutcome object"},
        trust_classification=TrustClassification.VALIDATED_FINDING,
    )
    assert evt.event_category == "validation"


def test_finding_record_valid(run_id):
    record = FindingRecord(
        provenance=make_provenance(run_id, PipelineStage.HUMAN_VERIFICATION),
        validation_outcome_record_id="j1",
        vulnerability_class="IDOR",
        skill_id_used="idor_v1",
        full_evidence_trail=["c1"],
        outcome_status="pending",
    )
    assert record.outcome_status == "pending"


def test_candidate_finding_record_valid(run_id):
    record = CandidateFindingRecord(
        provenance=make_provenance(run_id, PipelineStage.SPECIALIST),
        poc_record_id="g1",
        eventual_outcome="human_submitted",
    )
    assert record.eventual_outcome == "human_submitted"


def test_candidate_finding_record_rejects_unknown_outcome(run_id):
    with pytest.raises(ValidationError):
        CandidateFindingRecord(
            provenance=make_provenance(run_id, PipelineStage.SPECIALIST),
            poc_record_id="g1",
            eventual_outcome="unknown",
        )


def test_replication_record_rejects_empty_command(run_id):
    with pytest.raises(ValidationError):
        ReplicationRecord(
            provenance=make_provenance(run_id, PipelineStage.SPECIALIST),
            poc_record_id="g1",
            replication_command="",
            validated=False,
        )


def test_experiment_record_requires_at_least_one_candidate(run_id):
    with pytest.raises(ValidationError):
        ExperimentRecord(
            provenance=make_provenance(run_id, PipelineStage.JUDGE),
            experiment_id="exp-1",
            role_under_test="judge",
            candidate_model_ids=[],
            evaluation_dataset_id="ds-1",
            results_per_model=[],
        )


def test_experiment_record_valid(run_id):
    record = ExperimentRecord(
        provenance=make_provenance(run_id, PipelineStage.JUDGE),
        experiment_id="exp-judge-2026-08",
        role_under_test="judge",
        candidate_model_ids=["judge-model-a", "judge-model-b"],
        evaluation_dataset_id="ds-judge-eval-v1",
        results_per_model=[
            ExperimentModelResult(model_id="judge-model-a", metrics={"precision": 0.82}),
        ],
    )
    assert record.winner_model_id is None


def test_tool_sequence_record_rejects_unordered_sequence(run_id):
    with pytest.raises(ValidationError):
        ToolSequenceRecord(
            provenance=make_provenance(run_id, PipelineStage.TOOL_EXECUTION),
            run_id=run_id,
            sequence=[
                ToolSequenceEntry(tool_id="httpx", order_index=5, outcome="success"),
                ToolSequenceEntry(tool_id="subfinder", order_index=1, outcome="success"),
            ],
            led_to_candidate=True,
        )


def test_tool_sequence_record_valid_ordered_sequence(run_id):
    record = ToolSequenceRecord(
        provenance=make_provenance(run_id, PipelineStage.TOOL_EXECUTION),
        run_id=run_id,
        sequence=[
            ToolSequenceEntry(tool_id="subfinder", order_index=1, outcome="success"),
            ToolSequenceEntry(tool_id="httpx", order_index=2, outcome="success"),
        ],
        led_to_candidate=True,
    )
    assert record.led_to_candidate is True


def test_model_evaluation_record_valid(run_id):
    record = ModelEvaluationRecord(
        provenance=make_provenance(run_id, PipelineStage.JUDGE),
        model_id="judge-model-a",
        role="judge",
        evaluation_dataset_id="ds-judge-eval-v1",
        metrics={"precision": 0.82, "recall": 0.71},
        known_limitations=["struggles with contradictory evidence"],
    )
    assert record.role == "judge"


def test_dataset_record_requires_purity_notes(run_id):
    with pytest.raises(ValidationError):
        DatasetRecord(
            provenance=make_provenance(run_id, PipelineStage.JUDGE),
            dataset_id="ds-judge-eval-v1",
            version="2026-08-31",
            source_record_ids=["m1", "m2"],
            purity_notes="",
        )


def test_model_version_record_requires_training_data_reference_for_derivative(run_id):
    with pytest.raises(ValidationError):
        ModelVersionRecord(
            provenance=make_provenance(run_id, PipelineStage.JUDGE),
            model_id="specialist-idor-lora-v1",
            version="v1",
            parent_version="qwen2.5-1.5b-base",
        )


def test_model_version_record_base_model_has_no_parent(run_id):
    record = ModelVersionRecord(
        provenance=make_provenance(run_id, PipelineStage.JUDGE),
        model_id="qwen2.5-1.5b-base",
        version="v1",
    )
    assert record.parent_version is None
