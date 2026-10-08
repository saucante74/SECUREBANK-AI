# SecureBank-AI — Codex Agent Instructions

## 1. Project Context

SecureBank-AI is a four-day R&D prototype designed to demonstrate AI Solution Engineering and AI Integration Engineering skills.

The project follows AEROSPEC-AI, a previous RAG benchmarking project focused on Source Hit and Evidence Hit evaluation.

SecureBank-AI extends this work toward a secure, evidence-grounded, multi-agent architecture for Swiss banking compliance use cases.

The prototype is intended for technical demonstration and learning. It must not be presented as a FINMA-certified or legally compliant banking product.

## 2. Technology Stack

### Environment

- OS: Ubuntu
- Python: 3.12.x
- Node.js: >=24
- Backend: FastAPI
- Data validation: Pydantic v2
- Configuration: pydantic-settings
- Frontend: React 19, TypeScript, Vite
- Backend deployment: Render
- Frontend deployment: Vercel

### Planned AI Components

- LangGraph for agent orchestration
- Qdrant Cloud for dense retrieval
- BM25 for sparse retrieval
- Reciprocal Rank Fusion for hybrid retrieval
- FlashRank for contextual reranking
- FastMCP for business tool integration
- Langfuse for observability
- Presidio and regex for PII detection and masking

Do not install or implement planned components before their corresponding iteration.

## 3. Repository Structure

```text
SECUREBANK-AI/
├── AGENTS.md
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   ├── .env
│   └── requirements.txt
├── frontend/
└── docs/
```

Inspect the actual repository before creating files.

Never assume that a directory, dependency, or configuration already exists.

Do not reorganize existing code without explicit approval.

## 4. Absolute Rule: No Code Comments

Never introduce comments in source code.

Forbidden:

- Python comments
- JavaScript comments
- TypeScript comments
- HTML comments
- CSS comments
- Explanatory docstrings
- Commented-out code

Explain implementation decisions in the conversation, not inside source files.

Markdown documentation is allowed.

Mandatory syntax required by tools or configuration formats is allowed when technically necessary.

Code must remain readable through:

- Clear naming
- Explicit typing
- Small functions
- Separation of responsibilities
- Simple control flow

## 5. Micro-Iteration Development

This is the most important development rule.

Implement exactly one small, independently testable functionality per iteration.

Never implement an entire feature set at once.

Never anticipate future iterations.

Never implement the next iteration without explicit user approval.

Each iteration must follow:

1. Explain the objective.
2. Explain the technical concept.
3. Identify the files that need modification.
4. Implement the smallest working solution.
5. Execute relevant tests when possible.
6. Explain the implementation.
7. Provide Ubuntu verification commands.
8. Report the actual test results.
9. Stop and wait for validation.

If a task is too large, divide it into smaller iterations.

Do not implement multiple iterations in a single response.

## 6. Learning-Oriented Collaboration

Act as both a senior engineer and a technical mentor.

The user is developing AI Solution / Integration Engineering skills through hands-on implementation.

Prioritize understanding over development speed.

For each new concept, explain:

- What it is
- Why it is needed
- Where it belongs in the architecture
- How it interacts with existing components

Use concise technical explanations.

Do not overwhelm the user with unnecessary theory.

Do not introduce abstractions without a concrete need.

The user must be able to explain the implementation during a technical interview.

## 7. Python Engineering Standards

Use modern Python practices compatible with Python 3.12.

Requirements:

- PEP 8 compliance
- Standard Python naming conventions
- Explicit type annotations
- Explicit return types for functions and methods
- Modern Python 3.12 type syntax
- Imports organized according to Python conventions
- pathlib for filesystem paths instead of manual path manipulation
- Context managers for resources that require deterministic cleanup
- Pydantic v2
- FastAPI dependency injection where appropriate
- Async endpoints for asynchronous operations
- Clear separation of concerns
- Small and focused modules
- Predictable error handling
- Explicit and narrowly scoped exception handling
- Minimal dependencies
- No dead code
- No unnecessary duplication
- No uncontrolled mutable global state
- Standard-library solutions when they are sufficient

Avoid:

- Premature abstraction
- Premature optimization
- Unnecessary complexity
- Unnecessary design patterns
- Global mutable application state
- Broad exception handling without justification
- Silent generic exception handlers
- Unnecessary third-party packages
- Circular imports
- Duplicated business logic

