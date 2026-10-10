# SecureBank-AI

## Project Overview

SecureBank-AI is a four-day R&D prototype of a secure multi-agent platform for Swiss banking compliance analysis. It is a portfolio project focused on AI solution architecture, integration engineering, evidence-grounded retrieval, deterministic security controls, and production-oriented API design.

The prototype treats FINMA expectations and the Swiss Federal Act on Data Protection (LPD) as design constraints. It is not FINMA-certified and does not guarantee regulatory or legal compliance.

## Project Objectives

- Build a modular API gateway for simulated compliance workflows.
- Enforce authentication, authorization, and sensitive-data controls in application code.
- Retrieve and validate supporting regulatory evidence before generating answers.
- Coordinate bounded AI agents and simulated banking tools.
- Make system behavior observable and reproducible.
- Use synthetic data only and perform no real banking action.

## Technology Stack

| Area | Implemented | Planned |
| --- | --- | --- |
| Backend API | FastAPI, Uvicorn, Python 3.12 | Modular API and service layers |
| Containerization | Docker image and Docker Compose service for the backend | Frontend Compose service |
| Continuous integration | Pull Request backend workflow | Frontend checks |
| Validation and configuration | Pydantic v2, pydantic-settings | Extended configuration contracts |
| Security | HS256 JWT validation, Bearer authentication, RBAC, local PII detection and masking | Token generation |
| Retrieval | Typed documents, character chunking, in-memory BM25, local multilingual embeddings, cosine similarity | Qdrant, hybrid retrieval, RRF, FlashRank |
| Orchestration and tools | None | LangGraph, FastMCP |
| Observability | None | Langfuse |
| Frontend | None | React 19, TypeScript, Vite |
| Deployment | None | Render backend, Vercel frontend |

The backend requirements file already declares packages for later iterations. A declared dependency does not mean that its related capability is implemented.

## System Architecture

The current runtime consists of one FastAPI application exposing a public health endpoint, protected authentication demonstration endpoints, and a protected PII masking endpoint. HTTP authentication and RBAC dependencies are separated from JWT validation, typed request and response schemas, and local PII services. The current RAG components represent source documents, split them into typed passages, search those passages with an in-memory lexical index, and generate local vector representations independently of the API. Future modules will be introduced only in the iteration that needs them.

## Repository Structure

```text
SECUREBANK-AI/
├── .github/
│   └── workflows/
│       └── backend-ci.yml
├── AGENTS.md
├── README.md
├── compose.yml
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── dependencies.py
│   │   │   └── pii.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── jwt.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── documents.py
│   │   │   ├── pii.py
│   │   │   └── retrieval.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── bm25.py
│   │   │   ├── chunking.py
│   │   │   ├── pii.py
│   │   │   └── pii_masking.py
│   │   └── main.py
│   ├── .dockerignore
│   ├── .env
│   ├── .env.example
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── requirements-dev.txt
│   ├── requirements-runtime.txt
│   ├── requirements.txt
│   ├── scripts/
│   │   ├── prepare_embedding_model.py
│   │   └── verify_embedding_model.py
│   ├── tests/
│   │   ├── test_bm25.py
│   │   ├── test_chunking.py
│   │   ├── test_embeddings.py
│   │   ├── test_config.py
│   │   ├── test_health.py
│   │   ├── test_pii.py
│   │   ├── test_pii_api.py
│   │   └── test_pii_masking.py
│   └── venv/
├── frontend/
└── main.py
```

`backend/.env`, virtual environments, and IDE files are excluded from version control. The root `main.py` is the original IDE sample and is not part of the backend runtime.

## Prerequisites

- Ubuntu
- Git with GitHub SSH access configured
- Python 3.12
- `python3.12-venv`
- `curl`
- Docker Engine for containerized execution

Node.js is not required until frontend development begins.

## Installation

Clone the repository and enter it:

```bash
git clone git@github.com:saucante74/SECUREBANK-AI.git
cd SECUREBANK-AI
```

Create and activate the backend virtual environment:

```bash
python3.12 -m venv backend/venv
source backend/venv/bin/activate
```

Install the declared backend dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

PII detection requires `presidio-analyzer` and the small French spaCy model `fr_core_news_sm`. Both are pinned in the requirement manifests and installed before local execution or during the Docker image build. Runtime analysis does not download models or call cloud services.

