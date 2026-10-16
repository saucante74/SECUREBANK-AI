from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.services.reranking import FlashRankReranker
from scripts.demo_flashrank import (
    QUESTIONS,
    create_synthetic_results,
    load_reranker,
    main,
    run_demo,
)


def create_timer(values: list[float]) -> Iterator[float]:
    return iter(values)


def test_synthetic_results_cover_expected_topics() -> None:
    results = create_synthetic_results()

    assert [result.chunk.id for result in results] == [
        "epargne-entreprise",
        "assurance-degats-eaux",
        "remboursement-anticipe",
    ]
    assert all(result.chunk.source.startswith("synthetic://") for result in results)


def test_run_demo_preserves_chunks_and_prints_rankings(
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = MagicMock()
    engine.rerank.side_effect = [
        [
            {"id": 2, "score": 0.98},
            {"id": 1, "score": 0.32},
            {"id": 0, "score": 0.01},
        ],
        [
            {"id": 1, "score": 0.97},
            {"id": 2, "score": 0.21},
            {"id": 0, "score": 0.02},
        ],
    ]
    timer = create_timer([10.0, 10.25, 20.0, 20.5])

    rankings = run_demo(
        FlashRankReranker(engine=engine),
        timer=lambda: next(timer),
    )

    assert [ranking.question for ranking in rankings] == list(QUESTIONS)
    assert [result.chunk.id for result in rankings[0].after] == [
        "remboursement-anticipe",
        "assurance-degats-eaux",
        "epargne-entreprise",
    ]
    assert {result.chunk for result in rankings[0].after} == {
        result.chunk for result in rankings[0].before
    }
    assert rankings[0].inference_seconds == pytest.approx(0.25)
    assert rankings[1].inference_seconds == pytest.approx(0.5)
    output = capsys.readouterr().out
    assert output.count("Before reranking") == 2
    assert output.count("After reranking (FlashRank scores)") == 2
    assert "score=0.980000" in output
    assert "Inference time: 0.500000 s" in output


def test_load_reranker_measures_duration(tmp_path: Path) -> None:
    reranker = FlashRankReranker(engine=MagicMock())
    factory = MagicMock(return_value=reranker)
    timer = create_timer([4.0, 5.75])

    loaded, duration = load_reranker(
        tmp_path,
        factory,
        timer=lambda: next(timer),
    )

    assert loaded is reranker
    assert duration == pytest.approx(1.75)
    factory.assert_called_once_with(tmp_path)


def test_main_reports_missing_model(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(cache_dir=tmp_path)

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "Local FlashRank model unavailable" in output
    assert "python -m scripts.prepare_flashrank_model" in output


def test_main_reports_engine_error(capsys: pytest.CaptureFixture[str]) -> None:
    engine = MagicMock()
    engine.rerank.side_effect = RuntimeError("synthetic engine failure")
    reranker = FlashRankReranker(engine=engine)
    timer = create_timer([1.0, 1.1, 2.0])

    exit_code = main(
        reranker_factory=lambda _: reranker,
        timer=lambda: next(timer),
    )

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "Model load time: 0.100000 s" in output
    assert "FlashRank demonstration failed: synthetic engine failure" in output
