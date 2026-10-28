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
| Retrieval | Typed documents, character chunking, in-memory BM25, local multilingual embeddings, cosine similarity, Qdrant vector storage and search, RRF, hybrid retrieval, and FlashRank reranking orchestration | Semantic evidence validation |
| Generation | Configurable OpenAI-compatible LLM service, lazy RAG factory, RAG context, citation mapping, and explicit abstention | Semantic evidence validation |
| Orchestration and tools | None | LangGraph, FastMCP |
| Observability | Privacy-preserving RAG instrumentation, no-op default, and conditional Langfuse Python SDK 4.17.0 client | Live-server validation, dashboards, and alerts |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Vitest, i18next, native navigation, multilingual Assistant UI, typed native-fetch API client, development-only JWT connection | Production authentication and business interfaces |
| Deployment | None | Render backend, Vercel frontend |

The backend requirements file already declares packages for later iterations. A declared dependency does not mean that its related capability is implemented.

## System Architecture

The current runtime consists of one FastAPI application and a Qdrant vector database. The API exposes a public health endpoint, protected authentication demonstration endpoints, a protected PII masking endpoint, and a protected generative RAG endpoint that is disabled by default. HTTP authentication and RBAC dependencies are separated from JWT validation, typed request and response schemas, and local PII services. When enabled and configured, the generative RAG pipeline retrieves lexical BM25 and semantic MiniLM/Qdrant candidates and fuses both rankings with RRF. FlashRank remains available as an independent retrieval experiment but is not part of the default generative pipeline. `RagGenerationService` emits privacy-preserving lifecycle measurements through an injected typed observer and uses a stateless no-op observer by default.

## Repository Structure

```text
SECUREBANK-AI/
├── .github/
│   └── workflows/
│       └── backend-ci.yml
├── AGENTS.md
├── README.md
├── .env.langfuse.example
├── compose.langfuse.yml
├── compose.yml
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── dependencies.py
│   │   │   ├── pii.py
│   │   │   ├── rag.py
│   │   │   └── validation.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── jwt.py
│   │   │   └── rag_factory.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── documents.py
│   │   │   ├── evaluation.py
│   │   │   ├── pii.py
│   │   │   ├── rag_generation.py
│   │   │   └── retrieval.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── benchmark_dataset.py
│   │   │   ├── bm25.py
│   │   │   ├── chunking.py
│   │   │   ├── embeddings.py
│   │   │   ├── hybrid.py
│   │   │   ├── llm.py
│   │   │   ├── pii.py
│   │   │   ├── pii_masking.py
│   │   │   ├── qdrant.py
│   │   │   ├── rag_corpus.py
│   │   │   ├── rag_generation.py
│   │   │   ├── rag_observer.py
│   │   │   ├── rag_retrieval.py
│   │   │   ├── reranking.py
│   │   │   ├── retrieval_evaluation.py
│   │   │   └── rrf.py
│   │   └── main.py
│   ├── .dockerignore
│   ├── data/
│   │   └── rag_benchmark.json
│   ├── .env
│   ├── .env.example
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── requirements-dev.txt
│   ├── requirements-runtime.txt
│   ├── requirements.txt
│   ├── scripts/
│   │   ├── compare_retrievers.py
│   │   ├── demo_flashrank.py
│   │   ├── demo_hybrid_search.py
│   │   ├── demo_rag_retrieval.py
│   │   ├── demo_vector_search.py
│   │   ├── prepare_flashrank_model.py
│   │   ├── prepare_embedding_model.py
│   │   └── verify_embedding_model.py
│   ├── tests/
│   │   ├── test_benchmark_dataset.py
│   │   ├── test_compare_retrievers.py
│   │   ├── test_demo_flashrank.py
│   │   ├── test_demo_hybrid_search.py
│   │   ├── test_demo_rag_retrieval.py
│   │   ├── test_demo_vector_search.py
│   │   ├── test_bm25.py
│   │   ├── test_chunking.py
│   │   ├── test_embeddings.py
│   │   ├── test_config.py
│   │   ├── test_health.py
│   │   ├── test_hybrid.py
│   │   ├── test_pii.py
│   │   ├── test_pii_api.py
│   │   ├── test_pii_masking.py
│   │   ├── test_qdrant.py
│   │   ├── test_rag_api.py
│   │   ├── test_rag_corpus.py
│   │   ├── test_rag_factory.py
│   │   ├── test_rag_retrieval.py
│   │   ├── test_reranking.py
│   │   ├── test_retrieval_evaluation.py
│   │   └── test_rrf.py
│   └── venv/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── pages/
│   │   └── test/
│   ├── README.md
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── vite.config.ts
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
- Docker Compose v2 for the application and isolated Langfuse stacks
- OpenSSL for generating local Langfuse secrets

- Node.js 24 or later and npm 11 or later for frontend development

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
| `USER_DATABASE_PATH` | `backend/data/users.sqlite3` | Persistent SQLite user database path |
| `SESSION_LIFETIME_SECONDS` | `900` | Maximum server-side session lifetime |
| `SESSION_COOKIE_SECURE` | `false` | Sends session cookies only over HTTPS when enabled |
| `SESSION_COOKIE_SAMESITE` | `lax` | Session and CSRF cookie SameSite policy |
| `AUTH_TRUSTED_ORIGINS` | Local Vite and Compose origins | Comma-separated origins allowed to submit credentials |
| `LOGIN_ATTEMPT_LIMIT` | `5` | Failed attempts allowed during one rate-limit window |
| `LOGIN_ATTEMPT_WINDOW_SECONDS` | `300` | Persistent login rate-limit window |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant HTTP endpoint |
| `QDRANT_COLLECTION_NAME` | `securebank_chunks` | Collection used for chunk vectors |
| `RAG_ENABLED` | `false` | Enables lazy construction of the generative RAG pipeline |
| `RAG_CORPUS_PATH` | None | Path to the local JSON corpus used by BM25 and Qdrant |
| `LLM_API_KEY` | None | Secret credential for the configured LLM provider |
| `LLM_MODEL` | `gpt-4.1-mini` | Model identifier sent to the LLM provider |
| `LLM_BASE_URL` | None | Optional base URL for an OpenAI-compatible provider |
| `LLM_TIMEOUT_SECONDS` | `30` | Positive request timeout in seconds |
| `LANGFUSE_ENABLED` | `false` | Enables construction of the Langfuse SDK client with the lazy RAG pipeline |
| `LANGFUSE_PUBLIC_KEY` | None | Public project key required only when observability is enabled |
| `LANGFUSE_SECRET_KEY` | None | Secret project key required only when observability is enabled |
| `LANGFUSE_HOST` | `http://localhost:3000` | Configurable Langfuse HTTP endpoint |

