import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.documents import Chunk
from app.schemas.evaluation import EvaluationCase, UnannotatedBenchmarkQuestion
from app.schemas.retrieval import RetrievalResult
from scripts.compare_retrievers import (
    BENCHMARK_V2_COLLECTION_NAME,
    ENGINE_NAMES,
    TOP_K,
    compare_retrievers,
    corpus_fingerprint,
    create_local_comparison,
)

DEFAULT_OUTPUT_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "rag_annotation_pool.json"
)
V2_OUTPUT_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "rag_annotation_pool_v2.json"
)

type RelevanceJudgment = Literal[0, 1, 2] | None
type AnnotationQuestion = EvaluationCase | UnannotatedBenchmarkQuestion


class ComparisonResults(Protocol):
    results_by_case_id: Mapping[str, Sequence[RetrievalResult]]


class RetrievalProvenance(BaseModel):
    model_config = ConfigDict(frozen=True)

    engine: Literal["BM25", "Qdrant", "RRF", "RRF + FlashRank"]
    rank: int = Field(ge=1, le=TOP_K)


class CandidateAnnotation(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source: str | None = Field(default=None, exclude_if=lambda value: value is None)
    relevance: RelevanceJudgment = None
    retrieved_by: tuple[RetrievalProvenance, ...] = ()
    included_from_existing_positive: bool = False


class QuestionAnnotation(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    candidates: tuple[CandidateAnnotation, ...]


class AnnotationPoolMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    corpus_version: Literal["v2"]
    chunker: Literal["structured"]
    chunk_size: Literal[500]
    chunk_overlap: Literal[75]
    qdrant_collection: Literal["securebank_benchmark_chunks_v2"]
    corpus_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class AnnotationPool(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal[1, 2, 3] = 2
    unjudged_policy: Literal["null_is_unjudged"] = "null_is_unjudged"
    judgment_scale: dict[str, str] = Field(
        default_factory=lambda: {
            "0": "not_relevant",
            "1": "relevant",
            "2": "highly_relevant",
        }
    )
    metadata: AnnotationPoolMetadata | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    questions: tuple[QuestionAnnotation, ...]


def build_question_candidates(
    case: AnnotationQuestion,
    comparisons: Mapping[str, ComparisonResults],
    benchmark_chunks_by_id: Mapping[str, Chunk],
    include_existing_positives: bool,
    include_source: bool,
) -> tuple[CandidateAnnotation, ...]:
    chunks_by_id: dict[str, Chunk] = {}
    provenance_by_chunk_id: dict[str, list[RetrievalProvenance]] = {}
    for engine_name in ENGINE_NAMES:
        results = comparisons[engine_name].results_by_case_id[case.id][:TOP_K]
        for rank, result in enumerate(results, start=1):
            existing_chunk = chunks_by_id.get(result.chunk.id)
            if existing_chunk is not None and existing_chunk != result.chunk:
                raise ValueError(f"inconsistent metadata for chunk {result.chunk.id!r}")
            chunks_by_id.setdefault(result.chunk.id, result.chunk)
            provenance_by_chunk_id.setdefault(result.chunk.id, []).append(
                RetrievalProvenance(engine=engine_name, rank=rank)
            )
    retrieved_chunk_ids = frozenset(chunks_by_id)
    if include_existing_positives:
        if not isinstance(case, EvaluationCase):
            raise ValueError("existing positives require annotated evaluation cases")
        for chunk_id in sorted(case.expected_chunk_ids - retrieved_chunk_ids):
            try:
                chunks_by_id[chunk_id] = benchmark_chunks_by_id[chunk_id]
            except KeyError:
                raise ValueError(f"unknown positive chunk {chunk_id!r}") from None
    return tuple(
        CandidateAnnotation(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            text=chunk.content,
            source=chunk.source if include_source else None,
            retrieved_by=tuple(provenance_by_chunk_id.get(chunk.id, ())),
            included_from_existing_positive=(
                include_existing_positives and chunk.id not in retrieved_chunk_ids
            ),
        )
        for chunk in chunks_by_id.values()
    )


def build_annotation_pool(
    cases: Sequence[AnnotationQuestion],
    comparisons: Mapping[str, ComparisonResults],
    benchmark_chunks: Sequence[Chunk],
    metadata: AnnotationPoolMetadata | None = None,
) -> AnnotationPool:
    if tuple(comparisons) != ENGINE_NAMES:
        raise ValueError("annotation pooling requires the four configured retrievers")
    benchmark_chunks_by_id = {chunk.id: chunk for chunk in benchmark_chunks}
    is_v2 = metadata is not None
    return AnnotationPool(
        schema_version=3 if is_v2 else 2,
        metadata=metadata,
        questions=tuple(
            QuestionAnnotation(
                question_id=case.id,
                question=case.question,
                candidates=build_question_candidates(
                    case,
                    comparisons,
                    benchmark_chunks_by_id,
                    include_existing_positives=not is_v2,
                    include_source=is_v2,
                ),
            )
            for case in cases
        ),
    )


def save_annotation_pool(pool: AnnotationPool, output_path: Path) -> None:
    with output_path.open("x", encoding="utf-8") as output_file:
        output_file.write(pool.model_dump_json(indent=2) + "\n")


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-version", choices=("v1", "v2"), default="v1")
    parser.add_argument("--output", type=Path)
    parsed_arguments = parser.parse_args(arguments)
    if parsed_arguments.output is None:
        parsed_arguments.output = (
            V2_OUTPUT_PATH
            if parsed_arguments.corpus_version == "v2"
            else DEFAULT_OUTPUT_PATH
        )
    return parsed_arguments


def main(arguments: Sequence[str] | None = None) -> int:
    parsed_arguments = parse_arguments(arguments)
    if parsed_arguments.output.exists():
        print(
            f"Annotation pool already exists: {parsed_arguments.output}",
            file=sys.stderr,
        )
        return 1
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    pipeline = create_local_comparison(
        index_chunks=False,
        corpus_version=parsed_arguments.corpus_version,
    )
    comparisons = compare_retrievers(pipeline)
    metadata = (
        AnnotationPoolMetadata(
            corpus_version="v2",
            chunker="structured",
            chunk_size=500,
            chunk_overlap=75,
            qdrant_collection=BENCHMARK_V2_COLLECTION_NAME,
            corpus_fingerprint=corpus_fingerprint(
                pipeline.chunks,
                pipeline.metadata,
            ),
        )
        if parsed_arguments.corpus_version == "v2"
        else None
    )
    pool = build_annotation_pool(
        pipeline.cases,
        comparisons,
        pipeline.chunks,
        metadata=metadata,
    )
    save_annotation_pool(pool, parsed_arguments.output)
    print(f"Annotation pool saved: {parsed_arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
