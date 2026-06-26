# Demo script

1. Start the services:

```bash
docker compose up --build
```

2. Seed structured business data:

```bash
docker compose exec api python scripts/seed_business_data.py
```

3. Check service health:

```bash
curl http://localhost:8000/health
```

4. Create a run:

```bash
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"business_question":"Analyze last quarter sales and summarize risks and opportunities."}'
```

5. Ingest a raw-text document:

```bash
curl -X POST http://localhost:8000/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Commercial Policy",
    "source":"commercial_policy.md",
    "content":"Discount approval rules require manager review.",
    "metadata":{"department":"growth"}
  }'
```

6. Parse a Markdown file without ingesting it:

```bash
curl -X POST http://localhost:8000/documents/parse \
  -F 'file=@commercial_policy.md;type=text/markdown' \
  -F 'metadata={"department":"growth"}'
```

7. Parse and ingest a Markdown file:

```bash
curl -X POST http://localhost:8000/documents/parse-ingest \
  -F 'file=@commercial_policy.md;type=text/markdown' \
  -F 'metadata={"department":"growth"}'
```

8. Search indexed chunks after parse-ingest:

```bash
curl -X POST http://localhost:8000/documents/search \
  -H "Content-Type: application/json" \
  -d '{"query":"discount approval rules","limit":5}'
```

9. Copy the returned run identifier and retrieve relevant chunks:

```bash
curl -X POST http://localhost:8000/runs/<run_id>/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query":"What discount approval rules are relevant?","limit":5}'
```

10. Retrieve the saved run:

```bash
curl http://localhost:8000/runs/<run_id>
```

11. Query customers using the run identifier:

```bash
curl -X POST http://localhost:8000/business/customers/query \
  -H "Content-Type: application/json" \
  -d '{"run_id":"<run_id>","segment":"enterprise"}'
```

12. Summarize sales using the run identifier:

```bash
curl -X POST http://localhost:8000/business/sales/summary \
  -H "Content-Type: application/json" \
  -d '{"run_id":"<run_id>","channel":"online"}'
```

The resulting `tool_call_id` identifies the audit record showing which
structured data tool was used, its approved filters, its output, and latency.

13. Run the deterministic orchestration endpoint:

```bash
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "business_question":"Analyze online sales performance and find relevant commercial policy context.",
    "retrieval_query":"discount approval rules",
    "sales_region":"east",
    "sales_channel":"online",
    "customer_segment":"enterprise"
  }'
```

This response returns a completed run, the explicit execution plan, any
retrieval event identifier, any logged tool call identifiers, and a
deterministic trace summary.

14. Run orchestration with controlled response generation:

```bash
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "business_question":"Analyze online sales performance and find relevant commercial policy context.",
    "retrieval_query":"discount approval rules",
    "sales_region":"east",
    "sales_channel":"online",
    "customer_segment":"enterprise",
    "generate_response":true
  }'
```

This response includes the same deterministic trace plus a generated
human-readable response produced from that trace. The default provider is the
local mock implementation.

15. Run the optional Agno adapter endpoint:

```bash
curl -X POST http://localhost:8000/agent/agno/run \
  -H "Content-Type: application/json" \
  -d '{
    "business_question":"Analyze online sales performance and retrieve relevant commercial policy context.",
    "retrieval_query":"discount approval rules",
    "sales_region":"east",
    "sales_channel":"online",
    "customer_segment":"enterprise",
    "generate_response":true,
    "use_agno_agent":true
  }'
```

This keeps the existing trace-first flow as the source of truth while adding a
controlled allowlisted agent adapter layer.

16. Run the local MCP server:

```bash
python -m app.mcp.server
```

Expose the deterministic MCP tools:

```text
query_customers
summarize_sales
run_traceable_workflow
```

The MCP server uses stdio transport and routes each approved tool through the
existing service layer.

17. Run the deterministic eval script:

```bash
python scripts/run_evals.py
```

This prints a concise pass/fail report for the built-in retrieval and
orchestration cases.
It is intended for local and demo use and ingests the built-in eval documents
into the local retrieval/vector store.

18. Run the same eval suite through the API:

```bash
curl -X POST http://localhost:8000/evals/run
```

Review the `total`, `passed`, `failed`, and per-case metric results to confirm
retrieval, response generation, and trace behavior remain stable.

19. Trigger a controlled budget error:

```bash
curl -X POST http://localhost:8000/documents/search \
  -H "Content-Type: application/json" \
  -d '{"query":"discount approval rules","limit":20}'
```

This returns a structured error response instead of a stack trace when the
request exceeds the configured retrieval budget.

20. Trigger a controlled provider configuration error:

```bash
LLM_PROVIDER=openai uvicorn app.main:app --reload
```

Then call:

```bash
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "business_question":"Generate a response from the trace.",
    "generate_response":true
  }'
```

If no provider key is configured, the API returns a controlled structured error
instead of exposing internal exception details.
