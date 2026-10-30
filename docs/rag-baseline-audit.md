# RAG Baseline Audit

## Scope

This audit describes the implementation present at code version `2083519fae3fc2d026991322c23da6db67a387f6`. The project is an R&D prototype, not a certified or legally compliant banking product.

## Runtime pipeline

```text
POST /rag/ask
  -> Bearer JWT validation and role check
  -> request validation: question 1..2000 characters, top_k 1..5
  -> local PII masking of the question
  -> BM25 search over in-memory chunks, candidate count = top_k * 3
  -> local MiniLM question embedding
  -> Qdrant cosine search, candidate count = top_k * 3
  -> reciprocal rank fusion, rrf_k = 60
  -> keep top_k fused passages
  -> local PII masking of passage content, title, and source
  -> deterministic JSON context and grounded French prompt
  -> OpenAI-compatible Responses API generation
  -> strict JSON, abstention, and citation validation
  -> local PII masking of the answer
  -> typed answer, sources, citations, and abstention flag
```

The corpus is loaded from `RAG_CORPUS_PATH` and split into 180-character chunks with a 30-character overlap. The local embedding model is `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, loaded offline from `backend/models`, and produces 384-dimensional vectors. Qdrant uses the configured URL and `securebank_chunks` by default, with cosine distance. Chunks are deterministically upserted when the lazy RAG service is first built.

The active generation pipeline has no similarity threshold, metadata filter, semantic evidence validator, or reranker. FlashRank `ms-marco-MultiBERT-L-12` exists only in the experimental comparator. The API default is `top_k=3`; callers may select 1 through 5. BM25 excludes chunks with no lexical token overlap. Qdrant results are not thresholded.

The prompt serializes ordered passage metadata and content as JSON. It restricts the model to supplied passages, treats passage text as untrusted data, requires numbered citations, and defines an exact abstention response. Empty retrieval causes deterministic abstention without an LLM call. Model-requested abstention is normalized. A non-abstained answer without a valid in-range citation is rejected. Citation validation proves reference integrity, not claim support or answer correctness.

PII masking is fail-closed before retrieval and generation and again after generation. Questions, passage content, titles, sources, and answers are masked. Document and chunk identifiers are not masked and must remain opaque. Authentication, RBAC, session, and CSRF behavior were not changed by this baseline work.

## Langfuse audit

The backend pins the official Python SDK at `langfuse==4.17.0`. Observability is conditionally enabled with `LANGFUSE_ENABLED`; the current local environment enables it and targets `http://127.0.0.1:3000`. Keys remain in the ignored environment file and were not read or modified.

Each RAG request can create a `rag-request` span with one `rag-retrieval` child and, when generation occurs, one `rag-generation` child. Exported application metadata is allowlisted:

- retrieval duration and passage count;
- generation duration, model name, and complete token counters when available;
- total request duration, success or error status, and abstention when known.

Questions, prompts, answers, passages, citations, credentials, and raw exceptions are not exported by application code. Synchronous observer failures are swallowed and do not change the RAG response. SDK construction failure falls back to the no-op observer. Network export is asynchronous; server unavailability can therefore lose telemetry without failing the request. No retry, delivery confirmation, or trace identifier is currently returned to application code. Error traces carry an error level and generic `error` status, but no exception detail.

## Experimental variables

| Variable | Current value | Location | Modification cost |
| --- | --- | --- | --- |
| API `top_k` | default 3, allowed 1..5 | `schemas/rag_generation.py` | Simple configuration/request |
| Hybrid candidate multiplier | 3 | `services/hybrid.py` | Simple code configuration |
| RRF constant | 60 | `services/hybrid.py` | Simple code configuration |
| Similarity threshold | absent | `services/qdrant.py` | Architecture/behavior change |
| Chunk size | 180 characters | `services/rag_corpus.py` | Reindexing required |
| Chunk overlap | 30 characters | `services/rag_corpus.py` | Reindexing required |
| Embedding model | multilingual MiniLM L12 v2 | `services/embeddings.py` | Model preparation and reindexing |
| Embedding dimension | 384 | `services/qdrant.py` | Collection recreation/reindexing |
| Qdrant distance | cosine | `services/qdrant.py` | Collection recreation/reindexing |
| Search strategy | BM25 + Qdrant + RRF | `services/hybrid.py`, `core/rag_factory.py` | Architecture change |
| Reranking in active RAG | absent | `core/rag_factory.py` | Architecture change |
| Experimental reranker | FlashRank MultiBERT L12, max length 512 | `services/reranking.py` | Simple experimental switch after local model preparation |
| Prompt | deterministic French JSON prompt | `services/rag_generation.py` | Simple code change, requires generation reevaluation |
| Generation model | `gpt-4.1-mini` | `core/config.py`, local environment | Simple configuration |
| Generation timeout | 30 seconds | `core/config.py`, local environment | Simple configuration |
| Temperature and sampling | not configured | `services/llm.py` | Code/provider-contract change |

## Reproducible baseline

The retrieval dataset contains 30 synthetic documents and 40 documented answerable cases: 15 factual, 15 semantic, and 10 difficult. `backend/data/rag_generation_benchmark.json` adds expectation-only cases for answerable, unanswerable, ambiguous, citation, and confidentiality behavior. These expectations are not reported as measured scores.

Run from `backend/` with Qdrant available and the two local models prepared:

```bash
./venv/bin/python -m scripts.run_rag_baseline
```

Each successful run creates a new JSON file in `backend/benchmark_results`; existing runs are not overwritten. The record contains its benchmark and run identifiers, UTC date, Git revision, exact RAG configuration, optional parameter change, measured metrics, uncomputed metrics, and optional Langfuse trace identifiers.

The first measured retrieval run is `20261030T150643Z_9f7d9cadfc6f4033b3448b5515e1ee21.json`. Its aggregate results are:

| Engine | Source Hit@1 | Source Hit@3 | Evidence Hit@1 | Evidence Hit@3 | Mean local latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| BM25 | 0.575 | 0.800 | 0.450 | 0.700 | 0.344 ms |
| Qdrant | 0.550 | 0.700 | 0.350 | 0.525 | 21.834 ms |
| RRF | 0.600 | 0.800 | 0.425 | 0.675 | 15.365 ms |
| RRF + FlashRank | 0.300 | 0.825 | 0.250 | 0.650 | 229.547 ms |

Latency is a single local measurement, not a production benchmark. Answer correctness, abstention accuracy, citation correctness, and PII masking recall remain uncomputed. This run emitted no Langfuse traces because it evaluates retrieval engines directly rather than invoking the generative RAG service.

## Evaluation tab prerequisites

The next iteration should add a protected backend read API over validated historical result files, restricted by existing RBAC and same-origin session/CSRF rules. The frontend tab should consume only aggregate and sanitized per-case evaluation data. It should support run selection, configuration comparison, changed-parameter display, metric deltas, and linked Langfuse trace identifiers without exposing prompts, content, secrets, or PII. Generation evaluation and trace correlation should be implemented before presenting abstention, citation, or confidentiality scores.
