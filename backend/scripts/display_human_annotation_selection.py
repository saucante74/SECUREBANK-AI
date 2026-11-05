import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.schemas.documents import Chunk
from app.schemas.evaluation import UnannotatedBenchmarkQuestion
from app.services.benchmark_dataset import (
    create_benchmark_v2_chunks,
    load_benchmark_dataset_v2,
)

DEFAULT_SELECTION_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "rag_annotation_selection_v2_human_blind_test.json"
)


class SelectionEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)


class SelectionFile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1]
    corpus_version: Literal["v2"]
    selections: tuple[SelectionEntry, ...] = Field(min_length=1)

    @field_validator("selections")
    @classmethod
    def validate_unique_pairs(
        cls,
        selections: tuple[SelectionEntry, ...],
    ) -> tuple[SelectionEntry, ...]:
        pairs = [
            (selection.question_id, selection.chunk_id) for selection in selections
        ]
        if len(pairs) != len(set(pairs)):
            raise ValueError("selection pairs must be unique")
        return selections


class ResolvedSelection(BaseModel):
    model_config = ConfigDict(frozen=True)

    question: str
    passage: str


def load_selection(path: Path) -> SelectionFile:
    return SelectionFile.model_validate_json(path.read_text(encoding="utf-8"))


def resolve_selections(
    selection_file: SelectionFile,
    questions_by_id: Mapping[str, UnannotatedBenchmarkQuestion],
    chunks_by_id: Mapping[str, Chunk],
) -> tuple[ResolvedSelection, ...]:
    resolved: list[ResolvedSelection] = []
    missing_references: list[str] = []
    for selection in selection_file.selections:
        question = questions_by_id.get(selection.question_id)
        chunk = chunks_by_id.get(selection.chunk_id)
        if question is None:
            missing_references.append(f"question_id={selection.question_id!r}")
        if chunk is None:
            missing_references.append(f"chunk_id={selection.chunk_id!r}")
        if question is not None and chunk is not None:
            resolved.append(
                ResolvedSelection(
                    question=question.question,
                    passage=chunk.content,
                )
            )
    if missing_references:
        references = ", ".join(missing_references)
        raise ValueError(f"unresolved selection references: {references}")
    return tuple(resolved)


def render_selections(selections: Sequence[ResolvedSelection]) -> str:
    sections = [
        "\n".join(
            (
                f"{number}.",
                f"Question : {selection.question}",
                "Passage :",
                selection.passage,
                "Ma note (0/1/2) : ___",
            )
        )
        for number, selection in enumerate(selections, start=1)
    ]
    return "\n\n".join(sections)


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--selection-file",
        type=Path,
        default=DEFAULT_SELECTION_PATH,
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    try:
        parsed_arguments = parse_arguments(arguments)
        selection_file = load_selection(parsed_arguments.selection_file)
        dataset = load_benchmark_dataset_v2()
        questions_by_id = {
            question.id: question for question in dataset.reference_questions
        }
        chunks = create_benchmark_v2_chunks(dataset.documents)
        chunks_by_id = {chunk.id: chunk for chunk in chunks}
        selections = resolve_selections(
            selection_file,
            questions_by_id,
            chunks_by_id,
        )
        print(render_selections(selections))
        return 0
    except (OSError, ValidationError, ValueError) as error:
        print(f"Unable to display selection: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
