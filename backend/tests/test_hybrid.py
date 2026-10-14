from collections.abc import Callable
from unittest.mock import MagicMock

import pytest

from app.schemas.documents import Chunk
from app.schemas.retrieval import RetrievalResult
from app.services.hybrid import HybridRetriever


def create_result(identifier: str, score: float) -> RetrievalResult:
    return RetrievalResult(
        chunk=Chunk(
            id=identifier,
            document_id="synthetic-document",
            content=f"Synthetic evidence for {identifier}",
            position=0,
            title="Synthetic document",
            source="synthetic://document",
        ),
        score=score,
    )


def create_dependencies() -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    bm25_retriever = MagicMock()
    embedding_service = MagicMock()
    vector_retriever = MagicMock()
    rank_fusion = MagicMock()
    return bm25_retriever, embedding_service, vector_retriever, rank_fusion


def create_retriever(
    bm25_retriever: MagicMock,
    embedding_service: MagicMock,
    vector_retriever: MagicMock,
    rank_fusion: MagicMock,
    *,
    candidate_multiplier: int = 3,
    rrf_k: int = 60,
) -> HybridRetriever:
    return HybridRetriever(
        bm25_retriever=bm25_retriever,
        embedding_service=embedding_service,
        vector_retriever=vector_retriever,
        rank_fusion=rank_fusion,
        candidate_multiplier=candidate_multiplier,
        rrf_k=rrf_k,
    )


def test_search_executes_complete_hybrid_pipeline() -> None:
    bm25, embeddings, vectors, fusion = create_dependencies()
    bm25_results = [create_result("bm25", 4.2)]
    qdrant_results = [create_result("qdrant", 0.8)]
    fused_results = [
        create_result("shared", 0.032),
        create_result("bm25", 0.016),
    ]
    query_vector = [0.25] * 384
    bm25.search.return_value = bm25_results
    embeddings.embed_text.return_value = query_vector
    vectors.search.return_value = qdrant_results
    fusion.return_value = fused_results
    retriever = create_retriever(
        bm25,
        embeddings,
        vectors,
        fusion,
        candidate_multiplier=4,
        rrf_k=50,
    )

    results = retriever.search("Comment financer un logement ?", top_k=2)

    bm25.search.assert_called_once_with(
        "Comment financer un logement ?",
        top_k=8,
    )
    embeddings.embed_text.assert_called_once_with("Comment financer un logement ?")
    vectors.search.assert_called_once_with(query_vector, top_k=8)
    fusion.assert_called_once_with(
        bm25_results,
        qdrant_results,
        top_k=2,
        rrf_k=50,
    )
    assert results == fused_results
    assert [result.chunk.id for result in results] == ["shared", "bm25"]
    assert len(results) == 2


def test_default_fusion_combines_both_rankings() -> None:
    bm25, embeddings, vectors, _ = create_dependencies()
    shared = create_result("shared", 10.0)
    bm25.search.return_value = [shared, create_result("bm25", 8.0)]
    embeddings.embed_text.return_value = [0.25] * 384
    vectors.search.return_value = [create_result("qdrant", 0.9), shared]
    retriever = HybridRetriever(bm25, embeddings, vectors)

    results = retriever.search("Question bancaire synthétique", top_k=2)

    assert [result.chunk.id for result in results] == ["shared", "qdrant"]
    assert len(results) == 2


@pytest.mark.parametrize("question", ["", "   \t"])
def test_empty_question_is_rejected_before_dependency_calls(question: str) -> None:
    dependencies = create_dependencies()
    retriever = create_retriever(*dependencies)

    with pytest.raises(ValueError, match="question must contain"):
        retriever.search(question)

    assert all(not dependency.called for dependency in dependencies)


@pytest.mark.parametrize("top_k", [0, -1, 1.5, True])
def test_invalid_top_k_is_rejected_before_dependency_calls(top_k: object) -> None:
    dependencies = create_dependencies()
    retriever = create_retriever(*dependencies)

    with pytest.raises(ValueError, match="top_k must be a strictly positive integer"):
        retriever.search("Question valide", top_k=top_k)

    assert all(not dependency.called for dependency in dependencies)


@pytest.mark.parametrize("candidate_multiplier", [0, -1, 1.5, True])
def test_invalid_candidate_multiplier_is_rejected(
    candidate_multiplier: object,
) -> None:
    dependencies = create_dependencies()

    with pytest.raises(ValueError, match="candidate_multiplier"):
        create_retriever(*dependencies, candidate_multiplier=candidate_multiplier)


@pytest.mark.parametrize("rrf_k", [0, -1, 1.5, True])
def test_invalid_rrf_k_is_rejected(rrf_k: object) -> None:
    dependencies = create_dependencies()

    with pytest.raises(ValueError, match="rrf_k"):
        create_retriever(*dependencies, rrf_k=rrf_k)


@pytest.mark.parametrize(
    "configure_failure",
    [
        lambda bm25, embeddings, vectors, fusion, error: setattr(
            bm25.search,
            "side_effect",
            error,
        ),
        lambda bm25, embeddings, vectors, fusion, error: setattr(
            embeddings.embed_text,
            "side_effect",
            error,
        ),
        lambda bm25, embeddings, vectors, fusion, error: setattr(
            vectors.search,
            "side_effect",
            error,
        ),
        lambda bm25, embeddings, vectors, fusion, error: setattr(
            fusion,
            "side_effect",
            error,
        ),
    ],
)
def test_dependency_failure_is_propagated(
    configure_failure: Callable[..., None],
) -> None:
    dependencies = create_dependencies()
    error = RuntimeError("synthetic dependency failure")
    configure_failure(*dependencies, error)
    dependencies[0].search.return_value = []
    dependencies[1].embed_text.return_value = [0.25] * 384
    dependencies[2].search.return_value = []
    dependencies[3].return_value = []
    retriever = create_retriever(*dependencies)

    with pytest.raises(RuntimeError) as raised:
        retriever.search("Question bancaire synthétique")

    assert raised.value is error
