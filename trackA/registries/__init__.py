"""Track A registries: Tool / Worker / Skill / Model.

Context 2 scope (see the Context-2 task brief and docs/02_COMPONENT_SPECS.md
§1-4): the deterministic lookup/validation/registration mechanism for each
of the four manifest-backed registries named in docs/01_ARCHITECTURE.md §18,
plus the role -> model-candidate resolution abstraction that ties Worker/
Skill manifests to Model Registry entries (docs/04_WORKER_SKILL_CONTRACTS.md
"pointer, not a model identifier" design).

Deliberately four separate registry classes, not one generic
`Registry[T]` — each has real domain-specific behavior documented in its
own module (Skill Registry's caller-identity access control; Model
Registry's one-approved-candidate-per-role conflict rule; Tool Registry's
validation_status/stage gating). A private, unexported `_store.ManifestStore`
base class provides only the truly shared plumbing (dict storage, duplicate
detection, basic lookup) — see that module's docstring.

Out of scope for this context (see the Context-2 task brief §4): model
benchmarking/competition, Docker tool execution, Scope Gate, orchestration,
live tool execution, human validation, Track B, Darwin.

The "Model Serving Layer" (docs/02_COMPONENT_SPECS.md component 5 — the
actual inference-adapter/runtime abstraction) lives in the sibling
`trackA.models` package, not here, matching the repository layout
recommended in docs/15_ENGINEERING_HANDOFF.md §4 ("registries/" for
components 1-4, "models/" for component 5).
"""
from __future__ import annotations

from trackA.registries.errors import (
    AccessDeniedError,
    ConflictError,
    DuplicateIdError,
    InactiveEntryError,
    ManifestValidationError,
    MissingReferenceError,
    NoApprovedCandidateError,
    RegistryError,
    StageNotAllowedError,
    UnknownIdError,
    UnsupportedBackendError,
)
from trackA.registries.models import ModelRegistry
from trackA.registries.resolution import RoleResolver
from trackA.registries.skills import SkillRegistry
from trackA.registries.tools import ToolRegistry
from trackA.registries.workers import WorkerRegistry

__all__ = [
    "RegistryError",
    "ManifestValidationError",
    "DuplicateIdError",
    "ConflictError",
    "UnknownIdError",
    "InactiveEntryError",
    "StageNotAllowedError",
    "AccessDeniedError",
    "MissingReferenceError",
    "NoApprovedCandidateError",
    "UnsupportedBackendError",
    "ToolRegistry",
    "WorkerRegistry",
    "SkillRegistry",
    "ModelRegistry",
    "RoleResolver",
]
