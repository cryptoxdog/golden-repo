<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, observability]
tags: [L9_TEMPLATE, observability, logging]
owner: platform
status: active
/L9_META -->

# Logging

## Standard

structlog JSON, single line per event, UTC ISO 8601 timestamps.

## Required Fields (every log line)

- `ts` — ISO 8601 UTC
- `level` — `debug | info | warning | error | critical`
- `logger` — module name (`__name__`)
- `event` — short, lowercase, snake_case event identifier
- `trace_id` — propagated from packet header
- `tenant_id` — `tenant.org_id` (never user_id)
- `action` — action being processed
- `node_name` — current node identity

## Engine Usage

```python
import structlog

log = structlog.get_logger(__name__)

log.info(
    "match_started",
    domain_id=domain.id,
    candidate_count=len(candidates),
)
```

Engines call `structlog.get_logger(__name__)` and nothing else. Configuration is the chassis's job.

## Forbidden

- `structlog.configure()` in `engine/`
- `logging.basicConfig()` in `engine/`
- Logging PII values (the chassis filters declared PII paths; never bypass)
- Logging secrets (rotate immediately if a secret is logged)
- Logging full packet payloads at `info` or higher (use `debug` and only in dev)

## Levels

| Level | Use For |
|---|---|
| `debug` | Verbose state, payload bodies (dev only) |
| `info` | Normal lifecycle events, expected outcomes |
| `warning` | Degraded behavior, retries, fallbacks |
| `error` | Handler failures, validation rejections |
| `critical` | Process-level failures, integrity violations |

## Redaction

Configured by `chassis/middleware.py` based on declared PII fields in the domain spec (`compliance.pii.fields`). Modes: `hash`, `encrypt`, `redact`, `tokenize`. The redactor runs before structlog serialization.

## Backends

- **Local dev** — stdout
- **Production** — Loki via Alloy collector (`observability/QW1_alloy_config.alloy`)
- **Long-term archive** — S3 (lifecycle policy: 30 days hot, 1 year cold)

## Forbidden Anti-Patterns

| Pattern | Why |
|---|---|
| `print(...)` in `engine/` | Bypasses structlog and trace context |
| `logging.getLogger()` in `engine/` | Bypasses structlog config |
| Multi-line log messages | Breaks JSON parsing in Loki/ELK |
| F-strings inside log calls | Use kwargs so structlog can structure them |
| Logging in tight loops | Use sampling or aggregate first |
