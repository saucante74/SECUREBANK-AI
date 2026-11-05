from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.services.benchmark_dataset import create_v2_metadata
from scripts import run_rag_baseline_v2


def test_v2_launcher_disables_indexing_and_saves_v2_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pipeline = MagicMock()
    pipeline.metadata = create_v2_metadata()
    comparisons = {"BM25": MagicMock()}
    run = MagicMock()
    output_path = tmp_path / "v2.json"
    create_pipeline = MagicMock(return_value=pipeline)
    run_comparison = MagicMock(return_value=comparisons)
    build_run = MagicMock(return_value=run)
    save_run = MagicMock(return_value=output_path)
    current_version = MagicMock(return_value="a" * 40)
    monkeypatch.setattr(
        run_rag_baseline_v2,
        "create_local_comparison",
        create_pipeline,
    )
    monkeypatch.setattr(run_rag_baseline_v2, "run_comparison", run_comparison)
    monkeypatch.setattr(run_rag_baseline_v2, "build_baseline_run", build_run)
    monkeypatch.setattr(run_rag_baseline_v2, "save_baseline_run", save_run)
    monkeypatch.setattr(run_rag_baseline_v2, "current_code_version", current_version)

    result = run_rag_baseline_v2.main([])

    assert result == 0
    create_pipeline.assert_called_once_with(
        index_chunks=False,
        corpus_version="v2",
        judgments_path=None,
    )
    run_comparison.assert_called_once_with(pipeline)
    build_run.assert_called_once_with(
        comparisons,
        code_version="a" * 40,
        metadata=pipeline.metadata,
    )
    save_run.assert_called_once_with(run)


def test_v2_launcher_passes_explicit_judgments_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    judgments_path = tmp_path / "qwen.json"
    pipeline = MagicMock()
    pipeline.metadata = create_v2_metadata()
    create_pipeline = MagicMock(return_value=pipeline)
    monkeypatch.setattr(run_rag_baseline_v2, "create_local_comparison", create_pipeline)
    monkeypatch.setattr(
        run_rag_baseline_v2, "run_comparison", MagicMock(return_value={})
    )
    monkeypatch.setattr(run_rag_baseline_v2, "build_baseline_run", MagicMock())
    monkeypatch.setattr(run_rag_baseline_v2, "save_baseline_run", MagicMock())
    monkeypatch.setattr(
        run_rag_baseline_v2,
        "current_code_version",
        MagicMock(return_value="a" * 40),
    )

    result = run_rag_baseline_v2.main(["--judgments-file", str(judgments_path)])

    assert result == 0
    create_pipeline.assert_called_once_with(
        index_chunks=False,
        corpus_version="v2",
        judgments_path=judgments_path,
    )
