<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, runbooks]
tags: [L9_TEMPLATE, runbooks, on_call]
owner: platform
status: active
/L9_META -->

# On-Call

## Schedule

- **Primary** rotates weekly. Schedule managed in the team paging tool.
- **Secondary** is the previous week's primary, on call only if primary cannot acknowledge.
- **Manager escalation** for SEV-1 not acknowledged within 15 minutes.

## What You Are Responsible For

- Acknowledging pages within 5 minutes.
- Triaging incidents per [`INCIDENT.md`](INCIDENT.md).
- Keeping the incident channel updated.
- Filing a postmortem within 5 business days for any SEV-1 / SEV-2.
- **Not** fixing every problem yourself — pull in domain experts when needed.

## Pre-Shift Checklist

- [ ] Paging tool installed and tested
- [ ] VPN access verified
- [ ] kubectl / docker / gh / terraform CLIs working
- [ ] Read the previous week's incident summaries
- [ ] Check for any deferred work that may surface during the shift
- [ ] Confirm contact for Hetzner support (current hosting provider)

## Tools You Need

| Tool | Use |
|---|---|
| Grafana | SLO dashboards, recent error rates |
| Tempo / Jaeger | Trace inspection |
| Loki / ELK | Log search |
| Prometheus | Ad-hoc queries |
| `gh` CLI | Read recent deploys, file issues |
| `kubectl` / `docker compose` | Inspect pods/containers |
| Telegram | Deploy notifications |

## Pages You Will Receive

| Alert | Likely Action |
|---|---|
| Gate `dispatch_p99 > 100ms` | Check downstream node health |
| Gate `routing_failures_total` rate spike | Triage by `reason` label |
| Workflow stalled (`workflows_started - workflows_completed > N`) | Inspect Orchestrator logs; trigger replay |
| Runtime `handler_failures_total` spike | Check resource budget; check upstream dep |
| `transport_packet_schema_validation_failures` spike | Recent deploy of mismatched contract version — rollback |
| Tenant isolation alert | SEV-1, immediate response |

## Handoff

End-of-shift handoff to the next primary includes:

- Open incidents (status, owner, next action)
- Recent deploys still in canary
- Known noisy alerts and their workarounds
- Pending postmortem action items
