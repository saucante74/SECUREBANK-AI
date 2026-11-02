from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.annotate_pool import (
    DEFAULT_OUTPUT_PATH,
    V2_OUTPUT_PATH,
    V2_SOURCE_PATH,
    annotate,
    apply_judgment,
    create_annotation_session,
    load_pool,
    main,
    parse_arguments,
    parse_judgment,
    progress,
    save_session,
    validate_session_compatibility,
)
from scripts.build_annotation_pool import AnnotationPool


def source_pool() -> AnnotationPool:
    path = Path(__file__).resolve().parents[1] / "data" / "rag_annotation_pool.json"
    return load_pool(path)


def test_loads_existing_version_one_pool() -> None:
    pool = source_pool()

    assert pool.schema_version == 1
    assert len(pool.questions) == 40


def test_loads_version_two_pool(tmp_path: Path) -> None:
    pool = source_pool().model_copy(update={"schema_version": 2})
    path = tmp_path / "version-two.json"
    path.write_text(pool.model_dump_json(), encoding="utf-8")

    loaded = load_pool(path)

    assert loaded.schema_version == 2


def test_loads_version_three_v2_pool() -> None:
    pool = load_pool(V2_SOURCE_PATH)

    assert pool.schema_version == 3
    assert pool.metadata is not None
    assert pool.metadata.corpus_version == "v2"
    assert len(pool.questions) == 40


def test_v2_cli_selects_distinct_source_and_session_paths() -> None:
    arguments = parse_arguments(["--corpus-version", "v2", "--first-five"])

    assert arguments.source == V2_SOURCE_PATH
    assert arguments.output == V2_OUTPUT_PATH
    assert arguments.first_five is True


def test_new_session_resets_source_judgments_to_null() -> None:
    source = apply_judgment(source_pool(), 0, 0, 2)

    session = create_annotation_session(source)

    assert source.questions[0].candidates[0].relevance == 2
    assert session.questions[0].candidates[0].relevance is None


def test_save_requires_explicit_overwrite_permission(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    session = create_annotation_session(source_pool())
    save_session(session, path)

    with pytest.raises(FileExistsError):
        save_session(session, path)

    updated = apply_judgment(session, 0, 0, 1)
    save_session(updated, path, allow_overwrite=True)

    assert load_pool(path).questions[0].candidates[0].relevance == 1


def test_resume_preserves_judgments_and_validates_source(tmp_path: Path) -> None:
    source = source_pool()
    session = apply_judgment(create_annotation_session(source), 0, 0, 1)
    path = tmp_path / "session.json"
    save_session(session, path)

    resumed = load_pool(path)
    validate_session_compatibility(source, resumed)

    assert resumed.questions[0].candidates[0].relevance == 1
    judged, total = progress(resumed, 5)
    assert judged == 1
    assert total == sum(len(question.candidates) for question in source.questions[:5])


def test_resume_rejects_different_v2_metadata() -> None:
    source = load_pool(V2_SOURCE_PATH)
    session = create_annotation_session(source)
    assert session.metadata is not None
    incompatible_metadata = session.metadata.model_copy(
        update={"corpus_fingerprint": "0" * 64}
    )
    incompatible_session = session.model_copy(
        update={"metadata": incompatible_metadata}
    )

    with pytest.raises(ValueError, match="does not match"):
        validate_session_compatibility(source, incompatible_session)


def test_v2_prompt_displays_document_source_and_provenance(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = load_pool(V2_SOURCE_PATH)
    first_question = source.questions[0]
    first_candidate = first_question.candidates[0]
    session = source.model_copy(
        update={
            "questions": (
                first_question.model_copy(update={"candidates": (first_candidate,)}),
            )
        }
    )

    annotate(
        session,
        tmp_path / "v2-session.json",
        first_five=True,
        allow_overwrite=False,
        input_reader=lambda _: "q",
    )

    output = capsys.readouterr().out
    assert f"Question: {first_question.question}" in output
    assert f"Document: {first_candidate.document_id}" in output
    assert f"Source: {first_candidate.source}" in output
    assert "Retrieved by:" in output
    for provenance in first_candidate.retrieved_by:
        assert f"{provenance.engine} rank {provenance.rank}" in output
    assert f"Text:\n{first_candidate.text}" in output


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [("0", 0), ("1", 1), ("2", 2), ("", None), ("  ", None)],
)
def test_parse_judgment_accepts_supported_values(
    raw_value: str,
    expected: int | None,
) -> None:
    assert parse_judgment(raw_value, None) == expected


def test_rejects_unsupported_judgments() -> None:
    with pytest.raises(ValueError):
        parse_judgment("3", None)
    with pytest.raises(ValidationError):
        apply_judgment(source_pool(), 0, 0, 3)


def test_existing_session_requires_confirmation_before_overwrite(
    tmp_path: Path,
) -> None:
    source_path = (
        Path(__file__).resolve().parents[1] / "data" / "rag_annotation_pool.json"
    )
    output_path = tmp_path / "session.json"
    output_path.write_text("unchanged", encoding="utf-8")

    exit_code = main(
        ["--source", str(source_path), "--output", str(output_path)],
        input_reader=lambda _: "n",
    )

    assert exit_code == 1
    assert output_path.read_text(encoding="utf-8") == "unchanged"


def test_v2_selection_cannot_overwrite_v1_annotations() -> None:
    original_content = DEFAULT_OUTPUT_PATH.read_bytes()

    exit_code = main(
        [
            "--corpus-version",
            "v2",
            "--output",
            str(DEFAULT_OUTPUT_PATH),
        ],
        input_reader=lambda _: pytest.fail("input must not be requested"),
    )

    assert exit_code == 1
    assert DEFAULT_OUTPUT_PATH.read_bytes() == original_content