Environment variables override values loaded from `backend/.env`, which override the development defaults. Do not commit `.env` or place real banking data in it.

JWT settings remain optional at application startup, so the public health endpoint works without them. Access to protected endpoints is denied until a secret of at least 32 characters, an issuer, and an audience are configured. Replace every example value before using authentication outside local development.

Cookie sessions are stored server-side in the SQLite user database. Set `SESSION_COOKIE_SECURE=true` for HTTPS deployments; production configuration rejects insecure session cookies. `SameSite=None` is accepted only with a secure cookie. Add every frontend origin that may submit credentials to `AUTH_TRUSTED_ORIGINS`. The default `lax` policy is appropriate for the same-origin Vite and Nginx proxy architecture.

The LLM API key is also optional at application startup. Creating a real LLM client requires it. To use an OpenAI-compatible provider, set `LLM_API_KEY`, set the provider's model identifier in `LLM_MODEL`, and set `LLM_BASE_URL` to its API base URL. Leave `LLM_BASE_URL` empty for the official OpenAI endpoint. Keep provider credentials only in the untracked `.env` file or a deployment secret store.

Langfuse observability is disabled by default. When `LANGFUSE_ENABLED=false`, both keys may remain empty and the application creates no Langfuse client or network connection. Enabling the setting requires both keys and a valid HTTP or HTTPS host. The lazy RAG factory then constructs the official Langfuse Python SDK 4.17.0 client explicitly with those values. Both keys are represented with Pydantic `SecretStr`, and configuration errors hide their input values. An SDK initialization failure falls back to the no-op observer and does not prevent construction of the RAG pipeline.

The generative pipeline remains disabled while `RAG_ENABLED=false`. Enabling it also requires `RAG_CORPUS_PATH`, `LLM_API_KEY`, the existing Qdrant settings, a running Qdrant service, and the locally prepared MiniLM and Presidio models. The application loads none of these resources during import or startup. The first authorized RAG request loads and chunks the corpus, creates its local embeddings, upserts the same chunks into Qdrant, builds BM25, Qdrant, RRF, PII, and LLM services, and caches the resulting pipeline for later requests. Concurrent first requests are serialized during construction so only one cached instance is published. The standalone PII endpoint also initializes its cached masker only on first use.

`RAG_CORPUS_PATH` must point to a UTF-8 JSON file with a non-empty `documents` array. Each item follows the existing `Document` contract:

```json
{
  "documents": [
    {
      "id": "synthetic-policy",
      "content": "Synthetic regulatory content.",
      "title": "Synthetic policy",
      "source": "synthetic://policy"
    }
  ]
}
```

Use only synthetic or otherwise approved content. The benchmark dataset is never selected implicitly and is not a production corpus. A missing or invalid corpus, a missing LLM key, or a disabled pipeline produces HTTP 503 with a generic message. An unavailable local model or Qdrant service also produces a non-sensitive HTTP 503. Programming errors are not converted into configuration errors.

### LLM Generation Service

`OpenAILLMService` is an independent text-generation boundary. It sends the configured model, a minimal French system instruction, and the caller's prompt through the official SDK Responses API, then returns only the generated text. Its injected client contract allows unit tests to run with no network access.

Contract tests inject a test-only fake Responses client into `OpenAILLMService` and compose that real provider service with `RagGenerationService`. They verify request parameters, text extraction, empty and provider-error translation, strict JSON and citation validation, abstention, and PII masking before and after generation without an API key, network access, or OpenAI cost.

Generation and retrieval remain separate service boundaries. `OpenAILLMService` does not retrieve BM25 or Qdrant results, invoke RRF or FlashRank, add documents, validate evidence, or produce citations. `RagGenerationService` composes it with retrieval without adding those responsibilities to the LLM service.

Prompts are transmitted to the selected external provider when the service is called. Callers must mask sensitive data before transmission and assess the provider's retention, hosting, and confidentiality controls. The service does not log prompts, and its public errors omit provider details and credentials.

### Manual OpenAI Smoke Test

The manual smoke test checks one minimal call through the production `OpenAILLMService` and the OpenAI Responses API. It uses a fixed public arithmetic question and does not load the RAG corpus, Qdrant, embeddings, or banking data. It is a provider connectivity check, not a complete RAG validation.

The script is disarmed by default. This preparation command does not load the OpenAI configuration, construct a client, or make a network call:

```bash
cd backend
./venv/bin/python -m scripts.run_openai_smoke_test
```

To perform the manual test, configure `LLM_API_KEY` and optionally the existing `LLM_MODEL` and `LLM_BASE_URL` settings. Then explicitly authorize the single real call:

```bash
cd backend
./venv/bin/python -m scripts.run_openai_smoke_test --allow-real-openai-call
```

A real call can incur API charges. The authorized path uses a 15-second timeout, disables automatic retries, and makes at most one provider request. It prints only a generic success or failure status; it never prints the key, prompt, raw response, or HTTP headers. Never replace the fixed question with sensitive, personal, confidential, or banking data.

This smoke test confirms only that the configured provider can return a non-empty response. It does not evaluate answer quality, structured RAG output, retrieval, citation grounding, PII detection, or end-to-end application security. Automated tests inject local fakes and never contact OpenAI.

### Generative RAG Pipeline

`RagGenerationService` connects the existing `HybridRetriever` contract to the independent `LLMService` contract through dependency injection. It requests the configured number of BM25 and Qdrant results fused by RRF, preserves their order and metadata, builds a deterministic French prompt, and returns the generated answer with the chunks used as sources.

Before retrieval, the service applies local PII detection and masking to the user question. Only the masked question is sent to BM25, the local embedding service, Qdrant, and the prompt builder. After retrieval, it creates new immutable chunk values with masked `content`, `title`, and `source` fields. The original chunks remain untouched, and only these masked copies are sent to the LLM and exposed as HTTP sources. Chunk and document identifiers are preserved for citation mapping and must therefore remain opaque identifiers without personal data.

After the LLM response has passed JSON and citation validation, its answer text is checked and masked again. The service verifies that masking did not alter the ordered numeric citation references. A PII detector failure, unavailable detector, invalid masking result, or changed citation structure fails closed: generation stops before the LLM when possible, and no unchecked answer or original text is returned.

The default pipeline uses hybrid RRF results directly and does not invoke FlashRank. Retrieved passage content is serialized as untrusted JSON data, and the prompt tells the model to ignore instructions found inside documents, use no external knowledge, cite document-based claims, and answer only from the supplied passages.

The LLM must return only this JSON structure:

```json
{
  "answer": "Réponse en français avec références [1], [2]...",
  "abstained": false
}
```

