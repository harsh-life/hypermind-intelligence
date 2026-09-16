"""Track A schema/contract foundation.

Implements the machine-readable contracts defined in
docs/03_DATA_SCHEMAS_README.md, reconciled where necessary against
docs/01_ARCHITECTURE.md, docs/04_WORKER_SKILL_CONTRACTS.md,
docs/08_MODEL_REGISTRY.md, and docs/13_OPEN_DECISIONS.md. See each
module's docstring for exactly which fields/validators come from which
document, and every place a deviation from a single document's literal
text was made (all are flagged there and repeated in the top-level
implementation report).

Scope boundary: this package is schemas + validation + (de)serialization
only. It contains no registry, orchestration, execution, benchmarking,
Judge, Human-Validation-API, or reporting-pipeline *logic* — those are
explicitly out of scope for this context and are left for later
subsystems to build on top of these contracts.

---
Naming crosswalk
---
The implementing task named contracts using terms that do not always
match docs/03's literal schema names 1:1. Every requested name below is
aliased to the canonical, doc-grounded implementation it corresponds to.
Prefer the canonical (right-hand) names in new code; the left-hand
aliases exist so downstream subsystems can use either.

    RunScope            -> trackA.schemas.scope.RunScope
                           (Context 3: the structured, engagement-specific
                            authorization object from docs/03 §4.4 / OD-23 —
                            see RunScope's own docstring. An earlier context
                            used this name for the ScopeRequest+ScopeDecision
                            pairing; that type is now named
                            `ScopeAuthorization`, see below.)
    ScopeAuthorization  -> trackA.schemas.scope.ScopeAuthorization
                           (constructed pairing of ScopeRequest + ScopeDecision,
                            docs/03 §2.1-2.2 — see its own docstring)
    Run                 -> trackA.schemas.scope.Run
                           (UNRESOLVED AMBIGUITY: no dedicated schema exists in
                            any doc — see Run's own docstring)
    ToolRequest         -> trackA.schemas.tools.ToolExecutionRequest (docs/03 §2.5)
    ToolResult          -> trackA.schemas.tools.ToolExecutionResult (docs/03 §2.6)
    Observation         -> trackA.schemas.tools.RawToolOutput (docs/03 §2.7)
    Evidence            -> not a single schema; the MODEL_INTERPRETATION rung of
                           the trust ladder (docs/03 §1.2) is realised by TWO
                           distinct, differently-produced schemas that are kept
                           separate rather than merged: ExtractorJSON (docs/03 §2.9)
                           and WorkerOutput (docs/03 §2.12). No "Evidence" name is
                           aliased to either alone, to avoid implying they are
                           interchangeable.
    CandidateFinding    -> trackA.schemas.skills.SpecialistPoCOutput (docs/03 §2.17,
                           pipeline-tier) and
                           trackA.schemas.research.CandidateFindingRecord
                           (docs/03 §3.3, research-tier, derived from the former)
    ValidatedFinding    -> trackA.schemas.research.FindingRecord (docs/03 §3.2)
    ValidationEvent     -> trackA.schemas.human.ValidationOutcome (docs/03 §2.28/§3.5)
    Judge Evaluation Package
                        -> trackA.schemas.judge.JudgeInput (docs/03 §2.13)
    Failure records     -> trackA.schemas.audit.FailureEvent (docs/03 §2.23) and
                           trackA.schemas.audit.AuditEvent (docs/03 §2.22)
    Report/provenance structures
                        -> trackA.schemas.human.Report (docs/03 §2.21),
                           trackA.schemas.common.Provenance (docs/03 §1.1),
                           trackA.schemas.common.ManifestProvenance (OD-15, [LOCKED])
    Model records       -> trackA.schemas.models.ModelManifest (docs/08, candidate
                           model manifest only — no registry-state schema)
    Experiment / Trajectory records
                        -> trackA.schemas.research.ExperimentRecord (docs/03 §3.6),
                           trackA.schemas.research.ModelEvaluationRecord (docs/03 §3.8),
                           trackA.schemas.research.ToolSequenceRecord (docs/03 §3.7 —
                           "Trajectory" has no literally-named schema; this is the
                           closest documented concept, the ordered tool-call
                           sequence of one run)
    ScreenResult        -> trackA.schemas.common.ScreenResult (docs/02 §8 / OD-09)
    ToolManifest.expected_output
                        -> trackA.schemas.tools.ToolManifest.expected_output (OD-19)

Context 4 addendum: `BenchmarkCase`, `TrajectoryStep`, `EvaluationTrajectory`,
`EvaluationJudgePackage`, and `EvaluationJudgeVerdict` (trackA.schemas.
evaluation) are new schemas with no docs/03 §2/§3 counterpart — see that
module's docstring for why they are new rather than reusing/aliasing an
existing type, and in particular why `EvaluationJudgePackage` is a
*separate* type from the `JudgeEvaluationPackage = JudgeInput` alias above
(they serve two structurally different Judge invocations: live-pipeline
routing vs. benchmark-trajectory scoring).

Context 5 addendum: `AuthorizedAction` and `OrchestratorRejection`
(trackA.schemas.execution) are new schemas closing a genuine gap —
docs/02_COMPONENT_SPECS.md §11 names both as the Orchestrator's own
`propose_and_authorize(...) -> AuthorizedAction | OrchestratorRejection`
return type, but docs/03 never formalised either as a schema. See that
module's docstring for the full report.
"""
from __future__ import annotations

