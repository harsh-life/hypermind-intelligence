"""Research-data schemas. Source: docs/03_DATA_SCHEMAS_README.md §3.

[LOCKED] per docs/03 §3 / docs/10_RESEARCH_DATA_PIPELINE.md §1: every
schema here is written to the Research/Audit Store only and is never
read back into a live pipeline decision. That firewall is an interface-
level guarantee (the Research Store exposing record()/write but no
reachable query() to live components) which belongs to the Research
Store component itself — explicitly out of scope for this context. This
module implements only the record *shapes*.

ValidatedFinding (task's requested name) = FindingRecord.
"Trajectory" (task's requested "Experiment / Trajectory records") maps to
ToolSequenceRecord — no schema literally named "Trajectory" exists
anywhere in docs/01-18; ToolSequenceRecord (the ordered sequence of tool
executions in one run, docs/03 §3.7) is the closest documented concept.
See trackA/schemas/__init__.py for the alias list.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import model_validator

from trackA.schemas.base import HypermindModel
from trackA.schemas.common import Provenance, TrustClassification


class ResearchEvent(HypermindModel):
    """docs/03 §3.1. The generic envelope every other research object is
    wrapped in when written to the store.
    """

    provenance: Provenance
    event_category: Literal[
        "finding",
        "candidate",
        "replication",
        "validation",
        "experiment",
        "tool_sequence",
        "model_evaluation",
        "dataset",
        "model_version",
    ]
    payload: Dict[str, Any]
    trust_classification: TrustClassification

    @model_validator(mode="after")
    def _validation_events_carry_validated_trust(self) -> "ResearchEvent":
        # docs/03 §3.1's invalid example: "a validation event must carry
        # the post-validation trust level, not the pre-validation one."
        if self.event_category == "validation" and self.trust_classification != (
            TrustClassification.VALIDATED_FINDING
        ):
            raise ValueError(
                "ResearchEvent: event_category == 'validation' requires "
                "trust_classification == VALIDATED_FINDING (docs/03 §3.1)"
            )
        return self


class FindingRecord(HypermindModel):
    """docs/03 §3.2. Derived only from a ValidationOutcome where
    decision == "submit". The "ground truth" research record.
    """

    provenance: Provenance
    validation_outcome_record_id: str
    vulnerability_class: str
    skill_id_used: str
    full_evidence_trail: List[str]
    outcome_status: Optional[Literal["accepted", "rejected_by_platform", "pending"]] = None


class CandidateFindingRecord(HypermindModel):
    """docs/03 §3.3. Derived from every SpecialistPoCOutput, regardless of
    eventual outcome.
    """

    provenance: Provenance
    poc_record_id: str
    eventual_outcome: Literal[
        "pending",
        "passed_evidence_gate",
        "failed_evidence_gate",
        "blocked_duplicate",
        "human_discarded",
        "human_submitted",
    ]


class ReplicationRecord(HypermindModel):
    """docs/03 §3.4."""

    provenance: Provenance
    poc_record_id: str
    replication_command: str
    validated: bool

    @model_validator(mode="after")
    def _non_empty_command(self) -> "ReplicationRecord":
        if not self.replication_command:
            raise ValueError("ReplicationRecord.replication_command must be non-empty")
        return self


class ExperimentModelResult(HypermindModel):
    """ExperimentRecord.results_per_model[] item shape, docs/03 §3.6."""

    model_id: str
    metrics: Dict[str, Any]


class ExperimentRecord(HypermindModel):
    """docs/03 §3.6. For offline model-benchmarking experiments."""

    provenance: Provenance
    experiment_id: str
    role_under_test: Literal["extractor", "worker", "judge", "specialist", "report_polisher"]
    candidate_model_ids: List[str]
    evaluation_dataset_id: str
    results_per_model: List[ExperimentModelResult]
    winner_model_id: Optional[str] = None

    @model_validator(mode="after")
    def _at_least_one_candidate(self) -> "ExperimentRecord":
        if len(self.candidate_model_ids) < 1:
            raise ValueError("ExperimentRecord.candidate_model_ids must be non-empty")
        return self


class ToolSequenceEntry(HypermindModel):
    """ToolSequenceRecord.sequence[] item shape, docs/03 §3.7."""

    tool_id: str
    order_index: int
    outcome: str


class ToolSequenceRecord(HypermindModel):
    """docs/03 §3.7. Derived OFFLINE from a run's AuditEvent stream — not
    a live emission. This is the "trajectory" concept: which tool-call
    ordering, within one run, did or did not lead to a candidate.
    """

    provenance: Provenance
    run_id: str
    sequence: List[ToolSequenceEntry]
    led_to_candidate: bool

    @model_validator(mode="after")
    def _sequence_is_ordered(self) -> "ToolSequenceRecord":
        indices = [entry.order_index for entry in self.sequence]
        if indices != sorted(indices):
            raise ValueError(
                "ToolSequenceRecord.sequence entries must be ordered by "
                "order_index (docs/03 §3.7 invalid example)"
            )
        return self


class ModelEvaluationRecord(HypermindModel):
    """docs/03 §3.8. The persisted output of an ExperimentRecord; what
    docs/08_MODEL_REGISTRY.md reads from when populating a ModelManifest's
    quality_metrics.
    """

    provenance: Provenance
    model_id: str
    role: Literal["extractor", "worker", "judge", "specialist", "report_polisher"]
    evaluation_dataset_id: str
    metrics: Dict[str, Any]
    known_limitations: List[str]


class DatasetRecord(HypermindModel):
    """docs/03 §3.9. Versioning *policy* (immutability etc.) is Research
    Store / research-pipeline behavior and out of scope here; only the
    shape (including the required non-empty purity_notes) is enforced.
    """

    provenance: Provenance
    dataset_id: str
    version: str
    source_record_ids: List[str]
    purity_notes: str

    @model_validator(mode="after")
    def _purity_notes_required(self) -> "DatasetRecord":
        if not self.purity_notes:
            raise ValueError(
                "DatasetRecord.purity_notes must be non-empty (docs/03 §3.9 "
                "invalid example)"
            )
        return self


class ModelVersionRecord(HypermindModel):
    """docs/03 §3.10."""

    provenance: Provenance
    model_id: str
    version: str
    parent_version: Optional[str] = None
    training_data_reference: Optional[str] = None

    @model_validator(mode="after")
    def _training_data_reference_required_for_derivatives(self) -> "ModelVersionRecord":
        if self.parent_version and not self.training_data_reference:
            raise ValueError(
                "ModelVersionRecord.training_data_reference is required "
                "when parent_version is set (docs/03 §3.10)"
            )
        return self