Each `[n]` refers to the passage numbered `n` in the prompt. The RAG layer parses the JSON strictly, rejects missing or incorrectly typed fields, requires at least one valid reference for a factual answer, and derives each citation's document and chunk identifiers from the retrieved chunks rather than trusting identifiers generated by the LLM. Repeated references are deduplicated in their first-appearance order while all retrieved source metadata remains available in the result.

If retrieval returns no passage, the service skips generation and returns its deterministic no-passage answer with `abstained=true` and no citations. The model can also request abstention with `{"answer":"Les passages fournis ne permettent pas de répondre.","abstained":true}`; the service then replaces the model text with the same deterministic abstention answer and returns no citations. Invalid JSON, malformed output, unknown references, and uncited non-abstained answers raise a safe application error without exposing the raw provider response.

Citation validation proves only that a cited chunk was present in the supplied context. It does not verify that the chunk supports each claim, detect contradictions, establish answer correctness, or prevent hallucinations. The pipeline remains unsuitable for autonomous banking or compliance decisions.

### RAG API

`POST /rag/ask` exposes the generative RAG orchestration through a typed FastAPI contract. It requires a valid Bearer JWT and permits the `analyst`, `compliance_officer`, and `admin` roles. The question must contain non-whitespace characters and at most 2,000 characters. `top_k` defaults to 3 and accepts values from 1 through 5.

Synthetic request example:

```bash
curl --fail-with-body --request POST http://127.0.0.1:8000/rag/ask \
  --header "Authorization: Bearer ${SYNTHETIC_TEST_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"question":"Quelle règle synthétique est applicable ?","top_k":3}'
```

Example response:

```json
{
  "question": "Quelle règle synthétique est applicable ?",
  "answer": "La règle synthétique s'applique [1].",
  "sources": [
    {
      "id": "chunk-1",
      "document_id": "document-1",
      "content": "Passage réglementaire synthétique.",
      "position": 0,
      "title": "Document synthétique",
      "source": "synthetic://document-1"
    }
  ],
  "citations": [
    {
      "reference": 1,
      "document_id": "document-1",
      "chunk_id": "chunk-1"
    }
  ],
  "abstained": false
}
```

The application does not construct an OpenAI client, load an embedding or Presidio model, read the RAG corpus, or connect to Qdrant at startup. With `RAG_ENABLED=false`, the endpoint returns HTTP 503 before calling the factory. When enabled, missing configuration, unavailable construction dependencies, and PII protection failures return HTTP 503 with non-sensitive messages. Malformed provider output and LLM failures return HTTP 502, while authentication, authorization, and request-validation failures follow the existing 401, 403, and 422 contracts.

The endpoint masks detected PII in questions, retrieved passage text, exposed source metadata, and generated answers. Only masked prompt data is sent to the configured LLM provider. Presidio is probabilistic, so undetected values may still be transmitted or returned. Provider hosting, retention, access, and confidentiality controls must still be assessed. The implementation does not guarantee anonymization, GDPR compliance, Swiss data-protection compliance, or suitability for real banking data. Unit and API tests use synthetic fakes; no real OpenAI request or live Qdrant RAG request has been tested.

### RAG Pipeline Instrumentation

`RagGenerationService` emits four ordered lifecycle events through the injected `RagObserver`: request started; retrieval completed with its `time.perf_counter()` duration and passage count; generation completed with its duration and safe configured model name; and request completed with the closed `success` or `error` status. A no-passage abstention omits the generation event because no LLM call occurs. Retrieval, LLM, response-validation, and later pipeline failures produce an `error` completion event while preserving the original exception.

`NoOpRagObserver` is injected when callers provide no observer. It stores and transmits nothing, so observability remains disabled by default. Each observer callback is isolated from the pipeline: an observer exception is ignored, does not alter the RAG result or business error, and never retries generation.

`LangfuseRagObserver` is an optional adapter behind the same observer contract. It translates lifecycle callbacks into calls on the injected `LangfuseObservationClient`. This small typed client protocol remains an internal application boundary. `LangfuseSdkObservationClient` implements it with the official Langfuse Python SDK 4.17.0 API. The selected package declares Python 3.10 through 3.x support, Pydantic 2.x, and HTTPX below 1.0, which are compatible with the pinned Python 3.12, Pydantic 2.13.5, and HTTPX 0.28.1 environment.

The adapter creates one random technical trace identifier at request start and stores it in a private Python `ContextVar`. Retrieval, generation, and completion operations reuse that identifier. Context-local state keeps concurrent threads and asynchronous tasks independent without global mutable state, provided every callback for one request remains in the same execution context. The current synchronous RAG pipeline satisfies this condition. An abstention is represented as a successful trace because the existing observer contract intentionally contains no answer outcome or business content; a no-passage result has retrieval and successful completion operations without a generation operation.

Every internal client operation is isolated. A client failure is discarded without changing the RAG result, replacing a business exception, or retrying the LLM. The adapter does not log client exceptions. The concrete client removes completed trace state even when final status recording fails.

The concrete client creates one `rag-request` root observation, a `rag-retrieval` child, and, when generation occurs, a `rag-generation` child. It exports only the technical trace identifier, fixed numeric `duration_seconds` and `passage_count` metadata, the configured model name, and the closed `success` or `error` status. Questions, prompts, answers, document content, document titles and sources, citations, personal data, JWTs, API keys, raw exceptions, and arbitrary metadata dictionaries are explicitly forbidden. The client supplies no `input` or `output` value. Model identifiers must remain technical configuration values and must not contain user or document data.

The client uses direct SDK observation calls only. It does not enable the Langfuse OpenAI wrapper, decorators, prompt management, or automatic application instrumentation, so it does not automatically capture prompts or responses through this integration. The SDK export filter is explicitly restricted with its official `is_langfuse_span` predicate instead of the broader default filter that also accepts known third-party LLM instrumentation spans. SDK import and client construction occur only inside the enabled lazy factory path; importing the application performs neither action. Tests inject a fake SDK and perform no network request. No trace has been validated against a real Langfuse server, so server ingestion, persistence, dashboards, retention, access controls, and failure behavior remain unverified. Timing, passage counts, model names, and request status can still reveal usage patterns, and these measurements provide no proof of regulatory compliance.

The first local server validation remains an explicit manual operation. Follow [Local Langfuse Validation](docs/langfuse-local-validation.md) to prepare ignored secrets, start and stop the isolated stack without deleting volumes, submit one content-free synthetic trace without OpenAI, inspect its fields, and disable observability again. Langfuse is optional, and telemetry is not a complete business, security, or compliance audit.

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

Build and start the backend and Qdrant services from the repository root:

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

