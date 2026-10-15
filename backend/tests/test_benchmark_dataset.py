from collections import Counter

from app.core.config import settings
from app.schemas.retrieval import RetrievalResult
from app.services.benchmark_dataset import (
    BENCHMARK_COLLECTION_NAME,
    create_benchmark_chunks,
    load_benchmark_dataset,
)
from app.services.retrieval_evaluation import (
    SYNTHETIC_EVALUATION_CASES,
    evaluate_cases,
)
from scripts.demo_vector_search import create_documents


def test_benchmark_has_expected_size_domains_and_difficulties() -> None:
    dataset = load_benchmark_dataset()
    domain_counts = Counter(
        document.source.split("/")[3] for document in dataset.documents
    )
    difficulties = Counter(case.difficulty for case in dataset.cases)

    assert len(dataset.documents) == 30
    assert len(dataset.cases) == 40
    assert set(domain_counts) == {
        "credit-immobilier",
        "credit-consommation",
        "assurance",
        "epargne",
        "comptes-paiements",
        "securite-conformite",
    }
    assert set(domain_counts.values()) == {5}
    assert difficulties == {"factual": 15, "semantic": 15, "difficult": 10}


def test_benchmark_identifiers_and_references_are_valid() -> None:
    dataset = load_benchmark_dataset()
    chunks = create_benchmark_chunks(dataset.documents)
    document_ids = {document.id for document in dataset.documents}
    chunk_ids = {chunk.id for chunk in chunks}

    assert len(document_ids) == len(dataset.documents)
    assert len({case.id for case in dataset.cases}) == len(dataset.cases)
    assert len(chunk_ids) == len(chunks)
    assert 100 <= len(chunks) <= 200
    for case in dataset.cases:
        assert case.expected_document_ids <= document_ids
        assert case.expected_chunk_ids <= chunk_ids
        assert case.rationale


def test_benchmark_evidence_uses_multiple_chunk_positions() -> None:
    dataset = load_benchmark_dataset()
    chunks_by_id = {
        chunk.id: chunk for chunk in create_benchmark_chunks(dataset.documents)
    }
    positions = {
        chunks_by_id[chunk_id].position
        for case in dataset.cases
        for chunk_id in case.expected_chunk_ids
    }

    assert positions == {0, 1, 2, 3, 4}


def test_historical_evaluation_and_demo_corpus_are_preserved() -> None:
    assert len(SYNTHETIC_EVALUATION_CASES) == 6
    assert {document.id for document in create_documents()} == {
        "demo-credit-immobilier",
        "demo-assurance-habitation",
        "demo-epargne",
    }


def test_benchmark_uses_a_dedicated_qdrant_collection() -> None:
    assert BENCHMARK_COLLECTION_NAME == "securebank_benchmark_chunks"
    assert BENCHMARK_COLLECTION_NAME != settings.qdrant_collection_name


def test_existing_metrics_evaluate_benchmark_results_unchanged() -> None:
    dataset = load_benchmark_dataset()
    chunks_by_id = {
        chunk.id: chunk for chunk in create_benchmark_chunks(dataset.documents)
    }
    results = {
        case.id: [
            RetrievalResult(
                chunk=chunks_by_id[next(iter(case.expected_chunk_ids))],
                score=1.0,
            )
        ]
        for case in dataset.cases
    }

    report = evaluate_cases(dataset.cases, results, k=1)

    assert report.mean_source_hit_at_k == 1.0
    assert report.mean_evidence_hit_at_k == 1.0


def test_regression_question_has_real_benchmark_evidence() -> None:
    dataset = load_benchmark_dataset()
    case = next(
        case
        for case in dataset.cases
        if case.question == "Comment protéger mon logement contre les sinistres ?"
    )
    chunks_by_id = {
        chunk.id: chunk for chunk in create_benchmark_chunks(dataset.documents)
    }
    evidence = " ".join(
        chunks_by_id[chunk_id].content for chunk_id in case.expected_chunk_ids
    )

    assert "assurance habitation" in evidence
    assert "prévention" in evidence
