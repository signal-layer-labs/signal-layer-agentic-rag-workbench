# Signal Layer Agentic RAG Workbench

A traceable agentic RAG workbench for business data, documents, tools, and
auditable AI responses.

The current version is the backend foundation for traceable agent runs. It
records a business question as a run and provides database structures for
future tool and retrieval traces.

## Stack

- Python 3.12+
- FastAPI and Pydantic
- PostgreSQL 16
- SQLAlchemy 2
- Docker and Docker Compose
- pytest, ruff, and mypy

## Architecture

HTTP routes validate requests and delegate run operations to the service
layer. The service layer applies run behavior and uses repositories for
persistence. SQLAlchemy models represent agent runs, tool calls, and retrieval
events in PostgreSQL.

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

This starts PostgreSQL and the API at `http://localhost:8000`. Tables are
created when the API starts. To add one sample run:

```bash
docker compose exec api python scripts/seed_postgres.py
```

## Quality checks

```bash
ruff check .
pytest
mypy app
```

## Current scope

This phase provides health checks, run creation and lookup, PostgreSQL models,
repository boundaries, configuration, logging foundations, and local
containers.

Future phases will add document ingestion, vector retrieval, agent tools, an
MCP server, an LLM provider abstraction, document parsing, and cost and latency
tracking. These capabilities are intentionally outside the current scope.