Compose loads the ignored `backend/.env` file into the backend container at runtime. The local JWT generator and the container therefore use the same `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ISSUER`, and `JWT_AUDIENCE` values. The explicit Compose `QDRANT_URL` value still overrides the host-oriented value so the backend reaches Qdrant through the internal service name. The environment file is not copied into the image and must never be committed or printed.

The backend image includes the committed synthetic integration corpus and the locally prepared MiniLM embedding directory. Compose selects `/app/data/rag_integration_corpus.json` through the existing `RAG_CORPUS_PATH` setting. Before building the image on a fresh clone, prepare the ignored local embedding model from `backend/` with `venv/bin/python -m scripts.prepare_embedding_model`. The build fails instead of downloading a model implicitly when that directory is absent.

The backend is available at `http://localhost:8000`, and Qdrant exposes its HTTP API at `http://localhost:6333`. Its dashboard is available at `http://localhost:6333/dashboard`. The named `qdrant_data` volume preserves vector data across container restarts.

Stop and remove the Compose resources:

```bash
docker compose down
```

The frontend is included in Docker Compose and is served locally through Nginx on port `8080`.

### Running Langfuse Locally

The dedicated `compose.langfuse.yml` follows the current Langfuse v4 self-hosting architecture. It runs independently from `compose.yml` under the `securebank-langfuse` Compose project, so its containers, default network, and named volumes do not overlap with the backend and Qdrant stack.

Langfuse v4 requires six services: the web application, an asynchronous worker, PostgreSQL for transactional data, ClickHouse for traces and analytics, Redis for queues and caching, and MinIO for event and media object storage. For a VM deployment, the official Langfuse guide recommends at least 4 CPU cores, 16 GiB of memory, and sufficient disk for accumulated traces, with 100 GiB given as an example. Local evaluation requirements depend on workload, but all six containers must fit in available memory and disk.

Create the ignored local configuration:

```bash
cp .env.langfuse.example .env.langfuse
```

Replace every `replace-with-...` value in `.env.langfuse`. Generate independent local values with commands such as:

```bash
openssl rand -base64 32
openssl rand -hex 32
openssl rand -hex 24
```

Use URL-safe hexadecimal output for `POSTGRES_PASSWORD` because it is embedded in the PostgreSQL connection URL. Do not reuse credentials, commit `.env.langfuse`, paste its contents into logs, or use these local values in another environment.

Validate the resolved Compose model without printing its environment:

```bash
docker compose --project-name securebank-langfuse \
  --env-file .env.langfuse \
  -f compose.langfuse.yml config --quiet
```

Starting the stack downloads several large images and requires explicit approval in this project workflow:

```bash
docker compose --project-name securebank-langfuse \
  --env-file .env.langfuse \
  -f compose.langfuse.yml up -d
```

Allow approximately two to three minutes for the initial startup, then open `http://localhost:3000`. There is no default account. Create the first local user, organization, and project through the UI. Project public and secret API keys are created later from the project settings and must remain in ignored local configuration or an appropriate secret store.

Only `127.0.0.1:3000` for the web UI and `127.0.0.1:9090` for browser access to MinIO objects are published. PostgreSQL, ClickHouse, Redis, the worker, and the MinIO console remain accessible only inside the dedicated Compose network.

Stop and remove the Langfuse containers and network while preserving all named volumes:

```bash
docker compose --project-name securebank-langfuse \
  --env-file .env.langfuse \
  -f compose.langfuse.yml down
```

Do not add `--volumes` or `-v` unless permanent deletion of all local Langfuse data is explicitly intended and approved. This local Compose deployment provides no high availability, horizontal scaling, automated backup, TLS, disaster recovery, or production security guarantee. Docker logging and persistent data retention must be monitored to prevent disk exhaustion.

## Running the Frontend

Install the locked dependencies and start the Vite development server:

```bash
cd frontend
npm install
npm run dev
```

The current frontend displays a responsive public dashboard and a documentary Assistant in French, English, and Italian. Native browser navigation connects `/` and `/assistant` without requiring authentication. Submitting an anonymous question opens an accessible login dialog; successful cookie login preserves and immediately sends the question. The header exposes connected state and logout. Session expiry reopens login, while logout clears in-memory Assistant content. The typed client sends cookies, copies the CSRF cookie into protected POST headers, and retains optional in-memory Bearer support only for the development panel. JWTs, credentials, questions, and RAG content are not persisted in browser storage. See [Frontend README](frontend/README.md) for focused instructions and limitations.

For the Dockerized local stack, build and start the frontend with its backend dependency:

```bash
docker compose up --build frontend
```

Open `http://localhost:8080`. Nginx serves the compiled SPA and forwards `/api/*` to the `backend` service over the internal Compose network after removing the prefix. Stop the stack without deleting the existing Qdrant volume:

```bash
docker compose down
```

## Running Tests

From the repository root with the backend virtual environment active:

```bash
cd backend
python -m pytest
```

The tests cover configuration defaults, environment overrides, the health endpoint contract, JWT validation, Bearer authentication and RBAC, local PII detection and masking, deterministic document chunking, in-memory BM25 retrieval, local embeddings, and Qdrant vector storage.

Run the frontend quality checks separately:

```bash
cd frontend
npm run build
npm run lint
npm run test
```

### Local FlashRank Reranking Demonstration

FlashRank reranks a fixed candidate set by comparing each passage with the full question. Prepare `ms-marco-MultiBERT-L-12` explicitly from the backend directory while network access is available:

```bash
cd backend
python -m scripts.prepare_flashrank_model
```

The weights are stored in the Git-ignored `backend/models/flashrank` cache. After preparation, run the qualitative CPU demonstration with no network access:

```bash
python -m scripts.demo_flashrank
```

The script validates the required local files before creating the FlashRank engine, so a missing model produces a preparation command instead of a silent runtime download. It prints the initial synthetic ranking, the reranked order, model loading time, and inference time for two French banking questions. FlashRank scores express model-relative relevance within the candidate set; they are not calibrated probabilities and should not be interpreted as confidence or compliance guarantees. This small synthetic example supports visual qualitative inspection only. It does not measure retrieval recall, answer correctness, threshold quality, or performance on a representative banking corpus.

### Complete Retrieval and Reranking Pipeline

`RagRetriever` composes the existing hybrid retriever and FlashRank reranker without coupling their implementations. Retrieval finds a broad candidate set through BM25 and MiniLM/Qdrant before RRF fusion. Reranking then compares the full question with each fused passage and changes their order and scores while preserving every chunk and its metadata.

The service requests three times the desired final count by default. For `top_k=5`, hybrid retrieval receives `top_k=15`, and FlashRank returns at most five final results. The candidate multiplier is configurable and must be a strictly positive integer. A larger value gives FlashRank more candidates to examine but increases retrieval and CPU inference work.

