import math
from collections.abc import Callable, Sequence
from numbers import Real
from pathlib import Path
from typing import Protocol, cast

from flashrank import Ranker, RerankRequest

from app.schemas.retrieval import RetrievalResult

DEFAULT_RERANKER_MODEL = "ms-marco-MultiBERT-L-12"
DEFAULT_RERANKER_CACHE = Path(__file__).resolve().parents[2] / "models" / "flashrank"
RERANKER_MODEL_FILES = (
    "flashrank-MultiBERT-L12_Q.onnx",
    "config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
)


class FlashRankEngine(Protocol):
    def rerank(self, request: RerankRequest) -> list[dict[str, object]]: ...


type EngineFactory = Callable[[Path], FlashRankEngine]


def load_local_engine(cache_dir: Path) -> FlashRankEngine:
    return cast(
        FlashRankEngine,
        Ranker(
            model_name=DEFAULT_RERANKER_MODEL,
            cache_dir=str(cache_dir),
            max_length=512,
            log_level="WARNING",
        ),
    )


def validate_local_model(cache_dir: Path) -> None:
    model_dir = cache_dir / DEFAULT_RERANKER_MODEL
    missing_files = [
        filename
        for filename in RERANKER_MODEL_FILES
        if not (model_dir / filename).is_file()
    ]
    if missing_files:
        raise FileNotFoundError(
            f"FlashRank model is not prepared in {model_dir}. "
            "Run python -m scripts.prepare_flashrank_model first."
        )


class FlashRankReranker:
    def __init__(
        self,
        cache_dir: Path = DEFAULT_RERANKER_CACHE,
        engine: FlashRankEngine | None = None,
        engine_factory: EngineFactory = load_local_engine,
    ) -> None:
        if engine is None:
            validate_local_model(cache_dir)
            engine = engine_factory(cache_dir)
        self._engine = engine

    def rerank(
        self,
        question: str,
        results: Sequence[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must contain non-whitespace characters")
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
            raise ValueError("top_k must be a strictly positive integer")
        if not results:
            return []

        passages = [
            {"id": index, "text": result.chunk.content}
            for index, result in enumerate(results)
        ]
        reranked = self._engine.rerank(RerankRequest(query=question, passages=passages))
        validated = self._validate_response(reranked, len(results))
        return [
            RetrievalResult(chunk=results[index].chunk, score=score)
            for index, score in validated[:top_k]
        ]

    @staticmethod
    def _validate_response(
        reranked: Sequence[dict[str, object]],
        expected_count: int,
    ) -> list[tuple[int, float]]:
        if len(reranked) != expected_count:
            raise ValueError("FlashRank returned an unexpected number of results")

        validated: list[tuple[int, float]] = []
        seen_indices: set[int] = set()
        for item in reranked:
            index = item.get("id")
            score = item.get("score")
            if (
                not isinstance(index, int)
                or isinstance(index, bool)
                or not 0 <= index < expected_count
                or index in seen_indices
            ):
                raise ValueError("FlashRank returned an invalid result identifier")
            if not isinstance(score, Real) or not math.isfinite(float(score)):
                raise ValueError("FlashRank returned an invalid score")
            seen_indices.add(index)
            validated.append((index, float(score)))

        return sorted(validated, key=lambda item: (-item[1], item[0]))
