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

## Current limitations

The frontend currently contains one static home page. It has no authentication flow, API integration, routing, business interface, or production CORS configuration. It uses no real banking data and does not claim an active RAG connection.