Prefer standard-library solutions when appropriate.

The prohibition on code comments, explanatory docstrings, and commented-out code in Section 4 always applies.

## 8. Security Requirements

Security must be enforced through deterministic application logic.

### Authentication

- Validate JWT signatures.
- Validate token expiration.
- Validate issuer and audience when configured.
- Reject invalid or expired tokens.
- Never trust unverified JWT claims.

### Authorization

- Implement role-based access control.
- Use explicit role definitions.
- Apply least-privilege principles.
- Never delegate authorization decisions to an LLM.

Initial roles:

- Compliance_Officer
- Standard_Auditor

### Sensitive Data

- Never commit secrets.
- Never expose API keys.
- Never log credentials.
- Never log unmasked PII.
- Never send unmasked sensitive data to external LLM services.
- Use synthetic banking data for development.

PII detection and anonymization must be tested.

Do not claim that regex or Presidio provides perfect anonymization.

### External Services

Before introducing an external service, explain:

- What data is transmitted
- Why the service is required
- Potential confidentiality risks
- Available mitigation measures

## 9. RAG Engineering Principles

The RAG pipeline must prioritize evidence quality over answer generation.

Planned pipeline:

1. Document ingestion
2. Text chunking
3. Dense retrieval
4. Sparse retrieval
5. Reciprocal Rank Fusion
6. Cross-encoder reranking
7. Evidence validation
8. Answer generation or abstention

Keep retrieval, reranking, evidence validation, and generation logically separated.

Do not treat reranker scores as calibrated probabilities without validation.

Every generated regulatory answer must reference its supporting evidence.

If sufficient evidence is unavailable, the system must abstain.

Preserve the distinction between:

- Source Hit
- Evidence Hit
- Retrieval relevance
- Answer correctness
- Abstention accuracy

## 10. Agent Orchestration

LangGraph will be introduced during Day 3.

The planned architecture includes:

- Supervisor
- Routing logic
- RAG agent
- MCP tool agent
- Shared AgentState
- Controlled reevaluation

Agent execution must be bounded.

Avoid uncontrolled recursive tool calls.

Authorization must remain outside LLM decision-making.

MCP tools must validate their own inputs and permissions.

## 11. Testing Standards

Every implementation must be verifiable.

Use pytest for backend tests.

Test:

- Expected behavior
- Invalid inputs
- Relevant edge cases
- Security boundaries when applicable
- Business logic with focused unit tests
- Component integration when it provides meaningful coverage

Do not claim tests passed unless they were executed successfully.

If tests cannot run, explain why.

Do not silently skip failing tests.

Keep tests focused on the current iteration.

Testing requirements:

- Every micro-iteration must include tests proportional to its functionality.
- Preserve all existing tests unless an explicitly approved behavior change requires an update.
- Keep tests deterministic and independent of execution order.
- Isolate external dependencies.
- Never call real cloud services from unit tests.
- Never use real secrets in fixtures or test data.
- Do not silently ignore, disable, or skip tests.
- Never invent test execution or results.

## 12. Dependency Management

Inspect requirements.txt before installing packages.

Inspect requirements-dev.txt and pyproject.toml when they exist.

Do not upgrade existing dependencies without justification.

Do not install the entire planned AI stack in advance.

Add dependencies only when required by the current iteration.

Prefer compatible, reproducible versions.

Maintain compatibility with Python 3.12.x.

Separate production dependencies from development dependencies.

Keep requirements.txt, requirements-dev.txt, and pyproject.toml consistent when they exist.

Do not retain unused dependencies.

Use the active backend virtual environment.

Never install project dependencies globally.

## 13. Environment Management

The development environment is Ubuntu.

Use the existing backend virtual environment.

Preferred interpreter:

backend/venv/bin/python

Do not create additional virtual environments without approval.

Use Python 3.12.x.

Do not switch to Python 3.14.

Do not modify the user's IDE configuration without permission.

## 14. File Modification Policy

Before editing:

1. Inspect the relevant files.
2. Identify the smallest required change.
3. Preserve existing functionality.
4. Avoid unrelated refactoring.

Never:

- Delete files without approval.
- Rewrite unrelated modules.
- Modify frontend code during backend-only iterations.
- Replace existing configuration without inspection.
- Introduce unused files.
- Commit secrets.

Respect the existing project structure.

## 15. Frontend Rules

Frontend stack:

