import math
from pathlib import Path
from typing import cast

import pytest

from app.schemas.documents import Chunk
from app.services.embeddings import LocalEmbeddingService, cosine_similarity


class FakeTokenizer:
    def __call__(
        self,
        text: str,
        *,
        truncation: bool,
        add_special_tokens: bool,
    ) -> dict[str, list[int]]:
        tokens = list(range(len(text.split()) + 2))
        return {"input_ids": tokens}


class FakeEncoder:
    max_seq_length = 8
    tokenizer = FakeTokenizer()

    def __init__(self) -> None:
        self.encode_calls = 0

    def encode(
        self,
        sentences: list[str],
        *,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ) -> list[list[float]]:
        self.encode_calls += 1
        return [
            [float(len(text)), float(sum(map(ord, text))), float(index)]
            for index, text in enumerate(sentences)
        ]


def create_service() -> tuple[LocalEmbeddingService, FakeEncoder, list[Path]]:
    encoder = FakeEncoder()
    loaded_paths: list[Path] = []

    def factory(model_path: Path) -> FakeEncoder:
        loaded_paths.append(model_path)
        return encoder

    service = LocalEmbeddingService(Path("synthetic-model"), factory)
    return service, encoder, loaded_paths


def create_chunk(identifier: str, content: str, position: int) -> Chunk:
    return Chunk(
        id=identifier,
        document_id="synthetic-document",
        content=content,
        position=position,
        title="Synthetic guide",
        source="synthetic://guide",
    )


def test_embed_text_returns_finite_vector() -> None:
    service, _, _ = create_service()

    vector = service.embed_text("question synthétique")

    assert len(vector) == 3
    assert all(math.isfinite(value) for value in vector)


def test_embed_texts_preserves_order_and_dimension() -> None:
    service, _, _ = create_service()

    vectors = service.embed_texts(["un", "texte plus long", "fin"])

    assert [vector[0] for vector in vectors] == [2.0, 15.0, 3.0]
    assert {len(vector) for vector in vectors} == {3}


def test_embed_chunks_uses_ordered_chunk_contents() -> None:
    service, _, _ = create_service()
    chunks = [
        create_chunk("second", "deuxième", 1),
        create_chunk("first", "premier", 0),
    ]

    vectors = service.embed_chunks(chunks)

    assert [vector[0] for vector in vectors] == [8.0, 7.0]


def test_empty_list_returns_empty_list_without_encoding() -> None:
    service, encoder, _ = create_service()

    assert service.embed_texts([]) == []
    assert encoder.encode_calls == 0


@pytest.mark.parametrize("text", ["", "   \t"])
def test_invalid_text_raises_value_error(text: str) -> None:
    service, _, _ = create_service()

    with pytest.raises(ValueError, match="non-whitespace"):
        service.embed_text(text)


def test_invalid_text_in_list_raises_before_encoding() -> None:
    service, encoder, _ = create_service()

    with pytest.raises(ValueError, match="non-whitespace"):
        service.embed_texts(["valide", "   "])

    assert encoder.encode_calls == 0


def test_non_string_input_raises_value_error() -> None:
    service, _, _ = create_service()

    with pytest.raises(ValueError, match="non-whitespace"):
        service.embed_texts(cast(list[str], ["valide", 3]))


def test_text_over_model_limit_is_rejected_without_encoding() -> None:
    service, encoder, _ = create_service()

    with pytest.raises(ValueError, match="limit of 8 tokens"):
        service.embed_text("un deux trois quatre cinq six sept")

    assert encoder.encode_calls == 0


def test_model_is_loaded_once_and_reused() -> None:
    service, encoder, loaded_paths = create_service()

    service.embed_text("premier")
    service.embed_text("deuxième")

    assert loaded_paths == [Path("synthetic-model")]
    assert encoder.encode_calls == 2


def test_dimension_change_between_calls_is_rejected() -> None:
    service, encoder, _ = create_service()
    service.embed_text("premier")

    def changed_encode(
        sentences: list[str],
        *,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ) -> list[list[float]]:
        return [[1.0, 2.0] for _ in sentences]

    encoder.encode = changed_encode

    with pytest.raises(ValueError, match="dimension changed"):
        service.embed_text("deuxième")


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ([1.0, 2.0], [1.0, 2.0], 1.0),
        ([1.0, 0.0], [0.0, 1.0], 0.0),
        ([1.0, 2.0], [-1.0, -2.0], -1.0),
    ],
)
def test_cosine_similarity_expected_geometry(
    first: list[float],
    second: list[float],
    expected: float,
) -> None:
    assert cosine_similarity(first, second) == pytest.approx(expected)


def test_cosine_similarity_rejects_different_dimensions() -> None:
    with pytest.raises(ValueError, match="same dimension"):
        cosine_similarity([1.0], [1.0, 2.0])


def test_cosine_similarity_rejects_empty_vector() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        cosine_similarity([], [])


@pytest.mark.parametrize(
    ("first", "second"),
    [([0.0, 0.0], [1.0, 2.0]), ([1.0, 2.0], [0.0, 0.0])],
)
def test_cosine_similarity_rejects_zero_vector(
    first: list[float],
    second: list[float],
) -> None:
    with pytest.raises(ValueError, match="non-zero"):
        cosine_similarity(first, second)


@pytest.mark.parametrize("invalid_value", [math.inf, -math.inf, math.nan])
def test_cosine_similarity_rejects_non_finite_values(
    invalid_value: float,
) -> None:
    with pytest.raises(ValueError, match="finite"):
        cosine_similarity([1.0, invalid_value], [1.0, 2.0])
