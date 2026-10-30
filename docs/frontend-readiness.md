# Frontend readiness audit

## Useful routes

| Method | Route | Authentication | Authorized roles | Purpose |
| --- | --- | --- | --- | --- |
| `GET` | `/health` | None | Public | Backend availability, service name, and version |
| `GET` | `/auth/me` | Bearer JWT | Any recognized role | Current subject and role |
| `GET` | `/auth/analyst` | Bearer JWT | `analyst`, `compliance_officer`, `admin` | RBAC demonstration |
| `GET` | `/auth/admin` | Bearer JWT | `admin` | Admin RBAC demonstration |
| `POST` | `/pii/mask` | Bearer JWT | `analyst`, `compliance_officer`, `admin` | Local PII masking |
| `POST` | `/rag/ask` | Bearer JWT | `analyst`, `compliance_officer`, `admin` | Evidence-grounded RAG answer or abstention |

The backend has no login, token refresh, logout, or revocation route. It validates tokens issued elsewhere.

## JSON contracts

`GET /health` returns:

```json
{
  "status": "healthy",
  "service": "securebank-ai",
  "version": "0.1.0"
}
```

`GET /auth/me` returns:

```json
{
  "sub": "synthetic-user",
  "role": "analyst"
}
```

`POST /rag/ask` accepts `question` and optional `top_k`:

```json
{
  "question": "Quelle règle synthétique s'applique ?",
  "top_k": 3
}
```

`question` must contain between 1 and 2,000 characters and cannot contain only whitespace. `top_k` is a strict integer from 1 through 5 and defaults to 3.

A successful response has this structure:

```json
{
  "question": "Question après masquage local",
  "answer": "Réponse fondée sur les éléments retournés [1].",
  "sources": [
    {
      "id": "chunk-1",
      "document_id": "document-1",
      "content": "Passage synthétique après masquage local.",
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

`POST /pii/mask` accepts a non-blank `text` from 1 through 10,000 characters and returns `{"masked_text":"..."}`.

## Authentication and roles

Protected routes require `Authorization: Bearer <token>`. JWT validation permits only HS256 and requires a valid signature, expiration, issuer, audience, non-blank subject, and one recognized `role` claim. The roles are `analyst`, `compliance_officer`, and `admin`.

The token lifetime is determined by its `exp` claim. The backend does not define an issuance duration. `/auth/me` is the route for loading the current `sub` and `role` after a token has been obtained externally.

HTTP 401 means credentials are absent or invalid and includes `WWW-Authenticate: Bearer`. HTTP 403 means the authenticated role is not allowed. There is no refresh, logout, server-side session, denylist, or revocation mechanism.

## Citations and abstentions

Each citation contains a one-based `reference`, `document_id`, and `chunk_id`. The matching source contains the displayed passage, title, source, position, and identifiers. The frontend can resolve a citation by `document_id` and `chunk_id` and display its matching source.

An abstention is a normal HTTP 200 response with `abstained: true` and an empty `citations` list. It is a business outcome, not a technical error. The response still contains a non-blank explanatory answer and may contain retrieved sources.

## CORS

The application has no `CORSMiddleware`. No browser origin, method, or request header is currently authorized through CORS response headers. A frontend served from another origin, including a typical local Vite port, cannot call the backend directly with `Authorization`.

Before direct browser integration, configure a narrow origin allowlist containing the exact development frontend origin, allow the required methods, and allow the `Authorization` and `Content-Type` headers. Do not use a wildcard origin. A same-origin development proxy can temporarily avoid cross-origin requests but does not replace deployment CORS configuration.

## Errors and expected behavior

| Status | Meaning |
| --- | --- |
| `200` | Successful answer or explicit business abstention |
| `401` | Missing, malformed, expired, incorrectly signed, or otherwise invalid JWT |
| `403` | Authenticated role lacks permission |
| `422` | Invalid request; RAG and PII routes return sanitized validation details without the submitted value |
| `502` | Generation provider unavailable or returned an invalid response |
| `503` | RAG disabled or misconfigured, retrieval unavailable, or PII protection unavailable |

When `RAG_ENABLED=false`, authenticated `POST /rag/ask` requests return `503` with `{"detail":"RAG pipeline is not configured"}` without initializing the pipeline. Other routes remain usable.

Provider exceptions, Qdrant details, raw generation responses, and PII protection details are replaced with stable public messages. The application code does not add request-body logging. Infrastructure access and exception logging must still be configured so tokens, bodies, and query content are not captured.

## Confidentiality

The RAG response deliberately exposes the masked question, masked answer, masked source passages, masked titles, source identifiers, citations, and the abstention flag. These are the fields the frontend may display. Masking reduces exposure but is not guaranteed to detect every identifier, so real banking data remains outside the approved prototype usage.

The frontend must not display or persist JWTs, API keys, raw provider errors, server configuration, or Langfuse credentials. It must not treat source content as automatically safe HTML. Render it as text unless a separate sanitization policy is introduced.

## Blocking findings

- Direct browser integration is blocked until exact frontend origins and required headers are allowed by CORS, or a same-origin proxy is used for local development.
- End-to-end login, refresh, and logout flows are blocked until an external identity provider or a separate backend authentication contract is selected. The current backend only consumes existing JWTs.

These findings do not block initial component development, routing, typed API clients, mocked flows, or integration with a separately supplied development JWT.

## Non-blocking findings

- There is no dedicated capability or readiness endpoint for RAG; the frontend learns that it is disabled from the safe `503` response.
- There is no dedicated logout endpoint. Client-side token removal is sufficient only when the chosen token issuer and risk model permit it.
- There is no refresh-token contract or documented token issuance lifetime because token issuance is outside this backend.
- The API returns complete masked source chunks. UI truncation and disclosure controls can be designed during frontend implementation.
- `/auth/analyst` and `/auth/admin` are RBAC demonstration endpoints and are not required for the main frontend flow.

## Recommendation

**GO with prerequisites.** Frontend structure, screens, role-aware navigation, typed contracts, mocked RAG states, abstention rendering, and error handling can begin now, including when `RAG_ENABLED=false`. Direct browser-to-backend integration requires a minimal CORS decision. A complete authentication journey requires a documented external token issuer or a separately authorized authentication iteration.
