import argparse
from collections.abc import Callable, Sequence
from pathlib import Path

from pydantic import ValidationError

from scripts.build_annotation_pool import (
    AnnotationPool,
    CandidateAnnotation,
    QuestionAnnotation,
    RelevanceJudgment,
)

DEFAULT_SOURCE_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "rag_annotation_pool.json"
)
DEFAULT_OUTPUT_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "rag_annotation_judgments.json"
)
V2_SOURCE_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "rag_annotation_pool_v2.json"
)
V2_OUTPUT_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "rag_annotation_judgments_v2.json"
)

type InputReader = Callable[[str], str]


def load_pool(path: Path) -> AnnotationPool:
    return AnnotationPool.model_validate_json(path.read_text(encoding="utf-8"))


def create_annotation_session(source: AnnotationPool) -> AnnotationPool:
    return source.model_copy(
        update={
            "questions": tuple(
                question.model_copy(
                    update={
                        "candidates": tuple(
                            candidate.model_copy(update={"relevance": None})
                            for candidate in question.candidates
                        )
                    }
                )
                for question in source.questions
            )
        }
    )


def validate_session_compatibility(
    source: AnnotationPool,
    session: AnnotationPool,
) -> None:
    source_structure = pool_structure(source)
    session_structure = pool_structure(session)
    if source_structure != session_structure:
        raise ValueError("annotation session does not match the source pool")


def pool_structure(pool: AnnotationPool) -> tuple[object, ...]:
    return (
        pool.schema_version,
        pool.metadata,
        tuple(
            (
                question.question_id,
                question.question,
                tuple(
                    (
                        candidate.chunk_id,
                        candidate.document_id,
                        candidate.text,
                        candidate.source,
                        candidate.retrieved_by,
                        candidate.included_from_existing_positive,
                    )
                    for candidate in question.candidates
                ),
            )
            for question in pool.questions
        ),
    )


def save_session(
    session: AnnotationPool,
    output_path: Path,
    allow_overwrite: bool = False,
) -> None:
    mode = "w" if allow_overwrite else "x"
    with output_path.open(mode, encoding="utf-8") as output_file:
        output_file.write(session.model_dump_json(indent=2) + "\n")


def parse_judgment(
    value: str,
    current: RelevanceJudgment,
) -> RelevanceJudgment:
    normalized = value.strip()
    if not normalized:
        return current
    if normalized in {"0", "1", "2"}:
        return int(normalized)
    raise ValueError("judgment must be 0, 1, 2, or empty")


def apply_judgment(
    session: AnnotationPool,
    question_index: int,
    candidate_index: int,
    judgment: RelevanceJudgment,
) -> AnnotationPool:
    questions = list(session.questions)
    question = questions[question_index]
    candidates = list(question.candidates)
    candidate_payload = candidates[candidate_index].model_dump()
    candidate_payload["relevance"] = judgment
    candidates[candidate_index] = CandidateAnnotation.model_validate(candidate_payload)
    questions[question_index] = QuestionAnnotation.model_validate(
        {
            **question.model_dump(),
            "candidates": candidates,
        }
    )
    return session.model_copy(update={"questions": tuple(questions)})


def selected_question_count(session: AnnotationPool, first_five: bool) -> int:
    return min(5, len(session.questions)) if first_five else len(session.questions)


def progress(session: AnnotationPool, question_count: int) -> tuple[int, int]:
    candidates = tuple(
        candidate
        for question in session.questions[:question_count]
        for candidate in question.candidates
    )
    return sum(candidate.relevance is not None for candidate in candidates), len(
        candidates
    )