This service has no API route and performs no LLM generation. FlashRank scores are relative ranking signals rather than calibrated probabilities, confidence levels, or evidence-quality guarantees. Evidence validation, score-threshold calibration, answer generation, and abstention remain outside this iteration.

Run the complete pipeline demonstration after preparing both local models and starting Qdrant:

```bash
docker compose up -d qdrant
cd backend
python -m scripts.prepare_embedding_model
python -m scripts.prepare_flashrank_model
python -m scripts.demo_rag_retrieval
```

The demonstration runs BM25 and local MiniLM/Qdrant retrieval, combines their rankings with RRF, and passes a broader candidate set to local FlashRank for the final ranking. It prints RRF and FlashRank scores separately because their numeric scales are not comparable. Stable Qdrant point identifiers make repeated indexing idempotent, and the script verifies that the exact point count matches the synthetic chunks after each run. The demonstration uses three synthetic documents and three sample questions; it does not evaluate retrieval recall, score calibration, evidence quality, latency under load, or answer generation.

### Local End-to-End RAG Integration Test

The explicit integration script exercises the real local corpus loader, character chunking, BM25 retrieval, CPU MiniLM embeddings, Qdrant vector search, reciprocal rank fusion, Presidio/spaCy PII masking, citation validation, and `RagGenerationService`. It never constructs `OpenAILLMService` and makes no OpenAI or other external LLM call. A deterministic `FakeLLM` inspects only the masked question and masked passages, returns the existing structured JSON contract, cites matching evidence, and abstains when its small rule set finds no supported answer.

The dedicated `backend/data/rag_integration_corpus.json` contains four short, entirely synthetic documents about credit processing time, transfer limits, KYC renewal, and adviser contact details. Its synthetic e-mail values exercise masking in passage content and textual metadata. The script resets only the explicitly reserved `securebank_rag_integration_chunks` collection, indexes the current chunks, then indexes the same chunks again and asserts that the exact point count remains stable.

Prepare the local embedding and French spaCy models, then start Qdrant and run the script from the repository root:

```bash
docker compose up -d qdrant
cd backend
python -m scripts.prepare_embedding_model
python -m scripts.run_rag_integration
```

The asserted scenarios cover a factual cited answer, a masked PII-bearing question, PII masking in a retrieved passage and its metadata, masking of a generated synthetic e-mail while preserving its citation, explicit abstention for an unsupported question, and idempotent Qdrant reindexing. Console output contains only masked questions, answers, citation identifiers, source counts, and collection counts. On a PII-control failure, the script stops with a generic message.

This integration command is intentionally excluded from the default pytest suite because it needs Qdrant plus prepared local embedding, Presidio, and spaCy resources. The lightweight tests use substitutes and require no Docker, Qdrant server, model loading, or network. The `FakeLLM` supports only the demonstration's fixed evidence rules and cannot measure language-model quality, general grounding, or real-world abstention. Presidio and spaCy can produce false positives or false negatives, so successful masking in these scenarios does not prove exhaustive anonymization or legal compliance.

### Manual OpenAI RAG Integration Test

The manual OpenAI RAG integration test prepares the complete local pipeline with the existing four-document synthetic corpus, CPU embeddings, BM25, a dedicated Qdrant collection, RRF, Presidio, `RagGenerationService`, and the production `OpenAILLMService`. It runs no public HTTP server and must never be used with real banking or personal data.

The script is disarmed by default. The following command exits before loading embeddings, initializing Presidio, accessing Qdrant, constructing an OpenAI client, or requiring an API key:

```bash
cd backend
./venv/bin/python -m scripts.run_rag_openai_integration
```

For a later explicitly authorized manual run, prepare the local embedding and French spaCy models, start Qdrant, configure `LLM_API_KEY`, and run:

```bash
docker compose up -d qdrant
cd backend
./venv/bin/python -m scripts.run_rag_openai_integration --allow-real-openai-call
```

The authorized mode can make at most two OpenAI Responses API calls and can incur provider charges. It uses the smoke-test client configuration with a 15-second timeout and automatic retries disabled. Before each external call, a preflight guard verifies that every passage belongs to the pinned synthetic corpus and that its known synthetic PII is absent from the masked prompt. Prompts, raw responses, credentials, and source contents are not printed.

The two scenarios validate contract properties rather than exact wording: a non-abstained factual answer with citations attached to returned sources, and an explicit abstention without citations for unsupported evidence. Model output remains variable and can fail the strict JSON, citation, or abstention contract. Presidio can produce false negatives, and checking known synthetic values does not prove exhaustive anonymization. This manual test does not establish answer quality, regulatory compliance, production readiness, or safe processing of real data. Its automated tests use injected fakes without Docker, Qdrant, local models, Presidio, network access, or OpenAI calls.

### Local HTTP RAG Integration Test

The explicit HTTP integration script extends the local pipeline test through the real FastAPI `POST /rag/ask` route using an in-process ASGI client. It retains real JWT signature, issuer, audience, expiration, and RBAC validation while `app.dependency_overrides` supplies isolated synthetic JWT settings and replaces only the RAG service dependency with the prepared `RagGenerationService`. That service still uses real BM25 retrieval, local CPU embeddings, Qdrant vector search, reciprocal rank fusion, Presidio/spaCy masking, citation validation, and the deterministic `FakeLLM`. It never constructs `OpenAILLMService` or calls OpenAI.

Start Qdrant, prepare the local models, and run the script from the repository root:

```bash
docker compose up -d qdrant
cd backend
python -m scripts.prepare_embedding_model
python -m scripts.run_rag_http_integration
```

The script asserts HTTP 401 responses for missing and invalid tokens, HTTP 200 for an authorized compliance-officer token, cited factual generation, masking of a PII-bearing question, masking of passage content and textual metadata, masking of the generated answer, explicit documentary abstention, sanitized HTTP 422 validation errors, and HTTP 503 while RAG is disabled without initializing the production provider. Every role currently recognized by the application is authorized for this endpoint, so there is no recognized unauthorized role that can validly exercise HTTP 403. Overrides are restored after every request, including failed assertions, and the script never starts a public server.

The real HTTP script is excluded from the default pytest suite because it requires Qdrant and prepared local models. Lightweight tests cover token compatibility, override cleanup, ASGI routing with real JWT/RBAC, and validation rejection using substitutes without Docker, model loading, Presidio, network, or OpenAI. The fixed-rule `FakeLLM` cannot evaluate general language-model behavior, and successful synthetic PII checks do not guarantee exhaustive anonymization or regulatory compliance.

### Synthetic Retrieval Evaluation

