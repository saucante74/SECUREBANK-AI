import argparse
import os
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


class CandidateAnnotation(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    relevance: RelevanceJudgment = None


class QuestionAnnotation(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    candidates: tuple[CandidateAnnotation, ...]


class AnnotationPool(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal[1] = 1
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
) -> tuple[CandidateAnnotation, ...]:
    chunks_by_id: dict[str, Chunk] = {}
    for engine_name in ENGINE_NAMES:
        results = comparisons[engine_name].results_by_case_id[case.id][:TOP_K]
        for result in results:
            existing_chunk = chunks_by_id.get(result.chunk.id)
            if existing_chunk is not None and existing_chunk != result.chunk:
                raise ValueError(f"inconsistent metadata for chunk {result.chunk.id!r}")
            chunks_by_id.setdefault(result.chunk.id, result.chunk)
    return tuple(
        CandidateAnnotation(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            text=chunk.content,
        )
        for chunk in chunks_by_id.values()
    )


def build_annotation_pool(
    cases: Sequence[EvaluationCase],
    comparisons: Mapping[str, ComparisonResults],
) -> AnnotationPool:
    if tuple(comparisons) != ENGINE_NAMES:
        raise ValueError("annotation pooling requires the four configured retrievers")
    return AnnotationPool(
        questions=tuple(
            QuestionAnnotation(
                question_id=case.id,
                question=case.question,
                candidates=build_question_candidates(case, comparisons),
            )
            for case in cases
        )
    )


def save_annotation_pool(pool: AnnotationPool, output_path: Path) -> None:
    with output_path.open("x", encoding="utf-8") as output_file:
        output_file.write(pool.model_dump_json(indent=2) + "\n")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    pipeline = create_local_comparison(index_chunks=False)
    comparisons = compare_retrievers(pipeline)
    pool = build_annotation_pool(pipeline.cases, comparisons)
    save_annotation_pool(pool, arguments.output)
    print(f"Annotation pool saved: {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
