"""Local, write-once run-artifact persistence. Context-5 task brief §18.

Same convention already established by
`trackA.evaluation.storage.write_record` (a write that never overwrites),
applied here to run artifacts instead of evaluation records — not a
shared import from that module (trackA.orchestrator must not depend on
trackA.evaluation, see trackA/orchestrator/inference.py's docstring for
the same dependency-direction reasoning), and not a generic shared helper
either: this is the same small, independently-justified duplication
pattern this codebase already uses between `trackA/registries/_io.py` and
`trackA/evaluation/storage.py` (both read/write a JSON file without being
merged into one utility).
"""
from __future__ import annotations

import json
from pathlib import Path

from trackA.orchestrator.errors import RunArtifactAlreadyExistsError
from trackA.orchestrator.run_artifact import RunArtifact


def write_run_artifact(directory: Path, artifact: RunArtifact) -> Path:
    """Write `artifact` to `<directory>/<run_id>.json`. Raises
    `RunArtifactAlreadyExistsError` if that path already exists — a run's
    artifact, once written, is never silently overwritten (task brief
    §18: "do not let one live run silently alter another")."""
    target_dir = Path(directory)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{artifact.run_id}.json"
    if path.exists():
        raise RunArtifactAlreadyExistsError(
            f"run artifact already exists, refusing to overwrite: {path}"
        )
    path.write_text(
        json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def read_run_artifact(directory: Path, run_id: str) -> RunArtifact:
    """Offline/test-only read-back."""
    path = Path(directory) / f"{run_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return RunArtifact.model_validate(data)
