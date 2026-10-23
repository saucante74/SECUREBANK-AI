import argparse
import hashlib
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException

from app.core.config import Settings
from app.schemas.rag_generation import RagGenerationResult
from app.services.bm25 import BM25Retriever
from app.services.embeddings import LocalEmbeddingService
from app.services.hybrid import HybridRetriever
from app.services.llm import LLMGeneration, LLMService, LLMServiceError
from app.services.pii_masking import PiiMasker
from app.services.qdrant import QdrantVectorStore, QdrantVectorStoreError
from app.services.rag_corpus import RagCorpus, create_rag_chunks, load_rag_corpus
from app.services.rag_generation import (
    RagGenerationResponseError,
    RagGenerationService,
    RagPiiProtectionError,
)
from scripts.run_openai_smoke_test import (
    ALLOW_REAL_CALL_FLAG,
    OpenAIClientFactory,
    create_smoke_service,
)
from scripts.run_rag_integration import CORPUS_PATH, PASSAGE_EMAIL, parse_prompt

OPENAI_INTEGRATION_COLLECTION_NAME = "securebank_rag_openai_integration_chunks"
EXPECTED_CORPUS_SHA256 = (
    "a3d8fc3c5d8fc9932d7edf0941559754ff3101ca4eb051e77c886c9d3129b10a"
)
EXPECTED_DOCUMENT_IDS = frozenset(
    {
        "integration-credit-delay",
        "integration-transfer-limit",
        "integration-kyc-renewal",
        "integration-adviser-contact",
    }
)
KNOWN_SYNTHETIC_PII = (PASSAGE_EMAIL,)
MAX_OPENAI_CALLS = 2
TOP_K = 3
FACTUAL_QUESTION = "Quel est le plafond quotidien fictif des virements en ligne ?"
ABSTENTION_QUESTION = "Quel est le plafond d'une carte de débit extraterrestre ?"


class IntegrationSafetyError(RuntimeError):
    pass


class RagGenerator(Protocol):
    def generate(
        self,
        question: str,
        top_k: int | None = None,
    ) -> RagGenerationResult: ...


@dataclass(frozen=True)
class PreparedOpenAIIntegration:
    service: RagGenerator
    llm_guard: "PreflightLLMService"


class PreflightLLMService:
    def __init__(
        self,
        delegate: LLMService,
        allowed_document_ids: frozenset[str],
        allowed_chunk_ids: frozenset[str],
        forbidden_values: Sequence[str],
        max_calls: int = MAX_OPENAI_CALLS,
    ) -> None:
        if max_calls <= 0:
            raise ValueError("max_calls must be strictly positive")
        self._delegate = delegate
        self._allowed_document_ids = allowed_document_ids
        self._allowed_chunk_ids = allowed_chunk_ids
        self._forbidden_values = tuple(forbidden_values)
        self._max_calls = max_calls
        self._call_count = 0

    @property
    def call_count(self) -> int:
        return self._call_count

    def generate(self, prompt: str) -> LLMGeneration:
        if self._call_count >= self._max_calls:
            raise IntegrationSafetyError("OpenAI call budget exhausted")
        self._validate_prompt(prompt)
        self._call_count += 1
        return self._delegate.generate(prompt)

    def _validate_prompt(self, prompt: str) -> None:
        normalized_prompt = prompt.casefold()
        if any(
            value.casefold() in normalized_prompt for value in self._forbidden_values
        ):
            raise IntegrationSafetyError("PII preflight control failed")
        _, passages = parse_prompt(prompt)
        if not passages:
            raise IntegrationSafetyError("No authorized passage was provided")
        for passage in passages:
            document_id = passage.get("document_id")
            chunk_id = passage.get("chunk_id")
            if (
                document_id not in self._allowed_document_ids
                or chunk_id not in self._allowed_chunk_ids
            ):
                raise IntegrationSafetyError("Unauthorized passage detected")


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an explicitly authorized real-OpenAI RAG integration."
    )
    parser.add_argument(ALLOW_REAL_CALL_FLAG, action="store_true")
    return parser.parse_args(list(argv) if argv is not None else None)


def load_authorized_corpus(corpus_path: Path) -> RagCorpus:
    if corpus_path.resolve() != CORPUS_PATH.resolve():
        raise IntegrationSafetyError("Unauthorized corpus path")
    corpus_bytes = corpus_path.read_bytes()
    if hashlib.sha256(corpus_bytes).hexdigest() != EXPECTED_CORPUS_SHA256:
        raise IntegrationSafetyError("Unauthorized corpus content")
    corpus = load_rag_corpus(corpus_path)
    document_ids = {document.id for document in corpus.documents}
    if document_ids != EXPECTED_DOCUMENT_IDS:
        raise IntegrationSafetyError("Unauthorized corpus documents")
    return corpus


