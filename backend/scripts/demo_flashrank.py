from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from app.schemas.documents import Chunk
from app.schemas.retrieval import RetrievalResult
from app.services.reranking import DEFAULT_RERANKER_CACHE, FlashRankReranker

QUESTIONS = (
    "Puis-je rembourser mon crédit immobilier avant la fin du contrat ?",
    "Comment protéger mon logement contre les dégâts des eaux ?",
)

type RerankerFactory = Callable[[Path], FlashRankReranker]
type Timer = Callable[[], float]


@dataclass(frozen=True)
class QueryRanking:
    question: str
    before: list[RetrievalResult]
    after: list[RetrievalResult]
    inference_seconds: float


def create_synthetic_results() -> list[RetrievalResult]:
    passages = (
        (
            "epargne-entreprise",
            "Compte d'épargne entreprise",
            "Un compte d'épargne pour entreprise permet de placer une trésorerie "
            "disponible selon les conditions et le taux du produit bancaire.",
            0.92,
        ),
        (
            "assurance-degats-eaux",
            "Assurance habitation et dégâts des eaux",
            "Une assurance habitation peut couvrir les dommages causés par une "
            "fuite ou une infiltration d'eau. Le contrat précise les exclusions, "
            "la franchise et les démarches de déclaration du sinistre.",
            0.74,
        ),
        (
            "remboursement-anticipe",
            "Remboursement anticipé du crédit immobilier",
            "Un emprunteur peut rembourser tout ou partie de son crédit immobilier "
            "avant la date prévue. Le contrat indique le préavis et les éventuelles "
            "indemnités de remboursement anticipé.",
            0.61,
        ),
    )
    return [
        RetrievalResult(
            chunk=Chunk(
                id=identifier,
                document_id=f"document-{identifier}",
                content=content,
                position=0,
                title=title,
                source=f"synthetic://{identifier}",
            ),
            score=score,
        )
        for identifier, title, content, score in passages
    ]


def print_ranking(label: str, results: Sequence[RetrievalResult]) -> None:
    print(label)
    for rank, result in enumerate(results, start=1):
        print(
            f"  {rank}. score={result.score:.6f} | "
            f"{result.chunk.id} | {result.chunk.title}"
        )


def load_reranker(
    cache_dir: Path = DEFAULT_RERANKER_CACHE,
    reranker_factory: RerankerFactory = FlashRankReranker,
    timer: Timer = perf_counter,
) -> tuple[FlashRankReranker, float]:
    started_at = timer()
    reranker = reranker_factory(cache_dir)
    return reranker, timer() - started_at


def run_demo(
    reranker: FlashRankReranker,
    questions: Sequence[str] = QUESTIONS,
    timer: Timer = perf_counter,
) -> list[QueryRanking]:
    rankings: list[QueryRanking] = []
    for question in questions:
        before = create_synthetic_results()
        started_at = timer()
        after = reranker.rerank(question, before, top_k=len(before))
        inference_seconds = timer() - started_at
        ranking = QueryRanking(
            question=question,
            before=before,
            after=after,
            inference_seconds=inference_seconds,
        )
        rankings.append(ranking)
        print(f"\nQuestion: {question}")
        print_ranking("Before reranking", ranking.before)
        print_ranking("After reranking (FlashRank scores)", ranking.after)
        print(f"Inference time: {ranking.inference_seconds:.6f} s")
    return rankings


def main(
    cache_dir: Path = DEFAULT_RERANKER_CACHE,
    reranker_factory: RerankerFactory = FlashRankReranker,
    timer: Timer = perf_counter,
) -> int:
    try:
        reranker, load_seconds = load_reranker(cache_dir, reranker_factory, timer)
        print(f"Model load time: {load_seconds:.6f} s")
        run_demo(reranker, timer=timer)
    except FileNotFoundError as error:
        print(f"Local FlashRank model unavailable: {error}")
        return 1
    except (RuntimeError, ValueError) as error:
        print(f"FlashRank demonstration failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
