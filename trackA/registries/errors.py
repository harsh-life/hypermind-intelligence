"""Shared error taxonomy for every registry in trackA.registries and the
runtime/inference-adapter layer in trackA.models.

One base class (`RegistryError`) with narrow, specifically-named
subclasses so a caller (and a test) can distinguish *why* an operation
failed without parsing message strings. Each subclass maps to one of the
"obvious failure paths" the Context-2 task brief §3 asks to be handled
explicitly:

    ManifestValidationError  -> malformed manifest (schema validation failed)
    DuplicateIdError         -> an id already registered
    ConflictError            -> two registered entries conflict at the
                                 domain level even though their ids differ
                                 (e.g. two "approved" Model candidates for
                                 one role, docs/08_MODEL_REGISTRY.md:
                                 "exactly one is marked approved and
                                 active at a time per role")
    UnknownIdError            -> lookup of an id that was never registered
    InactiveEntryError        -> entry exists but its lifecycle status
                                 blocks use (docs/12_ACCEPTANCE_CRITERIA_
                                 README.md AC-007)
    StageNotAllowedError      -> tool exists and is active, but not
                                 permitted at the requested pipeline stage
    AccessDeniedError         -> caller identity is not permitted to reach
                                 this registry at all (docs/02_COMPONENT_
                                 SPECS.md §3, Skill Registry / Judge)
    MissingReferenceError     -> a manifest points at a role/id that
                                 cannot be resolved
    NoApprovedCandidateError  -> a role exists but has no approved
                                 candidate to resolve to
    UnsupportedBackendError   -> a runtime binding names a backend with no
                                 registered InferenceAdapter
"""
from __future__ import annotations

from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError as PydanticValidationError

_T = TypeVar("_T", bound=BaseModel)


class RegistryError(Exception):
    """Base class for every registry-layer failure in Track A."""


class ManifestValidationError(RegistryError):
    """Raised when raw manifest data fails schema validation."""


class DuplicateIdError(RegistryError):
    """Raised when registering a canonical id that is already registered."""


class ConflictError(RegistryError):
    """Raised when two registered entries conflict at the domain level."""


class UnknownIdError(RegistryError):
    """Raised on lookup of a canonical id that was never registered."""


class InactiveEntryError(RegistryError):
    """Raised when an entry's lifecycle status blocks its use."""


class StageNotAllowedError(RegistryError):
    """Raised when a tool is looked up for a pipeline stage it does not allow."""


class AccessDeniedError(RegistryError):
    """Raised when a caller identity is not permitted to access a registry."""


class MissingReferenceError(RegistryError):
    """Raised when a manifest references an id/role that cannot be resolved."""


class NoApprovedCandidateError(RegistryError):
    """Raised when a role has candidates but none is approval_status='approved'."""


class UnsupportedBackendError(RegistryError):
    """Raised when no InferenceAdapter is registered for a requested backend."""


def validate_manifest(model_cls: Type[_T], data: dict, *, source: str = "<unknown>") -> _T:
    """Validate `data` against `model_cls`, wrapping pydantic's
    ValidationError in the registry layer's own ManifestValidationError so
    every registry raises one consistent exception type for malformed
    input, regardless of which underlying schema it validates against.

    The original pydantic error is preserved via `__cause__` (exception
    chaining) so nothing about the underlying failure is lost — this
    wraps, it does not swallow.
    """
    try:
        return model_cls.model_validate(data)
    except PydanticValidationError as exc:
        raise ManifestValidationError(
            f"Invalid {model_cls.__name__} manifest from {source}: {exc}"
        ) from exc
