"""Role -> model-candidate resolution. Context-2 task brief §3.F.

The abstraction this module builds (Context-2 task brief §2):

    ROLE / CONTRACT
        |
        v
    MODEL CANDIDATE
        |
        v
    MODEL REGISTRY
        |
        v
    INFERENCE ADAPTER   (trackA.models.runtime)
        |
        v
    ACTUAL RUNTIME

`WorkerManifest.worker_role_binding` and `SkillManifest.
specialist_role_binding` are documented as pointers, not model
identifiers (docs/04_WORKER_SKILL_CONTRACTS.md: "This field is a POINTER,
not a model identifier"). `RoleResolver` is the one place that pointer is
actually followed to a concrete `ModelManifest`, so:

    - Worker Registry, Skill Registry, and Model Registry stay decoupled
      and independently loadable (no load-order dependency between them —
      see the module docstrings on `trackA.registries.workers` and
      `trackA.registries.skills`).
    - A worker/skill contract never needs editing when the Model
      Registry's selected implementation for its role changes (docs/01
      §4 [LOCKED]: "the worker contract must survive a model swap
      unmodified").
"""
from __future__ import annotations

from trackA.registries.models import ModelRegistry
from trackA.schemas.models import ModelManifest
from trackA.schemas.skills import SkillManifest
from trackA.schemas.workers import WorkerManifest


class RoleResolver:
    """Resolves a role name (or a manifest's role-binding pointer) to the
    Model Registry's approved candidate for that role.

    Deliberately a thin wrapper around `ModelRegistry`, not a new store:
    this component owns no manifest data of its own, only the resolution
    behavior — consistent with the Context-2 task brief §6's instruction
    to keep registry responsibilities separate rather than blurring them
    into one abstraction.
    """

    def __init__(self, model_registry: ModelRegistry) -> None:
        self._model_registry = model_registry

    def resolve(self, role: str) -> ModelManifest:
        """The single approved candidate for `role`.

        Raises NoApprovedCandidateError (via ModelRegistry.get_approved)
        whether `role` has no candidates registered at all, or has
        candidates but none approved — both are "cannot resolve a live
        implementation for this role right now," which is the caller-
        relevant distinction; `list_candidates` below remains available
        for callers that specifically need to tell those two cases apart
        (e.g. benchmarking tooling).
        """
        return self._model_registry.get_approved(role)

    def list_candidates(self, role: str):
        """Every registered candidate for `role`, any approval_status —
        the benchmarking-facing view. Never treat this list's contents as
        available for live use; only `resolve()`'s single approved result
        is (docs/08_MODEL_REGISTRY.md [LOCKED]: "exactly one is marked
        approved and active at a time per role")."""
        return self._model_registry.list_candidates(role)

    def resolve_for_worker(self, worker: WorkerManifest) -> ModelManifest:
        return self.resolve(worker.worker_role_binding)

    def resolve_for_skill(self, skill: SkillManifest) -> ModelManifest:
        return self.resolve(skill.specialist_role_binding)
