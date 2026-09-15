"""Tool Registry. docs/02_COMPONENT_SPECS.md §1, docs/06_TOOL_REGISTRY_README.md.

Responsibilities (docs/02 §1):
    (1) store versioned ToolManifest entries
    (2) reject lookups for unregistered tool_ids
    (3) validate a requested invocation against its manifest (allowed
        stage, active status) before authorizing
    (4) expose only currently-approved tools — no dynamic/ad-hoc tool
        addition at runtime [LOCKED]

Point (3) here is deliberately narrow: `validate_invocation` checks only
what the Tool Registry itself is documented to own — registration,
`validation_status`, and pipeline-stage permission (docs/06's per-tool
`allowed_stages`). Full request-schema validation against
`ToolManifest.input_schema`, resource accounting, and scope/policy
authorization belong to the Orchestrator and Docker Tool Execution Engine
(docs/02 §11-12) — explicitly out of scope for this context (Context-2
task brief §4: "authorization/policy enforcement", "orchestration",
"Docker tool execution").

Point (4) — "no dynamic/ad-hoc tool addition at runtime" — is honoured by
construction: nothing in this module exposes `register`/`load_directory`
to anything resembling a live pipeline caller; they are load-time-only
operations by convention, same as every other registry here.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from trackA.registries._store import ManifestStore
from trackA.registries.errors import InactiveEntryError, StageNotAllowedError
from trackA.schemas.tools import ToolManifest

ACTIVE = "active"


class ToolRegistry:
    def __init__(self) -> None:
        self._store: ManifestStore[ToolManifest] = ManifestStore(
            model_cls=ToolManifest, id_field="tool_id", kind_label="tool"
        )

    def register(self, manifest: ToolManifest) -> None:
        self._store.register(manifest)

    def register_from_dict(self, data: dict, *, source: str = "<dict>") -> ToolManifest:
        return self._store.register_from_dict(data, source=source)

    def lookup(self, tool_id: str) -> ToolManifest:
        """Plain lookup — raises UnknownIdError for any tool_id never
        registered, including encoding/whitespace/homoglyph variants of a
        real tool_id: dict-key lookup is exact-string equality, so a
        homoglyph or trailing-whitespace variant is structurally a
        different key and can never resolve to the real entry (this is
        the registry-level half of docs/11_TEST_PLAN_README.md ADV-005;
        the other half — where such a variant is even allowed to reach
        this call — is an Orchestrator/input-guard concern out of scope
        here)."""
        return self._store.get(tool_id)

    def is_active(self, tool_id: str) -> bool:
        return self.lookup(tool_id).validation_status == ACTIVE

    def validate_invocation(self, tool_id: str, *, stage: str) -> bool:
        """docs/02 §1's `validate_invocation(tool_id, request) -> bool`
        interface, narrowed to what the Tool Registry itself owns (see
        module docstring). Raises rather than returning False, so a
        caller always learns *why* — matching AC-004/AC-007's structural-
        audit framing ("a validation_status other than active blocks
        execution the same as full non-registration")."""
        manifest = self.lookup(tool_id)  # raises UnknownIdError if unregistered
        if manifest.validation_status != ACTIVE:
            raise InactiveEntryError(
                f"tool '{tool_id}' has validation_status={manifest.validation_status!r}, "
                f"not {ACTIVE!r} — execution blocked (docs/12 AC-007)"
            )
        if stage not in manifest.allowed_stages:
            raise StageNotAllowedError(
                f"tool '{tool_id}' is not permitted at stage {stage!r} "
                f"(allowed_stages={manifest.allowed_stages!r})"
            )
        return True

    def all(self) -> List[ToolManifest]:
        return self._store.all()

    def __contains__(self, tool_id: str) -> bool:
        return tool_id in self._store

    def __len__(self) -> int:
        return len(self._store)

    def to_dict(self) -> dict:
        return self._store.to_dict()

    @classmethod
    def from_directory(cls, directory: Path) -> "ToolRegistry":
        registry = cls()
        registry._store.load_directory(directory)
        return registry
