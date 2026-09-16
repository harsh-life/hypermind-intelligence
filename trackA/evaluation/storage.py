"""Local, append-only JSON artifact persistence. Context-4 task brief
§17/§18/§20.

Reuses the plain-JSON-file convention already established for registry
manifests (docs/13_OPEN_DECISIONS.md OD-08/OD-11 [LOCKED — architecture]:
"structured machine-readable data is canonical ... local to the execution
system for MVP"), rather than inventing a new persistence architecture.
Two functions only: a write that never overwrites, and a read used only
offline/by tests. Nothing in `trackA.evaluation.harness`/`judge`/
`judge_package`/`results`/`cases` calls `read_record` — this mirrors, at
this module's much smaller scope, the Research Store's own write-only-
from-the-live-path discipline (docs/10_RESEARCH_DATA_PIPELINE.md §1),
without building the actual Research Store component (out of scope,
Context-4 task brief §21).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Type, TypeVar

from trackA.evaluation.errors import ArtifactAlreadyExistsError
from trackA.schemas.base import HypermindModel

_T = TypeVar("_T", bound=HypermindModel)


def write_record(directory: Path, subdir: str, record_id: str, record: HypermindModel) -> Path:
    """Write `record` to `<directory>/<subdir>/<record_id>.json`.

    Raises `ArtifactAlreadyExistsError` if that path already exists — an
    evaluation artifact, once written, is never silently overwritten
    (task brief §17: "do not silently overwrite historical evaluation
    records"; §18: "do not silently replace old results"). A rerun must
    use a new `record_id` (e.g. a new `trajectory_id`/`experiment_id`),
    which every schema in `trackA.schemas.evaluation` already generates
    fresh by default.
    """
    target_dir = Path(directory) / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{record_id}.json"
    if path.exists():
        raise ArtifactAlreadyExistsError(f"artifact already exists, refusing to overwrite: {path}")
    path.write_text(
        json.dumps(record.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8"
    )
    return path


def read_record(directory: Path, subdir: str, record_id: str, model_cls: Type[_T]) -> _T:
    """Offline/test-only read-back — never called from any core
    evaluation module (see module docstring)."""
    path = Path(directory) / subdir / f"{record_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return model_cls.model_validate(data)
