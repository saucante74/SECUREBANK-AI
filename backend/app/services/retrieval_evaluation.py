from collections.abc import Collection, Mapping, Sequence
from math import fsum

from app.schemas.evaluation import (
    CaseEvaluation,
    EvaluationCase,
    EvaluationReport,
)
from app.schemas.retrieval import RetrievalResult

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
