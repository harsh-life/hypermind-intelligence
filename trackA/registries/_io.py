"""Manifest file I/O helpers, shared by every registry's `from_directory`/
`from_file` loader.

docs/13_OPEN_DECISIONS.md OD-08 (RESOLVED, [LOCKED — architecture]):
"registry manifests (Tool/Worker/Skill/Model) are version-controlled
JSON/YAML files directly in the Git repository for MVP ... No separate
database required for MVP." This module implements reading *either*
format into a plain dict; schema validation against the appropriate
Pydantic contract happens one layer up, in each registry (via
`trackA.registries.errors.validate_manifest`), not here — this module is
I/O only, deliberately with no knowledge of which manifest type it is
reading.

This is intentionally a small module of functions, not a class: sharing
file-parsing boilerplate across the four registries is not "one giant
generic registry abstraction" (which the Context-2 task brief explicitly
warns against) — it shares no registration/lookup/conflict *behavior*,
only "turn this file into a dict."
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterator

_MANIFEST_SUFFIXES = (".json", ".yaml", ".yml")


def read_manifest_file(path: Path) -> Dict[str, Any]:
    """Read one manifest file (.json / .yaml / .yml) into a plain dict.

    Raises ValueError for an unsupported extension or a file that does not
    parse to a JSON/YAML *object* (mapping) at the top level — a manifest
    is always a single object, never a list or a scalar.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")

    if path.suffix == ".json":
        data = json.loads(text)
    elif path.suffix in (".yaml", ".yml"):
        import yaml  # local import: only required when YAML is actually used

        data = yaml.safe_load(text)
    else:
        raise ValueError(
            f"Unsupported manifest file extension {path.suffix!r} for {path} "
            f"(supported: {', '.join(_MANIFEST_SUFFIXES)})"
        )

    if not isinstance(data, dict):
        raise ValueError(
            f"Manifest file {path} must contain a single JSON/YAML object "
            f"at the top level, got {type(data).__name__}"
        )
    return data


def iter_manifest_files(directory: Path) -> Iterator[Path]:
    """Yield every manifest file directly inside `directory`, sorted by
    filename for deterministic load order (docs/13 OD-08's git-tracked
    files are otherwise unordered on disk; registries must be
    deterministic per the Context-2 task brief §6).

    Non-recursive by design: each registry's data directory is flat.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError(f"Manifest directory does not exist: {directory}")
    matches = [
        p for p in directory.iterdir() if p.is_file() and p.suffix in _MANIFEST_SUFFIXES
    ]
    yield from sorted(matches, key=lambda p: p.name)
