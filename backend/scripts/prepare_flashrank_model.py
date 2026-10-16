import argparse
from pathlib import Path

from flashrank import Ranker

from app.services.reranking import DEFAULT_RERANKER_CACHE, DEFAULT_RERANKER_MODEL


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_RERANKER_CACHE)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    Ranker(
        model_name=DEFAULT_RERANKER_MODEL,
        cache_dir=str(arguments.output),
        max_length=512,
        log_level="WARNING",
    )


if __name__ == "__main__":
    main()
