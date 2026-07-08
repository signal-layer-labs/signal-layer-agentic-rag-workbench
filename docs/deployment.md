# Deployment readiness

This repository is a hosted demo foundation and local workbench, not a full
production SaaS.

## Positioning

- Local Docker Compose remains the primary demo path.
- Hosted demo deployment is supported with explicit environment variables.
- Authentication, tenant isolation, billing, rate limiting, and production
  secrets management are intentionally out of scope for this phase.

## Required environment variables

- `DATABASE_URL`: PostgreSQL connection string.
- `CHROMA_HOST`: ChromaDB host.
- `CHROMA_PORT`: ChromaDB port.
- `CHROMA_COLLECTION`: ChromaDB collection name.

## Deployment-oriented environment variables

- `APP_HOST`: bind host for the API process.
- `APP_PORT`: bind port for the API process.
- `DEPLOYMENT_MODE`: `local` or `hosted`.
- `CORS_ALLOWED_ORIGINS`: `*` locally, explicit origins for hosted demos.
- `ENABLE_DOCS`: enables Swagger/OpenAPI docs.
- `ENABLE_DEMO_ENDPOINTS`: controls demo-oriented endpoints.

## Recommended values

For local development:

- `DEPLOYMENT_MODE=local`
- `CORS_ALLOWED_ORIGINS=*`
- `ENABLE_DOCS=true`
- `ENABLE_DEMO_ENDPOINTS=true`

For a hosted demo:

- `DEPLOYMENT_MODE=hosted`
- `APP_HOST=0.0.0.0`
- `APP_PORT=8000`
- `CORS_ALLOWED_ORIGINS=https://demo.example.com`
- `ENABLE_DOCS=true`
- `ENABLE_DEMO_ENDPOINTS=true` only if the demo surface should remain visible

## Local Docker Compose

```bash
docker compose up --build
```

The compose file forwards the deployment-friendly environment defaults used by
the app.

## Health and readiness

- `GET /health` is the lightweight hosted-demo healthcheck.
- `GET /ready` verifies the API can reach PostgreSQL with a simple `SELECT 1`.

## Smoke validation

Run the deterministic smoke script against a live deployment:

```bash
BASE_URL=http://localhost:8000 python scripts/deployment_smoke.py
```

If docs are disabled, set:

```bash
DOCS_ENABLED=false BASE_URL=http://localhost:8000 python scripts/deployment_smoke.py
```

## Hosted demo caveats

- No auth or API key protection is included in this phase.
- No rate limiting, tenant model, or payments layer is included.
- Real provider execution remains disabled by default.
- Do not commit production secrets into this repository.

## Not production-ready yet

- Authenticated access control
- Tenant isolation
- Rate limiting and abuse protection
- Production secrets management
- External provider execution by default
- Remote MCP transport hardening
