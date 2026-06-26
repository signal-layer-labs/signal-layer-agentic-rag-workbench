# Architecture

The intended trace flow is:

```text
business question
  → create run
  → optional document retrieval
  → business tools
  → retrieval_events + tool_calls
  → deterministic trace summary
  → future agent response
```

The API creates durable agent runs and indexes raw document text as chunks in
ChromaDB. A run-linked retrieval searches those chunks and records its query
and results in PostgreSQL under the run identifier.

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

Retrieval events are written by `POST /runs/{run_id}/retrieve` and
`POST /agent/run` when a retrieval query is provided. Business tool calls with
a run identifier record their inputs, outputs, completion status, and latency
in `tool_calls`. The orchestration endpoint combines those trace records into a
single deterministic response that leaves room for future response generation.
