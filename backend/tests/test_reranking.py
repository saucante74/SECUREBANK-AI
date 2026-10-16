import math
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.schemas.documents import Chunk
from app.schemas.retrieval import RetrievalResult
from app.services.reranking import FlashRankReranker


def create_result(
    identifier: str,
    score: float,
    *,
    content: str | None = None,
) -> RetrievalResult:
    return RetrievalResult(
        chunk=Chunk(
            id=identifier,
            document_id="synthetic-document",
            content=content or f"Synthetic evidence for {identifier}",
            position=0,
            title=f"Synthetic title {identifier}",
            source=f"synthetic://{identifier}",
        ),
        score=score,
    )


def create_engine() -> MagicMock:
    return MagicMock()


def test_reranks_results_and_preserves_chunk_metadata() -> None:
    engine = create_engine()
    first = create_result("first", 0.9)
    second = create_result("second", 0.8)
    engine.rerank.return_value = [
        {"id": 1, "text": second.chunk.content, "score": 0.95},
        {"id": 0, "text": first.chunk.content, "score": 0.25},
    ]

    results = FlashRankReranker(engine=engine).rerank(
        "Question bancaire synthétique",
        [first, second],
        top_k=2,
    )

    request = engine.rerank.call_args.args[0]
    assert request.query == "Question bancaire synthétique"
    assert request.passages == [
        {"id": 0, "text": first.chunk.content},
        {"id": 1, "text": second.chunk.content},
    ]
    assert results == [
        RetrievalResult(chunk=second.chunk, score=0.95),
        RetrievalResult(chunk=first.chunk, score=0.25),
    ]


def test_same_text_with_different_identifiers_remains_distinct() -> None:
    engine = create_engine()
    first = create_result("first", 0.9, content="Identical synthetic text")
    second = create_result("second", 0.8, content="Identical synthetic text")
    engine.rerank.return_value = [
        {"id": 1, "text": second.chunk.content, "score": 0.7},
        {"id": 0, "text": first.chunk.content, "score": 0.6},
    ]

    results = FlashRankReranker(engine=engine).rerank(
        "Question synthétique",
        [first, second],
        top_k=2,
    )

    assert [result.chunk.id for result in results] == ["second", "first"]


def test_top_k_limits_results() -> None:
    engine = create_engine()
    candidates = [create_result(str(index), 1.0) for index in range(3)]
    engine.rerank.return_value = [
        {"id": 2, "score": 0.9},
        {"id": 1, "score": 0.8},
        {"id": 0, "score": 0.7},
    ]

    results = FlashRankReranker(engine=engine).rerank(
        "Question synthétique",
        candidates,
        top_k=2,
    )

    assert [result.chunk.id for result in results] == ["2", "1"]


def test_empty_list_returns_without_calling_engine() -> None:
    engine = create_engine()

    assert FlashRankReranker(engine=engine).rerank("Question valide", [], 3) == []
    engine.rerank.assert_not_called()


@pytest.mark.parametrize("question", ["", "   \t"])
def test_empty_question_is_rejected(question: str) -> None:
    engine = create_engine()

    with pytest.raises(ValueError, match="question must contain"):
        FlashRankReranker(engine=engine).rerank(question, [], 3)

    engine.rerank.assert_not_called()


@pytest.mark.parametrize("top_k", [0, -1, 1.5, True])
def test_invalid_top_k_is_rejected(top_k: object) -> None:
    engine = create_engine()

    with pytest.raises(ValueError, match="top_k must be a strictly positive integer"):
        FlashRankReranker(engine=engine).rerank("Question valide", [], top_k)

    engine.rerank.assert_not_called()


@pytest.mark.parametrize("score", [None, "invalid", math.nan, math.inf, -math.inf])
def test_invalid_score_is_rejected(score: object) -> None:
    engine = create_engine()
    engine.rerank.return_value = [{"id": 0, "score": score}]

    with pytest.raises(ValueError, match="invalid score"):
        FlashRankReranker(engine=engine).rerank(
            "Question valide",
            [create_result("first", 1.0)],
            1,
        )


def test_engine_error_is_propagated() -> None:
    engine = create_engine()
    error = RuntimeError("synthetic FlashRank failure")
    engine.rerank.side_effect = error

    with pytest.raises(RuntimeError) as raised:
        FlashRankReranker(engine=engine).rerank(
            "Question valide",
            [create_result("first", 1.0)],
            1,
        )

    assert raised.value is error


def test_injected_engine_prevents_model_loading_and_download() -> None:
    engine = create_engine()
    factory = MagicMock()

    reranker = FlashRankReranker(
        cache_dir=Path("missing-model"),
        engine=engine,
        engine_factory=factory,
    )

    assert reranker.rerank("Question valide", [], 1) == []
    factory.assert_not_called()


def test_model_is_loaded_once_per_service_instance(tmp_path: Path) -> None:
    model_dir = tmp_path / "ms-marco-MultiBERT-L-12"
    model_dir.mkdir()
    for filename in (
        "flashrank-MultiBERT-L12_Q.onnx",
        "config.json",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
    ):
        (model_dir / filename).touch()
    engine = create_engine()
    engine.rerank.return_value = [{"id": 0, "score": 0.5}]
    factory = MagicMock(return_value=engine)
    reranker = FlashRankReranker(cache_dir=tmp_path, engine_factory=factory)

    reranker.rerank("Première question", [create_result("first", 1.0)], 1)
    reranker.rerank("Deuxième question", [create_result("second", 1.0)], 1)

    factory.assert_called_once_with(tmp_path)


def test_missing_local_model_fails_before_engine_creation(tmp_path: Path) -> None:
    factory = MagicMock()

    with pytest.raises(FileNotFoundError, match="prepare_flashrank_model"):
        FlashRankReranker(cache_dir=tmp_path, engine_factory=factory)

    factory.assert_not_called()
