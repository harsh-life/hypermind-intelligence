"""Re-exposes the registries test suite's model-manifest factory for the
runtime/inference-adapter tests, which need a valid ModelManifest dict to
prove RuntimeRegistry's optional Model-Registry cross-check (see
test_bind_validates_candidate_exists_in_model_registry_when_provided).
Avoids duplicating the factory or reaching across test packages ad hoc.
"""
from __future__ import annotations

import pytest

from tests.registries.conftest import model_manifest_data


@pytest.fixture
def model_data():
    return model_manifest_data