Local embeddings require `sentence-transformers==6.1.0`, which supports Python 3.12 and brings large numerical and machine-learning dependencies, including PyTorch and Transformers. The requirement manifests add the official PyTorch CPU wheel index and pin `torch==2.14.1+cpu`, so the standard installation command does not install CUDA or NVIDIA runtime packages. The installation host must be able to reach both PyPI and `https://download.pytorch.org/whl/cpu`.

## Environment Configuration

Create the local environment file from the committed example:

```bash
cp backend/.env.example backend/.env
```

The implemented configuration accepts these variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `securebank-ai` | FastAPI title and service name |
| `APP_VERSION` | `0.1.0` | FastAPI and health contract version |
| `APP_ENV` | `development` | Runtime environment label |
| `JWT_SECRET_KEY` | None | Shared secret used to verify JWT signatures |
| `JWT_ALGORITHM` | `HS256` | Explicitly allowed JWT signing algorithm |
| `JWT_ISSUER` | None | Required JWT issuer |
| `JWT_AUDIENCE` | None | Required JWT audience |

Environment variables override values loaded from `backend/.env`, which override the development defaults. Do not commit `.env` or place real banking data in it.

JWT settings remain optional at application startup, so the public health endpoint works without them. Access to protected endpoints is denied until a secret of at least 32 characters, an issuer, and an audience are configured. Replace every example value before using authentication outside local development.

## Running the Backend

From the repository root with the virtual environment active:

```bash
cd backend
uvicorn app.main:app --reload
```

The API listens on `http://127.0.0.1:8000` by default.

Test the health endpoint from another terminal:

```bash
curl --fail --silent --show-error http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"healthy","service":"securebank-ai","version":"0.1.0"}
```

### Running the Backend with Docker

Build the backend image from the backend build context:

```bash
docker build --tag securebank-ai-backend:0.1.0 backend
```

Run the container without loading a local environment file:

```bash
docker run --rm --name securebank-ai-backend --publish 8000:8000 securebank-ai-backend:0.1.0
```

Verify the health endpoint from another terminal:

```bash
curl --fail --silent --show-error http://127.0.0.1:8000/health
```

The container accepts a `PORT` environment variable for Render-compatible port binding and defaults to port `8000`.

### Running the Backend with Docker Compose

Build and start the backend service from the repository root:

```bash
docker compose up --build -d
```

Check the service status:

```bash
docker compose ps
```

Read the service logs:

```bash
docker compose logs
```

The backend is available at `http://localhost:8000`.

Stop and remove the Compose resources:

```bash
docker compose down
```

The frontend will be added to Docker Compose after the React application is initialized.

## Running the Frontend

**Planned.** The `frontend/` directory is currently empty, so there is no frontend installation or start command yet.

## Running Tests

From the repository root with the backend virtual environment active:

```bash
cd backend
python -m pytest
```

The tests cover configuration defaults, environment overrides, the health endpoint contract, JWT validation, Bearer authentication and RBAC, local PII detection and masking, deterministic document chunking, and in-memory BM25 retrieval.

### Local PII Detection and Masking

`PiiDetector` accepts French text and returns typed entities containing the entity type, start offset, end offset, and Presidio confidence score. It detects e-mail addresses, phone numbers, valid IBANs, and person names recognized by the French spaCy model. The component is a Python service independent of FastAPI and does not store or log analyzed text.

`PiiMasker` reuses those detected positions and replaces retained entities with `[EMAIL_ADDRESS]`, `[PHONE_NUMBER]`, `[IBAN_CODE]`, or `[PERSON]`. Detection identifies candidate spans, while masking creates a new transformed string without changing the original value. No restoration mechanism is provided.

Synthetic example:

```text
Before: Camille Martin utilise alice.dupont@example.com.
After:  [PERSON] utilise [EMAIL_ADDRESS].
```

When detections overlap, the masker prefers the highest confidence score, then the longest span, followed by position and entity type for deterministic resolution. Presidio can still produce false positives or false negatives. A missed entity remains visible in the transformed text, so masking does not guarantee exhaustive anonymization or regulatory compliance.

### RAG Documents and Chunking

