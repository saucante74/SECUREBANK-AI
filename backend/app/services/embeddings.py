import math
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, cast

from app.schemas.documents import Chunk

DEFAULT_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "models"
    / "paraphrase-multilingual-MiniLM-L12-v2"
)


class Tokenizer(Protocol):
    def __call__(
        self,
        text: str,
        *,
        truncation: bool,
        add_special_tokens: bool,
    ) -> dict[str, Sequence[int]]: ...


class TextEncoder(Protocol):
    max_seq_length: int
    tokenizer: Tokenizer

    def encode(
        self,
        sentences: list[str],
        *,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ) -> object: ...


type EncoderFactory = Callable[[Path], TextEncoder]


def load_local_encoder(model_path: Path) -> TextEncoder:
    from sentence_transformers import SentenceTransformer

    return cast(
        TextEncoder,
        SentenceTransformer(
            str(model_path),
            device="cpu",
            local_files_only=True,
        ),
    )


class LocalEmbeddingService:
    def __init__(
        self,
        model_path: Path = DEFAULT_MODEL_PATH,
        encoder_factory: EncoderFactory = load_local_encoder,
    ) -> None:
        self._model_path = model_path
        self._encoder = encoder_factory(model_path)
        self._dimension: int | None = None

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        validated_texts = list(texts)
        if not validated_texts:
            return []

        for text in validated_texts:
            self._validate_text(text)
            self._validate_length(text)

        encoded = self._encoder.encode(
            validated_texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        vectors = self._to_vectors(encoded)
        self._validate_vectors(vectors, len(validated_texts))
        return vectors

    def embed_chunks(self, chunks: Sequence[Chunk]) -> list[list[float]]:
        return self.embed_texts([chunk.content for chunk in chunks])

    def _validate_text(self, text: str) -> None:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must contain non-whitespace characters")

    def _validate_length(self, text: str) -> None:
        tokenized = self._encoder.tokenizer(
            text,
            truncation=False,
            add_special_tokens=True,
        )
        token_count = len(tokenized["input_ids"])
        if token_count > self._encoder.max_seq_length:
            raise ValueError(
                f"text exceeds the model limit of {self._encoder.max_seq_length} tokens"
            )

    def _to_vectors(self, encoded: object) -> list[list[float]]:
        values = encoded.tolist() if hasattr(encoded, "tolist") else encoded
        return [[float(value) for value in row] for row in cast(Sequence, values)]

    def _validate_vectors(
        self,
        vectors: list[list[float]],
        expected_count: int,
    ) -> None:
        if len(vectors) != expected_count:
            raise ValueError("encoder returned an unexpected number of vectors")

        dimensions = {len(vector) for vector in vectors}
        if not dimensions or 0 in dimensions or len(dimensions) != 1:
            raise ValueError("encoder returned vectors with inconsistent dimensions")
        if not all(math.isfinite(value) for vector in vectors for value in vector):
            raise ValueError("encoder returned non-finite values")

        dimension = dimensions.pop()
        if self._dimension is None:
            self._dimension = dimension
        elif dimension != self._dimension:
            raise ValueError("encoder dimension changed between calls")


def cosine_similarity(
    first: Sequence[float],
    second: Sequence[float],
) -> float:
    if not first or not second:
        raise ValueError("vectors must not be empty")
    if len(first) != len(second):
        raise ValueError("vectors must have the same dimension")
    if not all(math.isfinite(value) for value in (*first, *second)):
        raise ValueError("vectors must contain only finite values")

    first_norm = math.hypot(*first)
    second_norm = math.hypot(*second)
    if first_norm == 0.0 or second_norm == 0.0:
        raise ValueError("vectors must be non-zero")

    similarity = math.fsum(
        (left / first_norm) * (right / second_norm)
        for left, right in zip(first, second, strict=True)
    )
    return max(-1.0, min(1.0, similarity))
