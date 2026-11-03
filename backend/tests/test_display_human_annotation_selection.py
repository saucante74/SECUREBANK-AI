import json
from pathlib import Path

import pytest

from scripts.display_human_annotation_selection import main


def test_displays_complete_blind_selection(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.count("Ma note (0/1/2) : ___") == 10
    assert "1.\nQuestion : Un remboursement anticipé" in captured.out
    assert "10.\nQuestion : Pourquoi mon horizon" in captured.out
    assert "Informations essentielles conservées" in captured.out
    assert "relevance" not in captured.out
    assert "reason" not in captured.out


def test_reports_unknown_reference(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "corpus_version": "v2",
                "selections": [
                    {
                        "question_id": "unknown-question",
                        "chunk_id": "unknown-chunk",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(["--selection-file", str(selection_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "question_id='unknown-question'" in captured.err
    assert "chunk_id='unknown-chunk'" in captured.err
