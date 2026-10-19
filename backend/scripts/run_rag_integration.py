import json
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException

from app.core.config import settings
from app.schemas.documents import Chunk
from app.schemas.rag_generation import RagGenerationResult
from app.services.bm25 import BM25Retriever
from app.services.embeddings import LocalEmbeddingService
from app.services.hybrid import HybridRetriever
from app.services.pii_masking import PiiMasker
from app.services.qdrant import QdrantVectorStore, QdrantVectorStoreError
from app.services.rag_corpus import create_rag_chunks, load_rag_corpus
from app.services.rag_generation import RagGenerationService, RagPiiProtectionError

BACKEND_DIR = Path(__file__).resolve().parents[1]
CORPUS_PATH = BACKEND_DIR / "data" / "rag_integration_corpus.json"
DEMO_COLLECTION_NAME = "securebank_rag_integration_chunks"
TOP_K = 3
QUESTION_EMAIL = "client.integration@example.com"
PASSAGE_EMAIL = "conseiller.integration@example.com"
ANSWER_EMAIL = "reponse.integration@example.com"
QUESTION_MARKER = "[EMAIL_ADDRESS]"
QUESTION_LABEL = "Question masquée"
PASSAGES_MARKER = "Passages récupérés (JSON):\n"

type PointCounter = Callable[[], int]
type CollectionResetter = Callable[[], None]


@dataclass(frozen=True)
class PreparedIntegration:
    chunks: list[Chunk]
    embeddings: list[list[float]]
    service: RagGenerationService
    llm: "FakeLLM"
    point_count: int


class IntegrationAssertionError(RuntimeError):
    pass


class PiiControlError(RuntimeError):
    pass


class FakeLLM:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must contain non-whitespace characters")
        self.prompts.append(prompt)
        question, passages = parse_prompt(prompt)
        rules = (
            (
                "plafond quotidien",
                "25000 CHF",
                "Le plafond quotidien fictif est de 25000 CHF",
            ),
            (
                "délai de traitement",
                "cinq jours ouvrés",
                "Le délai indicatif est de cinq jours ouvrés",
            ),
            (
                "coordonnées du conseiller",
                QUESTION_MARKER,
                f"Le conseiller répond à {ANSWER_EMAIL}",
            ),
        )
        for question_term, evidence_term, answer in rules:
            if question_term not in question.casefold():
                continue
            reference = find_passage_reference(passages, evidence_term)
            if reference is not None:
                return json.dumps(
                    {
                        "answer": f"{answer} [{reference}].",
                        "abstained": False,
                    },
                    ensure_ascii=False,
                )
        return json.dumps(
            {
                "answer": "Les passages fournis ne permettent pas de répondre.",
                "abstained": True,
            },
            ensure_ascii=False,
        )


def parse_prompt(prompt: str) -> tuple[str, list[dict[str, object]]]:
    question_prefix = "Question utilisateur:\n"
    question_start = prompt.index(question_prefix) + len(question_prefix)
    passages_start = prompt.index(PASSAGES_MARKER, question_start)
    question = prompt[question_start : passages_start - 2]
    passages = json.loads(prompt[passages_start + len(PASSAGES_MARKER) :])
    if not isinstance(passages, list) or not all(
        isinstance(passage, dict) for passage in passages
    ):
        raise ValueError("prompt passages must be a list of objects")
    return question, passages


def find_passage_reference(
    passages: Sequence[dict[str, object]],
    evidence_term: str,
) -> int | None:
    for passage in passages:
        content = passage.get("content")
        reference = passage.get("passage")
        if (
            isinstance(content, str)
            and evidence_term.casefold() in content.casefold()
            and isinstance(reference, int)
            and not isinstance(reference, bool)
        ):
            return reference
    return None


def prepare_integration(
    corpus_path: Path,
    embedding_service: LocalEmbeddingService,
    vector_store: QdrantVectorStore,
    pii_masker: PiiMasker,
    reset_collection: CollectionResetter,
    count_points: PointCounter,
) -> PreparedIntegration:
    corpus = load_rag_corpus(corpus_path)
    chunks = create_rag_chunks(corpus)
    embeddings = embedding_service.embed_chunks(chunks)
    reset_collection()
    vector_store.store_chunks(chunks, embeddings)
    point_count = count_points()
    if point_count != len(chunks):
        raise IntegrationAssertionError("Qdrant point count does not match the corpus")
    llm = FakeLLM()
    retriever = HybridRetriever(
        bm25_retriever=BM25Retriever(chunks),
        embedding_service=embedding_service,
        vector_retriever=vector_store,
    )
    service = RagGenerationService(
        retriever=retriever,
        llm_service=llm,
        pii_masker=pii_masker,
        top_k=TOP_K,
    )
    return PreparedIntegration(chunks, embeddings, service, llm, point_count)


def reset_demo_collection(client: QdrantClient, collection_name: str) -> None:
    if collection_name != DEMO_COLLECTION_NAME:
        raise ValueError("refusing to reset a non-demonstration collection")
    if client.collection_exists(collection_name):
        client.delete_collection(collection_name=collection_name)


