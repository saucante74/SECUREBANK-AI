from unittest.mock import MagicMock

import pytest

from app.schemas.documents import Chunk
from app.schemas.retrieval import RetrievalResult
from app.services.rag_retrieval import RagRetriever


def create_result(
    identifier: str,
    score: float,
    *,
    content: str | None = None,
    position: int = 0,
) -> RetrievalResult:
    return RetrievalResult(
        chunk=Chunk(
            id=identifier,
            document_id=f"document-{identifier}",
            content=content or f"Synthetic evidence for {identifier}",
            position=position,
            title=f"Synthetic title {identifier}",
            source=f"synthetic://{identifier}",
        ),
        score=score,
    )


def create_dependencies() -> tuple[MagicMock, MagicMock]:
    return MagicMock(), MagicMock()


def test_search_chains_hybrid_retrieval_and_reranking() -> None:
    hybrid, reranker = create_dependencies()
    candidates = [create_result(str(index), 1.0 - index / 10) for index in range(6)]
    reranked = [
        RetrievalResult(chunk=candidates[4].chunk, score=0.99),
        RetrievalResult(chunk=candidates[1].chunk, score=0.88),
    ]
    hybrid.search.return_value = candidates
    reranker.rerank.return_value = reranked

    results = RagRetriever(hybrid, reranker).search("Question bancaire", top_k=2)

    hybrid.search.assert_called_once_with("Question bancaire", top_k=6)
    reranker.rerank.assert_called_once_with(
        "Question bancaire",
        candidates,
        top_k=2,
    )
    assert results == reranked
    assert [result.chunk.id for result in results] == ["4", "1"]


def test_default_candidate_multiplier_is_three() -> None:
    hybrid, reranker = create_dependencies()
    hybrid.search.return_value = []

    RagRetriever(hybrid, reranker).search("Question bancaire", top_k=5)

    hybrid.search.assert_called_once_with("Question bancaire", top_k=15)


def test_custom_candidate_multiplier_is_used() -> None:
    hybrid, reranker = create_dependencies()
    hybrid.search.return_value = []

    RagRetriever(hybrid, reranker, candidate_multiplier=4).search(
        "Question bancaire",
        top_k=3,
    )

    hybrid.search.assert_called_once_with("Question bancaire", top_k=12)


def test_search_preserves_chunks_and_all_metadata() -> None:
    hybrid, reranker = create_dependencies()
    first = create_result("first", 0.8, position=2)
    second = create_result("second", 0.7, position=4)
    candidates = [first, second]
    reranked = [
        RetrievalResult(chunk=second.chunk, score=0.97),
        RetrievalResult(chunk=first.chunk, score=0.42),
    ]
    hybrid.search.return_value = candidates
    reranker.rerank.return_value = reranked

    results = RagRetriever(hybrid, reranker).search("Question bancaire", top_k=2)

    assert results[0].chunk is second.chunk
    assert results[1].chunk is first.chunk
    assert {result.chunk for result in results} == {first.chunk, second.chunk}


def test_distinct_chunks_with_identical_text_are_preserved() -> None:
    hybrid, reranker = create_dependencies()
    first = create_result("first", 0.8, content="Identical synthetic text")
    second = create_result("second", 0.7, content="Identical synthetic text")
    hybrid.search.return_value = [first, second]
    reranker.rerank.return_value = [second, first]

    results = RagRetriever(hybrid, reranker).search("Question bancaire", top_k=2)

    assert [result.chunk.id for result in results] == ["second", "first"]
    reranker.rerank.assert_called_once_with(
        "Question bancaire",
        [first, second],
        top_k=2,
    )


def test_empty_candidates_return_without_reranking() -> None:
    hybrid, reranker = create_dependencies()
    hybrid.search.return_value = []

    results = RagRetriever(hybrid, reranker).search("Question bancaire", top_k=3)

    assert results == []
    reranker.rerank.assert_not_called()


def test_fewer_candidates_than_top_k_are_reranked() -> None:
    hybrid, reranker = create_dependencies()
    candidates = [create_result("only", 0.5)]
    reranker.rerank.return_value = candidates
    hybrid.search.return_value = candidates

    results = RagRetriever(hybrid, reranker).search("Question bancaire", top_k=3)

    reranker.rerank.assert_called_once_with(
        "Question bancaire",
        candidates,
        top_k=3,
    )
    assert results == candidates


def test_final_results_are_limited_to_top_k() -> None:
    hybrid, reranker = create_dependencies()
    candidates = [create_result(str(index), 0.5) for index in range(3)]
    hybrid.search.return_value = candidates
    reranker.rerank.return_value = candidates

    results = RagRetriever(hybrid, reranker).search("Question bancaire", top_k=2)

    assert results == candidates[:2]


@pytest.mark.parametrize("question", ["", "   \t", None])
def test_invalid_question_is_rejected_before_dependency_calls(
    question: object,
) -> None:
    hybrid, reranker = create_dependencies()
    retriever = RagRetriever(hybrid, reranker)

    with pytest.raises(ValueError, match="question must contain"):
        retriever.search(question, top_k=3)

    hybrid.search.assert_not_called()
    reranker.rerank.assert_not_called()


@pytest.mark.parametrize("top_k", [0, -1, 1.5, True, None])
def test_invalid_top_k_is_rejected_before_dependency_calls(top_k: object) -> None:
    hybrid, reranker = create_dependencies()
    retriever = RagRetriever(hybrid, reranker)

    with pytest.raises(ValueError, match="top_k must be a strictly positive integer"):
        retriever.search("Question bancaire", top_k=top_k)

    hybrid.search.assert_not_called()
    reranker.rerank.assert_not_called()


@pytest.mark.parametrize("candidate_multiplier", [0, -1, 1.5, True, None])
def test_invalid_candidate_multiplier_is_rejected(
    candidate_multiplier: object,
) -> None:
    hybrid, reranker = create_dependencies()

    with pytest.raises(ValueError, match="candidate_multiplier"):
        RagRetriever(hybrid, reranker, candidate_multiplier=candidate_multiplier)


def test_hybrid_error_is_propagated() -> None:
    hybrid, reranker = create_dependencies()
    error = RuntimeError("synthetic hybrid failure")
    hybrid.search.side_effect = error

    with pytest.raises(RuntimeError) as raised:
        RagRetriever(hybrid, reranker).search("Question bancaire", top_k=3)

    assert raised.value is error
    reranker.rerank.assert_not_called()


def test_reranker_error_is_propagated() -> None:
    hybrid, reranker = create_dependencies()
    error = RuntimeError("synthetic reranker failure")
    hybrid.search.return_value = [create_result("candidate", 0.5)]
    reranker.rerank.side_effect = error

    with pytest.raises(RuntimeError) as raised:
        RagRetriever(hybrid, reranker).search("Question bancaire", top_k=3)

    assert raised.value is error
