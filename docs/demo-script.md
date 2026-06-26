# Demo script

For a client-friendly overview, see [docs/demo.md](demo.md).

1. Start the services:

```bash
docker compose up --build
```

2. Seed structured business data:

```bash
docker compose exec api python scripts/seed_business_data.py
```

3. Parse and ingest the sample policy document:

```bash
curl -X POST http://localhost:8000/documents/parse-ingest \
  -F 'file=@samples/commercial_policy.md;type=text/markdown' \
  -F 'metadata={"department":"growth","document_type":"policy"}'
```

4. Search indexed chunks for the approval rule:

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

5. Run the deterministic orchestration endpoint:

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

6. Run orchestration with controlled response generation:

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

7. Run the optional Agno adapter endpoint:

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

8. Run the local MCP server in a separate stdio process:

```bash
python -m app.mcp.server
```

Approved MCP tools:

```text
query_customers
summarize_sales
run_traceable_workflow
```

9. Run the deterministic eval script:

```bash
python scripts/run_evals.py
```

This is intended for local and demo use and ingests built-in eval documents
into the local retrieval/vector store.

10. Run the same eval suite through the API:

```bash
curl -X POST http://localhost:8000/evals/run
```

11. Trigger a controlled budget error:

```bash
curl -X POST http://localhost:8000/documents/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "discount approval rules",
    "limit": 20
  }'
```
