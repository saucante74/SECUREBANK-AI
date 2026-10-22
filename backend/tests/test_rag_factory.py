from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from app.core import rag_factory
from app.core.config import Settings
from app.core.rag_factory import (
    RagConfigurationError,
    RagDependencyUnavailableError,
    RagGenerationServiceProvider,
    create_rag_generation_service,
    create_rag_observer,
    rag_generation_service_provider,
)
from app.schemas.documents import Chunk, Document
from app.services.bm25 import BM25Retriever
from app.services.embeddings import LocalEmbeddingService
from app.services.hybrid import HybridRetriever
from app.services.llm import OpenAILLMService
from app.services.pii_masking import PiiMasker
from app.services.qdrant import QdrantVectorStore, QdrantVectorStoreError
from app.services.rag_corpus import RagCorpus
from app.services.rag_generation import RagGenerationService
from app.services.rag_observer import NoOpRagObserver
from app.services.rrf import reciprocal_rank_fusion


def create_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "rag_enabled": True,
        "rag_corpus_path": Path("synthetic-corpus.json"),
        "llm_api_key": SecretStr("synthetic-test-key"),
    }
    values.update(overrides)
    return Settings(**values)


def create_chunk() -> Chunk:
    return Chunk(
        id="synthetic-document:chunk:0",
        document_id="synthetic-document",
        content="Synthetic banking guidance.",
        position=0,
        title="Synthetic guide",
        source="synthetic://guide",
    )


def test_missing_corpus_configuration_is_rejected_before_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    embedding_factory = MagicMock()
    monkeypatch.setattr(rag_factory, "LocalEmbeddingService", embedding_factory)

    with pytest.raises(RagConfigurationError, match="corpus path"):
        create_rag_generation_service(create_settings(rag_corpus_path=None))

    embedding_factory.assert_not_called()


def test_missing_llm_configuration_is_rejected_before_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corpus_loader = MagicMock()
    monkeypatch.setattr(rag_factory, "load_rag_corpus", corpus_loader)

    with pytest.raises(RagConfigurationError, match="LLM API key"):
        create_rag_generation_service(create_settings(llm_api_key=None))

    corpus_loader.assert_not_called()


def test_factory_composes_bm25_qdrant_rrf_and_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk = create_chunk()
    corpus = RagCorpus(
        documents=(
            Document(
                id="synthetic-document",
                content=chunk.content,
                title=chunk.title,
                source=chunk.source,
            ),
        )
    )
    embeddings = MagicMock(spec=LocalEmbeddingService)
    embeddings.embed_chunks.return_value = [[0.1] * 384]
    bm25_retriever = MagicMock(spec=BM25Retriever)
    vector_store = MagicMock(spec=QdrantVectorStore)
    llm_service = MagicMock(spec=OpenAILLMService)
    pii_masker = MagicMock(spec=PiiMasker)
    monkeypatch.setattr(rag_factory, "load_rag_corpus", lambda path: corpus)
    monkeypatch.setattr(rag_factory, "create_rag_chunks", lambda value: [chunk])
    monkeypatch.setattr(rag_factory, "LocalEmbeddingService", lambda: embeddings)
    monkeypatch.setattr(
        rag_factory,
        "BM25Retriever",
        lambda chunks: bm25_retriever,
    )
    monkeypatch.setattr(
        rag_factory.QdrantVectorStore,
        "from_settings",
        lambda settings: vector_store,
    )
    monkeypatch.setattr(
        rag_factory,
        "create_openai_llm_service",
        lambda settings: llm_service,
    )
    monkeypatch.setattr(rag_factory, "PiiMasker", lambda: pii_masker)

    service = create_rag_generation_service(create_settings())

    assert isinstance(service, RagGenerationService)
    retriever = cast(HybridRetriever, service._retriever)
    assert retriever._bm25_retriever is bm25_retriever
    assert retriever._embedding_service is embeddings
    assert retriever._vector_retriever is vector_store
    assert retriever._rank_fusion is reciprocal_rank_fusion
    assert service._llm_service is llm_service
    assert service._pii_masker is pii_masker
    assert service._model_name == "gpt-4.1-mini"
    embeddings.embed_chunks.assert_called_once_with([chunk])
    vector_store.store_chunks.assert_called_once_with(
        [chunk], embeddings.embed_chunks.return_value
    )


