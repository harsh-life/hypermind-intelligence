"""Skill Registry. docs/02_COMPONENT_SPECS.md §3, docs/05_SKILL_MANIFESTS_
README.md.

[LOCKED, structural — docs/02 §3]: "must never expose a Skill to the
Judge — only to the Specialist Executor ... no interface exists for Judge
to call this registry — enforced by omission, not just policy."

At this stage of the build there is no live Judge/Specialist-Executor
component yet (orchestration is out of scope for Context 2), so "enforced
by omission" cannot yet mean "the calling code physically cannot compile
a Judge->Skill-Registry path" — that structural guarantee only becomes
fully real once the Orchestrator wires callers to registries. What CAN be
built now, and is built here, is the registry's own half of that
guarantee: every read path requires an explicit `caller` identity, and
any caller other than the one documented legitimate caller
(`"specialist_executor"`) is rejected — including a caller that literally
identifies itself as `"judge"`. This makes the Judge-neutrality rule
enforceable and testable at the registry layer today, and gives the
future Orchestrator wiring nothing to get wrong: it cannot pass a caller
string that would succeed.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from trackA.registries._store import ManifestStore
from trackA.registries.errors import AccessDeniedError
from trackA.schemas.skills import SkillManifest

SPECIALIST_EXECUTOR = "specialist_executor"
_ALLOWED_CALLERS = frozenset({SPECIALIST_EXECUTOR})


class SkillRegistry:
    def __init__(self) -> None:
        self._store: ManifestStore[SkillManifest] = ManifestStore(
            model_cls=SkillManifest, id_field="skill_id", kind_label="skill"
        )

    def register(self, manifest: SkillManifest) -> None:
        # Manifest authoring/registration is not a live-pipeline runtime
        # access path (docs/13 OD-08: git-tracked files, human-authored) —
        # no caller check applies here, only to reads below.
        self._store.register(manifest)

    def register_from_dict(self, data: dict, *, source: str = "<dict>") -> SkillManifest:
        return self._store.register_from_dict(data, source=source)

    def _check_caller(self, caller: str) -> None:
        if caller not in _ALLOWED_CALLERS:
            raise AccessDeniedError(
                f"caller {caller!r} may not access the Skill Registry — only "
                f"{sorted(_ALLOWED_CALLERS)!r} may (docs/02 §3, [LOCKED])"
            )

    def lookup(self, skill_id: str, *, caller: str) -> SkillManifest:
        self._check_caller(caller)
        return self._store.get(skill_id)

    def all(self, *, caller: str) -> List[SkillManifest]:
        self._check_caller(caller)
        return self._store.all()

    def __contains__(self, skill_id: str) -> bool:
        return skill_id in self._store

    def __len__(self) -> int:
        return len(self._store)

    def to_dict(self) -> dict:
        return self._store.to_dict()

    @classmethod
    def from_directory(cls, directory: Path) -> "SkillRegistry":
        registry = cls()
        registry._store.load_directory(directory)
        return registry
