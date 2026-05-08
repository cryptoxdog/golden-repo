<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs]
tags: [L9_TEMPLATE, docs, index]
owner: platform
status: active
/L9_META -->

# Documentation Index

> Docs explain. Contracts enforce. When the two disagree, **contracts win** and docs get fixed.

## Reading Order

| # | Doc | When to Read |
|---|---|---|
| 1 | [`architecture/OVERVIEW.md`](architecture/OVERVIEW.md) | First day on the platform |
| 2 | [`architecture/CONSTELLATION.md`](architecture/CONSTELLATION.md) | Before designing any new node |
| 3 | [`architecture/ROUTING.md`](architecture/ROUTING.md) | Before touching any transport code |
| 4 | [`boundaries/GATE.md`](boundaries/GATE.md), [`ORCHESTRATOR.md`](boundaries/ORCHESTRATOR.md), [`RUNTIME.md`](boundaries/RUNTIME.md) | Before contributing to any of the three |
| 5 | [`contracts/TRANSPORT_PACKET.md`](contracts/TRANSPORT_PACKET.md) | Before writing any code that constructs or consumes a packet |
| 6 | [`agents/CODING_GUIDE.md`](agents/CODING_GUIDE.md) | Every PR — this is the law for AI-authored code |
| 7 | [`adr/`](adr/) | When proposing a non-trivial architectural change |
| 8 | [`runbooks/`](runbooks/) | On-call, deploys, incidents |
| 9 | [`security/`](security/), [`observability/`](observability/) | When the system fails or behaves oddly |

## Layout

```
docs/
├── README.md                          ← this index
├── architecture/
│   ├── OVERVIEW.md                    ← chassis vs engine, single ingress
│   ├── CONSTELLATION.md               ← gate · orchestrator · runtime
│   └── ROUTING.md                     ← node→gate→node invariant
├── boundaries/
│   ├── GATE.md                        ← what gate may and may not do
│   ├── ORCHESTRATOR.md                ← workflow authority
│   ├── RUNTIME.md                     ← execution-only node
│   └── WHAT_LIVES_WHERE.md            ← canonical placement table
├── contracts/                         ← human-readable companions to /contracts/
│   ├── TRANSPORT_PACKET.md
│   ├── ROUTING_POLICY.md
│   ├── NODE_REGISTRATION.md
│   ├── DELEGATION_PROTOCOL.md
│   ├── PACKET_TYPE_REGISTRY.md
│   └── BREAKING_CHANGE_POLICY.md
├── agents/
│   ├── CODING_GUIDE.md                ← rules every AI-authored PR follows
│   ├── ORCHESTRATION_PATTERNS.md      ← recipes for common workflow shapes
│   └── LIFECYCLE.md                   ← agent boot, registration, drain
├── adr/
│   ├── README.md                      ← ADR template + process
│   ├── 0001-transport-packet-canonical.md
│   └── 0002-gate-workflow-stateless.md
├── runbooks/
│   ├── DEPLOY.md                      ← Hetzner + Docker + Argo
│   ├── INCIDENT.md                    ← severity, triage, war-room
│   └── ON_CALL.md                     ← schedule, paging, escalation
├── security/
│   ├── THREAT_MODEL.md
│   ├── SECRETS.md
│   └── BOUNDARIES.md                  ← enforcement of L9 boundaries
└── observability/
    ├── TRACING.md                     ← W3C trace context, OTel propagation
    ├── METRICS.md                     ← Prometheus, SLOs
    └── LOGGING.md                     ← structlog JSON, redaction
```

## Companion `/contracts/`

Every doc here has a counterpart contract under [`/contracts/`](../contracts/). The contract is the source of truth; the doc is the explanation.
