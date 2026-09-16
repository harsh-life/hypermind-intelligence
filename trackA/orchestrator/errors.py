"""Error taxonomy for the Orchestrator/run-lifecycle layer. Mirrors the
established per-package pattern (trackA.registries.errors,
trackA.evaluation.errors): one base class, narrow named subclasses.
"""
from __future__ import annotations


class OrchestratorError(Exception):
    """Base class for every trackA.orchestrator-layer failure."""


class RunTerminatedError(OrchestratorError):
    """Raised when any action is attempted against a `RunContext` after
    `finalize()` has already been called on it (task brief §18: "Runs are
    independent" / "terminating cleanly" — a terminated run must never
    silently continue producing new records under its own run_id)."""


class RunArtifactAlreadyExistsError(OrchestratorError):
    """Raised when finalizing a run whose artifact path already exists on
    disk — run artifacts are write-once, mirroring
    `trackA.evaluation.storage.write_record`'s identical convention (task
    brief §18: "do not let one live run silently alter another")."""
