from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.documents import Chunk, Document
from app.schemas.evaluation import EvaluationCase
from app.services.chunking import CharacterChunker

BENCHMARK_DATA_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "rag_benchmark.json"
)
BENCHMARK_COLLECTION_NAME = "securebank_benchmark_chunks"
BENCHMARK_CHUNK_SIZE = 180
BENCHMARK_CHUNK_OVERLAP = 30


class BenchmarkDataset(BaseModel):
    model_config = ConfigDict(frozen=True)

    documents: tuple[Document, ...] = Field(min_length=1)
    cases: tuple[EvaluationCase, ...] = Field(min_length=1)


def create_benchmark_chunks(
    documents: tuple[Document, ...],
    chunker: CharacterChunker | None = None,
) -> list[Chunk]:
    selected_chunker = chunker or CharacterChunker(
        chunk_size=BENCHMARK_CHUNK_SIZE,
        overlap=BENCHMARK_CHUNK_OVERLAP,
    )
    return [
        chunk for document in documents for chunk in selected_chunker.chunk(document)
    ]


def validate_benchmark_dataset(dataset: BenchmarkDataset) -> None:
    if len(dataset.documents) != 30:
        raise ValueError("benchmark must contain exactly 30 documents")
    if len(dataset.cases) != 40:
        raise ValueError("benchmark must contain exactly 40 cases")
    document_ids = [document.id for document in dataset.documents]
    case_ids = [case.id for case in dataset.cases]
    if len(document_ids) != len(set(document_ids)):
        raise ValueError("benchmark document identifiers must be unique")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("benchmark case identifiers must be unique")
    chunks = create_benchmark_chunks(dataset.documents)
    chunks_by_id = {chunk.id: chunk for chunk in chunks}
    if len(chunks_by_id) != len(chunks):
        raise ValueError("benchmark chunk identifiers must be unique")
    known_document_ids = set(document_ids)
    for case in dataset.cases:
        if case.difficulty is None or case.rationale is None:
            raise ValueError(f"incomplete benchmark case {case.id!r}")
        if not case.expected_document_ids <= known_document_ids:
            raise ValueError(f"unknown document reference in case {case.id!r}")
        if not case.expected_chunk_ids <= chunks_by_id.keys():
            raise ValueError(f"unknown chunk reference in case {case.id!r}")
        evidence_document_ids = {
            chunks_by_id[chunk_id].document_id for chunk_id in case.expected_chunk_ids
        }
        if not evidence_document_ids <= case.expected_document_ids:
            raise ValueError(f"inconsistent evidence reference in case {case.id!r}")


def load_benchmark_dataset(
    path: Path = BENCHMARK_DATA_PATH,
) -> BenchmarkDataset:
    dataset = BenchmarkDataset.model_validate_json(path.read_text(encoding="utf-8"))
    validate_benchmark_dataset(dataset)
    return dataset
