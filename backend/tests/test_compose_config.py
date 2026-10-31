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
    assert "      USER_DATABASE_PATH: /app/runtime/users.sqlite3\n" in backend_service
    assert "    volumes:\n      - securebank_users:/app/runtime\n" in backend_service
    assert "    healthcheck:\n" in backend_service
    assert "http://127.0.0.1:8000/health" in backend_service

    volumes = compose_content.rsplit("volumes:\n", maxsplit=1)[1]
    assert "  qdrant_data:\n" in volumes
    assert "  securebank_users:\n" in volumes


def test_frontend_waits_for_healthy_backend() -> None:
    compose_content = (REPOSITORY_ROOT / "compose.yml").read_text(encoding="utf-8")

    assert (
        "    depends_on:\n      backend:\n        condition: service_healthy\n"
        in compose_content
    )


def test_frontend_proxy_uses_docker_dns_runtime_resolution() -> None:
    nginx_content = (REPOSITORY_ROOT / "frontend" / "nginx.conf").read_text(
        encoding="utf-8"
    )

    assert "resolver 127.0.0.11 valid=10s ipv6=off;" in nginx_content
    assert "rewrite ^/api/(.*)$ /$1 break;" in nginx_content
    assert "proxy_pass $backend_upstream;" in nginx_content


def test_backend_image_includes_rag_runtime_assets() -> None:
    dockerfile = (REPOSITORY_ROOT / "backend" / "Dockerfile").read_text(
        encoding="utf-8"
    )

    assert "COPY --chown=app:app data ./data\n" in dockerfile
    assert (
        "COPY --chown=app:app scripts/create_user.py ./scripts/create_user.py\n"
        in dockerfile
    )
    assert (
        "COPY --chown=app:app models/paraphrase-multilingual-MiniLM-L12-v2 "
        "./models/paraphrase-multilingual-MiniLM-L12-v2\n" in dockerfile
    )
    assert "    && mkdir --parents /app/runtime \\\n" in dockerfile
    assert "    && chown app:app /app/runtime\n" in dockerfile


def test_backend_image_excludes_sqlite_databases() -> None:
    dockerignore = (REPOSITORY_ROOT / "backend" / ".dockerignore").read_text(
        encoding="utf-8"
    )

    assert "*.db\n" in dockerignore
    assert "*.sqlite\n" in dockerignore
    assert "*.sqlite3\n" in dockerignore
