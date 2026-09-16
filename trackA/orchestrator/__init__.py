"""The Orchestrator / run-lifecycle layer. Context 5 (runtime + tools +
orchestration).

Ties together, without duplicating, everything Contexts 1-4 already
built: schemas/contracts (trackA.schemas), the four registries + RoleResolver
(trackA.registries), the Policy Engine + Scope Gate (trackA.policy,
Context 3), and the model runtime abstraction (trackA.models.runtime,
Context 2) — plus this context's own new Tool Executor
(trackA.execution). See trackA/orchestrator/run.py's module docstring for
the full design.
"""
from __future__ import annotations

from trackA.orchestrator.errors import OrchestratorError, RunArtifactAlreadyExistsError, RunTerminatedError
from trackA.orchestrator.outcomes import (
    JudgeActionOutcome,
    SpecialistActionOutcome,
    ToolActionOutcome,
    WorkerActionOutcome,
)
from trackA.orchestrator.run import Orchestrator, RunContext
from trackA.orchestrator.run_artifact import RunArtifact
from trackA.orchestrator.storage import read_run_artifact, write_run_artifact

__all__ = [
    "Orchestrator",
    "RunContext",
    "RunArtifact",
    "ToolActionOutcome",
    "WorkerActionOutcome",
    "SpecialistActionOutcome",
    "JudgeActionOutcome",
    "OrchestratorError",
    "RunTerminatedError",
    "RunArtifactAlreadyExistsError",
    "write_run_artifact",
    "read_run_artifact",
]
