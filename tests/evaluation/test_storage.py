from __future__ import annotations

import pytest

from trackA.evaluation.errors import ArtifactAlreadyExistsError
from trackA.evaluation.storage import read_record, write_record
from trackA.schemas.evaluation import EvaluationJudgeVerdict
from trackA.schemas.common import PipelineStage
from tests.conftest import make_provenance


def make_verdict(run_id, **overrides) -> EvaluationJudgeVerdict:
    data = dict(
        provenance=make_provenance(run_id, PipelineStage.JUDGE),
        package_id="pkg-1",
        blinded_candidate_label="candidate_1",
        dimension_scores={"objective_outcome_match": 1.0},
        reasoning="matched",
    )
    data.update(overrides)
    return EvaluationJudgeVerdict(**data)


def test_write_and_read_record_round_trip(tmp_path, run_id):
    verdict = make_verdict(run_id)
    path = write_record(tmp_path, "verdicts", verdict.verdict_id, verdict)
    assert path.exists()

    reloaded = read_record(tmp_path, "verdicts", verdict.verdict_id, EvaluationJudgeVerdict)
    assert reloaded == verdict


def test_write_record_never_overwrites_existing_artifact(tmp_path, run_id):
    verdict = make_verdict(run_id, verdict_id="fixed-id")
    write_record(tmp_path, "verdicts", "fixed-id", verdict)

    different_verdict = make_verdict(run_id, verdict_id="fixed-id", reasoning="a different conclusion")
    with pytest.raises(ArtifactAlreadyExistsError):
        write_record(tmp_path, "verdicts", "fixed-id", different_verdict)

    # the original on disk is untouched
    reloaded = read_record(tmp_path, "verdicts", "fixed-id", EvaluationJudgeVerdict)
    assert reloaded.reasoning == "matched"


def test_write_record_creates_subdirectory(tmp_path, run_id):
    verdict = make_verdict(run_id)
    write_record(tmp_path, "nested/subdir", verdict.verdict_id, verdict)
    assert (tmp_path / "nested" / "subdir" / f"{verdict.verdict_id}.json").exists()
