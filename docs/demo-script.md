# Demo script

Start the services:

```bash
docker compose up --build
```

Seed structured business data:

```bash
docker compose exec api python scripts/seed_business_data.py
```

1. Check service health:

```bash
curl http://localhost:8000/health
```

2. Create a run:

```bash
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"business_question":"Analyze last quarter sales and summarize risks and opportunities."}'
```

3. Ingest a raw-text document:

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

4. Copy the returned run identifier and retrieve relevant chunks:

```bash
curl -X POST http://localhost:8000/runs/<run_id>/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query":"What discount approval rules are relevant?","limit":5}'
```

5. Retrieve the saved run:

```bash
curl http://localhost:8000/runs/<run_id>
```

6. Query customers using the run identifier:

```bash
curl -X POST http://localhost:8000/business/customers/query \
  -H "Content-Type: application/json" \
  -d '{"run_id":"<run_id>","segment":"enterprise"}'
```

7. Summarize sales using the run identifier:

```bash
curl -X POST http://localhost:8000/business/sales/summary \
  -H "Content-Type: application/json" \
  -d '{"run_id":"<run_id>","channel":"online"}'
```

The resulting `tool_call_id` identifies the audit record showing which
structured data tool was used, its approved filters, its output, and latency.
