from unittest.mock import MagicMock

import pytest

from app.schemas.documents import Chunk
from app.schemas.retrieval import RetrievalResult
from app.services.chunking import CharacterChunker
from app.services.embeddings import LocalEmbeddingService
from app.services.qdrant import QdrantVectorStore, QdrantVectorStoreError
from scripts.demo_hybrid_search import (
    main,
    prepare_pipeline,
    run_demo,
    validate_shared_chunks,
)


def create_result(chunk: Chunk, score: float) -> RetrievalResult:
    return RetrievalResult(chunk=chunk, score=score)


def create_embedding_service() -> MagicMock:
    service = MagicMock(spec=LocalEmbeddingService)
    service.embed_chunks.return_value = [[0.1] * 384] * 3
    service.embed_text.side_effect = [[0.2] * 384, [0.3] * 384]
    return service


def create_vector_store() -> MagicMock:
    store = MagicMock(spec=QdrantVectorStore)
    store.store_chunks.return_value = 3
    return store


def test_prepare_pipeline_builds_corpus_bm25_and_vector_index() -> None:
    embeddings = create_embedding_service()
    vector_store = create_vector_store()

    chunks, hybrid_retriever, _ = prepare_pipeline(
        CharacterChunker(chunk_size=1_000),
        embeddings,
        vector_store,
    )

    assert [chunk.id for chunk in chunks] == [
        "demo-credit-immobilier:chunk:0",
        "demo-assurance-habitation:chunk:0",
        "demo-epargne:chunk:0",
    ]
    embeddings.embed_chunks.assert_called_once_with(chunks)
    vector_store.ensure_collection.assert_called_once_with()
    vector_store.store_chunks.assert_called_once_with(
        chunks,
        embeddings.embed_chunks.return_value,
    )
    assert hybrid_retriever.search


def test_run_demo_calls_both_engines_and_fuses_shared_chunk(
    capsys: pytest.CaptureFixture[str],
) -> None:
    embeddings = create_embedding_service()
    vector_store = create_vector_store()
    chunks, _, _ = prepare_pipeline(
        CharacterChunker(chunk_size=1_000),
        embeddings,
        vector_store,
    )
    embeddings.reset_mock()
    vector_store.reset_mock()
    shared = chunks[0]
    vector_store.search.side_effect = [
        [create_result(shared, 0.9)],
        [create_result(chunks[1], 0.8)],
    ]

    rankings = run_demo(
        CharacterChunker(chunk_size=1_000),
        embeddings,
        vector_store,
        questions=("crédit immobilier", "protéger contre les sinistres"),
    )

    assert embeddings.embed_text.call_count == 2
    assert vector_store.search.call_count == 2
    assert all(call.kwargs["top_k"] == 9 for call in vector_store.search.call_args_list)
    assert rankings[0].bm25[0].chunk.id == shared.id
    assert rankings[0].qdrant[0].chunk.id == shared.id
    assert rankings[0].rrf[0].chunk.id == shared.id
    assert sum(result.chunk.id == shared.id for result in rankings[0].rrf) == 1
    output = capsys.readouterr().out
    assert "BM25 ranking" in output
    assert "Qdrant ranking" in output
    assert "RRF ranking" in output


def test_inconsistent_shared_chunk_metadata_is_rejected() -> None:
    chunk = Chunk(
        id="chunk-1",
        document_id="document-1",
        content="Synthetic content",
        position=0,
        title="Synthetic title",
        source="synthetic://document",
    )
    inconsistent = chunk.model_copy(update={"content": "Different synthetic content"})

    with pytest.raises(ValueError, match="Inconsistent chunk metadata"):
        validate_shared_chunks(
            [create_result(chunk, 1.0)],
            [create_result(inconsistent, 0.9)],
        )


def test_main_reports_missing_local_model(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unavailable_model() -> LocalEmbeddingService:
        raise OSError("model files missing")

    exit_code = main(embedding_factory=unavailable_model)

    assert exit_code == 1
    assert "Local embedding model unavailable" in capsys.readouterr().out


def test_main_reports_qdrant_failure(
    capsys: pytest.CaptureFixture[str],
) -> None:
    embeddings = create_embedding_service()
    vector_store = create_vector_store()
    vector_store.ensure_collection.side_effect = QdrantVectorStoreError(
        "Qdrant unavailable"
    )

    exit_code = main(
        embedding_factory=lambda: embeddings,
        vector_store_factory=lambda: vector_store,
    )

    assert exit_code == 1
    assert "Qdrant operation failed: Qdrant unavailable" in capsys.readouterr().out
