"""Private, unexported plumbing shared by the four registries.

The Context-2 task brief §6 warns: "Do not create one giant generic
'registry' abstraction if that would blur important domain boundaries."
`ManifestStore` is deliberately NOT that — it is not exported from
`trackA.registries`, carries no domain-specific validation, conflict, or
access-control logic, and provides only the mechanical parts every
registry needs identically: an id-keyed dict, duplicate rejection on
registration, and lookup-with-a-clear-error. Every piece of behavior a
test would actually assert *about a specific registry's domain rules*
(Skill Registry's caller check, Model Registry's one-approved-per-role
conflict rule, Tool Registry's validation_status/stage gating) lives in
that registry's own module, not here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Generic, Iterable, List, TypeVar

from pydantic import BaseModel

from trackA.registries._io import iter_manifest_files, read_manifest_file
from trackA.registries.errors import DuplicateIdError, UnknownIdError, validate_manifest

_T = TypeVar("_T", bound=BaseModel)


class ManifestStore(Generic[_T]):
    """id -> manifest dict with duplicate-safe registration and lookup."""

    def __init__(self, *, model_cls: type, id_field: str, kind_label: str) -> None:
        self._model_cls = model_cls
        self._id_field = id_field
        self._kind_label = kind_label
        self._entries: Dict[str, _T] = {}

    def _id_of(self, manifest: _T) -> str:
        return getattr(manifest, self._id_field)

    def register(self, manifest: _T) -> None:
        manifest_id = self._id_of(manifest)
        if manifest_id in self._entries:
            raise DuplicateIdError(
                f"{self._kind_label} '{manifest_id}' is already registered "
                f"(duplicate {self._id_field})"
            )
        self._entries[manifest_id] = manifest

    def get(self, manifest_id: str) -> _T:
        try:
            return self._entries[manifest_id]
        except KeyError:
            raise UnknownIdError(
                f"unregistered {self._kind_label} {self._id_field}: {manifest_id!r}"
            ) from None

    def __contains__(self, manifest_id: str) -> bool:
        return manifest_id in self._entries

    def all(self) -> List[_T]:
        return list(self._entries.values())

    def __len__(self) -> int:
        return len(self._entries)

    def register_from_dict(self, data: dict, *, source: str = "<dict>") -> _T:
        manifest = validate_manifest(self._model_cls, data, source=source)
        self.register(manifest)
        return manifest

    def load_directory(self, directory: Path) -> List[_T]:
        loaded: List[_T] = []
        for path in iter_manifest_files(Path(directory)):
            data = read_manifest_file(path)
            loaded.append(self.register_from_dict(data, source=str(path)))
        return loaded

    def to_dict(self) -> Dict[str, Any]:
        """Serialize every registered manifest to a plain JSON-safe dict,
        keyed by canonical id, for round-trip (dump -> reload) tests."""
        return {
            manifest_id: manifest.model_dump(mode="json")
            for manifest_id, manifest in self._entries.items()
        }
