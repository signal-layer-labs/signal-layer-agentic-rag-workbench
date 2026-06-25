# Signal Layer Agentic RAG Workbench

A traceable agentic RAG workbench for business data, documents, tools, and
auditable AI responses.

The current version provides traceable agent runs, raw-text document retrieval,
and deterministic tools for querying structured business data. PostgreSQL
stores business records and audit events while ChromaDB stores document chunks.

## Stack

- Python 3.12+
- FastAPI and Pydantic
- PostgreSQL 16
- ChromaDB
- SQLAlchemy 2
- Docker and Docker Compose
- pytest, ruff, and mypy

## Architecture

HTTP routes validate requests and delegate run and retrieval operations to
service layers. PostgreSQL stores run traces while ChromaDB stores document
chunks, metadata, and vectors.

See [docs/architecture.md](docs/architecture.md) for the intended request and
trace flow.

## Local setup

Create a virtual environment and install the project:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

When running the API outside Docker, change the database host in `.env` from
`postgres` to `localhost`, then start the API:

```bash
uvicorn app.main:app --reload
```

OpenAPI documentation is available at `http://localhost:8000/docs`.

## Environment variables

- `DATABASE_URL`: SQLAlchemy connection URL for PostgreSQL.
- `APP_ENV`: runtime environment name.
- `LOG_LEVEL`: application logging level.

## Docker Compose

```bash
docker compose up --build
```

This starts PostgreSQL, ChromaDB, and the API at `http://localhost:8000`.
Tables and the Chroma collection are created on first use. To add one sample
run:

```bash
docker compose exec api python scripts/seed_postgres.py
```

## Document retrieval

Ingest raw text:

```bash
curl -X POST http://localhost:8000/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Commercial Policy",
    "source": "commercial_policy.md",
    "content": "Discount approval rules require manager review.",
    "metadata": {"department": "growth", "document_type": "policy"}
  }'
```

Search indexed chunks:

```bash
curl -X POST http://localhost:8000/documents/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "discount approval rules",
    "limit": 5,
    "where": {"department": "growth"}
  }'
```

Link retrieval to an existing run:

```bash
curl -X POST http://localhost:8000/runs/<run_id>/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query":"What discount approval rules are relevant?","limit":5}'
```

## Business data tools

Seed the local fake customer, product, and sales dataset:

```bash
docker compose exec api python scripts/seed_business_data.py
```

The script replaces only the seeded business tables. It does not clear agent
runs, tool calls, or retrieval events.

Query customers:

```bash
curl -X POST http://localhost:8000/business/customers/query \
  -H "Content-Type: application/json" \
  -d '{"run_id":"<run_id>","segment":"enterprise","region":"east"}'
```

Query sales:

```bash
curl -X POST http://localhost:8000/business/sales/query \
  -H "Content-Type: application/json" \
  -d '{"run_id":"<run_id>","channel":"online","limit":20}'
```

Summarize sales:

```bash
curl -X POST http://localhost:8000/business/sales/summary \
  -H "Content-Type: application/json" \
  -d '{"run_id":"<run_id>","region":"east"}'
```

These endpoints expose deterministic local tools. They do not select or invoke
tools autonomously. When `run_id` is supplied, the input, output, status, and
latency are recorded in `tool_calls`.

## Quality checks

```bash
ruff check .
pytest
mypy app
```

## Current scope

This phase accepts raw text only, uses deterministic mock embeddings, and
provides allowlisted structured queries. It does not parse files, generate
natural-language answers, or orchestrate agents.

Future phases will add real embedding providers, document parsing, agent tools,
an MCP server, an LLM provider abstraction, and cost and latency tracking.
