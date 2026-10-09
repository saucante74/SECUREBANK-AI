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
| Security | HS256 JWT validation, Bearer authentication, RBAC, local PII detection | Token generation and PII masking |
| Retrieval | None | BM25, Qdrant, RRF, FlashRank |
| Orchestration and tools | None | LangGraph, FastMCP |
| Observability | None | Langfuse |
| Frontend | None | React 19, TypeScript, Vite |
| Deployment | None | Render backend, Vercel frontend |

The backend requirements file already declares packages for later iterations. A declared dependency does not mean that its related capability is implemented.

## System Architecture

The current runtime consists of one FastAPI application exposing a public health endpoint and protected authentication demonstration endpoints. HTTP authentication and RBAC dependencies are separated from JWT validation and typed response schemas. An independent service detects PII locally without exposing an HTTP endpoint. Future modules will be introduced only in the iteration that needs them.

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
│   │   │   └── dependencies.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── jwt.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   └── pii.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── pii.py
│   │   └── main.py
│   ├── .dockerignore
│   ├── .env
│   ├── .env.example
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── requirements-dev.txt
│   ├── requirements-runtime.txt
│   ├── requirements.txt
│   ├── tests/
│   │   ├── test_config.py
│   │   ├── test_health.py
│   │   └── test_pii.py
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

The tests cover configuration defaults, environment overrides, the health endpoint contract, JWT validation, Bearer authentication and RBAC, and local PII detection.

### Local PII Detection

`PiiDetector` accepts French text and returns typed entities containing the entity type, start offset, end offset, and Presidio confidence score. It detects e-mail addresses, phone numbers, valid IBANs, and person names recognized by the French spaCy model. The component is a Python service independent of FastAPI and does not store or log analyzed text.

Detection identifies candidate spans; it does not alter the input. Masking and anonymization are separate operations and are not implemented. Presidio combines patterns, checksums, contextual logic, and named-entity recognition, but results can still contain false positives or miss sensitive data. Detection is not a guarantee of exhaustive identification.

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

## Security Considerations

- The repository must contain no secrets or real banking data.
- Development data must be synthetic.
- JWT validation verifies HS256 signatures and requires valid `exp`, `iss`, `aud`, and non-empty `sub` claims.
- Bearer authentication requires a recognized, non-empty `role` claim and returns the authenticated subject and role from `GET /auth/me`.
- RBAC protects demonstration endpoints with explicit role allowlists and denies authenticated users with HTTP 403 when their role is insufficient.
- PII detection runs locally with Presidio Analyzer and a French spaCy model; analyzed values are neither persisted nor logged by the service.
- E-mail validation uses the public-suffix snapshot bundled with `tldextract` and performs no runtime network refresh.
- Token generation and PII masking are not implemented.
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
| Day 1 | FastAPI gateway, health check, settings, JWT, RBAC, PII detection and masking, security tests | In Progress: health check, settings, JWT authentication, RBAC, and PII detection completed |
| Day 2 | Regulatory corpus, Qdrant, BM25, RRF, reranking, evidence validation, abstention | Planned |
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
- Backend Docker image using Python 3.12 slim and a non-root runtime user.
- Backend Docker Compose service exposed on local port `8000`.
- Pull Request-only backend GitHub Actions workflow.

### In Progress

- Day 1 API gateway and security foundation.

### Planned

- Token generation and token revocation.
- PII masking.
- Hybrid retrieval, evidence validation, and abstention.
- FastMCP and LangGraph orchestration.
- Langfuse observability.
- React frontend and cloud deployment.

## Known Limitations

- Only the health endpoint, application settings, JWT validation, Bearer authentication, demonstration RBAC, and local PII detection are implemented.
- PII detection is probabilistic and may produce false positives or false negatives, especially for person names and ambiguous number formats. It does not guarantee exhaustive identification of sensitive data.
- There is no token generation, user directory, token revocation, PII masking, RAG pipeline, agent orchestration, MCP server, observability, frontend, or deployment configuration.
- Docker Compose currently starts only the backend; frontend integration is planned after the React application is initialized.
- The backend workflow has not yet been executed and validated by GitHub Actions on a Pull Request.
- The dependency manifest includes packages reserved for future iterations.
- The existing backend virtual environment reports Python 3.12.13; the project supports Python 3.12.x.
- The API version is currently defined directly in the FastAPI application and health response.
