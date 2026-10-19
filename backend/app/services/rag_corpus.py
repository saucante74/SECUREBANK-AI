from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.documents import Chunk, Document
from app.services.chunking import CharacterChunker

RAG_CHUNK_SIZE = 180
RAG_CHUNK_OVERLAP = 30


class RagCorpus(BaseModel):
    model_config = ConfigDict(frozen=True)

    documents: tuple[Document, ...] = Field(min_length=1)


def load_rag_corpus(path: Path) -> RagCorpus:
    return RagCorpus.model_validate_json(path.read_text(encoding="utf-8"))


def create_rag_chunks(corpus: RagCorpus) -> list[Chunk]:
    chunker = CharacterChunker(
        chunk_size=RAG_CHUNK_SIZE,
        overlap=RAG_CHUNK_OVERLAP,
    )
    return [chunk for document in corpus.documents for chunk in chunker.chunk(document)]
