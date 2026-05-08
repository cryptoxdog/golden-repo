<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, runbooks]
tags: [L9_TEMPLATE, runbooks, deploy]
owner: platform
status: active
/L9_META -->

# Deploy Runbook

> The standard deploy path is **GitHub Actions → 3-LLM stacked review → merge → ArgoCD auto-deploy → Telegram notification**. This runbook covers the manual fallback and the production checklist.

## Pre-Deploy Checklist

- [ ] All required CI checks green (lint · type-check · contracts · unit · integration · compliance · LLM review)
- [ ] Contract version pinned in `contracts/_schemas/` and matches handler signatures
- [ ] No new top-level directories without ADR
- [ ] `CHANGELOG.md` updated
- [ ] If breaking contract change: ADR merged and dual-read window planned
- [ ] `scripts/predeploy_check.py` passes against target env

## Standard Deploy (ArgoCD)

1. PR merges to `main`.
2. GitHub Actions builds and pushes container to registry, signed with cosign.
3. ArgoCD detects new image tag, syncs to staging.
4. Smoke tests run (`tools/infra/precommit_smoke.sh`).
5. Manual approval (or auto for non-prod).
6. ArgoCD syncs to production canary (10%).
7. SLO monitor watches for 15 minutes.
8. Auto-promote to 100% if SLOs hold; auto-rollback if they do not.
9. Telegram notification on success or failure.

## Manual Deploy (fallback)

```bash
# 1. Build
tools/infra/docker_validate.sh
docker build -f infrastructure/docker/Dockerfile -t <registry>/<service>:<sha> .
docker push <registry>/<service>:<sha>

# 2. Predeploy check
scripts/predeploy_check.py --env=production

# 3. Deploy
deploy/scripts/deploy_remote.sh --env=production --tag=<sha>

# 4. Verify
curl -f https://<host>/v1/health
curl -f https://<host>/v1/readiness
```

## Rollback

```bash
deploy/scripts/rollback_remote.sh --env=production --to=<previous_sha>
```

Rollback restores the previous container image. Persistent state migrations should always be **forward-compatible** — schema changes use `expand → migrate → contract` so a rollback never corrupts data.

## Database Migrations

- Forward-compatible: add column nullable, backfill, drop default in next release.
- Never: rename a column in one release; never drop a column the previous release reads.
- Migration tool: `database/init_db.py` + Alembic-style versioned scripts.

## Secrets

- Source: AWS Secrets Manager, RAM-only via `secure-env.sh`.
- **Never** commit secrets. **Never** log secrets. GitGuardian enforces both.
- Rotate quarterly or on incident.

## Post-Deploy Verification

| Check | How |
|---|---|
| Health | `GET /v1/health` returns 200 |
| Readiness | `GET /v1/readiness` returns 200 with `ready=true` |
| Registration | Node visible in Gate `node_registry` and `active` |
| Trace propagation | Sample request shows full span chain in Grafana Tempo / Jaeger |
| Metrics | `/metrics` scraped; SLO dashboards updated |
| Smoke action | Send canonical `TransportPacket` for a known action; assert response shape |

## Telegram Notification Format

- Success: `✓ <service>@<sha> → <env> · ${duration}s`
- Failure: `✗ <service>@<sha> → <env> · failed: <stage> · <link to logs>`

(Emojis only because the Telegram channel uses them — never in source artifacts.)
