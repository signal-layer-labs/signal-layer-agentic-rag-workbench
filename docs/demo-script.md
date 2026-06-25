# Demo script

Start the services:

```bash
docker compose up --build
```

Check service health:

```bash
curl http://localhost:8000/health
```

Create a run:

```bash
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"business_question":"Analyze last quarter sales and summarize risks and opportunities."}'
```

Copy the returned `run_id`, then retrieve the saved run:

```bash
curl http://localhost:8000/runs/<run_id>
```