def annotate(
    session: AnnotationPool,
    output_path: Path,
    first_five: bool,
    allow_overwrite: bool,
    input_reader: InputReader = input,
) -> AnnotationPool:
    question_count = selected_question_count(session, first_five)
    output_exists = output_path.exists()
    for question_index, question in enumerate(session.questions[:question_count]):
        for candidate_index, candidate in enumerate(question.candidates):
            if candidate.relevance is not None:
                continue
            judged, total = progress(session, question_count)
            print(f"\nProgress: {judged}/{total}")
            print(f"Question: {question.question}")
            print(f"Chunk: {candidate.chunk_id}")
            print(f"Document: {candidate.document_id}")
            print(f"Source: {candidate.source or 'N/A'}")
            provenance = ", ".join(
                f"{item.engine} rank {item.rank}" for item in candidate.retrieved_by
            )
            print(f"Retrieved by: {provenance or 'N/A'}")
            print(f"Text:\n{candidate.text}")
            while True:
                raw_value = input_reader("Judgment [0/1/2, Enter=null, q=quit]: ")
                if raw_value.strip().lower() == "q":
                    save_session(
                        session,
                        output_path,
                        allow_overwrite=allow_overwrite or output_exists,
                    )
                    return session
                try:
                    judgment = parse_judgment(raw_value, candidate.relevance)
                except ValueError as error:
                    print(error)
                    continue
                session = apply_judgment(
                    session,
                    question_index,
                    candidate_index,
                    judgment,
                )
                save_session(
                    session,
                    output_path,
                    allow_overwrite=allow_overwrite or output_exists,
                )
                output_exists = True
                break
    judged, total = progress(session, question_count)
    print(f"\nProgress: {judged}/{total}")
    return session


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-version", choices=("v1", "v2"), default="v1")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--first-five", action="store_true")
    parsed_arguments = parser.parse_args(arguments)
    if parsed_arguments.source is None:
        parsed_arguments.source = (
            V2_SOURCE_PATH
            if parsed_arguments.corpus_version == "v2"
            else DEFAULT_SOURCE_PATH
        )
    if parsed_arguments.output is None:
        parsed_arguments.output = (
            V2_OUTPUT_PATH
            if parsed_arguments.corpus_version == "v2"
            else DEFAULT_OUTPUT_PATH
        )
    return parsed_arguments


def validate_output_path(corpus_version: str, output_path: Path) -> None:
    protected_v1_paths = {
        DEFAULT_SOURCE_PATH.resolve(),
        DEFAULT_OUTPUT_PATH.resolve(),
    }
    if corpus_version == "v2" and output_path.resolve() in protected_v1_paths:
        raise ValueError("v2 annotations cannot overwrite v1 files")


def validate_source_version(corpus_version: str, source: AnnotationPool) -> None:
    is_v2 = (
        source.schema_version == 3
        and source.metadata is not None
        and source.metadata.corpus_version == "v2"
    )
    if (corpus_version == "v2") != is_v2:
        raise ValueError("annotation pool does not match the selected corpus version")


def main(
    arguments: Sequence[str] | None = None,
    input_reader: InputReader = input,
) -> int:
    parsed_arguments = parse_arguments(arguments)
    if parsed_arguments.source.resolve() == parsed_arguments.output.resolve():
        print("Source and output paths must be different")
        return 1
    try:
        validate_output_path(
            parsed_arguments.corpus_version,
            parsed_arguments.output,
        )
        source = load_pool(parsed_arguments.source)
        validate_source_version(parsed_arguments.corpus_version, source)
        if parsed_arguments.output.exists():
            confirmation = input_reader(
                f"Resume and overwrite {parsed_arguments.output}? [y/N]: "
            )
            if confirmation.strip().lower() != "y":
                print("Annotation session cancelled")
                return 1
            session = load_pool(parsed_arguments.output)
            validate_session_compatibility(source, session)
            allow_overwrite = True
        else:
            session = create_annotation_session(source)
            allow_overwrite = False
        annotate(
            session,
            parsed_arguments.output,
            parsed_arguments.first_five,
            allow_overwrite,
            input_reader,
        )
    except (OSError, ValidationError, ValueError) as error:
        print(f"Annotation failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
