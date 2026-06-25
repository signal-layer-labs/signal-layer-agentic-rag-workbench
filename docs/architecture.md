# Architecture

The intended trace flow is:

```text
business question
  → agent run
  → retrieval query
  → ChromaDB
  → retrieved chunks
  → retrieval event
  → future agent response
```

The API creates durable agent runs and indexes raw document text as chunks in
ChromaDB. A run-linked retrieval searches those chunks and records its query
and results in PostgreSQL under the run identifier.

## Layers

- API routes define HTTP contracts and status handling.
- Schemas validate input and shape responses.
- Services coordinate run, ingestion, and retrieval behavior.
- Repositories isolate persistence operations.
- SQLAlchemy models define PostgreSQL records and relationships.
- The RAG layer provides deterministic chunking, mock embeddings, and the
  ChromaDB boundary.
- Observability provides a home for logging and future trace instrumentation.

The `tool_calls` table remains a future trace boundary. Retrieval events are
now written by `POST /runs/{run_id}/retrieve`.
