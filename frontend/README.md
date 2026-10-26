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

The frontend currently contains a responsive presentation dashboard inside a reusable application shell. The navigation identifies future sections without linking to unavailable routes. There is no authentication flow, application-level API integration, routing, business interface, or production CORS configuration. The Docker proxy provides same-origin access locally but does not define the future cloud deployment architecture. The frontend uses no real banking data and does not claim an active RAG connection.