The benchmark corpus contains 30 fictitious French banking documents: five each for mortgage credit, consumer credit, insurance, savings, accounts and payments, and security and compliance. The 180-character chunk size with a 30-character overlap produces 137 deterministic chunks. The separate demonstration corpus remains limited to its original three documents.

The benchmark contains 40 questions: 15 factual questions, 15 semantic reformulations, and 10 difficult or intentionally ambiguous questions. Every case references validated document and chunk identifiers and records a short evidence rationale. The six historical evaluation cases remain available as a separate regression set.

Source Hit@K equals one when at least one expected document appears among the first K results. Evidence Hit@K applies the same rule to expected chunk identifiers and therefore measures whether a precise supporting passage was retrieved. `@K` limits evaluation to the first K ranked results. Dataset evaluation reports both metrics per case and their arithmetic means.

Run the four-way comparison after preparing the local models and starting Qdrant:

```bash
docker compose up -d qdrant
cd backend
python -m scripts.compare_retrievers
```

The script evaluates BM25, MiniLM/Qdrant, hybrid RRF, and hybrid RRF followed by FlashRank on the same 40 cases, chunks, references, and final `top_k=3`. It uses the dedicated `securebank_benchmark_chunks` Qdrant collection so benchmark points cannot mix with demonstration points. It reports Source Hit@1, Source Hit@3, Evidence Hit@1, Evidence Hit@3, failed questions, FlashRank changes relative to RRF, the first-ranked document per question, and separate local mean latencies. MiniLM and FlashRank must already exist in their documented local caches.

The documents and questions are synthetic and cannot reproduce production language, policy complexity, corpus growth, user behavior, statistically reliable quality, or production latency. Forty questions support regression diagnosis but remain too few for broad statistical conclusions. This benchmark does not represent production retrieval performance.

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

Retrieval-Augmented Generation grounds a generated answer in passages retrieved from a source corpus. The current pipeline implements document representation, chunking, independent lexical retrieval, local embeddings, and Qdrant vector search. Fusion and generation remain planned.

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

An embedding is a fixed-size numeric vector that represents a text so that related meanings can be compared geometrically. BM25 ranks exact or normalized lexical terms and remains effective for identifiers and precise wording. Semantic search compares embeddings and can retrieve related French passages even when a question uses different words. `LocalEmbeddingService` generates vectors and computes pairwise cosine similarity, while Qdrant provides the separate vector index and nearest-neighbor search.

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

### Qdrant Vector Storage and Search

Qdrant persists the 384-dimensional embeddings produced for existing `Chunk` objects. `QdrantVectorStore` creates the configured collection with cosine distance when needed, then upserts each vector with a deterministic UUID and the metadata required to reconstruct its `Chunk`. Reprocessing the same document and chunk identifiers targets the same point.

`QdrantVectorStore.search` accepts a 384-dimensional query vector and a positive `top_k`, asks Qdrant for the nearest points, and returns typed `RetrievalResult` values in Qdrant relevance order. Results contain the reconstructed chunk and its cosine similarity score; stored vectors are excluded from the response. Invalid payloads and Qdrant failures are translated into `QdrantVectorStoreError`.

Vectors must contain exactly 384 finite numeric values. The service validates identifiers, vectors, and result payloads. Vector search remains independent from BM25 and does not perform fusion, reranking, evidence validation, or answer generation.

Run the focused unit tests without Docker, a Qdrant server, or embedding model weights:

```bash
cd backend
python -m pytest tests/test_qdrant.py tests/test_config.py
```

### End-to-End Vector Search Demonstration

Start Qdrant from the repository root:

```bash
docker compose up -d qdrant
```

With the prepared local MiniLM model and the backend virtual environment active, run the demonstration from the backend directory:

```bash
cd backend
python -m scripts.demo_vector_search
```

The script creates three fictitious French banking documents, splits them into deterministic chunks, generates local embeddings, upserts them into the configured Qdrant collection, and prints the three nearest chunks with their cosine scores for a fictitious housing-finance question. Running it again updates the same deterministic point identifiers instead of creating duplicates. The demonstration data is entirely synthetic and contains no real personal or banking information.

Inspect the collection and its points in the Qdrant dashboard at `http://localhost:6333/dashboard`.

### Reciprocal Rank Fusion

Reciprocal Rank Fusion combines the ordered BM25 and Qdrant results by adding `1 / (k + rank)` for each ranking in which a chunk appears. The implementation identifies chunks by document and chunk identifiers, ignores source scores, removes repeated contributions from the same ranking, and uses `k=60` by default.

The independent `reciprocal_rank_fusion` service provides deterministic hybrid ranking and is used by `HybridRetriever`. It is not connected to a reranker, evidence validator, or answer generator.

### Hybrid Retrieval

`HybridRetriever` coordinates the implemented retrieval components through dependency injection. For each question, it requests lexical candidates from BM25, creates one local MiniLM query embedding, requests semantic candidates from Qdrant, and applies Reciprocal Rank Fusion to return the requested number of results.

Each engine receives three times the requested result count by default so RRF has a broader candidate pool. The multiplier and RRF constant are configurable. Dependency failures propagate to the caller, and the service does not log questions or chunks. No API route exposes hybrid retrieval yet.

Run the real hybrid demonstration after starting Qdrant and preparing the local MiniLM model:

```bash
cd backend
python -m scripts.demo_hybrid_search
```

The demonstration reuses the fictitious French banking corpus from the vector-search example, builds BM25 and Qdrant indexes with the same deterministic chunk identifiers, and runs two synthetic questions. It prints the lexical BM25 ranking, the semantic MiniLM/Qdrant ranking, and the final RRF ranking for comparison. BM25 favors matching terms, Qdrant compares semantic vectors, and RRF combines their rank positions without mixing their incompatible source scores. Repeated runs upsert the same Qdrant points instead of creating duplicates. All demonstration documents and questions are fictitious.

### FlashRank Reranking

Reranking applies a cross-encoder after retrieval so each candidate is scored jointly with the question. `FlashRankReranker` accepts existing `RetrievalResult` values, preserves their chunks and metadata, replaces retrieval scores with FlashRank scores, and returns the highest-scoring candidates. It remains independent and is not yet called automatically by `HybridRetriever`.

The selected model is `ms-marco-MultiBERT-L-12`, the FlashRank model explicitly documented as multilingual for more than 100 languages. It runs as a quantized ONNX model on CPU and is approximately 150 MB. Multilingual coverage includes French, but it does not establish banking-domain quality, calibrated relevance probabilities, or regulatory answer correctness.

FlashRank downloads missing models by default. Runtime loading prevents that behavior by requiring a prepared local cache at `backend/models/flashrank/ms-marco-MultiBERT-L-12`. Prepare it explicitly from the backend directory in an environment with network access:

