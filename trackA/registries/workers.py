"""Worker Registry. docs/02_COMPONENT_SPECS.md §2, docs/04_WORKER_SKILL_
CONTRACTS.md.

Responsibilities (docs/02 §2): same register/lookup mechanism as the Tool
Registry, scoped to WorkerManifest entries. No caller-identity access
control is documented for the Worker Registry (contrast the Skill
Registry, docs/02 §3) — any component may look up a worker manifest.

`WorkerManifest.worker_role_binding` is a pointer into the Model
Registry's role space (docs/04: "a POINTER, not a model identifier"). Its
resolution to an actual model candidate is deliberately NOT performed
here — that cross-registry concern belongs to
`trackA.registries.resolution.RoleResolver`, so the Worker Registry can be
loaded and used standalone without requiring the Model Registry to be
populated first (no load-order dependency between registries).
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from trackA.registries._store import ManifestStore
from trackA.schemas.workers import WorkerManifest


class WorkerRegistry:
    def __init__(self) -> None:
        self._store: ManifestStore[WorkerManifest] = ManifestStore(
            model_cls=WorkerManifest, id_field="worker_id", kind_label="worker"
        )

    def register(self, manifest: WorkerManifest) -> None:
        self._store.register(manifest)

    def register_from_dict(self, data: dict, *, source: str = "<dict>") -> WorkerManifest:
        return self._store.register_from_dict(data, source=source)

    def lookup(self, worker_id: str) -> WorkerManifest:
        return self._store.get(worker_id)

    def all(self) -> List[WorkerManifest]:
        return self._store.all()

    def __contains__(self, worker_id: str) -> bool:
        return worker_id in self._store

    def __len__(self) -> int:
        return len(self._store)

    def to_dict(self) -> dict:
        return self._store.to_dict()

    @classmethod
    def from_directory(cls, directory: Path) -> "WorkerRegistry":
        registry = cls()
        registry._store.load_directory(directory)
        return registry