Retrieval-Augmented Generation grounds a generated answer in passages retrieved from a source corpus. This iteration implements only the representation and chunking stage; retrieval and generation remain planned.

A `Document` stores a stable identifier, content, title, and source. `CharacterChunker` turns it into an ordered list of `Chunk` objects carrying the parent metadata and a deterministic identifier. `chunk_size` sets the maximum number of characters per passage. `overlap` repeats the end of one passage at the start of the next to preserve local context and must remain smaller than `chunk_size`.

For `abcdefghij`, `chunk_size=5` and `overlap=2` produce `abcde`, `defgh`, and `ghij`. Character boundaries are simple and reproducible, but they can split words, sentences, or semantic units. Token-aware and structure-aware chunking, document ingestion, dense retrieval, fusion, reranking, evidence validation, and answer generation remain planned.

### In-Memory BM25 Retrieval

BM25 is a lexical ranking algorithm: it scores chunks from the query terms they contain, their frequency, document length, and term rarity across the corpus. Semantic retrieval instead compares learned vector representations and can connect related meanings even when the exact words differ. Only lexical BM25 retrieval is implemented.

`BM25Retriever` receives typed chunks, removes duplicate identifiers while preserving their first occurrence, and builds a local `rank-bm25` index. A search returns typed results ordered by descending BM25 score, with the original chunk metadata intact. Ties preserve the initial chunk order. The index exists only in process memory and must be rebuilt after a restart.

Synthetic example:

```text
Chunks: "Contrôle du risque de crédit" | "Solde du compte bancaire"
Query:  "risque crédit"
Result: "Contrôle du risque de crédit"
```

Tokenization uses Unicode word sequences after case folding, so punctuation is separated and French accents are preserved. It does not perform stemming, lemmatization, stop-word removal, synonym expansion, spelling correction, or accent folding. Terms such as `conformité` and `conformite` are therefore distinct.

### Local Multilingual Embeddings

An embedding is a fixed-size numeric vector that represents a text so that related meanings can be compared geometrically. BM25 ranks exact or normalized lexical terms and remains effective for identifiers and precise wording. Semantic search compares embeddings and can retrieve related French passages even when a question uses different words. This iteration generates vectors and computes pairwise cosine similarity; it does not implement semantic retrieval or a vector index.

`LocalEmbeddingService` uses `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` on CPU. The model supports French and produces vectors with 384 dimensions. The service accepts one text, multiple texts, or existing `Chunk` contents, preserves input order, and loads the encoder once per service instance. Empty or whitespace-only texts are rejected, and no input text is stored or logged.

The default local model directory is `backend/models/paraphrase-multilingual-MiniLM-L12-v2`. A different `pathlib.Path` can be passed to the service constructor. Runtime loading sets `local_files_only=True`, so the backend fails if the prepared files are absent instead of downloading them implicitly.

Prepare the weights explicitly from the backend directory in an environment with network access:

```bash
cd backend
python -m scripts.prepare_embedding_model
```

An alternative source model or destination can be selected explicitly:

```bash
python -m scripts.prepare_embedding_model \
  --model-name sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 \
  --output /srv/securebank/models/paraphrase-multilingual-MiniLM-L12-v2
```

After preparing the default local model, run the reproducible offline verification:

```bash
python -m scripts.verify_embedding_model
```

The command validates a real 384-dimensional finite embedding, compares related and unrelated French questions, and reports the measured model loading time and process peak resident memory on Ubuntu. It enables the Hugging Face and Transformers offline modes before loading the model.

The prepared weights must be provisioned before production startup. The local prepared model occupies approximately 466 MB. In the validated Python 3.12 environment, the CPU-only PyTorch package occupies approximately 769 MB and installs no NVIDIA, CUDA, or Triton package. CPU inference needs enough RAM for the model, Python runtime, and temporary tensors, commonly around 1 GB or more depending on batch size and package versions. Loading and encoding time depend on the host CPU, storage, text length, and batch size; no latency guarantee is claimed.

The model limit is 128 tokens including special tokens. The service measures untruncated tokenization and raises `ValueError` above that limit instead of silently truncating text. Character count is not equivalent to token count. Upstream chunk sizes must therefore be selected and validated against this token limit.

