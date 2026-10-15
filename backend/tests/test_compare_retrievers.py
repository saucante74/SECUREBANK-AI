from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.documents import Chunk
from app.schemas.retrieval import RetrievalResult
from app.services.chunking import CharacterChunker
from app.services.embeddings import LocalEmbeddingService
from app.services.qdrant import QdrantVectorStore, QdrantVectorStoreError
from app.services.reranking import FlashRankReranker
from app.services.retrieval_evaluation import (
    SYNTHETIC_EVALUATION_CASES,
    evaluate_cases,
)
from scripts.compare_retrievers import (
    ENGINE_NAMES,
    ComparisonPipeline,
    SemanticRetriever,
    compare_retrievers,
    evaluate_engine,
    main,
    prepare_comparison,
    run_comparison,
)


def create_result(
    document_id: str,
    chunk_id: str,
) -> RetrievalResult:
    return RetrievalResult(
        chunk=Chunk(
            id=chunk_id,
            document_id=document_id,
            content=f"Synthetic evidence for {chunk_id}",
            position=0,
            title=f"Synthetic title for {document_id}",
            source=f"synthetic://{document_id}",
        ),
        score=1.0,
    )


def create_timer(values: list[float]) -> Iterator[float]:
    return iter(values)


def create_pipeline(result: RetrievalResult | None = None) -> ComparisonPipeline:
    engines: dict[str, MagicMock] = {}
    for name in ENGINE_NAMES:
        engine = MagicMock()
        engine.search.return_value = [result] if result else []
        engines[name] = engine
    return ComparisonPipeline(
        chunks=[result.chunk] if result else [],
        engines=engines,
        qdrant_point_count=1 if result else 0,
    )


def test_prepare_comparison_builds_the_four_real_configurations() -> None:
    embeddings = MagicMock(spec=LocalEmbeddingService)
    embeddings.embed_chunks.return_value = [[0.1] * 384] * 3
    vector_store = MagicMock(spec=QdrantVectorStore)
    vector_store.store_chunks.return_value = 3
    reranker = MagicMock(spec=FlashRankReranker)

    pipeline = prepare_comparison(
        CharacterChunker(chunk_size=1_000),
        embeddings,
        vector_store,
        reranker,
        point_counter=lambda chunks: len(chunks),
    )

    assert tuple(pipeline.engines) == ENGINE_NAMES
    assert len(pipeline.chunks) == 3
    assert pipeline.qdrant_point_count == 3
    embeddings.embed_chunks.assert_called_once_with(pipeline.chunks)
    vector_store.store_chunks.assert_called_once()


def test_semantic_retriever_embeds_question_before_qdrant_search() -> None:
    embeddings = MagicMock(spec=LocalEmbeddingService)
    vector_store = MagicMock(spec=QdrantVectorStore)
    embeddings.embed_text.return_value = [0.2] * 384
    vector_store.search.return_value = []

    results = SemanticRetriever(embeddings, vector_store).search("Question", top_k=3)

    assert results == []
    embeddings.embed_text.assert_called_once_with("Question")
    vector_store.search.assert_called_once_with([0.2] * 384, top_k=3)


def test_comparison_uses_all_six_existing_cases_and_four_engines() -> None:
    first_case = SYNTHETIC_EVALUATION_CASES[0]
    result = create_result(
        next(iter(first_case.expected_document_ids)),
        next(iter(first_case.expected_chunk_ids)),
    )
    pipeline = create_pipeline(result)

    comparisons = compare_retrievers(pipeline)

    assert tuple(comparisons) == ENGINE_NAMES
    for engine in pipeline.engines.values():
        assert engine.search.call_count == 6
        assert [call.args[0] for call in engine.search.call_args_list] == [
            case.question for case in SYNTHETIC_EVALUATION_CASES
        ]
        assert all(call.kwargs == {"top_k": 3} for call in engine.search.call_args_list)
    assert all(len(item.results_by_case_id) == 6 for item in comparisons.values())


def test_evaluate_engine_uses_existing_metric_aggregation() -> None:
    case = SYNTHETIC_EVALUATION_CASES[0]
    result = create_result(
        next(iter(case.expected_document_ids)),
        next(iter(case.expected_chunk_ids)),
    )
    engine = MagicMock()
    engine.search.return_value = [result]

    with patch(
        "scripts.compare_retrievers.evaluate_cases",
        wraps=evaluate_cases,
    ) as evaluator:
        comparison = evaluate_engine(engine, [result.chunk], [case])

    assert evaluator.call_count == 2
    assert [call.kwargs["k"] for call in evaluator.call_args_list] == [1, 3]
    assert comparison.report_at_1.mean_source_hit_at_k == 1.0
    assert comparison.report_at_1.mean_evidence_hit_at_k == 1.0


def test_evaluate_engine_associates_results_and_measures_latency() -> None:
    cases = SYNTHETIC_EVALUATION_CASES[:2]
    first = create_result(
        "demo-credit-immobilier",
        "demo-credit-immobilier:chunk:0",
    )
    engine = MagicMock()
    engine.search.side_effect = [[first], []]
    timer = create_timer([1.0, 1.1, 2.0, 2.4])

    comparison = evaluate_engine(
        engine,
        [first.chunk],
        cases,
        timer=lambda: next(timer),
    )

    assert comparison.results_by_case_id == {
        cases[0].id: [first],
        cases[1].id: [],
    }
    assert comparison.latency_by_case_id[cases[0].id] == pytest.approx(0.1)
    assert comparison.latency_by_case_id[cases[1].id] == pytest.approx(0.4)
    assert comparison.mean_latency_seconds == pytest.approx(0.25)


def test_run_comparison_displays_tables_and_empty_results(
    capsys: pytest.CaptureFixture[str],
) -> None:
    pipeline = create_pipeline()

    comparisons = run_comparison(pipeline)

    assert all(
        comparison.report_at_1.mean_source_hit_at_k == 0.0
        for comparison in comparisons.values()
    )
    output = capsys.readouterr().out
    assert "Aggregate metrics" in output
    assert "Source Hit@1" in output
    assert "Evidence Hit@3" in output
    assert "Per-question comparison" in output
    assert output.count("first=No result") == 24
    assert "not a production benchmark" in output


def test_dependency_error_is_propagated() -> None:
    pipeline = create_pipeline()
    error = RuntimeError("synthetic retriever failure")
    pipeline.engines["BM25"].search.side_effect = error

    with pytest.raises(RuntimeError) as raised:
        compare_retrievers(pipeline)

    assert raised.value is error


def test_main_reports_dependency_error(capsys: pytest.CaptureFixture[str]) -> None:
    def unavailable_pipeline() -> ComparisonPipeline:
        raise QdrantVectorStoreError("Qdrant unavailable")

    exit_code = main(pipeline_factory=unavailable_pipeline)

    assert exit_code == 1
    assert "Qdrant operation failed: Qdrant unavailable" in capsys.readouterr().out
