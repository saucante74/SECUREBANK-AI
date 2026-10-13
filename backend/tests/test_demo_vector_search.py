from unittest.mock import MagicMock

from app.schemas.documents import Chunk
from app.schemas.retrieval import RetrievalResult
from app.services.chunking import CharacterChunker
from app.services.embeddings import LocalEmbeddingService
from app.services.qdrant import QdrantVectorStore, QdrantVectorStoreError
from scripts.demo_vector_search import QUESTION, create_documents, main, run_demo


def create_embedding_service() -> MagicMock:
    service = MagicMock(spec=LocalEmbeddingService)
    service.embed_chunks.return_value = [[0.1] * 384] * 3
    service.embed_text.return_value = [0.2] * 384
    return service


def create_vector_store() -> MagicMock:
    store = MagicMock(spec=QdrantVectorStore)
    store.store_chunks.return_value = 3
    store.search.return_value = [
        RetrievalResult(
            chunk=Chunk(
                id="demo-credit-immobilier:chunk:0",
                document_id="demo-credit-immobilier",
                content="Le crédit immobilier finance l'achat d'un logement.",
                position=0,
                title="Guide du crédit immobilier",
                source="synthetic://credit-immobilier",
            ),
            score=0.91,
        )
    ]
    return store


def test_documents_are_synthetic_and_have_stable_identifiers() -> None:
    documents = create_documents()

    assert [document.id for document in documents] == [
        "demo-credit-immobilier",
        "demo-assurance-habitation",
        "demo-epargne",
    ]
    assert all(document.source.startswith("synthetic://") for document in documents)


def test_run_demo_executes_vector_pipeline(capsys: object) -> None:
    embedding_service = create_embedding_service()
    vector_store = create_vector_store()

    results = run_demo(
        CharacterChunker(chunk_size=1_000),
        embedding_service,
        vector_store,
    )

    chunks = embedding_service.embed_chunks.call_args.args[0]
    assert [chunk.id for chunk in chunks] == [
        "demo-credit-immobilier:chunk:0",
        "demo-assurance-habitation:chunk:0",
        "demo-epargne:chunk:0",
    ]
    vector_store.ensure_collection.assert_called_once_with()
    vector_store.store_chunks.assert_called_once_with(
        chunks,
        embedding_service.embed_chunks.return_value,
    )
    embedding_service.embed_text.assert_called_once_with(QUESTION)
    vector_store.search.assert_called_once_with([0.2] * 384, top_k=3)
    assert results == vector_store.search.return_value


def test_main_reports_missing_local_model(capsys: object) -> None:
    def unavailable_model() -> LocalEmbeddingService:
        raise OSError("model files missing")

    exit_code = main(embedding_factory=unavailable_model)

    assert exit_code == 1
    assert "Local embedding model unavailable" in capsys.readouterr().out


def test_main_reports_qdrant_failure(capsys: object) -> None:
    store = create_vector_store()
    store.ensure_collection.side_effect = QdrantVectorStoreError("Qdrant unavailable")

    exit_code = main(
        embedding_factory=create_embedding_service,
        vector_store_factory=lambda: store,
    )

    assert exit_code == 1
    assert "Qdrant operation failed: Qdrant unavailable" in capsys.readouterr().out
