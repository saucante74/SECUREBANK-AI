# Local Langfuse Validation

## Purpose and safety boundary

This procedure prepares the first local validation of SecureBank-AI trace export to Langfuse. It is intentionally manual and must not be executed with real banking data. It validates local connectivity and the visible trace shape; it does not validate regulatory compliance, business correctness, evidence quality, retention policy, access governance, backup, or production readiness.

The validation emits only a random technical trace identifier, numeric durations, a passage count, a synthetic model name, and a `success` status. It does not start the RAG pipeline and cannot call OpenAI.

## Preconditions

- Docker Engine and Docker Compose are installed.
- Backend dependencies are installed in `backend/venv` with Python 3.12.
- Ports `3000` and `9090` are available on the loopback interface.
- No real customer, employee, account, transaction, authentication, or regulatory case data is used.

## A. Prepare local secrets

From the repository root, create the ignored local environment file and restrict its permissions:

```bash
cp .env.langfuse.example .env.langfuse
chmod 600 .env.langfuse
```

Replace every `replace-with-...` placeholder in `.env.langfuse` with a unique, locally generated high-entropy value. Use at least 32 random bytes for `NEXTAUTH_SECRET` and `SALT`, exactly 32 random bytes encoded as 64 hexadecimal characters for `ENCRYPTION_KEY`, and unique random passwords for PostgreSQL, ClickHouse, Redis, and MinIO. Generate and insert them without copying them into shell history, chat, tickets, source files, screenshots, or command output retained in logs.

Verify only that no placeholder remains:

```bash
if grep --quiet 'replace-with-' .env.langfuse; then
  echo 'Langfuse placeholders remain' >&2
  exit 1
fi
```

Do not commit `.env.langfuse`. Confirm its ignored status without displaying its contents:

```bash
git check-ignore -v .env.langfuse
```

## B. Start the Langfuse stack explicitly

Review the resolved configuration without printing it:

```bash
docker compose --project-name securebank-langfuse \
  --env-file .env.langfuse \
  -f compose.langfuse.yml config --quiet
```

Start the six services only after that command succeeds:

```bash
docker compose --project-name securebank-langfuse \
  --env-file .env.langfuse \
  -f compose.langfuse.yml up --detach
```

Inspect service state without printing environment variables:

```bash
docker compose --project-name securebank-langfuse \
  --env-file .env.langfuse \
  -f compose.langfuse.yml ps
```

PostgreSQL, ClickHouse, Redis, and MinIO have Compose healthchecks. The current Compose file does not define healthchecks for `langfuse-web` or `langfuse-worker`, so their readiness must be confirmed through service state, the web interface, and the later trace ingestion check.

## C. Verify the web interface

Open `http://127.0.0.1:3000` locally. Complete the local Langfuse account setup if required. Do not expose port `3000` through a public interface, tunnel, or reverse proxy for this validation.

The MinIO API is published only at `127.0.0.1:9090` because Langfuse media URLs use it. No MinIO console port is published.

## D. Configure Langfuse API keys

Create a dedicated local Langfuse project in the web interface and create project API keys. Store the public and secret keys only in the ignored `backend/.env` file:

```text
LANGFUSE_ENABLED=false
LANGFUSE_PUBLIC_KEY=<local-project-public-key>
LANGFUSE_SECRET_KEY=<local-project-secret-key>
LANGFUSE_HOST=http://127.0.0.1:3000
```

Keep `LANGFUSE_ENABLED=false` until the stack and local project are ready. Do not print the file, pass keys as command-line arguments, or copy them into the Langfuse Compose environment file.

## E. Enable the backend explicitly

Change only this line in the ignored `backend/.env` file:

```text
LANGFUSE_ENABLED=true
```

The SDK remains lazy: the application import and FastAPI startup do not create the Langfuse client. Construction occurs only when the lazy RAG factory builds the RAG service. The standalone validation in the next section creates the same SDK client boundary directly and does not construct the RAG pipeline.

## F. Emit one synthetic technical trace

Run this command from `backend/`. It performs a local Langfuse request only after the explicit configuration above. It does not load the corpus, retrieve documents, call an LLM, or print observation content or credentials.

```bash
./venv/bin/python - <<'PY'
import sys
import time
from uuid import uuid4

from langfuse import Langfuse, is_langfuse_span

from app.core.config import Settings
from app.services.langfuse_sdk_client import LangfuseSdkObservationClient
from app.services.rag_observer import RagRequestStatus

settings = Settings()
if not settings.langfuse_enabled:
    print("Langfuse validation is disabled", file=sys.stderr)
    raise SystemExit(1)
if settings.langfuse_public_key is None or settings.langfuse_secret_key is None:
    print("Langfuse validation configuration is incomplete", file=sys.stderr)
    raise SystemExit(1)

try:
    sdk = Langfuse(
        public_key=settings.langfuse_public_key.get_secret_value(),
        secret_key=settings.langfuse_secret_key.get_secret_value(),
        base_url=str(settings.langfuse_host),
        debug=False,
        should_export_span=is_langfuse_span,
    )
    client = LangfuseSdkObservationClient(sdk)
    trace_id = uuid4().hex
    request_started = time.perf_counter()
    client.start_trace(trace_id=trace_id)
    client.record_retrieval(
        trace_id=trace_id,
        duration_seconds=0.001,
        passage_count=0,
    )
    client.record_generation(
        trace_id=trace_id,
        duration_seconds=0.001,
        model="synthetic-local-validation-model",
    )
    client.finish_trace(
        trace_id=trace_id,
        status=RagRequestStatus.SUCCESS,
        total_duration_seconds=time.perf_counter() - request_started,
        abstained=False,
    )
    sdk.flush()
except Exception:
    print("Synthetic Langfuse validation failed", file=sys.stderr)
    raise SystemExit(1) from None

print("Synthetic Langfuse validation submitted")
PY
```

