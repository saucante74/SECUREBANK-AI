# SecureBank-AI Frontend

## Prerequisites

- Node.js 24 or later
- npm 11 or later

## Installation

```bash
cd frontend
npm install
```

## Development server

```bash
npm run dev
```

Vite serves the application locally and prints the exact URL in the terminal.

## Quality checks

```bash
npm run build
npm run lint
npm run test
```

## FastAPI development proxy

Requests sent by the frontend to `/api/*` are forwarded to `http://127.0.0.1:8000/*` during local Vite development. The `/api` prefix is removed before forwarding, so `/api/health` reaches the backend route `/health`.

Start FastAPI on port `8000` before using the proxy. The current home page does not make API requests.

## TypeScript API client

The centralized API client is located in `src/api/`. It uses the native `fetch` API and the relative `/api` prefix, which works with both the Vite development proxy and the Nginx Docker proxy.

The service functions are:

- `getHealth()` for `GET /api/health`;
- `getCurrentUser(token)` for `GET /api/auth/me`;
- `askRag(request, token)` for `POST /api/rag/ask`.

Protected services accept a Bearer token supplied by their caller. The client does not create, persist, or retrieve tokens and does not provide a login or session system. An `AbortSignal` and a custom API client backed by an injected `fetch` implementation can be supplied when cancellation or isolated testing is needed.

Failures are represented by a structured `ApiError`. It distinguishes unauthenticated, forbidden, validation, upstream provider, unavailable service, network, cancellation, unexpected response, and other HTTP failures. User-facing messages are stable and do not expose arbitrary server response bodies.

The API services are not connected to the interface yet and make no automatic request when the application loads.

## Docker image

Build the production-style Nginx image from the repository root:

```bash
docker compose build frontend
```

The build stage uses Node.js 24, installs the locked dependencies with `npm ci`, and creates the static Vite bundle. The runtime stage contains only Nginx, its configuration, and the compiled files. It does not contain `node_modules` or local environment files.

Start the application stack:

```bash
docker compose up --build frontend
```

Open `http://localhost:8080`. The Compose backend must be able to start successfully. The frontend container reaches it through the Compose network with the service name `backend`.

Inside Docker, Nginx forwards `/api/*` to `http://backend:8000/*` and removes the `/api` prefix. It disables API response caching and API access logging. In local npm development, Vite provides the equivalent proxy to `http://127.0.0.1:8000` instead.

Verify the running frontend and public health proxy:

```bash
curl --fail http://localhost:8080/
curl --fail http://localhost:8080/api/health
```

Stop the stack without removing volumes:

```bash
docker compose down
```

## Current limitations

The frontend currently contains a responsive presentation dashboard inside a reusable application shell and a typed API client that is not connected to the interface. The navigation identifies future sections without linking to unavailable routes. There is no authentication flow, routing, business interface, or production CORS configuration. The Docker proxy provides same-origin access locally but does not define the future cloud deployment architecture. The frontend uses no real banking data and does not claim an active RAG connection.
