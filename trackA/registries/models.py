"""Model Registry. docs/02_COMPONENT_SPECS.md §4, docs/08_MODEL_REGISTRY.md.

Responsibilities (docs/02 §4):
    (1) store ModelManifest entries per role
    (2) track primary/approved status per role
    (3) expose evaluation metadata so a model is never selected on size
        alone [LOCKED] — already enforced at the schema layer by
        `ModelQualityMetrics`' null-until-measured rule (trackA/schemas/
        models.py); nothing further to add here
    (4) support multiple candidate models per role for benchmarking

docs/08 [LOCKED]: "A role may have multiple candidate models under
evaluation simultaneously; exactly one is marked `approved` and active at
a time per role." That is a domain-level conflict rule this registry
enforces at registration time — two different `candidate_id`s can be
registered for the same `intended_worker_role`, but at most one of them
may have `approval_status == "approved"`.

Explicitly NOT implemented here (Context-2 task brief §4: "model
benchmarking", "model competition/evaluation"): the benchmarking process
itself, and the "Currently Selected Implementations" table's actual
per-role default choices — this registry only stores and resolves
whatever `ModelManifest.approval_status`/`intended_worker_role` values
its caller registers.

Note on "the same candidate usable for multiple roles" (Context-2 task
brief §5): `ModelManifest.intended_worker_role` (docs/08, unmodified,
Context-1-locked) is a single string field — one manifest entry names one
role. A single underlying model identity that serves multiple roles is
represented as multiple `ModelManifest` entries (distinct `candidate_id`,
shared `model_identity`/`version`), one per role — this requires no
schema change and is exercised in the seed data (see
`trackA/registries/data/models/`).
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from trackA.registries._io import iter_manifest_files, read_manifest_file
from trackA.registries._store import ManifestStore
from trackA.registries.errors import ConflictError, NoApprovedCandidateError, validate_manifest
from trackA.schemas.models import ModelManifest

APPROVED = "approved"


class ModelRegistry:
    def __init__(self) -> None:
        self._store: ManifestStore[ModelManifest] = ManifestStore(
            model_cls=ModelManifest, id_field="candidate_id", kind_label="model candidate"
        )

    def register(self, manifest: ModelManifest) -> None:
        # DuplicateIdError (candidate_id collision) is raised by the store
        # itself before this check runs. This check is the domain-specific
        # conflict rule layered on top: at most one approved candidate per
        # role, regardless of candidate_id.
        if manifest.approval_status == APPROVED:
            existing_approved = [
                m
                for m in self._store.all()
                if m.intended_worker_role == manifest.intended_worker_role
                and m.approval_status == APPROVED
            ]
            if existing_approved:
                raise ConflictError(
                    f"role {manifest.intended_worker_role!r} already has an "
                    f"approved candidate ({existing_approved[0].candidate_id!r}); "
                    f"cannot also approve {manifest.candidate_id!r} "
                    f"(docs/08_MODEL_REGISTRY.md [LOCKED]: exactly one approved "
                    f"candidate per role)"
                )
        self._store.register(manifest)

    def register_from_dict(self, data: dict, *, source: str = "<dict>") -> ModelManifest:
        manifest = validate_manifest(ModelManifest, data, source=source)
        self.register(manifest)
        return manifest

    def lookup(self, candidate_id: str) -> ModelManifest:
        return self._store.get(candidate_id)

    def list_candidates(self, role: str) -> List[ModelManifest]:
        """Every registered candidate for `role`, any approval_status,
        sorted by candidate_id for deterministic ordering. This is the
        benchmarking-facing view (docs/02 §4's `list_candidates`) — never
        use this list directly to select a live implementation; use
        `get_approved` for that."""
        return sorted(
            (m for m in self._store.all() if m.intended_worker_role == role),
            key=lambda m: m.candidate_id,
        )

    def get_approved(self, role: str) -> ModelManifest:
        for manifest in self.list_candidates(role):
            if manifest.approval_status == APPROVED:
                return manifest
        raise NoApprovedCandidateError(
            f"no approved model candidate is registered for role {role!r}"
        )

    def all(self) -> List[ModelManifest]:
        return self._store.all()

    def __contains__(self, candidate_id: str) -> bool:
        return candidate_id in self._store

    def __len__(self) -> int:
        return len(self._store)

    def to_dict(self) -> dict:
        return self._store.to_dict()

    @classmethod
    def from_directory(cls, directory: Path) -> "ModelRegistry":
        # Deliberately does not delegate to ManifestStore.load_directory:
        # that helper calls the *store's* plain register (duplicate-id
        # check only), which would silently skip this registry's
        # one-approved-candidate-per-role conflict rule. Going through
        # `self.register` for every loaded manifest keeps both checks
        # (duplicate id AND role conflict) enforced identically for
        # file-loaded and programmatically-registered candidates alike.
        registry = cls()
        for path in iter_manifest_files(Path(directory)):
            data = read_manifest_file(path)
            manifest = validate_manifest(ModelManifest, data, source=str(path))
            registry.register(manifest)
        return registry
