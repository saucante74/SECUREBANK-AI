from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.evaluation import EvaluationCase
from app.services.benchmark_dataset import BenchmarkDatasetV2

QWEN_V2_JUDGMENTS_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "rag_annotation_judgments_llm_v2_full.json"
)
V2_ANNOTATION_POOL_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "rag_annotation_pool_v2.json"
)
QWEN_V2_JUDGMENT_COUNT = 260


class JudgmentMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provenance: Literal["llm_judge"]
    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    corpus_version: Literal["v2"]
    source_schema_version: Literal[3]
    corpus_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    updated_at: datetime


class RelevanceJudgment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    relevance: Literal[0, 1, 2]
    reason: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)


class QwenJudgmentSet(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1]
    metadata: JudgmentMetadata
    judgments: tuple[RelevanceJudgment, ...] = Field(
        min_length=QWEN_V2_JUDGMENT_COUNT,
        max_length=QWEN_V2_JUDGMENT_COUNT,
    )


class PoolCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    chunk_id: str = Field(min_length=1)


class PoolQuestion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    question_id: str = Field(min_length=1)
    candidates: tuple[PoolCandidate, ...]


class AnnotationPoolStructure(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    schema_version: Literal[3]
    questions: tuple[PoolQuestion, ...]


def load_qwen_evaluation_cases(
    dataset: BenchmarkDatasetV2,
    corpus_chunk_ids: set[str],
    corpus_fingerprint: str,
    judgments_path: Path = QWEN_V2_JUDGMENTS_PATH,
    pool_path: Path = V2_ANNOTATION_POOL_PATH,
) -> tuple[EvaluationCase, ...]:
    judgment_set = QwenJudgmentSet.model_validate_json(
        judgments_path.read_text(encoding="utf-8")
    )
    if judgment_set.metadata.corpus_fingerprint != corpus_fingerprint:
        raise ValueError("Qwen judgments do not match the v2 corpus fingerprint")
    questions_by_id = {
        question.id: question for question in dataset.reference_questions
    }
    judgment_pairs = [
        (judgment.question_id, judgment.chunk_id) for judgment in judgment_set.judgments
    ]
    if len(judgment_pairs) != len(set(judgment_pairs)):
        raise ValueError("Qwen judgments contain duplicate question/chunk pairs")
    pool = AnnotationPoolStructure.model_validate_json(
        pool_path.read_text(encoding="utf-8")
    )
    pool_pairs = {
        (question.question_id, candidate.chunk_id)
        for question in pool.questions
        for candidate in question.candidates
    }
    if set(judgment_pairs) != pool_pairs:
        raise ValueError(
            "Qwen judgment pairs do not exactly match the v2 annotation pool"
        )
    if not {question_id for question_id, _ in judgment_pairs} <= questions_by_id.keys():
        raise ValueError("Qwen judgments reference unknown benchmark questions")
    if not {chunk_id for _, chunk_id in judgment_pairs} <= corpus_chunk_ids:
        raise ValueError("Qwen judgments reference unknown benchmark chunks")
    judgments_by_question: dict[str, list[RelevanceJudgment]] = {}
    for judgment in judgment_set.judgments:
        judgments_by_question.setdefault(judgment.question_id, []).append(judgment)
    cases: list[EvaluationCase] = []
    for question in dataset.reference_questions:
        positive_chunk_ids = {
            judgment.chunk_id
            for judgment in judgments_by_question.get(question.id, ())
            if judgment.relevance > 0
        }
        if not positive_chunk_ids:
            continue
        cases.append(
            EvaluationCase(
                id=question.id,
                question=question.question,
                difficulty=question.difficulty,
                rationale=question.rationale,
                expected_chunk_ids=positive_chunk_ids,
                expected_document_ids={
                    chunk_id.split(":structured-chunk:", maxsplit=1)[0]
                    for chunk_id in positive_chunk_ids
                },
            )
        )
    return tuple(cases)
