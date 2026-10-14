import argparse
from pathlib import Path

from sentence_transformers import SentenceTransformer

from app.services.embeddings import DEFAULT_MODEL_NAME, DEFAULT_MODEL_PATH


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--output", type=Path, default=DEFAULT_MODEL_PATH)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    model = SentenceTransformer(arguments.model_name, device="cpu")
    model.save_pretrained(str(arguments.output))


if __name__ == "__main__":
    main()
