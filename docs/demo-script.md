# Demo script

For a client-friendly overview, see [docs/demo.md](demo.md).

## 1. Start services

```bash
docker compose up --build
```

## 2. Seed business data

```bash
docker compose exec api python scripts/seed_business_data.py
```

## 3. Check service health

```bash
curl http://localhost:8000/health
```

## 4. Parse and ingest the sample policy document

```bash
curl -X POST http://localhost:8000/documents/parse-ingest \
  -F 'file=@samples/commercial_policy.md;type=text/markdown' \
  -F 'metadata={"department":"growth","document_type":"policy"}'
```

## 5. Search indexed chunks

```bash
curl -X POST http://localhost:8000/documents/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "discount approval rules",
    "limit": 5,
    "where": {
      "department": "growth"
    }
  }'
```

## 6. Run deterministic orchestration

```bash
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "business_question": "Analyze online sales performance and find relevant commercial policy context.",
    "retrieval_query": "discount approval rules",
    "sales_region": "east",
    "sales_channel": "online",
    "customer_segment": "enterprise"
  }'
```

## 7. Run controlled response generation

```bash
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "business_question": "Analyze online sales performance and find relevant commercial policy context.",
    "retrieval_query": "discount approval rules",
    "sales_region": "east",
    "sales_channel": "online",
    "customer_segment": "enterprise",
    "generate_response": true
  }'
```

## 8. Run the optional Agno adapter endpoint

```bash
curl -X POST http://localhost:8000/agent/agno/run \
  -H "Content-Type: application/json" \
  -d '{
    "business_question": "Analyze online sales performance and retrieve relevant commercial policy context.",
    "retrieval_query": "discount approval rules",
    "sales_region": "east",
    "sales_channel": "online",
    "customer_segment": "enterprise",
    "generate_response": true,
    "use_agno_agent": true
  }'
```

## 9. Run the local MCP server

Run this in a separate stdio process:

```bash
python -m app.mcp.server
```

Approved MCP tools:

```text
query_customers
summarize_sales
run_traceable_workflow
```

## 10. Run deterministic evals from the script

```bash
python scripts/run_evals.py
```

The built-in eval runner is intended for local and demo use and ingests
built-in eval documents into the local retrieval/vector store.

## 11. Run deterministic evals through the API

```bash
curl -X POST http://localhost:8000/evals/run
```

## 12. Trigger a structured budget error

```bash
curl -X POST http://localhost:8000/documents/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "discount approval rules",
    "limit": 20
  }'
```

This returns a structured error response instead of a stack trace when the
request exceeds the configured retrieval budget.
