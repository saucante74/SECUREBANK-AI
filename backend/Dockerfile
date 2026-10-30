FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /nonexistent --shell /usr/sbin/nologin app \
    && mkdir --parents /app/runtime \
    && chown app:app /app/runtime

COPY requirements-runtime.txt ./requirements-runtime.txt

RUN pip install --no-cache-dir --disable-pip-version-check -r requirements-runtime.txt

COPY --chown=app:app app ./app
COPY --chown=app:app scripts/create_user.py ./scripts/create_user.py
COPY --chown=app:app data ./data
COPY --chown=app:app models/paraphrase-multilingual-MiniLM-L12-v2 ./models/paraphrase-multilingual-MiniLM-L12-v2

USER app

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