- React 19
- TypeScript
- Vite

The frontend is a presentation layer.

Security, authorization, orchestration, and business logic belong in the backend.

Do not implement frontend features until explicitly requested.

Do not expose backend secrets through frontend environment variables.

## 16. Deployment Constraints

Target architecture:

Frontend: Vercel
Backend: Render

Prefer deployment-compatible implementations.

Account for:

- Environment variables
- CORS
- HTTP health checks
- Stateless application design
- Resource limitations
- Cold starts
- External service connectivity

Do not assume free hosting tiers provide guaranteed availability or persistent storage.

Do not deploy without explicit user approval.

## 17. Four-Day Roadmap

### Day 1 — API Gateway and Security

- FastAPI initialization
- Health check
- Pydantic Settings
- JWT authentication
- RBAC authorization
- PII masking
- Security tests

### Day 2 — Hybrid RAG

- Regulatory corpus preparation
- Qdrant integration
- BM25 retrieval
- Reciprocal Rank Fusion
- Cross-encoder reranking
- Evidence validation
- Abstention rules

### Day 3 — MCP and LangGraph

- Independent FastMCP server
- Mock banking tools
- MCP client integration
- LangGraph state
- Supervisor and routing
- Controlled tool execution

### Day 4 — Observability and Deployment

- Langfuse integration
- Tracing
- Evaluation
- Benchmarking
- Documentation
- Frontend integration
- Cloud deployment

The roadmap is indicative.

Do not sacrifice testing or understanding to meet the schedule.

## 18. Current Project Status

Day 1 — Iteration 1: COMPLETED

Implemented:

- Minimal FastAPI application
- GET /health
- HTTP 200 response
- JSON health contract
- Swagger UI

Verified successfully.

Current environment:

- Ubuntu
- Python 3.12.13 in backend/venv
- FastAPI 0.141.1
- Uvicorn 0.53.0

A separate Python 3.14 virtual environment may exist.

Do not use it.

Next planned iteration:

Day 1 — Iteration 2: Pydantic Settings.

Only begin when explicitly authorized.

## 19. Mandatory Response Format

For each completed iteration, respond in French using:

1. Objectif
2. Concept technique
3. Modifications effectuées
4. Explication du fonctionnement
5. Commandes de test Ubuntu
6. Résultats réels des tests
7. Attente de validation

Keep explanations concise and educational.

Never claim that an unexecuted test succeeded.

Always stop after the current iteration.

## 20. Final Principle

Build SecureBank-AI incrementally.

Favor:

Correctness over speed.

Understanding over automation.

Security over convenience.

Evidence over plausible answers.

Simplicity over unnecessary complexity.

One iteration at a time.

## 21. SOLID Principles

Apply the five SOLID principles whenever they provide concrete value:

- Single Responsibility Principle: each module, class, and function must have one clearly defined responsibility.
- Open/Closed Principle: prefer components that can be extended without unnecessary modification of existing code.
- Liskov Substitution Principle: preserve the behavioral contracts of interfaces and abstractions.
- Interface Segregation Principle: use small, specialized interfaces.
- Dependency Inversion Principle: decouple business logic from technical implementations through dependency injection when necessary.

Apply SOLID pragmatically:

- Treat the Single Responsibility Principle as mandatory.
- Do not create unnecessary classes or interfaces.
- Do not introduce premature abstractions.
- Prefer composition.
- Use Python Protocols only when they provide real value.
- Use the FastAPI dependency system when appropriate.
- Apply Dependency Inversion when it removes meaningful coupling to technical implementations.
- Explain which SOLID principles apply during each iteration.

## 22. Modular Architecture Boundaries

Enforce these module responsibilities strictly when the corresponding modules are needed:

### backend/app/api/

HTTP routes, endpoints, and FastAPI dependencies.

### backend/app/core/

Application configuration, authentication, and security infrastructure.

### backend/app/schemas/

Pydantic models, validation, and data contracts.

### backend/app/services/

Business logic, use cases, and application services.

Introduce these future modules only when required by an authorized iteration:

### backend/app/rag/

Hybrid retrieval, reranking, evidence validation, and abstention.

### backend/app/agents/

LangGraph orchestration, AgentState, supervisor, and routing.

### backend/app/integrations/

External service clients, Qdrant, MCP, and observability.

### backend/mcp_server/

Independent FastMCP server and simulated banking business tools.

