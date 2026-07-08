# Hosted Demo Runbook

## Purpose

This runbook explains how to deploy and validate the hosted demo safely. It is
for repeatable demo operations, not for production SaaS operation.

## Required Environment

Set the following values for a hosted demo deployment:

- `DEPLOYMENT_MODE=hosted`
- `APP_HOST=0.0.0.0`
- `APP_PORT=8000`
- `DATABASE_URL=<hosted-postgres-url>`
- `CHROMA_HOST=<hosted-chroma-host>`
- `CHROMA_PORT=<hosted-chroma-port>`
- `CHROMA_COLLECTION=business_documents`
- `CORS_ALLOWED_ORIGINS=<hosted-demo-origin>`
- `ENABLE_DOCS=true` or `false`
- `ENABLE_DEMO_ENDPOINTS=true`
- `REQUIRE_DEMO_API_KEY=true`
- `DEMO_API_KEY=<long-random-secret>`
- `DEMO_API_KEY_HEADER=X-Demo-API-Key`
- `RATE_LIMIT_ENABLED=true`
- `RATE_LIMIT_REQUESTS=60`
- `RATE_LIMIT_WINDOW_SECONDS=60`
- `MAX_REQUEST_BODY_BYTES=1048576`
- `LOG_LEVEL=INFO`
- `EMBEDDING_PROVIDER=mock`

## Hosted Docs Guidance

When `ENABLE_DOCS=true`, `/docs`, `/redoc`, and `/openapi.json` are publicly
available.

For a private or shared external demo, prefer `ENABLE_DOCS=false` unless docs
are intentionally needed during the demo session.

## Demo API Key Usage

When `REQUIRE_DEMO_API_KEY=true`, demo endpoints require the configured API key
in the `X-Demo-API-Key` header by default.

Use the placeholder `<DEMO_API_KEY>` in operator examples and scripts when
referring to the configured secret.

## Final Smoke Validation

Run the following checks against the hosted deployment.

Health:

```bash
curl -i <HOSTED_BASE_URL>/health
```

Readiness:

```bash
curl -i <HOSTED_BASE_URL>/ready
```

Unauthorized demo request should return `401`:

```bash
curl -i -X POST <HOSTED_BASE_URL>/agent/run \
  -H "Content-Type: application/json" \
  -d '{"business_question":"Analyze sales."}'
```

Authorized demo request should return `200` or a valid app-level response:

```bash
curl -i -X POST <HOSTED_BASE_URL>/agent/run \
  -H "Content-Type: application/json" \
  -H "X-Demo-API-Key: <DEMO_API_KEY>" \
  -d '{"business_question":"Analyze sales."}'
```

Payload too large check:

```bash
curl -i -X POST <HOSTED_BASE_URL>/agent/run \
  -H "Content-Type: application/json" \
  -H "X-Demo-API-Key: <DEMO_API_KEY>" \
  -H "Content-Length: 1048577" \
  -d '{"business_question":"Analyze sales."}'
```

## Smoke Script Usage

Without API key:

```bash
BASE_URL=<HOSTED_BASE_URL> python scripts/deployment_smoke.py
```

With API key:

```bash
BASE_URL=<HOSTED_BASE_URL> \
DEMO_API_KEY=<DEMO_API_KEY> \
DEMO_API_KEY_HEADER=X-Demo-API-Key \
python scripts/deployment_smoke.py
```

Docs disabled:

```bash
DOCS_ENABLED=false \
BASE_URL=<HOSTED_BASE_URL> \
DEMO_API_KEY=<DEMO_API_KEY> \
python scripts/deployment_smoke.py
```

## Post-Deploy Verification

- Hosted URL loads.
- `/health` returns `200`.
- `/ready` returns `200`.
- Demo endpoint without API key returns `401`.
- Demo endpoint with API key succeeds.
- CORS origin is not wildcard for hosted demo.
- Rate limiting is enabled.
- Request size limit is configured.
- Logs show no startup deployment warnings that block the demo.
- No real provider execution is enabled unless intentionally configured.
- No secrets are committed to the repository.

## Rollback Notes

- Revert to the previous deployment.
- Disable the demo surface with `ENABLE_DEMO_ENDPOINTS=false`.
- Disable docs with `ENABLE_DOCS=false`.
- Rotate `DEMO_API_KEY` if exposed.
- Check logs after rollback.
- Re-run smoke checks.

## Limitations

- Not production SaaS.
- No user auth.
- No tenant isolation.
- No billing.
- Rate limiting is in-memory and single-process.
- Request size guard relies on `Content-Length`.
- `X-Forwarded-For` trust depends on hosting/proxy configuration.
- Real provider execution should remain disabled by default.
