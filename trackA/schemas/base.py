"""Shared base model for every Track A schema/contract.

Rules applied uniformly, per docs/03_DATA_SCHEMAS_README.md and
docs/04_WORKER_SKILL_CONTRACTS.md ("Implement these exactly. Do not
improvise field names."):

- extra="forbid": every schema in this package is a closed contract.
  An unrecognised field must fail validation, not be silently accepted.
- protected_namespaces=(): several documented field names begin with
  "model_" (model_id, model_version, model_identity, ...), which would
  otherwise collide with pydantic's own reserved "model_" namespace.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class HypermindModel(BaseModel):
    """Base class for all Track A data contracts."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        protected_namespaces=(),
    )