def assert_positive_result(result: RagGenerationResult) -> None:
    if result.abstained or not result.citations or not result.sources:
        raise IntegrationAssertionError("expected a cited answer")
    source_ids = {source.id for source in result.sources}
    if any(citation.chunk_id not in source_ids for citation in result.citations):
        raise IntegrationAssertionError("citation does not reference a returned source")


def assert_absent(value: str, texts: Sequence[str]) -> None:
    if any(value in text for text in texts):
        raise PiiControlError("PII control failed")


def run_scenarios(prepared: PreparedIntegration) -> list[RagGenerationResult]:
    factual = prepared.service.generate(
        "Quel est le plafond quotidien fictif des virements en ligne ?"
    )
    assert_positive_result(factual)
    if "25000 CHF" not in factual.answer:
        raise IntegrationAssertionError("factual answer is incomplete")

    pii_question = prepared.service.generate(
        f"Quel est le délai de traitement pour {QUESTION_EMAIL} ?"
    )
    assert_positive_result(pii_question)
    if QUESTION_MARKER not in pii_question.question:
        raise PiiControlError("PII control failed")
    assert_absent(
        QUESTION_EMAIL,
        [pii_question.model_dump_json(), prepared.llm.prompts[-1]],
    )

    pii_passage = prepared.service.generate(
        "Quelles sont les coordonnées du conseiller ?"
    )
    assert_positive_result(pii_passage)
    serialized_result = pii_passage.model_dump_json()
    prompt = prepared.llm.prompts[-1]
    assert_absent(PASSAGE_EMAIL, [prompt, serialized_result])
    assert_absent(ANSWER_EMAIL, [serialized_result])
    if QUESTION_MARKER not in prompt or QUESTION_MARKER not in pii_passage.answer:
        raise PiiControlError("PII control failed")
    cited_references = [citation.reference for citation in pii_passage.citations]
    if any(
        f"[{reference}]" not in pii_passage.answer for reference in cited_references
    ):
        raise IntegrationAssertionError("PII masking did not preserve the citation")

    abstention = prepared.service.generate(
        "Quel est le plafond d'une carte de débit extraterrestre ?"
    )
    if not abstention.abstained or abstention.citations:
        raise IntegrationAssertionError("expected an explicit abstention")
    return [factual, pii_question, pii_passage, abstention]


def print_results(results: Sequence[RagGenerationResult]) -> None:
    for index, result in enumerate(results, start=1):
        print(f"\nScénario {index}")
        print(f"{QUESTION_LABEL}: {result.question}")
        print(f"Réponse masquée: {result.answer}")
        print(f"Abstention: {result.abstained}")
        print(
            "Citations: "
            + (
                ", ".join(
                    f"[{citation.reference}] {citation.chunk_id}"
                    for citation in result.citations
                )
                or "aucune"
            )
        )
        print(f"Sources masquées: {len(result.sources)}")


def create_local_integration() -> tuple[
    PreparedIntegration, QdrantVectorStore, PointCounter
]:
    client = QdrantClient(url=settings.qdrant_url)
    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        collection_name=DEMO_COLLECTION_NAME,
        client=client,
    )

    def counter() -> int:
        return client.count(
            collection_name=DEMO_COLLECTION_NAME,
            exact=True,
        ).count

    prepared = prepare_integration(
        corpus_path=CORPUS_PATH,
        embedding_service=LocalEmbeddingService(),
        vector_store=vector_store,
        pii_masker=PiiMasker(),
        reset_collection=lambda: reset_demo_collection(
            client,
            DEMO_COLLECTION_NAME,
        ),
        count_points=counter,
    )
    return prepared, vector_store, counter


def main() -> int:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        prepared, vector_store, count_points = create_local_integration()
        results = run_scenarios(prepared)
        before_reindex = prepared.point_count
        vector_store.store_chunks(
            prepared.chunks,
            prepared.embeddings,
        )
        after_reindex = count_points()
        if before_reindex != after_reindex:
            raise IntegrationAssertionError(
                "Qdrant point count changed after reindexing"
            )
        print_results(results)
        print(f"\nCollection Qdrant: {DEMO_COLLECTION_NAME}")
        print(f"Points avant réexécution: {before_reindex}")
        print(f"Points après réexécution: {after_reindex}")
    except PiiControlError:
        print("Échec générique du contrôle PII.")
        return 1
    except RagPiiProtectionError:
        print("Protection PII indisponible.")
        return 1
    except IntegrationAssertionError:
        print("Échec générique d'une assertion d'intégration.")
        return 1
    except FileNotFoundError:
        print("Une ressource locale requise est indisponible.")
        return 1
    except (QdrantVectorStoreError, ResponseHandlingException):
        print("Qdrant est indisponible pour le test d'intégration.")
        return 1
    except (OSError, RuntimeError, ValueError):
        print("Le test d'intégration local n'a pas pu être exécuté.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