def test_qdrant_failure_has_controlled_dependency_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk = create_chunk()
    embeddings = MagicMock(spec=LocalEmbeddingService)
    embeddings.embed_chunks.return_value = [[0.1] * 384]
    vector_store = MagicMock(spec=QdrantVectorStore)
    vector_store.store_chunks.side_effect = QdrantVectorStoreError(
        "secret-qdrant-address"
    )
    monkeypatch.setattr(rag_factory, "load_rag_corpus", lambda path: MagicMock())
    monkeypatch.setattr(rag_factory, "create_rag_chunks", lambda corpus: [chunk])
    monkeypatch.setattr(rag_factory, "LocalEmbeddingService", lambda: embeddings)
    monkeypatch.setattr(
        rag_factory.QdrantVectorStore,
        "from_settings",
        lambda settings: vector_store,
    )

    with pytest.raises(RagDependencyUnavailableError) as error:
        create_rag_generation_service(create_settings())

    assert "secret-qdrant-address" not in str(error.value)


def test_pii_initialization_failure_has_controlled_dependency_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk = create_chunk()
    embeddings = MagicMock(spec=LocalEmbeddingService)
    embeddings.embed_chunks.return_value = [[0.1] * 384]
    vector_store = MagicMock(spec=QdrantVectorStore)
    monkeypatch.setattr(rag_factory, "load_rag_corpus", lambda path: MagicMock())
    monkeypatch.setattr(rag_factory, "create_rag_chunks", lambda corpus: [chunk])
    monkeypatch.setattr(rag_factory, "LocalEmbeddingService", lambda: embeddings)
    monkeypatch.setattr(
        rag_factory.QdrantVectorStore,
        "from_settings",
        lambda settings: vector_store,
    )
    monkeypatch.setattr(
        rag_factory,
        "PiiMasker",
        MagicMock(side_effect=RuntimeError("sensitive-presidio-details")),
    )

    with pytest.raises(RagDependencyUnavailableError) as error:
        create_rag_generation_service(create_settings())

    assert "sensitive-presidio-details" not in str(error.value)


def test_programming_error_is_not_converted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rag_factory,
        "load_rag_corpus",
        MagicMock(side_effect=TypeError("programming defect")),
    )

    with pytest.raises(TypeError, match="programming defect"):
        create_rag_generation_service(create_settings())


def test_provider_builds_lazily_once_and_reuses_service() -> None:
    service = MagicMock(spec=RagGenerationService)
    factory = MagicMock(return_value=service)
    provider = RagGenerationServiceProvider(factory=factory)
    settings = create_settings()

    factory.assert_not_called()
    assert provider.get(settings) is service
    assert provider.get(settings) is service
    factory.assert_called_once_with(settings)


def test_module_import_does_not_construct_pipeline() -> None:
    assert rag_generation_service_provider._service is None


def test_observability_is_disabled_by_default() -> None:
    observer = create_rag_observer(create_settings())

    assert isinstance(observer, NoOpRagObserver)


def test_enabled_observability_constructs_sdk_client_with_explicit_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    client_factory = MagicMock(return_value=client)
    monkeypatch.setattr(
        rag_factory,
        "create_langfuse_sdk_observation_client",
        client_factory,
    )
    settings = create_settings(
        langfuse_enabled=True,
        langfuse_public_key=SecretStr("synthetic-public-key"),
        langfuse_secret_key=SecretStr("synthetic-secret-key"),
        langfuse_host="https://langfuse.example.test",
    )

    observer = create_rag_observer(settings)

    client_factory.assert_called_once_with(
        public_key="synthetic-public-key",
        secret_key="synthetic-secret-key",
        host="https://langfuse.example.test/",
    )
    assert observer._client is client


def test_sdk_initialization_failure_falls_back_to_noop(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sensitive_public_key = "public-key-that-must-not-be-logged"
    sensitive_secret_key = "secret-key-that-must-not-be-logged"
    monkeypatch.setattr(
        rag_factory,
        "create_langfuse_sdk_observation_client",
        MagicMock(
            side_effect=RuntimeError(
                f"SDK failure {sensitive_public_key} {sensitive_secret_key}"
            )
        ),
    )
    settings = create_settings(
        langfuse_enabled=True,
        langfuse_public_key=SecretStr(sensitive_public_key),
        langfuse_secret_key=SecretStr(sensitive_secret_key),
    )

    observer = create_rag_observer(settings)

    assert isinstance(observer, NoOpRagObserver)
    assert sensitive_public_key not in caplog.text
    assert sensitive_secret_key not in caplog.text
