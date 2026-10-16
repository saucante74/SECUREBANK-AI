from collections.abc import Collection

import pytest
from pydantic import ValidationError

from app.schemas.documents import Chunk
from app.schemas.evaluation import EvaluationCase
from app.schemas.retrieval import RetrievalResult
from app.services.chunking import CharacterChunker
from app.services.retrieval_evaluation import (
    SYNTHETIC_EVALUATION_CASES,
    evaluate_cases,
    evidence_hit_at_k,
    source_hit_at_k,
)
from scripts.demo_vector_search import create_chunks, create_documents


def create_result(
    document_id: str,
    chunk_id: str,
    score: float = 1.0,
) -> RetrievalResult:
    return RetrievalResult(
        chunk=Chunk(
            id=chunk_id,
            document_id=document_id,
            content=f"Synthetic evidence for {chunk_id}",
            position=0,
            title=f"Synthetic title for {document_id}",
            source=f"synthetic://{document_id}",
        ),
        score=score,
    )


def create_case(
    identifier: str,
    expected_document_ids: Collection[str] = ("expected-document",),
    expected_chunk_ids: Collection[str] = ("expected-chunk",),
) -> EvaluationCase:
    return EvaluationCase(
        id=identifier,
        question=f"Synthetic question for {identifier}",
        expected_document_ids=expected_document_ids,
        expected_chunk_ids=expected_chunk_ids,
    )


def test_source_hit_at_one_and_three() -> None:
    results = [
        create_result("other-document", "other-chunk"),
        create_result("expected-document", "expected-chunk"),
    ]

    assert source_hit_at_k(results, {"expected-document"}, 1) == 0
    assert source_hit_at_k(results, {"expected-document"}, 3) == 1


def test_evidence_hit_at_one_and_three() -> None:
    results = [
        create_result("expected-document", "other-chunk"),
        create_result("expected-document", "expected-chunk"),
    ]

    assert evidence_hit_at_k(results, {"expected-chunk"}, 1) == 0
    assert evidence_hit_at_k(results, {"expected-chunk"}, 3) == 1


def test_metrics_return_zero_without_relevant_or_any_results() -> None:
    unrelated = [create_result("other-document", "other-chunk")]

    assert source_hit_at_k(unrelated, {"expected-document"}, 3) == 0
    assert evidence_hit_at_k(unrelated, {"expected-chunk"}, 3) == 0
    assert source_hit_at_k([], {"expected-document"}, 3) == 0
    assert evidence_hit_at_k([], {"expected-chunk"}, 3) == 0


def test_metrics_accept_multiple_relevant_identifiers() -> None:
    results = [create_result("second-document", "second-chunk")]

    assert (
        source_hit_at_k(
            results,
            {"first-document", "second-document"},
            1,
        )
        == 1
    )
    assert (
        evidence_hit_at_k(
            results,
            {"first-chunk", "second-chunk"},
            1,
        )
        == 1
    )


def test_duplicate_results_do_not_change_hits() -> None:
    relevant = create_result("expected-document", "expected-chunk")
    results = [relevant, relevant, create_result("other-document", "other-chunk")]

    assert source_hit_at_k(results, {"expected-document"}, 3) == 1
    assert evidence_hit_at_k(results, {"expected-chunk"}, 3) == 1


@pytest.mark.parametrize("k", [0, -1, 1.5, True, False, None])
def test_invalid_k_is_rejected(k: object) -> None:
    with pytest.raises(ValueError, match="k must be a strictly positive integer"):
        source_hit_at_k([], {"expected-document"}, k)

    with pytest.raises(ValueError, match="k must be a strictly positive integer"):
        evidence_hit_at_k([], {"expected-chunk"}, k)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("id", " ", "Value must contain"),
        ("question", "", "Value must contain"),
        ("expected_document_ids", [], "at least 1"),
        ("expected_chunk_ids", [], "at least 1"),
        ("expected_document_ids", ["duplicate", "duplicate"], "duplicates"),
        ("expected_chunk_ids", ["duplicate", "duplicate"], "duplicates"),
        ("expected_document_ids", "identifier", "collection"),
        ("expected_chunk_ids", "identifier", "collection"),
    ],
)
def test_evaluation_case_rejects_invalid_values(
    field: str,
    value: object,
    message: str,
) -> None:
    values: dict[str, object] = {
        "id": "valid-case",
        "question": "Valid question",
        "expected_document_ids": ["expected-document"],
        "expected_chunk_ids": ["expected-chunk"],
    }
    values[field] = value

    with pytest.raises(ValidationError, match=message):
        EvaluationCase(**values)


def test_evaluate_cases_calculates_per_case_and_mean_metrics() -> None:
    first = create_case("first")
    second = create_case("second")
    results = {
        "second": [create_result("expected-document", "other-chunk")],
        "first": [create_result("expected-document", "expected-chunk")],
    }

    report = evaluate_cases([first, second], results, k=1)

    assert report.k == 1
    assert [evaluation.case_id for evaluation in report.cases] == [
        "first",
        "second",
    ]
    assert [evaluation.source_hit_at_k for evaluation in report.cases] == [1, 1]
    assert [evaluation.evidence_hit_at_k for evaluation in report.cases] == [1, 0]
    assert report.mean_source_hit_at_k == pytest.approx(1.0)
    assert report.mean_evidence_hit_at_k == pytest.approx(0.5)


@pytest.mark.parametrize(
    "results",
    [
        {"first": []},
        {"first": [], "second": [], "unexpected": []},
    ],
)
def test_evaluate_cases_requires_exact_case_result_association(
    results: dict[str, list[RetrievalResult]],
) -> None:
    cases = [create_case("first"), create_case("second")]

    with pytest.raises(ValueError, match="results must match"):
        evaluate_cases(cases, results, k=1)


def test_evaluate_cases_rejects_duplicate_case_identifiers() -> None:
    cases = [create_case("duplicate"), create_case("duplicate")]

    with pytest.raises(ValueError, match="case identifiers must be unique"):
        evaluate_cases(cases, {"duplicate": []}, k=1)


def test_synthetic_dataset_uses_real_chunk_identifiers() -> None:
    chunks = create_chunks(
        create_documents(),
        CharacterChunker(chunk_size=180, overlap=30),
    )
    actual_document_ids = {chunk.document_id for chunk in chunks}
    actual_chunk_ids = {chunk.id for chunk in chunks}
    referenced_document_ids = {
        document_id
        for case in SYNTHETIC_EVALUATION_CASES
        for document_id in case.expected_document_ids
    }
    referenced_chunk_ids = {
        chunk_id
        for case in SYNTHETIC_EVALUATION_CASES
        for chunk_id in case.expected_chunk_ids
    }

    assert len(SYNTHETIC_EVALUATION_CASES) == 6
    assert len({case.id for case in SYNTHETIC_EVALUATION_CASES}) == 6
    assert referenced_document_ids <= actual_document_ids
    assert referenced_chunk_ids <= actual_chunk_ids
