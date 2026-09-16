"""Error taxonomy for the Context-4 evaluation harness.

Mirrors `trackA.registries.errors`'s pattern (one base class, narrow
specifically-named subclasses) rather than reusing that module's classes
directly: the evaluation harness is a distinct component from the four
manifest registries, and conflating "an evaluation-lab-specific failure"
with "a registry lookup failure" would blur that boundary for no benefit.
Where a genuine registry-layer failure occurs *through* this package
(e.g. `ModelRegistry.list_candidates` returning nothing), the harness lets
the original `trackA.registries.errors` exception propagate rather than
re-wrapping it — only failures that originate in this package's own logic
get a type defined here.
"""
from __future__ import annotations


class EvaluationError(Exception):
    """Base class for every trackA.evaluation-layer failure."""


class UnknownCaseError(EvaluationError):
    """Raised on lookup of a case_id that was never registered."""


class UnknownDatasetError(EvaluationError):
    """Raised on lookup of a (dataset_id, version) pair that does not exist."""


class DuplicateDatasetVersionError(EvaluationError):
    """Raised when registering a (dataset_id, version) pair that already
    exists. Datasets are immutable once versioned (Context-4 task brief
    §5/§18; docs/10_RESEARCH_DATA_PIPELINE.md §11): a correction or
    contamination fix must register a *new* version, never overwrite an
    existing one silently."""


class NoCandidatesRegisteredError(EvaluationError):
    """Raised when a role has no Model Registry candidates at all to
    compete (distinct from `NoApprovedCandidateError`
    (trackA.registries.errors): the evaluation harness deliberately
    competes every registered candidate regardless of approval_status,
    so "zero candidates exist for this role" is the only registry-side
    condition that blocks a benchmark run — an unapproved candidate is
    exactly what benchmarking exists to evaluate)."""


class ArtifactAlreadyExistsError(EvaluationError):
    """Raised when writing an evaluation artifact whose identity (record
    id) already exists on disk — storage is append-only/immutable per
    Context-4 task brief §17/§18 and §20 ("do not silently overwrite
    historical evaluation records")."""
