import os
from collections.abc import Callable

from app.core.config import settings
from app.schemas.documents import Chunk, Document
from app.schemas.retrieval import RetrievalResult
from app.services.chunking import CharacterChunker
from app.services.embeddings import LocalEmbeddingService
from app.services.qdrant import QdrantVectorStore, QdrantVectorStoreError

QUESTION = "Comment financer l'achat d'un logement ?"


def create_documents() -> list[Document]:
    return [
        Document(
            id="demo-credit-immobilier",
            title="Guide du crédit immobilier",
            source="synthetic://credit-immobilier",
            content=(
                "Le crédit immobilier finance l'achat d'un logement. "
                "La banque examine les revenus, les charges, l'apport et la capacité "
                "de remboursement avant de proposer une durée et un taux."
            ),
        ),
        Document(
            id="demo-assurance-habitation",
            title="Guide de l'assurance habitation",
            source="synthetic://assurance-habitation",
            content=(
                "L'assurance habitation couvre notamment les dommages causés par un "
                "incendie, un dégât des eaux ou un vol selon les garanties du contrat. "
                "Les exclusions et franchises doivent être examinées."
            ),
        ),
        Document(
            id="demo-epargne",
            title="Guide de l'épargne",
            source="synthetic://epargne",
            content=(
                "Une solution d'épargne permet de constituer progressivement une "
                "réserve financière. Le rendement, le risque, les frais et la "
                "disponibilité des fonds varient selon le produit choisi."
            ),
        ),
    ]


def create_chunks(
    documents: list[Document],
    chunker: CharacterChunker,
) -> list[Chunk]:
    return [chunk for document in documents for chunk in chunker.chunk(document)]


def run_demo(
    chunker: CharacterChunker,
    embedding_service: LocalEmbeddingService,
    vector_store: QdrantVectorStore,
) -> list[RetrievalResult]:
    chunks = create_chunks(create_documents(), chunker)
    embeddings = embedding_service.embed_chunks(chunks)
    vector_store.ensure_collection()
    stored_count = vector_store.store_chunks(chunks, embeddings)
    query_vector = embedding_service.embed_text(QUESTION)
    results = vector_store.search(query_vector, top_k=3)
    print(f"Indexed chunks: {stored_count}")
    print(f"Question: {QUESTION}")
    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. score={result.score:.4f} | "
            f"{result.chunk.title} | {result.chunk.content}"
        )
    return results


def main(
    embedding_factory: Callable[[], LocalEmbeddingService] = LocalEmbeddingService,
    vector_store_factory: Callable[[], QdrantVectorStore] | None = None,
) -> int:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        embedding_service = embedding_factory()
    except (OSError, RuntimeError) as error:
        print(f"Local embedding model unavailable: {error}")
        return 1

    factory = vector_store_factory or (
        lambda: QdrantVectorStore.from_settings(settings)
    )
    try:
        run_demo(
            CharacterChunker(chunk_size=180, overlap=30),
            embedding_service,
            factory(),
        )
    except QdrantVectorStoreError as error:
        print(f"Qdrant operation failed: {error}")
        return 1
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Vector search demonstration failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
