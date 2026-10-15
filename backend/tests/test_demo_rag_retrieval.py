from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest

from app.schemas.documents import Chunk
from app.schemas.retrieval import RetrievalResult
from app.services.chunking import CharacterChunker
from app.services.embeddings import LocalEmbeddingService
from app.services.qdrant import QdrantVectorStore, QdrantVectorStoreError
from app.services.rag_retrieval import RagRetriever
from scripts.demo_hybrid_search import RecordingRankFusion
from scripts.demo_rag_retrieval import (
    MeasuredHybridRetriever,
    MeasuredReranker,
    PreparedPipeline,
    main,
    prepare_pipeline,
    run_demo,
    validate_results,
)


def create_result(chunk: Chunk, score: float) -> RetrievalResult:
    return RetrievalResult(chunk=chunk, score=score)


def create_timer(values: list[float]) -> Iterator[float]:
    return iter(values)


def create_embedding_service() -> MagicMock:
    service = MagicMock(spec=LocalEmbeddingService)
    service.embed_chunks.return_value = [[0.1] * 384] * 3
    return service


def create_vector_store() -> MagicMock:
    store = MagicMock(spec=QdrantVectorStore)
    store.store_chunks.return_value = 3
    return store


def test_prepare_pipeline_builds_all_components() -> None:
    embeddings = create_embedding_service()
    vector_store = create_vector_store()
    reranker = MagicMock()

    pipeline = prepare_pipeline(
        CharacterChunker(chunk_size=1_000),
        embeddings,
        vector_store,
        reranker,
        point_counter=lambda chunks: len(chunks),
    )

    assert len(pipeline.chunks) == 3
    embeddings.embed_chunks.assert_called_once_with(pipeline.chunks)
    vector_store.ensure_collection.assert_called_once_with()
    vector_store.store_chunks.assert_called_once_with(
        pipeline.chunks,
        embeddings.embed_chunks.return_value,
    )
    assert pipeline.point_count == 3


def test_prepare_pipeline_rejects_unexpected_qdrant_count() -> None:
    with pytest.raises(ValueError, match="Qdrant contains 4 points"):
        prepare_pipeline(
            CharacterChunker(chunk_size=1_000),
            create_embedding_service(),
            create_vector_store(),
            MagicMock(),
            point_counter=lambda chunks: len(chunks) + 1,
        )


def test_run_demo_orchestrates_and_displays_rankings(
    capsys: pytest.CaptureFixture[str],
) -> None:
    embeddings = create_embedding_service()
    embeddings.embed_text.return_value = [0.2] * 384
    vector_store = create_vector_store()
    reranker = MagicMock()
    pipeline = prepare_pipeline(
        CharacterChunker(chunk_size=1_000),
        embeddings,
        vector_store,
        reranker,
        point_counter=lambda chunks: len(chunks),
    )
    vector_store.search.return_value = [create_result(pipeline.chunks[1], 0.8)]
    reranker.rerank.side_effect = lambda question, results, top_k: [
        RetrievalResult(chunk=result.chunk, score=0.9 - index / 10)
        for index, result in enumerate(reversed(results[:top_k]))
    ]

    runs = run_demo(pipeline, questions=("protéger le logement",))

    assert runs[0].candidate_request == 9
    assert runs[0].rrf
    assert runs[0].final
    assert {result.chunk for result in runs[0].final}.issubset(
        {result.chunk for result in runs[0].rrf}
    )
    output = capsys.readouterr().out
    assert "RRF ranking" in output
    assert "FlashRank ranking" in output
    assert "Candidate request: 9" in output
    assert "Hybrid search time:" in output
    assert "Reranking time:" in output
    assert "Total time:" in output


def test_measured_components_record_durations_and_candidates() -> None:
    chunk = Chunk(
        id="chunk-1",
        document_id="document-1",
        content="Synthetic content",
        position=0,
        title="Synthetic title",
        source="synthetic://document-1",
    )
    result = create_result(chunk, 0.5)
    hybrid = MagicMock()
    hybrid.search.return_value = [result]
    reranker = MagicMock()
    reranker.rerank.return_value = [create_result(chunk, 0.9)]
    timer = create_timer([1.0, 1.25, 2.0, 2.4])
    measured_hybrid = MeasuredHybridRetriever(hybrid, lambda: next(timer))
    measured_reranker = MeasuredReranker(reranker, lambda: next(timer))

    hybrid_results = measured_hybrid.search("Question", top_k=9)
    final_results = measured_reranker.rerank("Question", hybrid_results, top_k=3)

    assert measured_hybrid.duration_seconds == pytest.approx(0.25)
    assert measured_reranker.duration_seconds == pytest.approx(0.4)
    assert measured_hybrid.requested_top_k == 9
    assert measured_reranker.candidates == [result]
    assert final_results[0].chunk is chunk


def test_validate_results_rejects_changed_metadata() -> None:
    original = Chunk(
        id="chunk-1",
        document_id="document-1",
        content="Synthetic content",
        position=0,
        title="Synthetic title",
        source="synthetic://document-1",
    )
    changed = original.model_copy(update={"title": "Changed title"})

    with pytest.raises(ValueError, match="FlashRank returned inconsistent"):
        validate_results(
            [original],
            [create_result(original, 0.4)],
            [create_result(changed, 0.9)],
        )


def test_run_demo_handles_empty_results(capsys: pytest.CaptureFixture[str]) -> None:
    hybrid = MagicMock()
    hybrid.search.return_value = []
    reranker = MagicMock()
    measured_hybrid = MeasuredHybridRetriever(hybrid)
    measured_reranker = MeasuredReranker(reranker)

    pipeline = PreparedPipeline(
        chunks=[],
        rag_retriever=RagRetriever(measured_hybrid, measured_reranker),
        hybrid_retriever=measured_hybrid,
        reranker=measured_reranker,
        fusion=RecordingRankFusion(),
        point_count=0,
    )

    runs = run_demo(pipeline, questions=("Question synthétique",))

    assert runs[0].rrf == []
    assert runs[0].final == []
    assert capsys.readouterr().out.count("No result") == 2
    reranker.rerank.assert_not_called()


def test_hybrid_error_is_propagated() -> None:
    hybrid = MagicMock()
    error = RuntimeError("synthetic hybrid failure")
    hybrid.search.side_effect = error

    with pytest.raises(RuntimeError) as raised:
        MeasuredHybridRetriever(hybrid).search("Question", top_k=9)

    assert raised.value is error


def test_reranker_error_is_propagated() -> None:
    reranker = MagicMock()
    error = RuntimeError("synthetic reranker failure")
    reranker.rerank.side_effect = error

    with pytest.raises(RuntimeError) as raised:
        MeasuredReranker(reranker).rerank("Question", [], top_k=3)

    assert raised.value is error


def test_main_reports_dependency_error(capsys: pytest.CaptureFixture[str]) -> None:
    def unavailable_pipeline() -> PreparedPipeline:
        raise QdrantVectorStoreError("Qdrant unavailable")

    exit_code = main(pipeline_factory=unavailable_pipeline)

    assert exit_code == 1
    assert "Qdrant operation failed: Qdrant unavailable" in capsys.readouterr().out
