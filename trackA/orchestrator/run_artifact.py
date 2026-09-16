"""The structured artifact one run produces. Context-5 task brief §3/§18.

Not a docs/03 schema (no document defines a "run artifact" record — see
`trackA.schemas.scope.Run`'s own docstring for the same "no literal
schema exists" situation, which this composes on top of). A plain,
inspectable summary + full outcome list, written once at
`RunContext.finalize()` via `trackA.orchestrator.storage`.
"""
from __future__ import annotations

from typing import List

from pydantic import model_validator

from trackA.schemas.audit import AuditEvent, FailureEvent
from trackA.schemas.base import HypermindModel
from trackA.orchestrator.outcomes import (
    JudgeActionOutcome,
    SpecialistActionOutcome,
    ToolActionOutcome,
    WorkerActionOutcome,
)


class RunArtifact(HypermindModel):
    run_id: str
    started_at: str
    finalized_at: str
    scope_established: bool
    actions_proposed: int
    tool_actions: List[ToolActionOutcome] = []
    worker_actions: List[WorkerActionOutcome] = []
    specialist_actions: List[SpecialistActionOutcome] = []
    judge_actions: List[JudgeActionOutcome] = []
    audit_events: List[AuditEvent] = []
    failure_events: List[FailureEvent] = []

    @model_validator(mode="after")
    def _validate(self) -> "RunArtifact":
        if self.actions_proposed < 0:
            raise ValueError("RunArtifact.actions_proposed must be >= 0")
        return self