The final message means the synchronous SDK calls and flush request returned. It does not prove that the asynchronous exporter delivered the trace. Confirm delivery in the Langfuse interface.

## G. Verify the exported trace

In the local Langfuse interface, find the newest `rag-request` trace and confirm that it contains:

- one `rag-retrieval` child with numeric `duration_seconds` and `passage_count=0`;
- one `rag-generation` child with numeric `duration_seconds` and model `synthetic-local-validation-model`;
- final status `success`, numeric non-negative `total_duration_seconds`, and boolean `abstained=false` on `rag-request`;
- one shared technical trace identifier.

`total_duration_seconds` measures the complete RAG request with a monotonic clock and is not calculated by adding retrieval and generation durations. `abstained` records the final business outcome only when it is known; failed requests omit it. `passage_count` is the integer number of retrieval results and remains attached only to `rag-retrieval`.

If no trace appears, inspect container status and sanitized logs. Do not paste full logs into external systems because SDK or infrastructure diagnostics may contain endpoints or operational identifiers.

## H. Verify the absence of sensitive data

Inspect the root and both child observations. Confirm that none contains:

- a question, prompt, answer, document, passage, title, source, or citation;
- a JWT, API key, password, personal identifier, or raw exception;
- arbitrary application metadata;
- populated business `input` or `output` fields.

The application exports only the status and the three technical metrics described above, plus the existing observation names, durations, and model identifier. It never adds questions, answers, prompts, passages, documents, titles, sources, citations, personal identifiers, JWTs, secret keys, or raw exceptions to Langfuse metadata.

The SDK and OpenTelemetry protocol still add transport and tracing fields such as observation names, types, timestamps, span identifiers, SDK version, and authentication headers required by the local Langfuse server. The application-level allowlist cannot remove protocol-required fields. The `is_langfuse_span` filter excludes known third-party LLM instrumentation spans, but the exact server-side representation cannot be guaranteed until this visual inspection is completed.

### Public key in technical metadata

Langfuse Python SDK 4.17.0 creates its OpenTelemetry tracer with the project public key in the instrumentation scope attributes. The Langfuse span processor reads this attribute before export to associate SDK spans with the correct client and prevent cross-project export. OpenTelemetry serializes the resulting instrumentation scope as `scope.attributes.public_key`; OpenTelemetry does not create the value itself.

The public key identifies the Langfuse project but does not grant access without the corresponding secret key. The secret key is used with the public key in the OTLP authentication header and must never appear in trace metadata, logs, documentation, screenshots, or diagnostics. The public key remains operational metadata and should still be disclosed only where needed.

Langfuse 4.17.0 provides no public API that removes instrumentation scope attributes. Its public `mask_otel_spans` hook can change span attributes only and explicitly cannot change the instrumentation scope. A custom span exporter would require application-owned reconstruction of OpenTelemetry spans and manual preservation of the Langfuse endpoint, authentication headers, batching, and compatibility behavior. This validation therefore keeps `scope.attributes.public_key` unchanged rather than depending on SDK internals, a monkey patch, or a fragile exporter wrapper.

Apply the following confidentiality policy:

- treat the public key as a project identifier with limited disclosure, not as an authentication secret;
- keep the secret key restricted to the ignored backend environment file and transport authentication;
- restrict access to Langfuse traces, exports, screenshots, and diagnostic logs;
- avoid copying raw trace payloads into external systems;
- rotate the project credentials if project identifiers or authentication material are disclosed beyond the intended environment;
- reassess this decision when upgrading Langfuse if a documented instrumentation-scope filtering API becomes available.

## I. Disable Langfuse

Restore this value in `backend/.env`:

```text
LANGFUSE_ENABLED=false
```

Restart the backend process if it was running. A newly constructed RAG pipeline will then use `NoOpRagObserver` and create no Langfuse client.

## J. Stop the containers safely

Stop and remove the Langfuse containers and network while preserving all named volumes:

```bash
docker compose --project-name securebank-langfuse \
  --env-file .env.langfuse \
  -f compose.langfuse.yml down
```

Do not add `--volumes` or `-v`. Those options delete the local PostgreSQL, ClickHouse, Redis, and MinIO data and are outside this validation procedure.

## Failure interpretation

Synchronous SDK construction and observation-method exceptions are isolated by the application and fall back to or behave like the no-op observer. They do not change the RAG response and do not retry the LLM.

Server unavailability during span export is different. Langfuse 4.17.0 uses an OpenTelemetry batch processor, so network export normally occurs asynchronously after an observation ends. A mock that raises from `start_observation`, `update`, or `end` validates synchronous isolation only; it does not validate an unavailable server. This procedure requires the UI ingestion check to establish successful local delivery. A later deliberately authorized test is required to observe real network failure behavior.
