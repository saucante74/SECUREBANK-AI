from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from math import fsum, log2
from typing import Literal

from app.schemas.evaluation import (
    CaseEvaluation,
    EvaluationCase,
    EvaluationReport,
)
from app.schemas.retrieval import RetrievalResult

type RelevanceGrade = Literal[0, 1, 2]


@dataclass(frozen=True)
class MetricResult:
    value: float | None
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        if (self.value is None) == (self.unavailable_reason is None):
            raise ValueError(
                "metric must contain either a value or an unavailable reason"
            )


@dataclass(frozen=True)
class QuestionIRMetrics:
    question_id: str
    k: int
    precision_at_k: MetricResult
    recall_at_k: MetricResult
    f1_at_k: MetricResult
    average_precision_at_k: MetricResult
    success_at_k: MetricResult
    reciprocal_rank_at_k: MetricResult
    ndcg_at_k: MetricResult


@dataclass(frozen=True)
class AggregatedMetric:
    value: float | None
    evaluated_question_count: int
    unavailable_question_count: int


@dataclass(frozen=True)
class IRMetricsReport:
    k: int
    questions: tuple[QuestionIRMetrics, ...]
    precision_at_k: AggregatedMetric
    recall_at_k: AggregatedMetric
    f1_at_k: AggregatedMetric
    map_at_k: AggregatedMetric
    success_at_k: AggregatedMetric
    mrr_at_k: AggregatedMetric
    ndcg_at_k: AggregatedMetric


SYNTHETIC_EVALUATION_CASES = (
    EvaluationCase(
        id="credit-financial-criteria",
        question=(
            "Quels revenus, charges et apport sont pris en compte pour un crédit "
            "immobilier ?"
        ),
        expected_document_ids={"demo-credit-immobilier"},
        expected_chunk_ids={"demo-credit-immobilier:chunk:0"},
    ),
    EvaluationCase(
        id="credit-semantic-reformulation",
        question=(
            "Quels éléments financiers la banque étudie-t-elle avant de financer "
            "un logement ?"
        ),
        expected_document_ids={"demo-credit-immobilier"},
        expected_chunk_ids={"demo-credit-immobilier:chunk:0"},
    ),
    EvaluationCase(
        id="insurance-covered-events",
        question="Quels sinistres peuvent être couverts par l'assurance habitation ?",
        expected_document_ids={"demo-assurance-habitation"},
        expected_chunk_ids={"demo-assurance-habitation:chunk:0"},
    ),
    EvaluationCase(
        id="insurance-contract-conditions",
        question=(
            "Que faut-il examiner dans le contrat concernant les exclusions et les "
            "franchises ?"
        ),
        expected_document_ids={"demo-assurance-habitation"},
        expected_chunk_ids={
            "demo-assurance-habitation:chunk:0",
            "demo-assurance-habitation:chunk:1",
        },
    ),
    EvaluationCase(
        id="savings-financial-reserve",
        question="Comment constituer progressivement une réserve financière ?",
        expected_document_ids={"demo-epargne"},
        expected_chunk_ids={"demo-epargne:chunk:0"},
    ),
    EvaluationCase(
        id="savings-semantic-reformulation",
        question=(
            "Quels critères distinguent les produits permettant de placer son épargne ?"
        ),
        expected_document_ids={"demo-epargne"},
        expected_chunk_ids={"demo-epargne:chunk:0"},
    ),
)


def validate_k(k: int) -> None:
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise ValueError("k must be a strictly positive integer")


def source_hit_at_k(
    results: Sequence[RetrievalResult],
    expected_document_ids: Collection[str],
    k: int,
) -> int:
    validate_k(k)
    return int(
        any(result.chunk.document_id in expected_document_ids for result in results[:k])
    )


def evidence_hit_at_k(
    results: Sequence[RetrievalResult],
    expected_chunk_ids: Collection[str],
    k: int,
) -> int:
    validate_k(k)
    return int(any(result.chunk.id in expected_chunk_ids for result in results[:k]))


def validate_relevance_judgments(
    judgments: Mapping[str, RelevanceGrade],
) -> None:
    for chunk_id, relevance in judgments.items():
        if not chunk_id.strip():
            raise ValueError("judgment chunk identifiers must not be blank")
        if relevance not in {0, 1, 2} or isinstance(relevance, bool):
            raise ValueError("relevance judgments must be 0, 1, or 2")


def available_metric(value: float) -> MetricResult:
    return MetricResult(value=value)


def unavailable_metric(reason: str) -> MetricResult:
    return MetricResult(value=None, unavailable_reason=reason)