from trackA.schemas.audit import AuditEvent, FailureEvent
from trackA.schemas.common import (
    ManifestProvenance,
    PipelineStage,
    Provenance,
    ScreenResult,
    TrustClassification,
)
from trackA.schemas.evaluation import (
    BenchmarkCase,
    EvaluationJudgePackage,
    EvaluationJudgeVerdict,
    EvaluationTrajectory,
    TrajectoryStep,
)
from trackA.schemas.execution import AuthorizedAction, OrchestratorRejection
from trackA.schemas.extraction import ExtractedEntity, ExtractorInput, ExtractorJSON
from trackA.schemas.gates import CheckResult, DeduplicationResult, EvidenceGateResult
from trackA.schemas.human import HumanReviewPackage, Report, ValidationOutcome
from trackA.schemas.judge import JudgeInput, JudgeRoutingDecision
from trackA.schemas.models import ModelManifest, ModelQualityMetrics, ModelRuntimeRequirements
from trackA.schemas.orchestrator import OrchestratorAction
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
from trackA.schemas.scope import Run, RunScope, ScopeAuthorization, ScopeDecision, ScopeRequest
from trackA.schemas.skills import SkillManifest, SpecialistInput, SpecialistPoCOutput
from trackA.schemas.tools import (
    RawToolOutput,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolManifest,
)
from trackA.schemas.workers import WorkerInput, WorkerManifest, WorkerOutput

# --- Naming crosswalk aliases (see module docstring) -----------------------
ToolRequest = ToolExecutionRequest
ToolResult = ToolExecutionResult
Observation = RawToolOutput
CandidateFinding = SpecialistPoCOutput
ValidatedFinding = FindingRecord
ValidationEvent = ValidationOutcome
JudgeEvaluationPackage = JudgeInput
Trajectory = ToolSequenceRecord

__all__ = [
    # common
    "TrustClassification",
    "PipelineStage",
    "Provenance",
    "ManifestProvenance",
    "ScreenResult",
    # scope / run
    "ScopeRequest",
    "ScopeDecision",
    "ScopeAuthorization",
    "RunScope",
    "Run",
    # orchestrator
    "OrchestratorAction",
    "AuthorizedAction",
    "OrchestratorRejection",
    # tools
    "ToolManifest",
    "ToolExecutionRequest",
    "ToolExecutionResult",
    "RawToolOutput",
    "ToolRequest",
    "ToolResult",
    "Observation",
    # extraction
    "ExtractorInput",
    "ExtractedEntity",
    "ExtractorJSON",
    # workers
    "WorkerManifest",
    "WorkerInput",
    "WorkerOutput",
    # judge
    "JudgeInput",
    "JudgeRoutingDecision",
    "JudgeEvaluationPackage",
    # skills
    "SkillManifest",
    "SpecialistInput",
    "SpecialistPoCOutput",
    "CandidateFinding",
    # gates
    "CheckResult",
    "EvidenceGateResult",
    "DeduplicationResult",
    # human / reporting
    "HumanReviewPackage",
    "ValidationOutcome",
    "ValidationEvent",
    "Report",
    # audit
    "AuditEvent",
    "FailureEvent",
    # research
    "ResearchEvent",
    "FindingRecord",
    "ValidatedFinding",
    "CandidateFindingRecord",
    "ReplicationRecord",
    "ExperimentRecord",
    "ExperimentModelResult",
    "ToolSequenceRecord",
    "ToolSequenceEntry",
    "Trajectory",
    "ModelEvaluationRecord",
    "DatasetRecord",
    "ModelVersionRecord",
    # models
    "ModelManifest",
    "ModelRuntimeRequirements",
    "ModelQualityMetrics",
    # evaluation (Context 4)
    "BenchmarkCase",
    "TrajectoryStep",
    "EvaluationTrajectory",
    "EvaluationJudgePackage",
    "EvaluationJudgeVerdict",
]
