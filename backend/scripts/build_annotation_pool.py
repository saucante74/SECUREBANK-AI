import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.documents import Chunk
from app.schemas.evaluation import EvaluationCase
from app.schemas.retrieval import RetrievalResult
from scripts.compare_retrievers import (
    ENGINE_NAMES,
    TOP_K,
    compare_retrievers,
    create_local_comparison,
)

DEFAULT_OUTPUT_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "rag_annotation_pool.json"
)

type RelevanceJudgment = Literal[0, 1, 2] | None


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
    relevance: RelevanceJudgment = None
    retrieved_by: tuple[RetrievalProvenance, ...] = ()
    included_from_existing_positive: bool = False


class QuestionAnnotation(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    candidates: tuple[CandidateAnnotation, ...]


class AnnotationPool(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal[1, 2] = 2
    unjudged_policy: Literal["null_is_unjudged"] = "null_is_unjudged"
    judgment_scale: dict[str, str] = Field(
        default_factory=lambda: {
            "0": "not_relevant",
            "1": "relevant",
            "2": "highly_relevant",
        }
    )
    questions: tuple[QuestionAnnotation, ...]


def build_question_candidates(
    case: EvaluationCase,
    comparisons: Mapping[str, ComparisonResults],
    benchmark_chunks_by_id: Mapping[str, Chunk],
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
            retrieved_by=tuple(provenance_by_chunk_id.get(chunk.id, ())),
            included_from_existing_positive=chunk.id not in retrieved_chunk_ids,
        )
        for chunk in chunks_by_id.values()
    )


def build_annotation_pool(
    cases: Sequence[EvaluationCase],
    comparisons: Mapping[str, ComparisonResults],
    benchmark_chunks: Sequence[Chunk],
) -> AnnotationPool:
    if tuple(comparisons) != ENGINE_NAMES:
        raise ValueError("annotation pooling requires the four configured retrievers")
    benchmark_chunks_by_id = {chunk.id: chunk for chunk in benchmark_chunks}
    return AnnotationPool(
        questions=tuple(
            QuestionAnnotation(
                question_id=case.id,
                question=case.question,
                candidates=build_question_candidates(
                    case,
                    comparisons,
                    benchmark_chunks_by_id,
                ),
            )
            for case in cases
        )
    )


def save_annotation_pool(pool: AnnotationPool, output_path: Path) -> None:
    with output_path.open("x", encoding="utf-8") as output_file:
        output_file.write(pool.model_dump_json(indent=2) + "\n")


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args(arguments)


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
    pipeline = create_local_comparison(index_chunks=False)
    comparisons = compare_retrievers(pipeline)
    pool = build_annotation_pool(pipeline.cases, comparisons, pipeline.chunks)
    save_annotation_pool(pool, parsed_arguments.output)
    print(f"Annotation pool saved: {parsed_arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
