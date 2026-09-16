from __future__ import annotations

import pytest

from trackA.evaluation.cases import BenchmarkCaseStore, DatasetStore
from trackA.evaluation.errors import DuplicateDatasetVersionError, UnknownCaseError, UnknownDatasetError
from trackA.registries.errors import DuplicateIdError
from trackA.schemas.research import DatasetRecord
from tests.conftest import make_manifest_provenance, make_provenance
from trackA.schemas.common import PipelineStage


def make_case_data(**overrides):
    data = dict(
        case_id="c1",
        role="specialist",
        task_description="do the thing",
        starting_inputs={"x": 1},
        provenance=make_manifest_provenance().model_dump(mode="json"),
    )
    data.update(overrides)
    return data


# --- BenchmarkCaseStore ------------------------------------------------------


def test_register_and_lookup_case():
    store = BenchmarkCaseStore()
    store.register_from_dict(make_case_data())
    assert store.lookup("c1").task_description == "do the thing"
    assert "c1" in store


def test_lookup_unregistered_case_raises():
    store = BenchmarkCaseStore()
    with pytest.raises(UnknownCaseError):
        store.lookup("nonexistent")


def test_duplicate_case_id_rejected():
    store = BenchmarkCaseStore()
    store.register_from_dict(make_case_data())
    with pytest.raises(DuplicateIdError):
        store.register_from_dict(make_case_data())


def test_from_directory_loads_seed_cases():
    from tests.evaluation.conftest import SEED_DATA_DIR

    store = BenchmarkCaseStore.from_directory(SEED_DATA_DIR / "cases")
    assert len(store) == 3
    assert "idor-lab-001" in store
    assert "injection-probe-001" in store
    assert "endpoint-mapper-lab-001" in store


# --- DatasetStore: versioning -------------------------------------------------


def make_dataset_record(version="v1", source_record_ids=None, purity_notes="synthetic/lab-derived", run_id="ds-run"):
    return DatasetRecord(
        provenance=make_provenance(run_id, PipelineStage.JUDGE),
        dataset_id="ds-1",
        version=version,
        source_record_ids=source_record_ids or ["c1"],
        purity_notes=purity_notes,
    )


def test_dataset_store_register_and_get():
    store = DatasetStore()
    record = make_dataset_record()
    store.register(record)
    assert store.get("ds-1", "v1") is record


def test_dataset_store_unknown_dataset_raises():
    store = DatasetStore()
    with pytest.raises(UnknownDatasetError):
        store.get("ds-1", "v1")


def test_dataset_store_duplicate_version_rejected():
    """Datasets are immutable once versioned (task brief §5/§18)."""
    store = DatasetStore()
    store.register(make_dataset_record())
    with pytest.raises(DuplicateDatasetVersionError):
        store.register(make_dataset_record(purity_notes="a different, contaminated-fix note"))


def test_dataset_store_new_version_coexists_with_old_and_both_remain_readable():
    """Contaminated/corrected cases are handled through a NEW version,
    never by mutating history (task brief §5: 'contaminated, invalid, or
    corrected benchmark cases must be handled through dataset versioning
    rather than silently mutating historical experiments')."""
    store = DatasetStore()
    v1 = make_dataset_record(version="v1", source_record_ids=["c1", "c2"])
    v2 = make_dataset_record(
        version="v2",
        source_record_ids=["c1"],  # c2 was found contaminated and dropped
        purity_notes="c2 removed: found to be a duplicate of a real disclosed finding, not synthetic",
    )
    store.register(v1)
    store.register(v2)

    assert store.versions("ds-1") == ["v1", "v2"]
    # v1 is completely unchanged and still independently retrievable
    still_there = store.get("ds-1", "v1")
    assert still_there.source_record_ids == ["c1", "c2"]
    assert still_there is v1
    assert store.get("ds-1", "v2").source_record_ids == ["c1"]


def test_dataset_store_latest_picks_last_registered_version():
    store = DatasetStore()
    store.register(make_dataset_record(version="v1"))
    store.register(make_dataset_record(version="v2"))
    assert store.latest("ds-1").version == "v2"


def test_dataset_store_latest_unknown_dataset_raises():
    store = DatasetStore()
    with pytest.raises(UnknownDatasetError):
        store.latest("nonexistent")


def test_resolve_cases_from_seed_data():
    from tests.evaluation.conftest import SEED_DATA_DIR

    case_store = BenchmarkCaseStore.from_directory(SEED_DATA_DIR / "cases")
    dataset_store = DatasetStore()
    dataset_store.register_from_directory(SEED_DATA_DIR / "datasets")

    cases = dataset_store.resolve_cases("ds-track-a-bootstrap", "v1", case_store)
    assert [c.case_id for c in cases] == ["idor-lab-001", "injection-probe-001", "endpoint-mapper-lab-001"]


def test_seed_dataset_purity_notes_label_synthetic_lab_derived():
    """docs/13_OPEN_DECISIONS.md OD-27: cases must be explicitly labeled
    synthetic/lab-derived in DatasetRecord.purity_notes."""
    from tests.evaluation.conftest import SEED_DATA_DIR

    dataset_store = DatasetStore()
    dataset_store.register_from_directory(SEED_DATA_DIR / "datasets")
    record = dataset_store.get("ds-track-a-bootstrap", "v1")
    assert "synthetic" in record.purity_notes.lower()
    assert "never field-validated" in record.purity_notes.lower() or "not" in record.purity_notes.lower()
