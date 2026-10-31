import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.schemas.documents import Chunk
from app.schemas.retrieval import RetrievalResult
from app.services.retrieval_evaluation import SYNTHETIC_EVALUATION_CASES
from scripts.build_annotation_pool import (
    AnnotationPool,
    CandidateAnnotation,
    build_annotation_pool,
    main,
    save_annotation_pool,
)
from scripts.compare_retrievers import ENGINE_NAMES


def create_result(
    chunk_id: str,
    document_id: str,
    text: str | None = None,
) -> RetrievalResult:
    return RetrievalResult(
        chunk=Chunk(
            id=chunk_id,
            document_id=document_id,
            content=text or f"Evidence for {chunk_id}",
            position=0,
            title=f"Title for {document_id}",
            source=f"synthetic://{document_id}",
        ),
        score=1.0,
    )


def create_comparisons(
    results_by_engine: dict[str, list[RetrievalResult]],
) -> dict[str, SimpleNamespace]:
    case_id = SYNTHETIC_EVALUATION_CASES[0].id
    return {
        engine_name: SimpleNamespace(
            results_by_case_id={case_id: results_by_engine.get(engine_name, [])}
        )
        for engine_name in ENGINE_NAMES
    }


def benchmark_chunks(*results: RetrievalResult) -> list[Chunk]:
    return [result.chunk for result in results]


def create_positive_result() -> RetrievalResult:
    case = SYNTHETIC_EVALUATION_CASES[0]
    return create_result(
        next(iter(case.expected_chunk_ids)),
        next(iter(case.expected_document_ids)),
    )


def test_pool_deduplicates_chunks_and_limits_each_engine_to_top_three() -> None:
    shared = create_result("document-a:chunk:0", "document-a")
    bm25_results = [
        shared,
        create_result("document-a:chunk:1", "document-a"),
        create_result("document-b:chunk:0", "document-b"),
        create_result("document-c:chunk:0", "document-c"),
    ]
    comparisons = create_comparisons(
        {
            "BM25": bm25_results,
            "Qdrant": [shared, create_result("document-d:chunk:0", "document-d")],
        }
    )
    positive = create_positive_result()

    pool = build_annotation_pool(
        SYNTHETIC_EVALUATION_CASES[:1],
        comparisons,
        benchmark_chunks(
            *bm25_results,
            *comparisons["Qdrant"].results_by_case_id[SYNTHETIC_EVALUATION_CASES[0].id],
            positive,
        ),
    )

    candidates = pool.questions[0].candidates
    assert [candidate.chunk_id for candidate in candidates] == [
        "document-a:chunk:0",
        "document-a:chunk:1",
        "document-b:chunk:0",
        "document-d:chunk:0",
        "demo-credit-immobilier:chunk:0",
    ]
    assert all(candidate.relevance is None for candidate in candidates)
    assert tuple(item.model_dump() for item in candidates[0].retrieved_by) == (
        {"engine": "BM25", "rank": 1},
        {"engine": "Qdrant", "rank": 1},
    )
    assert candidates[-1].included_from_existing_positive is True
    assert candidates[-1].retrieved_by == ()


def test_pool_json_marks_unjudged_candidates_as_null() -> None:
    result = create_result("document-a:chunk:0", "document-a", "Candidate text")
    pool = build_annotation_pool(
        SYNTHETIC_EVALUATION_CASES[:1],
        create_comparisons({"BM25": [result]}),
        benchmark_chunks(result, create_positive_result()),
    )

    payload = json.loads(pool.model_dump_json())

    assert payload["unjudged_policy"] == "null_is_unjudged"
    assert payload["judgment_scale"] == {
        "0": "not_relevant",
        "1": "relevant",
        "2": "highly_relevant",
    }
    assert payload["questions"][0]["question_id"] == SYNTHETIC_EVALUATION_CASES[0].id
    assert payload["questions"][0]["candidates"][0] == {
        "chunk_id": "document-a:chunk:0",
        "document_id": "document-a",
        "text": "Candidate text",
        "relevance": None,
        "retrieved_by": [{"engine": "BM25", "rank": 1}],
        "included_from_existing_positive": False,
    }


@pytest.mark.parametrize("judgment", [None, 0, 1, 2])
def test_candidate_accepts_supported_judgments(judgment: int | None) -> None:
    candidate = CandidateAnnotation(
        chunk_id="document-a:chunk:0",
        document_id="document-a",
        text="Candidate text",
        relevance=judgment,
    )

    assert candidate.relevance == judgment


def test_candidate_rejects_unsupported_judgment() -> None:
    with pytest.raises(ValidationError):
        CandidateAnnotation(
            chunk_id="document-a:chunk:0",
            document_id="document-a",
            text="Candidate text",
            relevance=3,
        )


def test_pool_rejects_inconsistent_metadata_for_a_stable_chunk_id() -> None:
    comparisons = create_comparisons(
        {
            "BM25": [create_result("shared:chunk:0", "document-a")],
            "Qdrant": [create_result("shared:chunk:0", "document-b")],
        }
    )

    with pytest.raises(ValueError, match="inconsistent metadata"):
        build_annotation_pool(
            SYNTHETIC_EVALUATION_CASES[:1],
            comparisons,
            benchmark_chunks(
                comparisons["BM25"].results_by_case_id[
                    SYNTHETIC_EVALUATION_CASES[0].id
                ][0]
            ),
        )


def test_pool_supports_questions_without_candidates() -> None:
    case = SYNTHETIC_EVALUATION_CASES[0]
    positive = create_result(
        next(iter(case.expected_chunk_ids)),
        next(iter(case.expected_document_ids)),
    )
    pool = build_annotation_pool(
        [case],
        create_comparisons({}),
        benchmark_chunks(positive),
    )

    assert isinstance(pool, AnnotationPool)
    assert pool.questions[0].candidates[0].retrieved_by == ()
    assert pool.questions[0].candidates[0].included_from_existing_positive is True
    assert pool.questions[0].candidates[0].relevance is None


def test_save_pool_refuses_to_overwrite_existing_annotations(tmp_path: Path) -> None:
    pool = build_annotation_pool(
        [],
        create_comparisons({}),
        [],
    )
    output_path = tmp_path / "annotation-pool.json"

    save_annotation_pool(pool, output_path)

    with pytest.raises(FileExistsError):
        save_annotation_pool(pool, output_path)


def test_existing_output_stops_before_pipeline_initialization(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / "existing.json"
    output_path.write_text("existing", encoding="utf-8")

    with patch("scripts.build_annotation_pool.create_local_comparison") as factory:
        exit_code = main(["--output", str(output_path)])

    assert exit_code == 1
    factory.assert_not_called()
    assert f"Annotation pool already exists: {output_path}" in capsys.readouterr().err


def test_existing_version_one_pool_remains_readable() -> None:
    path = Path(__file__).resolve().parents[1] / "data" / "rag_annotation_pool.json"

    pool = AnnotationPool.model_validate_json(path.read_text(encoding="utf-8"))

    assert pool.schema_version == 1
    assert all(
        candidate.retrieved_by == ()
        and candidate.included_from_existing_positive is False
        for question in pool.questions
        for candidate in question.candidates
    )