def reset_openai_integration_collection(
    client: QdrantClient,
    collection_name: str,
) -> None:
    if collection_name != OPENAI_INTEGRATION_COLLECTION_NAME:
        raise IntegrationSafetyError("Refusing to reset a foreign collection")
    if client.collection_exists(collection_name):
        client.delete_collection(collection_name=collection_name)


def create_openai_integration(
    settings: Settings,
    client_factory: OpenAIClientFactory = OpenAI,
) -> PreparedOpenAIIntegration:
    corpus = load_authorized_corpus(CORPUS_PATH)
    chunks = create_rag_chunks(corpus)
    embedding_service = LocalEmbeddingService()
    pii_masker = PiiMasker()
    client = QdrantClient(url=settings.qdrant_url)
    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        collection_name=OPENAI_INTEGRATION_COLLECTION_NAME,
        client=client,
    )
    embeddings = embedding_service.embed_chunks(chunks)
    reset_openai_integration_collection(client, OPENAI_INTEGRATION_COLLECTION_NAME)
    vector_store.store_chunks(chunks, embeddings)
    openai_service = create_smoke_service(settings, client_factory)
    llm_guard = PreflightLLMService(
        delegate=openai_service,
        allowed_document_ids=frozenset(chunk.document_id for chunk in chunks),
        allowed_chunk_ids=frozenset(chunk.id for chunk in chunks),
        forbidden_values=KNOWN_SYNTHETIC_PII,
    )
    retriever = HybridRetriever(
        bm25_retriever=BM25Retriever(chunks),
        embedding_service=embedding_service,
        vector_retriever=vector_store,
    )
    service = RagGenerationService(
        retriever=retriever,
        llm_service=llm_guard,
        pii_masker=pii_masker,
        top_k=TOP_K,
    )
    return PreparedOpenAIIntegration(service=service, llm_guard=llm_guard)


def assert_cited_result(result: RagGenerationResult) -> None:
    if result.abstained or not result.answer.strip():
        raise IntegrationSafetyError("Expected a non-abstained answer")
    if not result.sources or not result.citations:
        raise IntegrationSafetyError("Expected sources and citations")
    source_ids = {source.id for source in result.sources}
    if any(citation.chunk_id not in source_ids for citation in result.citations):
        raise IntegrationSafetyError("Citation does not reference a returned source")


def run_scenarios(
    prepared: PreparedOpenAIIntegration,
) -> tuple[RagGenerationResult, RagGenerationResult]:
    factual = prepared.service.generate(FACTUAL_QUESTION)
    assert_cited_result(factual)
    abstention = prepared.service.generate(ABSTENTION_QUESTION)
    if not abstention.abstained or abstention.citations:
        raise IntegrationSafetyError("Expected an explicit abstention")
    if prepared.llm_guard.call_count > MAX_OPENAI_CALLS:
        raise IntegrationSafetyError("OpenAI call budget exceeded")
    return factual, abstention


def main(
    argv: Sequence[str] | None = None,
    settings_factory: Callable[[], Settings] = Settings,
    integration_factory: Callable[[Settings], PreparedOpenAIIntegration] = (
        create_openai_integration
    ),
) -> int:
    arguments = parse_arguments(argv)
    if not arguments.allow_real_openai_call:
        print(
            "OpenAI RAG integration disabled. "
            f"Use {ALLOW_REAL_CALL_FLAG} to authorize up to two real calls."
        )
        return 0

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        settings = settings_factory()
        if settings.llm_api_key is None:
            raise IntegrationSafetyError("OpenAI configuration is unavailable")
        prepared = integration_factory(settings)
        run_scenarios(prepared)
    except (
        FileNotFoundError,
        IntegrationSafetyError,
        LLMServiceError,
        OSError,
        QdrantVectorStoreError,
        RagGenerationResponseError,
        RagPiiProtectionError,
        ResponseHandlingException,
        ValueError,
    ):
        print("OpenAI RAG integration failed.")
        return 1

    print("Scenario A validated: cited factual answer.")
    print("Scenario B validated: documentary abstention.")
    print(f"OpenAI calls: {prepared.llm_guard.call_count}/{MAX_OPENAI_CALLS} maximum.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