```bash
python -m scripts.prepare_flashrank_model
```

Run the focused unit tests without a model download or external service:

```bash
python -m pytest tests/test_reranking.py
```

## API Documentation

With the backend running, open Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

Current endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Reports service availability, identity, and version |
| `POST` | `/auth/login` | Verifies local credentials and creates a cookie session |
| `POST` | `/auth/logout` | Revokes the current cookie session |
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

A valid HS256 token with matching `exp`, `iss`, `aud`, non-empty `sub`, and a recognized `role` can establish an authenticated identity. The same endpoints also accept an unexpired server-side session through the HttpOnly `securebank_session` cookie. Missing or invalid credentials return HTTP 401 with `WWW-Authenticate: Bearer`. An authenticated identity without an explicitly allowed role receives HTTP 403. The application does not issue JWTs.

For local development only, generate a 15-minute `analyst` token from the JWT configuration in `backend/.env`:

```bash
cd backend
venv/bin/python -m scripts.generate_development_jwt
```

The script requires `JWT_SECRET_KEY`, `JWT_ISSUER`, and `JWT_AUDIENCE`. It does not contain, persist, or log the secret or generated token. The token is printed once to standard output so it can be entered manually in the frontend development panel. This utility is not a production authentication mechanism, and the FastAPI application still does not expose a token-issuing endpoint.

Available roles:

- `analyst`
- `compliance_officer`
- `admin`

Create a local user without placing a password in shell history:

```bash
cd backend
venv/bin/python -m scripts.create_user demo.analyst --role analyst
```

The command prompts twice for a password, requires at least 12 characters and at most 72 UTF-8 bytes, stores only a bcrypt hash, and creates an active account by default. Add `--disabled` to create an inactive account. Usernames are unique case-insensitively. The ignored SQLite file is created at `USER_DATABASE_PATH` and supplies `POST /auth/login`.

Browser login requires a trusted `Origin` header and returns the authenticated UUID and role. Successful responses set an opaque HttpOnly session cookie and a readable CSRF cookie. The raw session and CSRF values are never stored in SQLite; only SHA-256 fingerprints are persisted. State-changing requests authenticated by cookie must copy the CSRF cookie value into `X-CSRF-Token`. Logout deletes the server-side session before expiring both cookies. Failed logins are limited persistently per normalized username and use the same generic error for unknown users, wrong passwords, and disabled accounts.

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
- Cookie authentication uses opaque, time-limited, server-side SQLite sessions with HttpOnly transport and effective logout revocation.
- Cookie-authenticated state changes require a matching CSRF cookie, request header, and server-side fingerprint.
- Login requires an explicitly trusted origin and applies a persistent per-username attempt limit.
- RBAC protects demonstration endpoints with explicit role allowlists and denies authenticated users with HTTP 403 when their role is insufficient.
- PII detection runs locally with Presidio Analyzer and a French spaCy model; analyzed values are neither persisted nor logged by the service.
- PII masking replaces detected values locally with typed markers and provides no restoration mechanism.
- The protected PII endpoint sanitizes validation errors so rejected request values are not echoed in HTTP 422 responses.
- E-mail validation uses the public-suffix snapshot bundled with `tldextract` and performs no runtime network refresh.
- Token issuance is not exposed by the API; a local 15-minute `analyst` token generator exists only for development.
- In production, a trusted identity system must assign roles. Permission changes may require token revocation or short expiration because an issued JWT retains its embedded role until it expires or is revoked.
- Future authorization decisions will remain deterministic and outside LLM control.
- The observability contract accepts only explicitly typed technical measurements and excludes request, response, document, identity, authentication, and credential content.
- The local Langfuse stack binds its only published ports to the loopback interface and stores credentials in the ignored `.env.langfuse` file.
- Sensitive data must be anonymized before transmission to external services.
- The prototype must not be represented as FINMA-certified or as guaranteeing LPD compliance.

## Continuous Integration

The backend workflow is implemented in `.github/workflows/ci.yml`. It runs Ruff linting, Ruff format verification, and pytest with Python 3.12. Docker image builds remain available for local validation and are not part of the CI workflow.

The workflow executes exclusively for Pull Requests that are opened, synchronized with new commits, or reopened. A push to a branch without an open Pull Request does not trigger it. A push to a branch with an open Pull Request triggers it through the `pull_request` `synchronize` activity.

The workflow uses read-only repository permissions and requires no secrets. It performs validation only: it does not deploy services, push Docker images, modify code, or create commits. Frontend checks remain planned.

The workflow configuration and all equivalent checks have been validated locally. GitHub Actions execution remains unverified until a Pull Request runs the workflow successfully.

## Deployment

The backend has a production-oriented Docker image and a local Docker Compose service. An isolated Langfuse v4 Compose definition is prepared for local deployment but has not been started or connected to the application. Cloud deployment remains **planned**, with Render targeted for the backend and Vercel for the frontend. Hosted environments are not implemented.

## Development Roadmap