def evaluate_ir_question(
    question_id: str,
    results: Sequence[RetrievalResult],
    judgments: Mapping[str, RelevanceGrade],
    k: int,
) -> QuestionIRMetrics:
    validate_k(k)
    validate_relevance_judgments(judgments)
    selected_results = results[:k]
    selected_chunk_ids = [result.chunk.id for result in selected_results]
    unjudged_chunk_ids = tuple(
        chunk_id for chunk_id in selected_chunk_ids if chunk_id not in judgments
    )
    if unjudged_chunk_ids:
        displayed_ids = ", ".join(dict.fromkeys(unjudged_chunk_ids))
        unavailable = unavailable_metric(
            f"unjudged result chunks at evaluated ranks: {displayed_ids}"
        )
        return QuestionIRMetrics(
            question_id=question_id,
            k=k,
            precision_at_k=unavailable,
            recall_at_k=unavailable,
            f1_at_k=unavailable,
            average_precision_at_k=unavailable,
            success_at_k=unavailable,
            reciprocal_rank_at_k=unavailable,
            ndcg_at_k=unavailable,
        )
    selected_relevances = [judgments[chunk_id] for chunk_id in selected_chunk_ids]
    binary_relevances = [int(relevance >= 1) for relevance in selected_relevances]
    known_positive_count = sum(relevance >= 1 for relevance in judgments.values())
    retrieved_positive_count = sum(binary_relevances)
    precision = retrieved_positive_count / k
    success = float(retrieved_positive_count > 0)
    reciprocal_rank = next(
        (
            1.0 / rank
            for rank, relevance in enumerate(binary_relevances, start=1)
            if relevance
        ),
        0.0,
    )
    precision_result = available_metric(precision)
    success_result = available_metric(success)
    reciprocal_rank_result = available_metric(reciprocal_rank)
    if known_positive_count == 0:
        no_positives = unavailable_metric(
            "no positive judgments are available for this question"
        )
        return QuestionIRMetrics(
            question_id=question_id,
            k=k,
            precision_at_k=precision_result,
            recall_at_k=no_positives,
            f1_at_k=no_positives,
            average_precision_at_k=no_positives,
            success_at_k=success_result,
            reciprocal_rank_at_k=reciprocal_rank_result,
            ndcg_at_k=no_positives,
        )
    recall = retrieved_positive_count / known_positive_count
    f1 = (
        0.0
        if precision + recall == 0
        else 2 * precision * recall / (precision + recall)
    )
    precisions_at_relevant_ranks = [
        sum(binary_relevances[:rank]) / rank
        for rank, relevance in enumerate(binary_relevances, start=1)
        if relevance
    ]
    average_precision = fsum(precisions_at_relevant_ranks) / min(
        known_positive_count,
        k,
    )
    discounted_gain = fsum(
        ((2**relevance) - 1) / log2(rank + 1)
        for rank, relevance in enumerate(selected_relevances, start=1)
    )
    ideal_relevances = sorted(judgments.values(), reverse=True)[:k]
    ideal_discounted_gain = fsum(
        ((2**relevance) - 1) / log2(rank + 1)
        for rank, relevance in enumerate(ideal_relevances, start=1)
    )
    return QuestionIRMetrics(
        question_id=question_id,
        k=k,
        precision_at_k=precision_result,
        recall_at_k=available_metric(recall),
        f1_at_k=available_metric(f1),
        average_precision_at_k=available_metric(average_precision),
        success_at_k=success_result,
        reciprocal_rank_at_k=reciprocal_rank_result,
        ndcg_at_k=available_metric(discounted_gain / ideal_discounted_gain),
    )


def aggregate_metric(results: Sequence[MetricResult]) -> AggregatedMetric:
    values = [result.value for result in results if result.value is not None]
    return AggregatedMetric(
        value=fsum(values) / len(values) if values else None,
        evaluated_question_count=len(values),
        unavailable_question_count=len(results) - len(values),
    )


def evaluate_ir_metrics(
    results_by_question_id: Mapping[str, Sequence[RetrievalResult]],
    judgments_by_question_id: Mapping[str, Mapping[str, RelevanceGrade]],
    k: int,
) -> IRMetricsReport:
    validate_k(k)
    if not judgments_by_question_id:
        raise ValueError("judgments must not be empty")
    if set(results_by_question_id) != set(judgments_by_question_id):
        raise ValueError("results must match judgment question identifiers")
    questions = tuple(
        evaluate_ir_question(
            question_id,
            results_by_question_id[question_id],
            judgments,
            k,
        )
        for question_id, judgments in judgments_by_question_id.items()
    )
    metric_names = (
        "precision_at_k",
        "recall_at_k",
        "f1_at_k",
        "average_precision_at_k",
        "success_at_k",
        "reciprocal_rank_at_k",
        "ndcg_at_k",
    )
    aggregated = {
        name: aggregate_metric([getattr(question, name) for question in questions])
        for name in metric_names
    }
    return IRMetricsReport(
        k=k,
        questions=questions,
        precision_at_k=aggregated["precision_at_k"],
        recall_at_k=aggregated["recall_at_k"],
        f1_at_k=aggregated["f1_at_k"],
        map_at_k=aggregated["average_precision_at_k"],
        success_at_k=aggregated["success_at_k"],
        mrr_at_k=aggregated["reciprocal_rank_at_k"],
        ndcg_at_k=aggregated["ndcg_at_k"],
    )


def evaluate_cases(
    cases: Sequence[EvaluationCase],
    results_by_case_id: Mapping[str, Sequence[RetrievalResult]],
    k: int,
) -> EvaluationReport:
    validate_k(k)
    if not cases:
        raise ValueError("cases must not be empty")

    case_ids = [case.id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("case identifiers must be unique")
    if set(case_ids) != set(results_by_case_id):
        raise ValueError("results must match evaluation case identifiers")

    evaluations = tuple(
        CaseEvaluation(
            case_id=case.id,
            source_hit_at_k=source_hit_at_k(
                results_by_case_id[case.id],
                case.expected_document_ids,
                k,
            ),
            evidence_hit_at_k=evidence_hit_at_k(
                results_by_case_id[case.id],
                case.expected_chunk_ids,
                k,
            ),
        )
        for case in cases
    )
    return EvaluationReport(
        k=k,
        cases=evaluations,
        mean_source_hit_at_k=(
            fsum(evaluation.source_hit_at_k for evaluation in evaluations)
            / len(evaluations)
        ),
        mean_evidence_hit_at_k=(
            fsum(evaluation.evidence_hit_at_k for evaluation in evaluations)
            / len(evaluations)
        ),
    )
