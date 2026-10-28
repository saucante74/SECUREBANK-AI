from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_backend_compose_service_loads_backend_environment() -> None:
    compose_content = (REPOSITORY_ROOT / "compose.yml").read_text(encoding="utf-8")
    backend_service = compose_content.split("  backend:\n", maxsplit=1)[1].split(
        "  qdrant:\n", maxsplit=1
    )[0]

    assert "    env_file:\n      - ./backend/.env\n" in backend_service
    assert "      QDRANT_URL: http://qdrant:6333\n" in backend_service
    assert (
        "      RAG_CORPUS_PATH: /app/data/rag_integration_corpus.json\n"
        in backend_service
    )


def test_backend_image_includes_rag_runtime_assets() -> None:
    dockerfile = (REPOSITORY_ROOT / "backend" / "Dockerfile").read_text(
        encoding="utf-8"
    )

    assert "COPY --chown=app:app data ./data\n" in dockerfile
    assert (
        "COPY --chown=app:app models/paraphrase-multilingual-MiniLM-L12-v2 "
        "./models/paraphrase-multilingual-MiniLM-L12-v2\n" in dockerfile
    )
