# Deployment readiness

This repository is a hosted demo foundation and local workbench, not a full
production SaaS.

## Positioning

- Local Docker Compose remains the primary demo path.
- Hosted demo deployment is supported with explicit environment variables.
- User accounts, tenant isolation, billing, and production secrets management
  are intentionally out of scope for this phase.

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
- `ENABLE_DEMO_ENDPOINTS`: gates demo/business/workflow routes when disabled.
- `REQUIRE_DEMO_API_KEY`: requires a demo API key for hosted demo endpoints.
- `DEMO_API_KEY`: shared demo API key value.
- `DEMO_API_KEY_HEADER`: header name used for demo API key checks.
- `RATE_LIMIT_ENABLED`: enables per-process demo rate limiting.
- `RATE_LIMIT_REQUESTS`: number of requests allowed per window.
- `RATE_LIMIT_WINDOW_SECONDS`: rolling rate-limit window size.
- `MAX_REQUEST_BODY_BYTES`: request body ceiling enforced from `Content-Length`.

## Recommended values

For local development:

- `DEPLOYMENT_MODE=local`
- `CORS_ALLOWED_ORIGINS=*`
- `ENABLE_DOCS=true`
- `ENABLE_DEMO_ENDPOINTS=true`
- `REQUIRE_DEMO_API_KEY=false`
- `RATE_LIMIT_ENABLED=false`

For a hosted demo:

- `DEPLOYMENT_MODE=hosted`
- `APP_HOST=0.0.0.0`
- `APP_PORT=8000`
- `CORS_ALLOWED_ORIGINS=https://demo.example.com`
- `ENABLE_DOCS=true`
- `ENABLE_DEMO_ENDPOINTS=true`
- `REQUIRE_DEMO_API_KEY=true`
- `DEMO_API_KEY=use-a-long-random-secret`
- `RATE_LIMIT_ENABLED=true`
- `RATE_LIMIT_REQUESTS=60`
- `RATE_LIMIT_WINDOW_SECONDS=60`
- `MAX_REQUEST_BODY_BYTES=1048576`

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

- Local mode remains open by default.
- Hosted demos should set `REQUIRE_DEMO_API_KEY=true` and use a strong
  `DEMO_API_KEY`.
- Hosted demos should use explicit `CORS_ALLOWED_ORIGINS`.
- `ENABLE_DEMO_ENDPOINTS=true` when serving the demo surface; set it to
  `false` when only health, readiness, and docs should remain exposed.
- Rate limiting is in-memory and single-process only.
- Request size protection uses `Content-Length`; it does not buffer the body.
- No tenant model or payments layer is included.
- Real provider execution remains disabled by default.
- Do not commit production secrets into this repository.

## Not production-ready yet

- Authenticated access control
- Tenant isolation
- Rate limiting and abuse protection
- Production secrets management
- External provider execution by default
- Remote MCP transport hardening
