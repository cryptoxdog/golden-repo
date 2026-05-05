<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, security]
tags: [L9_TEMPLATE, security, secrets]
owner: platform
status: active
/L9_META -->

# Secrets Management

## Sources

| Source | Use |
|---|---|
| AWS Secrets Manager | Production secrets; canonical source of truth |
| Doppler / Vault (alternative) | Dev/staging environments |
| `.env.local` (developer machine only) | Local dev — never committed |

## Loading

- Production: `secure-env.sh` fetches secrets from AWS Secrets Manager into RAM-only env vars at process start. Never written to disk.
- Local: `.env.local` (gitignored) loaded by `chassis/settings.py`.
- All env vars consumed via `pydantic-settings`. Engines never read os.environ directly.

## Naming Convention

- All L9 platform env vars are prefixed `L9_`.
- Engine-specific vars use `L9_<ENGINE>_` (e.g., `L9_GATE_NEO4J_URI`, `L9_RUNTIME_OPENAI_API_KEY`).
- Secret references in IaC use the AWS Secrets Manager key name only — never the value.

## Rules

- **Never** commit secrets. GitGuardian enforces this on every push.
- **Never** log secrets. structlog redaction filters are configured by the chassis.
- **Never** include secrets in error messages, traces, or telemetry.
- **Always** use SHA-256 with constant-time comparison for API key verification (`hmac.compare_digest`).
- **Always** rotate secrets quarterly and on incident.

## Rotation Procedure

1. Generate new secret in AWS Secrets Manager (versioned).
2. Roll out to all consumers via deploy.
3. Verify production traffic uses new secret (telemetry).
4. Mark old secret as `AWSPENDING → AWSPREVIOUS`.
5. After 24h grace, delete `AWSPREVIOUS`.

## Compromise Procedure

1. Rotate the compromised secret immediately.
2. Audit logs for the lifetime of the secret to identify potential abuse.
3. Open SEV-1 incident if customer data may have been accessed.
4. Postmortem with root cause and structural fix (often: improved scope, shorter TTL, separate keys per consumer).

## Forbidden

- Hardcoded secrets in source.
- Secrets in `git` history (rotate immediately if found; the secret IS compromised).
- Sharing secrets via chat, email, or screenshots.
- Single shared secret across multiple environments.