| Day | Scope | Status |
| --- | --- | --- |
| Day 1 | FastAPI gateway, health check, settings, JWT, RBAC, PII detection and masking, security tests | In Progress: health check, settings, JWT authentication, RBAC, PII detection, masking, and protected PII API completed |
| Day 2 | Regulatory corpus, chunking, embeddings, Qdrant, BM25, RRF, reranking, evidence validation, abstention | In Progress: document models, character chunking, BM25, local embeddings, Qdrant vector search, RRF, hybrid orchestration, and independent FlashRank reranking completed |
| Day 3 | Independent FastMCP server, simulated tools, MCP client, LangGraph state and routing | Planned |
| Day 4 | Langfuse, tracing, evaluation, documentation, frontend integration, deployment | In Progress: privacy-preserving RAG instrumentation, no-op default, and conditional Langfuse SDK client implemented; live integration remains planned |
| Phase 6 | React frontend | In Progress: Vite, TypeScript, Tailwind CSS design system, responsive application shell, native navigation, French/English/Italian localization, development-only Assistant API connection, typed API client, ESLint, Vitest, and Docker integration implemented |

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
- Persistent SQLite user store with unique identifiers, bcrypt password hashes, explicit roles, and active status.
- Interactive local user-creation command that does not accept passwords as command-line arguments.
- Credential login with generic failures for unknown, incorrect, and inactive accounts.
- Revocable, expiring SQLite sessions through configurable HttpOnly cookies.
- CSRF double-submit protection backed by a server-side token fingerprint.
- Persistent login-attempt limiting and trusted-origin validation.
- Typed roles for `analyst`, `compliance_officer`, and `admin`.
- Reusable deny-by-default RBAC dependency with explicit role allowlists.
- Protected authentication demonstration endpoints for identity, analyst access, and admin access.
- Local typed PII detection for e-mail addresses, phone numbers, IBANs, and French person names.
- Deterministic local PII masking with typed markers and overlap resolution.
- Protected `POST /pii/mask` endpoint with sanitized validation errors.
- Protected `POST /rag/ask` endpoint with typed input, RBAC, safe upstream errors, and replaceable pipeline injection.
- Immutable document and chunk contracts with deterministic character chunking.
- Deterministic in-memory BM25 retrieval with typed scored results.
- Local multilingual embeddings for text and chunks with deterministic input validation.
- Independent cosine similarity with vector validation.
- Persistent Qdrant storage and nearest-vector search with typed scored results.
- Deterministic Reciprocal Rank Fusion for independent BM25 and Qdrant rankings.
- Injected hybrid retriever coordinating BM25, MiniLM, Qdrant, and RRF.
- Independent multilingual FlashRank reranking with explicit local model preparation.
- Independent configurable OpenAI-compatible LLM generation service with an injected client contract.
- Generative RAG orchestration connecting hybrid RRF retrieval to LLM generation without FlashRank by default.
- Lazy, cached RAG composition from a configurable local synthetic corpus, local embeddings, Qdrant, BM25, RRF, and OpenAI generation.
- Fail-closed PII masking for RAG questions, retrieved source text and metadata, and generated answers.
- Reproducible offline validation with the prepared local embedding model.
- Backend Docker image using Python 3.12 slim and a non-root runtime user.
- Backend and frontend Docker Compose services exposed on local ports `8000` and `8080`.
- Pull Request-only backend GitHub Actions workflow.
- Disabled-by-default Langfuse configuration with conditional credential validation and no network initialization.
- Typed privacy-preserving `RagObserver` contract and stateless `NoOpRagObserver` implementation.
- Injected RAG lifecycle instrumentation for retrieval and generation durations, passage count, safe model name, and completion status.
- Offline `LangfuseRagObserver` adapter with an injected internal client contract and context-local trace correlation.
- Conditional official Langfuse Python SDK 4.17.0 client with correlated root, retrieval, and generation observations.
- Isolated Langfuse v4 Docker Compose definition with loopback-only published ports and persistent local volumes.
- React 19 frontend initialized with strict TypeScript, Vite, Tailwind CSS, ESLint, and Vitest.
- Responsive SecureBank-AI presentation dashboard with a reusable shell, accessible mobile navigation, and no API or authentication behavior.
- Centralized typed native-fetch API client for health, current-user, and RAG requests with injectable transport, cancellation, Bearer headers, and structured safe errors.
- Native browser navigation between the dashboard and a directly accessible documentary Assistant page.
- Accessible disabled Assistant form and reusable typed presentation components for RAG answers, sources, citations, and abstentions, without backend calls or simulated production responses.
- Local French, English, and Italian interface catalogs with a persistent validated language preference and synchronized HTML language metadata.
- Development-only in-memory JWT panel connecting the Assistant to the typed RAG API service with loading, localized errors, cancellation, and stale-response protection.
- On-demand accessible login dialog with keyboard focus management and preserved question submission.
- Cookie session restoration, CSRF-protected RAG and logout requests, expiration handling, connected state, and logout cleanup.
- Local Vite `/api` proxy prepared for the FastAPI backend without changing backend routes or CORS.
- Multi-stage frontend image with a Node.js build stage and an Nginx runtime serving the SPA and reverse-proxying `/api` to the backend service.

### In Progress

- Day 1 API gateway and security foundation.

### Planned

- JWT revocation and persistent Docker storage for the SQLite user database.
- Document ingestion, automatic reranking integration, and semantic evidence validation.
- FastMCP and LangGraph orchestration.
- Live Langfuse trace export validation, dashboards, and alerts.
- Production authentication design, production Assistant submission, business interfaces, and cloud deployment.

## Known Limitations

- The RAG API is disabled by default and requires an explicit local corpus, prepared embedding model, running Qdrant service, and LLM provider configuration.
- PII detection is probabilistic and may produce false positives or false negatives, especially for person names and ambiguous number formats. It does not guarantee exhaustive identification of sensitive data.
- False negatives remain unmasked in transformed text. The masking service and endpoint reduce exposure risk without guaranteeing complete anonymization or regulatory compliance.
- Character chunking can split words and semantic units because it does not understand tokens, sentences, or document structure.
- BM25 matches lexical tokens only, does not understand meaning or synonyms, and has no persistent index.
- The embedding model rejects texts above its 128-token limit and does not split them automatically.
- Cosine similarity is uncalibrated and cannot establish answer correctness or sufficient evidence by itself.
- Local embedding inference increases installation size, startup time, CPU use, and RAM use; performance has not been benchmarked for this project.
- The multilingual FlashRank model adds approximately 150 MB and has not been evaluated on French banking or regulatory benchmarks.
- FlashRank reranking is not yet connected automatically to `HybridRetriever`.
- LLM generation has no semantic evidence validation. PII masking reduces exposure but cannot guarantee that every sensitive value is detected.
- Enabling RAG transmits masked questions and passages to the configured LLM provider. False negatives can expose original values, so provider hosting, retention, access, and confidentiality controls must be assessed before use.
- RAG PII integration has been tested with synthetic fakes only; no real OpenAI call or live Qdrant RAG flow has been performed.
- Generative RAG validates citation references structurally but does not verify semantic support and cannot guarantee grounded answers when retrieved documents are misleading, incomplete, or malicious.
- The frontend cookie login is implemented, but live browser validation still depends on a configured local user and backend RAG stack.
- The SQLite database has no Docker Compose volume yet, so container recreation does not preserve users or sessions.
- Login limiting is keyed by normalized username; it reduces brute-force attempts but can temporarily block a targeted account.
- The RAG observer is no-op by default. The official SDK client has only been exercised with offline fakes; no real trace ingestion, persistence, dashboard, or alert behavior has been validated.
- The Langfuse Compose stack has not been pulled, started, health-checked, or exercised through its UI; local capacity and image compatibility remain unverified.
- Qdrant vector search requires a running Qdrant service; the vector store creates its collection when needed, but the demonstration corpus must be indexed before it can be searched.
- Docker Compose starts the frontend, backend, and Qdrant; the frontend container depends on backend startup but not on backend health because the backend service has no Compose health check.
- The backend workflow has not yet been executed and validated by GitHub Actions on a Pull Request.
- The dependency manifest includes packages reserved for future iterations.
- The existing backend virtual environment reports Python 3.12.13; the project supports Python 3.12.x.
- The API version is currently defined directly in the FastAPI application and health response.
