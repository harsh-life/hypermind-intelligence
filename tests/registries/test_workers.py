from __future__ import annotations

import pytest

from trackA.registries.errors import DuplicateIdError, ManifestValidationError, UnknownIdError
from trackA.registries.workers import WorkerRegistry
from tests.registries.conftest import SEED_DATA_DIR


def test_register_and_lookup(worker_data):
    registry = WorkerRegistry()
    registry.register_from_dict(worker_data())
    assert len(registry) == 1
    assert registry.lookup("endpoint_mapper_v1").worker_role_binding == "endpoint_mapper"


def test_lookup_unregistered_raises(worker_data):
    registry = WorkerRegistry()
    with pytest.raises(UnknownIdError):
        registry.lookup("object_reference_analyst_v1")


def test_duplicate_worker_id_rejected(worker_data):
    registry = WorkerRegistry()
    registry.register_from_dict(worker_data())
    with pytest.raises(DuplicateIdError):
        registry.register_from_dict(worker_data())


def test_malformed_manifest_missing_must_not_rejected(worker_data):
    """docs/03 §2.10's invalid example: must_not missing entirely is
    rejected — it's the structural enforcement point for docs/02 §14."""
    data = worker_data()
    del data["must_not"]
    registry = WorkerRegistry()
    with pytest.raises(ManifestValidationError):
        registry.register_from_dict(data)


def test_malformed_manifest_non_positive_timeout_rejected(worker_data):
    registry = WorkerRegistry()
    with pytest.raises(ManifestValidationError):
        registry.register_from_dict(worker_data(timeout_seconds=0))


def test_serialization_round_trip(worker_data):
    registry = WorkerRegistry()
    registry.register_from_dict(worker_data())
    dumped = registry.to_dict()

    reloaded = WorkerRegistry()
    for manifest_data in dumped.values():
        reloaded.register_from_dict(manifest_data)

    assert reloaded.lookup("endpoint_mapper_v1").model_dump(mode="json") == dumped["endpoint_mapper_v1"]


def test_from_directory_loads_real_seed_manifests():
    registry = WorkerRegistry.from_directory(SEED_DATA_DIR / "workers")
    assert {w.worker_id for w in registry.all()} == {"endpoint_mapper_v1"}
