<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, runbooks]
tags: [L9_TEMPLATE, runbooks, incident]
owner: platform
status: active
/L9_META -->

# Incident Response

## Severity

| Level | Definition | Response |
|---|---|---|
| **SEV-1** | Customer-facing outage; data loss; security breach | Page on-call · war room · status page within 15 min |
| **SEV-2** | Significant degradation; SLO at risk; major feature broken | Page on-call · incident channel · status page within 60 min |
| **SEV-3** | Minor degradation; no SLO breach; partial feature broken | Ticket · address in business hours |
| **SEV-4** | Cosmetic; no user impact | Backlog |

## First 10 Minutes

1. **Acknowledge** the page within 5 minutes.
2. **Assess severity** — SEV-1/2 require immediate war-room.
3. **Open incident channel** `#inc-<short-name>`.
4. **Post initial status** — what you know, what you don't, ETA for next update.
5. **Assign roles**: Incident Commander · Comms Lead · Tech Lead.

## Triage

### Is Gate routing?

```bash
# Recent 5xx by node
curl -s gate:9090/api/v1/query?query='sum by(node)(rate(gate_routing_failures_total[5m]))'
# Trace context missing
curl -s gate:9090/api/v1/query?query='rate(gate_trace_context_missing_total[5m])'
```

### Is a node draining or unhealthy?

```bash
gh api repos/cryptoxdog/golden-repo/contents/contracts/registration  # check expected nodes
# Then for each node:
curl -f https://<node>/v1/health
curl -f https://<node>/v1/readiness
```

### Is the workflow authority advancing?

```bash
# Workflows started but not completed
curl -s orch:9090/api/v1/query?query='workflows_started_total - workflows_completed_total'
```

### Is admission blocking traffic?

```bash
curl -s gate:9090/api/v1/query?query='sum by(reason)(rate(gate_admission_denials_total[5m]))'
```

## Common Root Causes

| Symptom | Likely Cause | Mitigation |
|---|---|---|
| `UNROUTABLE` errors spike | Node deregistered or supported_actions empty | Re-register node; check `predeploy_check` output |
| `NODE_UNAVAILABLE` errors spike | Health probes failing | Inspect node logs; check resource exhaustion |
| `ADMISSION_DENIED` errors spike | Circuit breaker tripped or load shedding | Check upstream stability; tune thresholds |
| Trace gaps | Detached async work; SDK not propagating | Audit code for LAW-08 violations |
| Memory growth on Runtime | Bounded state guarantees broken | Audit `state_manager.py`; check cache eviction |
| Workflows stuck | Orchestrator checkpoint store unreachable | Check Postgres/Redis; trigger replay from last good checkpoint |
| Tenant isolation violation | Cross-tenant query | SEV-1 — pull node, audit, root-cause, postmortem |

## Communication Cadence

- **SEV-1**: status update every 30 min until resolved.
- **SEV-2**: status update every 60 min until resolved.
- **All sev**: final "resolved" message with timeline + root cause summary.

## Postmortem

Within 5 business days of any SEV-1 or SEV-2:

- Timeline (UTC, minute-resolution)
- Impact (customers, duration, data)
- Root cause (technical + organizational)
- What went well
- What went poorly
- Action items (each owned, dated, tracked in Linear)

Postmortems are blameless and published to the team. ADRs are opened for any structural change identified.
