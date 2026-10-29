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

Start FastAPI on port `8000` before using the proxy. Public pages remain available when the backend reports that no session exists.

## TypeScript API client

The centralized API client is located in `src/api/`. It uses the native `fetch` API and the relative `/api` prefix, which works with both the Vite development proxy and the Nginx Docker proxy.

The service functions are:

- `getHealth()` for `GET /api/health`;
- `getCurrentUser()` for cookie-authenticated `GET /api/auth/me`;
- `loginUser(credentials)` for `POST /api/auth/login`;
- `logoutUser()` for CSRF-protected `POST /api/auth/logout`;
- `askRag(request)` for CSRF-protected `POST /api/rag/ask`.

Every request uses `credentials: "include"`. Protected session requests copy the readable `securebank_csrf` cookie into `X-CSRF-Token`. The generic API client retains optional Bearer support for API compatibility, but the React interface has no manual token entry. No JWT, username, password, question, or RAG response is stored in browser storage. An `AbortSignal` and a custom API client backed by an injected `fetch` implementation can be supplied when cancellation or isolated testing is needed.

Failures are represented by a structured `ApiError`. It distinguishes unauthenticated, forbidden, validation, upstream provider, unavailable service, network, cancellation, unexpected response, and other HTTP failures. User-facing messages are stable and do not expose arbitrary server response bodies.

The application checks `GET /auth/me` once at startup to restore an existing cookie session. HTTP 401 leaves the public application accessible and does not open the login dialog.

## Application navigation and Assistant

The application provides two directly accessible pages:

- `/` for the presentation dashboard;
- `/assistant` for the documentary Assistant interface.

Navigation uses native browser history and supports direct access, reload, and previous or next navigation without an external routing dependency. The responsive sidebar identifies the active page and keeps the About entry non-interactive as a planned capability.

The Assistant page provides an accessible controlled textarea with a 2,000-character limit, a character counter, three localized suggested-question buttons, an empty conversation area, and reusable presentation components for typed RAG answers, sources, citations, and abstentions. Selecting a suggestion only fills the textarea and never submits automatically. Long source excerpts are visually limited while their text remains in the document, and citations link only to sources whose document and chunk identifiers match.

The Assistant connects to `POST /api/rag/ask` through the existing typed `askRag` service. A valid non-blank question enables submission. Anonymous submission opens an accessible login dialog without clearing the question. Successful login closes the dialog and immediately submits the preserved question through the cookie session. While a request is active, the question remains visible, duplicate submission is disabled, and an accessible loading panel cycles through localized waiting indications without presenting them as backend telemetry. Successful responses, sources, citations, and business abstentions use the existing typed presentation components. HTTP 401 reopens login for an expired session; other structured failures map to localized safe messages.

The dialog moves focus to the username, traps keyboard focus, closes through Cancel or Escape, and restores focus to its trigger. The header provides accessible icon actions for sign-in and sign-out. Sign-out requires confirmation in a keyboard-accessible dialog; cancellation preserves the session, while successful confirmation clears Assistant question and response and leaves public pages accessible.

Active requests use `AbortController`. They are cancelled when the Assistant unmounts or when navigation leaves the page. Request sequencing prevents a late or obsolete response from updating the interface.

## Internationalization

The complete interface is available in French, English, and Italian through local `i18next` catalogs. French is the default and fallback language. The language selector in the header changes the interface without reloading the page, changing its URL, resetting navigation, or clearing the current Assistant question.

Only the validated language code is stored under `securebank.language` in `localStorage`. Missing, invalid, or unavailable storage safely falls back to French. The root HTML `lang` attribute follows every language change.

Internationalization applies only to interface labels, accessibility text, presentation states, and the future mapping of API error categories. User questions, generated answers, document titles, excerpts, source references, and citation identifiers are never translated automatically. The backend API contracts and requests contain no language parameter, and the backend is not presented as multilingual.

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

The frontend contains a responsive public dashboard, native browser navigation, a French/English/Italian interface, on-demand cookie authentication, reusable RAG response presentation components, and a typed API client. The Compose stack persists backend users and sessions in the `securebank_users` named volume. RAG remains dependent on its separately configured backend corpus, Qdrant, local model, and LLM provider. The frontend must be used only with synthetic data and is not a production banking interface.
