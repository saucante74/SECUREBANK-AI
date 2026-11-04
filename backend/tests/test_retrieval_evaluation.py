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
    evaluate_ir_metrics,
    evaluate_ir_question,
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


def test_ir_metrics_return_zero_when_no_relevant_result_is_retrieved() -> None:
    metrics = evaluate_ir_question(
        "question",
        [create_result("document", "negative")],
        {"negative": 0, "positive": 2},
        k=1,
    )

    assert metrics.precision_at_k.value == 0.0
    assert metrics.recall_at_k.value == 0.0
    assert metrics.f1_at_k.value == 0.0
    assert metrics.average_precision_at_k.value == 0.0
    assert metrics.success_at_k.value == 0.0
    assert metrics.reciprocal_rank_at_k.value == 0.0
    assert metrics.ndcg_at_k.value == 0.0


def test_ir_metrics_treat_partial_and_strong_relevance_as_binary_positives() -> None:
    metrics = evaluate_ir_question(
        "question",
        [
            create_result("document", "partial"),
            create_result("document", "strong"),
        ],
        {"partial": 1, "strong": 2},
        k=2,
    )

    assert metrics.precision_at_k.value == 1.0
    assert metrics.recall_at_k.value == 1.0
    assert metrics.f1_at_k.value == 1.0
    assert metrics.success_at_k.value == 1.0
    assert metrics.average_precision_at_k.value == 1.0
    assert metrics.reciprocal_rank_at_k.value == 1.0


def test_ir_metrics_make_every_metric_unavailable_for_an_unjudged_result() -> None:
    metrics = evaluate_ir_question(
        "question",
        [create_result("document", "unjudged")],
        {"positive": 2},
        k=1,
    )

    for field_name in (
        "precision_at_k",
        "recall_at_k",
        "f1_at_k",
        "average_precision_at_k",
        "success_at_k",
        "reciprocal_rank_at_k",
        "ndcg_at_k",
    ):
        result = getattr(metrics, field_name)
        assert result.value is None
        assert result.unavailable_reason == (
            "unjudged result chunks at evaluated ranks: unjudged"
        )


def test_empty_results_are_valid_and_use_known_pool_positives() -> None:
    metrics = evaluate_ir_question(
        "question",
        [],
        {"positive": 1},
        k=3,
    )

    assert metrics.precision_at_k.value == 0.0
    assert metrics.recall_at_k.value == 0.0
    assert metrics.f1_at_k.value == 0.0
    assert metrics.average_precision_at_k.value == 0.0
    assert metrics.success_at_k.value == 0.0
    assert metrics.reciprocal_rank_at_k.value == 0.0
    assert metrics.ndcg_at_k.value == 0.0


def test_precision_at_three_uses_k_with_fewer_than_three_results() -> None:
    metrics = evaluate_ir_question(
        "question",
        [create_result("document", "positive")],
        {"positive": 1},
        k=3,
    )

    assert metrics.precision_at_k.value == pytest.approx(1 / 3)
    assert metrics.recall_at_k.value == 1.0
    assert metrics.f1_at_k.value == pytest.approx(0.5)


def test_map_and_mrr_use_the_ranked_positions_of_multiple_positives() -> None:
    metrics = evaluate_ir_question(
        "question",
        [
            create_result("document", "negative"),
            create_result("document", "positive-1"),
            create_result("document", "positive-2"),
        ],
        {"negative": 0, "positive-1": 1, "positive-2": 2},
        k=3,
    )

    assert metrics.average_precision_at_k.value == pytest.approx((1 / 2 + 2 / 3) / 2)
    assert metrics.reciprocal_rank_at_k.value == pytest.approx(1 / 2)
    assert metrics.success_at_k.value == 1.0


def test_ndcg_uses_exponential_graded_gain() -> None:
    metrics = evaluate_ir_question(
        "question",
        [
            create_result("document", "partial"),
            create_result("document", "strong"),
            create_result("document", "negative"),
        ],
        {"partial": 1, "strong": 2, "negative": 0},
        k=3,
    )
    discounted_gain = 1 + 3 / 1.584962500721156
    ideal_discounted_gain = 3 + 1 / 1.584962500721156

    assert metrics.ndcg_at_k.value == pytest.approx(
        discounted_gain / ideal_discounted_gain
    )


def test_metrics_without_known_positives_expose_metric_specific_reasons() -> None:
    metrics = evaluate_ir_question(
        "question",
        [create_result("document", "negative")],
        {"negative": 0},
        k=1,
    )

    assert metrics.precision_at_k.value == 0.0
    assert metrics.success_at_k.value == 0.0
    assert metrics.reciprocal_rank_at_k.value == 0.0
    for result in (
        metrics.recall_at_k,
        metrics.f1_at_k,
        metrics.average_precision_at_k,
        metrics.ndcg_at_k,
    ):
        assert result.value is None
        assert result.unavailable_reason == (
            "no positive judgments are available for this question"
        )


def test_ir_report_aggregates_only_available_questions_and_counts_them() -> None:
    report = evaluate_ir_metrics(
        {
            "available": [create_result("document", "positive")],
            "unavailable": [create_result("document", "unjudged")],
        },
        {
            "available": {"positive": 2},
            "unavailable": {"positive": 1},
        },
        k=1,
    )

    assert report.precision_at_k.value == 1.0
    assert report.precision_at_k.evaluated_question_count == 1
    assert report.precision_at_k.unavailable_question_count == 1
    assert report.map_at_k.value == 1.0
    assert report.map_at_k.evaluated_question_count == 1
    assert report.mrr_at_k.value == 1.0
    assert report.ndcg_at_k.value == 1.0