Architectural rules:

- Routes must not contain complex business logic.
- Services must not depend on HTTP routes.
- Pydantic schemas must not orchestrate workflows.
- External integrations must remain isolated.
- Do not couple business logic directly to external services when an application boundary is warranted.
- Avoid circular dependencies.
- Preserve separation of responsibilities.
- Keep the architecture extensible and minimal.
- Never create future modules prematurely.
- Do not create any module without a functional need in the current authorized iteration.
- Explain every significant architectural evolution before implementation.
- The repository tree in Section 3 is a target structure and does not imply that every listed directory currently exists.

## 23. Continuous Documentation

Codex is responsible for creating and maintaining README.md at the repository root.

README.md must be written in English and contain:

- Project Overview
- Project Objectives
- Technology Stack
- System Architecture
- Repository Structure
- Prerequisites
- Installation
- Environment Configuration
- Running the Backend
- Running the Frontend when implemented
- Running Tests
- API Documentation
- Security Considerations
- Deployment when implemented
- Development Roadmap
- Current Implementation Status
- Known Limitations

README.md must allow a developer to clone and start the project on Ubuntu.

Include exact commands for:

- Cloning the repository
- Creating and activating a Python 3.12 virtual environment
- Installing backend dependencies
- Configuring environment variables
- Starting FastAPI
- Testing GET /health
- Accessing Swagger UI
- Running tests when tests exist

Documentation rules:

- Document only functionality that is actually available.
- Clearly distinguish Implemented, In Progress, and Planned capabilities.
- Never invent functionality, commands, dependencies, or environment variables.
- After every validated iteration, check whether README.md needs updating.
- Documentation updates are part of the iteration and are not a separate feature.

## 24. FastAPI Best Practices

Apply these rules to every FastAPI implementation:

- Use async def only when the endpoint performs asynchronous work or awaits asynchronous dependencies.
- Never block the event loop with expensive synchronous I/O or CPU-bound work.
- Use Depends for dependency injection when it provides a clear application boundary.
- Introduce APIRouter when the number or grouping of endpoints justifies it.
- Keep HTTP routes thin and free of complex business logic.
- Separate request validation, business logic, and infrastructure concerns.
- Use Pydantic models for complex request and response contracts.
- Define coherent HTTP status codes.
- Do not expose internal implementation details in error responses.
- Preserve compatibility with Render and a stateless deployment model.
- Avoid unnecessary middleware.
- Do not introduce complex mechanisms before a concrete requirement exists.

## 25. Pydantic v2 Best Practices

Apply these rules to configuration and data contracts:

- Use Pydantic v2 APIs.
- Use BaseSettings for application configuration.
- Use SettingsConfigDict when settings source behavior requires configuration.
- Validate critical parameters explicitly.
- Source deployable configuration from environment variables.
- Never hard-code secrets.
- Use SecretStr for secret values when it provides meaningful protection against accidental disclosure.
- Keep configuration, data validation, and business logic separate.
- Test default settings and environment overrides.
- Avoid unnecessarily complex Pydantic models.

## 26. Code Quality Tools

Ruff is the preferred tool for Python linting, format verification, and import organization.

When Ruff is available, run from backend/ or use explicit appropriate paths:

```bash
ruff check .
ruff format --check .
```

Never run these mutating commands without explicit user authorization:

```bash
ruff check --fix .
ruff format .
```

If a static type checker is configured, run it with the project configuration.

Do not install Ruff, a type checker, or another quality tool without a concrete justification for the current iteration.

## 27. Quality Gate Before Validation

Before declaring an implementation complete, Codex must:

1. Verify compliance with the modular architecture boundaries.
2. Verify the relevant SOLID principles, including Single Responsibility.
3. Verify explicit typing and Python 3.12 compatibility.
4. Verify the absence of code comments, explanatory docstrings, commented-out code, dead code, and unnecessary duplication.
5. Execute the tests relevant to the iteration.
6. Execute Ruff checks when Ruff is available.
7. Check for regressions in existing behavior and tests.
8. Verify that secrets and sensitive values are not exposed in code, logs, tests, documentation, or responses.
9. Determine whether README.md requires an update and update it when the validated behavior changed.
10. Report every check that could not be completed and explain why.

An iteration must not be declared validated while blocking errors remain.

Codex may declare its implementation complete after the quality gate passes. Final iteration validation always belongs to the user.
