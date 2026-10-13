import pytest

from app.schemas.documents import Chunk
from app.schemas.retrieval import RetrievalResult
from app.services.rrf import reciprocal_rank_fusion


def create_result(
    chunk_id: str,
    score: float,
    *,
    document_id: str = "document-1",
    content: str | None = None,
) -> RetrievalResult:
    return RetrievalResult(
        chunk=Chunk(
            id=chunk_id,
            document_id=document_id,
            content=content or f"Synthetic content for {chunk_id}",
            position=0,
            title="Synthetic document",
            source="synthetic://document",
        ),
        score=score,
    )


def test_exact_rrf_formula_for_result_in_both_rankings() -> None:
    shared = create_result("shared", 100.0)

    results = reciprocal_rank_fusion(
        [create_result("bm25-first", 200.0), shared],
        [shared],
        top_k=3,
        rrf_k=60,
    )

    scores = {result.chunk.id: result.score for result in results}
    assert scores["shared"] == pytest.approx(1 / 62 + 1 / 61)
    assert scores["bm25-first"] == pytest.approx(1 / 61)


def test_fuses_two_rankings_in_descending_rrf_order() -> None:
    results = reciprocal_rank_fusion(
        [create_result("shared", 4.0), create_result("bm25-only", 3.0)],
        [create_result("qdrant-only", 0.9), create_result("shared", 0.8)],
        top_k=3,
    )

    assert [result.chunk.id for result in results] == [
        "shared",
        "qdrant-only",
        "bm25-only",
    ]
    assert results[0].score == pytest.approx(1 / 61 + 1 / 62)
    assert results[1].score == pytest.approx(1 / 61)
    assert results[2].score == pytest.approx(1 / 62)


def test_results_present_in_only_one_ranking_are_retained() -> None:
    results = reciprocal_rank_fusion(
        [create_result("bm25-only", 2.0)],
        [create_result("qdrant-only", 0.7)],
        top_k=2,
    )

    assert [result.chunk.id for result in results] == [
        "bm25-only",
        "qdrant-only",
    ]


def test_empty_rankings_return_empty_list() -> None:
    assert reciprocal_rank_fusion([], [], top_k=3) == []


def test_duplicate_in_one_ranking_contributes_only_once() -> None:
    duplicate = create_result("duplicate", 9.0)

    results = reciprocal_rank_fusion(
        [duplicate, duplicate, create_result("third", 7.0)],
        [],
        top_k=3,
        rrf_k=10,
    )

    scores = {result.chunk.id: result.score for result in results}
    assert scores["duplicate"] == pytest.approx(1 / 11)
    assert scores["third"] == pytest.approx(1 / 13)
    assert len(results) == 2


def test_same_text_with_different_identifiers_remains_distinct() -> None:
    shared_content = "Identical synthetic banking text"

    results = reciprocal_rank_fusion(
        [create_result("chunk-1", 2.0, content=shared_content)],
        [create_result("chunk-2", 0.8, content=shared_content)],
        top_k=2,
    )

    assert [result.chunk.id for result in results] == ["chunk-1", "chunk-2"]


def test_same_chunk_id_in_different_documents_remains_distinct() -> None:
    results = reciprocal_rank_fusion(
        [create_result("chunk-1", 2.0, document_id="document-1")],
        [create_result("chunk-1", 0.8, document_id="document-2")],
        top_k=2,
    )

    assert [result.chunk.document_id for result in results] == [
        "document-1",
        "document-2",
    ]


def test_equal_scores_preserve_first_appearance_order() -> None:
    results = reciprocal_rank_fusion(
        [create_result("first", 1.0)],
        [create_result("second", 1.0)],
        top_k=2,
    )

    assert [result.chunk.id for result in results] == ["first", "second"]


def test_top_k_limits_results() -> None:
    results = reciprocal_rank_fusion(
        [create_result("first", 3.0), create_result("second", 2.0)],
        [create_result("third", 1.0)],
        top_k=2,
    )

    assert len(results) == 2
    assert [result.chunk.id for result in results] == ["first", "third"]


@pytest.mark.parametrize("top_k", [0, -1, 1.5, True])
def test_invalid_top_k_is_rejected(top_k: object) -> None:
    with pytest.raises(ValueError, match="top_k must be a strictly positive integer"):
        reciprocal_rank_fusion([], [], top_k=top_k)


@pytest.mark.parametrize("rrf_k", [0, -1, 1.5, True])
def test_invalid_rrf_k_is_rejected(rrf_k: object) -> None:
    with pytest.raises(ValueError, match="rrf_k must be a strictly positive integer"):
        reciprocal_rank_fusion([], [], top_k=1, rrf_k=rrf_k)


def test_source_scores_do_not_affect_fusion() -> None:
    first = reciprocal_rank_fusion(
        [create_result("shared", 1_000.0), create_result("bm25-only", -5.0)],
        [create_result("qdrant-only", -100.0), create_result("shared", 0.001)],
        top_k=3,
    )
    second = reciprocal_rank_fusion(
        [create_result("shared", -7.0), create_result("bm25-only", 900.0)],
        [create_result("qdrant-only", 500.0), create_result("shared", -80.0)],
        top_k=3,
    )

    assert [result.chunk.id for result in first] == [
        result.chunk.id for result in second
    ]
    assert [result.score for result in first] == [result.score for result in second]
