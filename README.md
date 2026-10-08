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
| Validation and configuration | Pydantic v2, pydantic-settings | Extended configuration contracts |
| Security | No application security feature yet | JWT, RBAC, Presidio and regex masking |
| Retrieval | None | BM25, Qdrant, RRF, FlashRank |
| Orchestration and tools | None | LangGraph, FastMCP |
| Observability | None | Langfuse |
| Frontend | None | React 19, TypeScript, Vite |
| Deployment | None | Render backend, Vercel frontend |

The backend requirements file already declares packages for later iterations. A declared dependency does not mean that its related capability is implemented.

## System Architecture

The current runtime consists of one FastAPI application exposing a health endpoint. The target architecture separates HTTP routes, security infrastructure, schemas, business services, retrieval, agent orchestration, and external integrations. Future modules will be introduced only in the iteration that needs them.

## Repository Structure

```text
SECUREBANK-AI/
├── AGENTS.md
├── README.md
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py
│   │   └── main.py
│   ├── .env
│   ├── .env.example
│   ├── requirements.txt
│   ├── tests/
│   │   ├── test_config.py
│   │   └── test_health.py
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

Environment variables override values loaded from `backend/.env`, which override the development defaults. Do not commit `.env` or place real banking data in it.

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

## Running the Frontend

**Planned.** The `frontend/` directory is currently empty, so there is no frontend installation or start command yet.

## Running Tests

From the repository root with the backend virtual environment active:

```bash
cd backend
python -m pytest
```

The tests cover configuration defaults, environment overrides, and the health endpoint contract.

## API Documentation

With the backend running, open Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

Current endpoint:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Reports service availability, identity, and version |

## Security Considerations

- The repository must contain no secrets or real banking data.
- Development data must be synthetic.
- JWT validation, RBAC, and PII masking are planned and are not currently enforced.
- Future authorization decisions will remain deterministic and outside LLM control.
- Sensitive data must be anonymized before transmission to external services.
- The prototype must not be represented as FINMA-certified or as guaranteeing LPD compliance.

## Deployment

**Planned.** The target platforms are Render for the backend and Vercel for the frontend. No deployment configuration or hosted environment is currently implemented.

## Development Roadmap

| Day | Scope | Status |
| --- | --- | --- |
| Day 1 | FastAPI gateway, health check, settings, JWT, RBAC, PII masking, security tests | In Progress: health check and settings completed |
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

### In Progress

- Day 1 API gateway and security foundation.

### Planned

- JWT authentication and deterministic RBAC.
- PII detection and masking.
- Hybrid retrieval, evidence validation, and abstention.
- FastMCP and LangGraph orchestration.
- Langfuse observability.
- React frontend and cloud deployment.

## Known Limitations

- Only the health endpoint and application settings are implemented.
- There is no authentication, authorization, PII masking, RAG pipeline, agent orchestration, MCP server, observability, frontend, or deployment configuration.
- The dependency manifest includes packages reserved for future iterations.
- The existing backend virtual environment reports Python 3.12.13; the project supports Python 3.12.x.
- The API version is currently defined directly in the FastAPI application and health response.