Cosine similarity measures vector direction from `-1` to `1`; larger values indicate closer directions for this embedding space. It is a ranking signal, not a calibrated probability or proof that two texts have the same regulatory meaning. Empty, zero-length, zero-norm, dimension-mismatched, and non-finite vectors are rejected.

## API Documentation

With the backend running, open Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

Current endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Reports service availability, identity, and version |
| `GET` | `/auth/me` | Returns the authenticated `sub` and `role` |
| `GET` | `/auth/analyst` | Allows `analyst`, `compliance_officer`, and `admin` |
| `GET` | `/auth/admin` | Allows only `admin` |
| `POST` | `/pii/mask` | Masks detected PII for authenticated and authorized users |

Call the protected endpoint with an existing token:

```bash
curl --fail --silent --show-error \
  --header "Authorization: Bearer ${JWT_TOKEN}" \
  http://127.0.0.1:8000/auth/me
```

A valid HS256 token with matching `exp`, `iss`, `aud`, non-empty `sub`, and a recognized `role` can establish an authenticated identity. Missing or invalid credentials return HTTP 401 with `WWW-Authenticate: Bearer`. An authenticated identity without an explicitly allowed role receives HTTP 403. The application does not issue tokens.

Available roles:

- `analyst`
- `compliance_officer`
- `admin`

RBAC denies access unless an endpoint explicitly lists the authenticated role. The role comes only from the cryptographically verified JWT claim; it is never accepted from request parameters, custom headers, or request bodies.

### PII Masking API

`POST /pii/mask` requires a valid Bearer JWT with the `analyst`, `compliance_officer`, or `admin` role. The JSON request contains one string field between 1 and 10,000 characters and cannot contain only whitespace:

```json
{"text":"Camille Martin utilise alice.dupont@example.com."}
```

The response contains only the transformed text:

```json
{"masked_text":"[PERSON] utilise [EMAIL_ADDRESS]."}
```

Missing, invalid, or expired credentials return HTTP 401 with `WWW-Authenticate: Bearer`. An authenticated identity without an allowed role returns HTTP 403. Invalid request data returns HTTP 422 with sanitized validation details that exclude the submitted value. The endpoint does not return detected values, positions, confidence scores, or the original text.

## Security Considerations

- The repository must contain no secrets or real banking data.
- Development data must be synthetic.
- JWT validation verifies HS256 signatures and requires valid `exp`, `iss`, `aud`, and non-empty `sub` claims.
- Bearer authentication requires a recognized, non-empty `role` claim and returns the authenticated subject and role from `GET /auth/me`.
- RBAC protects demonstration endpoints with explicit role allowlists and denies authenticated users with HTTP 403 when their role is insufficient.
- PII detection runs locally with Presidio Analyzer and a French spaCy model; analyzed values are neither persisted nor logged by the service.
- PII masking replaces detected values locally with typed markers and provides no restoration mechanism.
- The protected PII endpoint sanitizes validation errors so rejected request values are not echoed in HTTP 422 responses.
- E-mail validation uses the public-suffix snapshot bundled with `tldextract` and performs no runtime network refresh.
- Token generation is not implemented.
- In production, a trusted identity system must assign roles. Permission changes may require token revocation or short expiration because an issued JWT retains its embedded role until it expires or is revoked.
- Future authorization decisions will remain deterministic and outside LLM control.
- Sensitive data must be anonymized before transmission to external services.
- The prototype must not be represented as FINMA-certified or as guaranteeing LPD compliance.

## Continuous Integration

The backend workflow is implemented in `.github/workflows/ci.yml`. It runs Ruff linting, Ruff format verification, and pytest with Python 3.12. Docker image builds remain available for local validation and are not part of the CI workflow.

The workflow executes exclusively for Pull Requests that are opened, synchronized with new commits, or reopened. A push to a branch without an open Pull Request does not trigger it. A push to a branch with an open Pull Request triggers it through the `pull_request` `synchronize` activity.

The workflow uses read-only repository permissions and requires no secrets. It performs validation only: it does not deploy services, push Docker images, modify code, or create commits. Frontend checks remain planned.

The workflow configuration and all equivalent checks have been validated locally. GitHub Actions execution remains unverified until a Pull Request runs the workflow successfully.

## Deployment

