# Architecture

The API creates durable agent runs, indexes raw document text in ChromaDB, and
records trace events in PostgreSQL. The current orchestration path is explicit
and deterministic. It does not use autonomous LLM-based tool selection.

## Document retrieval flow

```text
uploaded file
  → parser selection
  → normalized parsed text
  → chunking
  → mock embeddings
  → ChromaDB
  → POST /documents/search
  → matching chunks with distances
```

For run-linked retrieval, `POST /runs/{run_id}/retrieve` reuses the same search
path and persists the query plus retrieved chunks in `retrieval_events`.

## Structured business data flow

```text
approved customer or sales filters
  → business service
  → PostgreSQL
  → deterministic results or summaries
  → optional tool_calls audit record
```

The business endpoints expose approved filters only. They do not accept raw SQL
or choose tools dynamically.

## Deterministic orchestration flow

```text
business question
  → create run
  → set status to running
  → optional document retrieval
  → optional customer query
  → sales summary
  → retrieval_events + tool_calls
  → deterministic trace summary
  → set status to completed
```

`POST /agent/run` executes this plan directly. The steps are fixed in code and
do not depend on autonomous reasoning or LLM-driven tool selection.

## Response generation flow

```text
business question
  → deterministic orchestration
  → trace summary
  → provider abstraction
  → controlled generated response
  → future autonomous agent layer
```

When `generate_response=true`, the completed trace is passed to the configured
provider. The provider only transforms the existing trace into a readable
response. It does not choose tools or trigger additional retrieval or business
queries.

## MCP exposure flow

```text
MCP client
  → MCP server
  → approved tool wrapper
  → existing service layer
  → PostgreSQL / ChromaDB
  → structured MCP response
```

The MCP wrapper layer reuses the same deterministic business and orchestration
services used by the HTTP API. It does not expose raw SQL, shell execution, or
arbitrary write operations.

## RAG evaluation flow

```text
golden eval case
  → ingest case documents
  → run deterministic orchestration
  → inspect retrieval_events / tool_calls / generated_response
  → compute deterministic metrics
  → eval report
```

The eval layer reuses the existing ingestion, retrieval, orchestration, and
response-generation boundaries. It scores retrieval expectations, generated
response consistency, and trace creation without using LLM-as-judge behavior.

## Agno agent flow

```text
business question
  → Agno agent adapter
  → allowlisted Agno tools
  → existing service layer
  → retrieval_events / tool_calls / agent_runs
  → controlled generated response
  → structured trace output
```

The Agno adapter is optional and controlled. It does not bypass the existing
trace-first orchestration baseline or expose raw SQL, shell commands, or
unrestricted tool selection.

## Production hardening flow

```text
request / tool / provider failure
  → AppError or normalized error
  → structured HTTP response or controlled MCP envelope
  → trace / eval output remains inspectable
```

The hardening layer adds shared error types, provider normalization, budget
guardrails, and latency measurement helpers without changing the deterministic
execution model.

## Layers

- API routes define HTTP contracts and status handling.
- Schemas validate input and shape responses.
- Services coordinate run, ingestion, retrieval, and orchestration behavior.
- Repositories isolate persistence operations.
- SQLAlchemy models define PostgreSQL records and relationships.
- The RAG layer provides deterministic chunking, mock embeddings, and the
  ChromaDB boundary.
- Local business tools expose approved customer and sales filters without
  accepting raw SQL.
- Observability provides a home for logging and future trace instrumentation.

Retrieval events are written by `POST /runs/{run_id}/retrieve` and by
`POST /agent/run` when a retrieval query is provided. Business tool calls with
a run identifier record their inputs, outputs, completion status, and latency
in `tool_calls`. The orchestration endpoint combines those records into a
single deterministic response while keeping room for future response
generation.
