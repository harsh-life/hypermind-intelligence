"""Benchmark case store + versioned dataset store. Context-4 task brief §5.

Two stores, deliberately not merged into one:

    BenchmarkCaseStore
        id -> BenchmarkCase, one entry per case_id. Built on the same
        `ManifestStore` plumbing every other manifest-backed registry in
        this codebase already uses (trackA.registries._store) — a
        BenchmarkCase is authored/versioned exactly like a Tool/Worker/
        Skill manifest (docs/13_OPEN_DECISIONS.md OD-08: git-tracked
        JSON/YAML), so reusing that store avoids a second, parallel
        implementation of "id-keyed dict with duplicate-safe
        registration and file loading."

    DatasetStore
        (dataset_id, version) -> DatasetRecord (docs/03_DATA_SCHEMAS_
        README.md §3.9, reused unmodified from trackA.schemas.research).
        NOT built on `ManifestStore`, because a dataset's canonical key is
        a *compound* (dataset_id, version) pair, not a single id field —
        `ManifestStore` only supports one id field. This is the concrete
        mechanism behind "benchmark datasets must be versioned" and
        "a benchmark result must record which dataset/version was used"
        (task brief §5): registering a second `DatasetRecord` under an
        already-used (dataset_id, version) pair is rejected outright, so
        a contaminated/corrected dataset can only ever be represented as
        a *new* version, never as a silent mutation of an existing one
        (docs/10_RESEARCH_DATA_PIPELINE.md §11's immutability
        recommendation, OD-26).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from trackA.evaluation.errors import DuplicateDatasetVersionError, UnknownCaseError, UnknownDatasetError
from trackA.registries._io import iter_manifest_files, read_manifest_file
from trackA.registries._store import ManifestStore
from trackA.registries.errors import UnknownIdError
from trackA.schemas.evaluation import BenchmarkCase
from trackA.schemas.research import DatasetRecord


class BenchmarkCaseStore:
    """id -> BenchmarkCase. See module docstring."""

    def __init__(self) -> None:
        self._store: ManifestStore[BenchmarkCase] = ManifestStore(
            model_cls=BenchmarkCase, id_field="case_id", kind_label="benchmark case"
        )

    def register(self, case: BenchmarkCase) -> None:
        self._store.register(case)

    def register_from_dict(self, data: dict, *, source: str = "<dict>") -> BenchmarkCase:
        return self._store.register_from_dict(data, source=source)

    def lookup(self, case_id: str) -> BenchmarkCase:
        try:
            return self._store.get(case_id)
        except UnknownIdError as exc:
            raise UnknownCaseError(str(exc)) from exc

    def all(self) -> List[BenchmarkCase]:
        return self._store.all()

    def __contains__(self, case_id: str) -> bool:
        return case_id in self._store

    def __len__(self) -> int:
        return len(self._store)

    def to_dict(self) -> dict:
        return self._store.to_dict()

    @classmethod
    def from_directory(cls, directory: Path) -> "BenchmarkCaseStore":
        store = cls()
        store._store.load_directory(directory)
        return store


class DatasetStore:
    """(dataset_id, version) -> DatasetRecord. See module docstring."""

    def __init__(self) -> None:
        self._entries: Dict[Tuple[str, str], DatasetRecord] = {}

    def register(self, record: DatasetRecord) -> None:
        key = (record.dataset_id, record.version)
        if key in self._entries:
            raise DuplicateDatasetVersionError(
                f"dataset {record.dataset_id!r} version {record.version!r} is "
                f"already registered — datasets are immutable once versioned; "
                f"register a new version instead of overwriting this one"
            )
        self._entries[key] = record

    def register_from_directory(self, directory: Path) -> List[DatasetRecord]:
        """Load every DatasetRecord file in `directory` (non-recursive,
        deterministic order) — mirrors the other registries'
        `from_directory` loaders, reusing the same file-IO helpers."""
        loaded: List[DatasetRecord] = []
        for path in iter_manifest_files(Path(directory)):
            data = read_manifest_file(path)
            record = DatasetRecord.model_validate(data)
            self.register(record)
            loaded.append(record)
        return loaded

    def get(self, dataset_id: str, version: str) -> DatasetRecord:
        try:
            return self._entries[(dataset_id, version)]
        except KeyError:
            raise UnknownDatasetError(
                f"no dataset registered for dataset_id={dataset_id!r} version={version!r}"
            ) from None

    def versions(self, dataset_id: str) -> List[str]:
        return sorted(v for (d, v) in self._entries if d == dataset_id)

    def latest(self, dataset_id: str) -> DatasetRecord:
        """The lexicographically-last registered version for `dataset_id`.

        [documented judgment call] "Latest" has no universal ordering for
        an open-ended `version: str` field (docs/03 §3.9 leaves the
        versioning scheme itself to this layer, per docs/10 §11's own
        note: "the specific choice matters less than the immutability
        guarantee"). Sorting lexicographically works correctly for the
        two conventions docs/03 §3.9's own example uses (ISO dates,
        "vN" with matching digit width) and is never used to make an
        authorization or safety decision — only to pick a sensible
        default dataset version for a caller that does not name one
        explicitly. A caller that needs an exact version should always
        pass it explicitly to `get()` rather than relying on this.
        """
        versions = self.versions(dataset_id)
        if not versions:
            raise UnknownDatasetError(f"no dataset registered for dataset_id={dataset_id!r}")
        return self.get(dataset_id, versions[-1])

    def resolve_cases(
        self, dataset_id: str, version: str, case_store: BenchmarkCaseStore
    ) -> List[BenchmarkCase]:
        """Every BenchmarkCase referenced by this dataset version's
        `source_record_ids`, in the order listed."""
        record = self.get(dataset_id, version)
        return [case_store.lookup(case_id) for case_id in record.source_record_ids]

    def all(self) -> List[DatasetRecord]:
        return list(self._entries.values())

    def __len__(self) -> int:
        return len(self._entries)