The backend has a production-oriented Docker image and a local Docker Compose service. Cloud deployment remains **planned**, with Render targeted for the backend and Vercel for the frontend. Hosted environments are not implemented.

## Development Roadmap

| Day | Scope | Status |
| --- | --- | --- |
| Day 1 | FastAPI gateway, health check, settings, JWT, RBAC, PII detection and masking, security tests | In Progress: health check, settings, JWT authentication, RBAC, PII detection, masking, and protected PII API completed |
| Day 2 | Regulatory corpus, chunking, embeddings, Qdrant, BM25, RRF, reranking, evidence validation, abstention | In Progress: document models, character chunking, in-memory BM25, and local embeddings completed |
| Day 3 | Independent FastMCP server, simulated tools, MCP client, LangGraph state and routing | Planned |
| Day 4 | Langfuse, tracing, evaluation, documentation, frontend integration, deployment | Planned |

## Current Implementation Status

### Implemented

- Minimal typed FastAPI application.
- Asynchronous `GET /health` endpoint.
- HTTP 200 health response with the documented JSON contract.
- Automatically generated Swagger UI at `/docs`.
- Iteration 1 validated against a live Uvicorn server.
- Typed application settings with development defaults and environment overrides.
- Configuration tests and health contract regression test.
- Independent JWT validator for HS256 signatures and required `exp`, `iss`, `aud`, and non-empty `sub` claims.
- Deterministic JWT validation tests using synthetic tokens and secrets.
- Reusable FastAPI Bearer authentication dependency.
- Typed roles for `analyst`, `compliance_officer`, and `admin`.
- Reusable deny-by-default RBAC dependency with explicit role allowlists.
- Protected authentication demonstration endpoints for identity, analyst access, and admin access.
- Local typed PII detection for e-mail addresses, phone numbers, IBANs, and French person names.
- Deterministic local PII masking with typed markers and overlap resolution.
- Protected `POST /pii/mask` endpoint with sanitized validation errors.
- Immutable document and chunk contracts with deterministic character chunking.
- Deterministic in-memory BM25 retrieval with typed scored results.
- Local multilingual embeddings for text and chunks with deterministic input validation.
- Independent cosine similarity with vector validation.
- Reproducible offline validation with the prepared local embedding model.
- Backend Docker image using Python 3.12 slim and a non-root runtime user.
- Backend Docker Compose service exposed on local port `8000`.
- Pull Request-only backend GitHub Actions workflow.

### In Progress

- Day 1 API gateway and security foundation.

### Planned

- Token generation and token revocation.
- Document ingestion, vector storage, dense retrieval, reciprocal rank fusion, reranking, evidence validation, and abstention.
- FastMCP and LangGraph orchestration.
- Langfuse observability.
- React frontend and cloud deployment.

## Known Limitations

- Only the health endpoint, application settings, JWT validation, Bearer authentication, demonstration RBAC, local PII detection and masking, and the protected masking endpoint are implemented.
- PII detection is probabilistic and may produce false positives or false negatives, especially for person names and ambiguous number formats. It does not guarantee exhaustive identification of sensitive data.
- False negatives remain unmasked in transformed text. The masking service and endpoint reduce exposure risk without guaranteeing complete anonymization or regulatory compliance.
- Character chunking can split words and semantic units because it does not understand tokens, sentences, or document structure.
- BM25 matches lexical tokens only, does not understand meaning or synonyms, and has no persistent index.
- The embedding model rejects texts above its 128-token limit and does not split them automatically.
- Cosine similarity is uncalibrated and cannot establish answer correctness or sufficient evidence by itself.
- Local embedding inference increases installation size, startup time, CPU use, and RAM use; performance has not been benchmarked for this project.
- There is no token generation, user directory, token revocation, dense retrieval, vector database, RAG generation pipeline, agent orchestration, MCP server, observability, frontend, or deployment configuration.
- Docker Compose currently starts only the backend; frontend integration is planned after the React application is initialized.
- The backend workflow has not yet been executed and validated by GitHub Actions on a Pull Request.
- The dependency manifest includes packages reserved for future iterations.
- The existing backend virtual environment reports Python 3.12.13; the project supports Python 3.12.x.
- The API version is currently defined directly in the FastAPI application and health response.
