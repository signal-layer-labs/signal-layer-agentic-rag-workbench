# Architecture

The intended trace flow is:

```text
business question
  → agent run
  → tools
  → retrieval
  → response
  → trace
```

The API currently implements the first boundary: a validated business question
creates a durable agent run. The run identifier will connect future tool calls,
retrieval events, and final responses into one auditable trace.

## Layers

- API routes define HTTP contracts and status handling.
- Schemas validate input and shape responses.
- Services coordinate run behavior.
- Repositories isolate persistence operations.
- SQLAlchemy models define PostgreSQL records and relationships.
- Observability provides a home for logging and future trace instrumentation.

The `tool_calls` and `retrieval_events` tables are present as trace foundations,
but no tool execution or retrieval pipeline runs in this phase.
