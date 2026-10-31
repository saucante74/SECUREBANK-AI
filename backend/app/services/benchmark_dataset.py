from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.documents import Chunk, Document
from app.schemas.evaluation import EvaluationCase, UnannotatedBenchmarkQuestion
from app.services.chunking import CharacterChunker, StructuredChunker

BENCHMARK_DATA_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "rag_benchmark.json"
)
BENCHMARK_COLLECTION_NAME = "securebank_benchmark_chunks"
BENCHMARK_CHUNK_SIZE = 180
BENCHMARK_CHUNK_OVERLAP = 30
BENCHMARK_V2_DATA_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "rag_benchmark_v2.json"
)
BENCHMARK_V2_CHUNK_SIZE = 500
BENCHMARK_V2_CHUNK_OVERLAP = 75


class BenchmarkDatasetMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    corpus_version: Literal["v1", "v2"]
    chunker: Literal["character", "structured"]
    chunk_size: int = Field(gt=0)
    chunk_overlap: int = Field(ge=0)
    relevance_annotations: bool


def create_v1_metadata() -> BenchmarkDatasetMetadata:
    return BenchmarkDatasetMetadata(
        corpus_version="v1",
        chunker="character",
        chunk_size=BENCHMARK_CHUNK_SIZE,
        chunk_overlap=BENCHMARK_CHUNK_OVERLAP,
        relevance_annotations=True,
    )


def create_v2_metadata() -> BenchmarkDatasetMetadata:
    return BenchmarkDatasetMetadata(
        corpus_version="v2",
        chunker="structured",
        chunk_size=BENCHMARK_V2_CHUNK_SIZE,
        chunk_overlap=BENCHMARK_V2_CHUNK_OVERLAP,
        relevance_annotations=False,
    )


class BenchmarkDataset(BaseModel):
    model_config = ConfigDict(frozen=True)

    documents: tuple[Document, ...] = Field(min_length=1)
    cases: tuple[EvaluationCase, ...] = Field(min_length=1)
    metadata: BenchmarkDatasetMetadata = Field(default_factory=create_v1_metadata)


class BenchmarkDatasetV2(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal[2]
    source_dataset: str
    annotation_status: Literal["unannotated"]
    documents: tuple[Document, ...] = Field(min_length=1)
    reference_questions: tuple[UnannotatedBenchmarkQuestion, ...] = Field(min_length=1)
    metadata: BenchmarkDatasetMetadata = Field(default_factory=create_v2_metadata)


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


def create_benchmark_v2_chunks(
    documents: tuple[Document, ...],
) -> list[Chunk]:
    chunker = StructuredChunker(
        chunk_size=BENCHMARK_V2_CHUNK_SIZE,
        overlap=BENCHMARK_V2_CHUNK_OVERLAP,
    )
    return [chunk for document in documents for chunk in chunker.chunk(document)]


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


def validate_benchmark_dataset_v2(dataset: BenchmarkDatasetV2) -> None:
    if len(dataset.documents) != 30:
        raise ValueError("benchmark v2 must contain exactly 30 documents")
    if len(dataset.reference_questions) != 40:
        raise ValueError("benchmark v2 must contain exactly 40 questions")
    document_ids = [document.id for document in dataset.documents]
    question_ids = [question.id for question in dataset.reference_questions]
    if len(document_ids) != len(set(document_ids)):
        raise ValueError("benchmark v2 document identifiers must be unique")
    if len(question_ids) != len(set(question_ids)):
        raise ValueError("benchmark v2 question identifiers must be unique")
    chunks = create_benchmark_v2_chunks(dataset.documents)
    if len({chunk.id for chunk in chunks}) != len(chunks):
        raise ValueError("benchmark v2 chunk identifiers must be unique")


def load_benchmark_dataset_v2(
    path: Path = BENCHMARK_V2_DATA_PATH,
) -> BenchmarkDatasetV2:
    dataset = BenchmarkDatasetV2.model_validate_json(path.read_text(encoding="utf-8"))
    validate_benchmark_dataset_v2(dataset)
    return dataset
