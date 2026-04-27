<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, architecture]
tags: [L9_TEMPLATE, architecture, overview]
owner: platform
status: active
/L9_META -->

# L9 Architecture Overview

> Every L9 product is a standalone engine that plugs into a universal chassis. The chassis is reusable. The engine is what you build. Nothing else.

## Core Principle

- **One ingress** — `POST /v1/execute` is the only mutation endpoint. `GET /v1/health` is the only other route.
- **One contract** — `TransportPacket` is the canonical execution envelope. Nothing else crosses node boundaries.
- **One topology** — every follow-up packet returns through Gate. Workers never call workers.

## The Three Authorities

| Authority | Role | Workflow State | Owns |
|---|---|---|---|
| **Gate** | Transport authority | None | Validation · routing · admission · dispatch |
| **Orchestrator** | Workflow authority | Durable | Decomposition · sequencing · replay · compensation |
| **Runtime** | Execution authority | Bounded | Capability execution · resource budgets · local caches |

See:
- [`boundaries/GATE.md`](../boundaries/GATE.md)
- [`boundaries/ORCHESTRATOR.md`](../boundaries/ORCHESTRATOR.md)
- [`boundaries/RUNTIME.md`](../boundaries/RUNTIME.md)

## The Universal Path

```
Client ──▶ Gate ──▶ Worker (Runtime or Orchestrator)
                       │
                       ▼
                     Gate ──▶ Worker  (sub-steps)
                       │
                       ▼
                     Gate ──▶ Client
```

Every arrow is a `TransportPacket`. Every transition is observable, idempotent, and replayable.

## What the Chassis Provides (Do Not Rebuild)

- `chassis/auth.py` — SHA-256 API key verification
- `chassis/router.py` — action → handler mapping
- `chassis/tenant.py` — 5-method resolution (header → subdomain → key prefix → envelope → default)
- `chassis/middleware.py` — structured logging, trace propagation, metrics
- `chassis/health.py` — `/v1/health`, `/v1/readiness`, `/metrics`
- `chassis/orchestrator.py` — gate-client transport boundary

## What Each Engine Builds

- Action handlers (`handle_<action>(packet: TransportPacket) -> TransportPacket`)
- Domain spec (`domains/<id>/spec.yaml`)
- Capability implementations under `engine/`
- Tests under `tests/{unit,integration,contracts,compliance}`

Nothing else. No FastAPI imports in `engine/`. No Dockerfile authored per-repo. No custom transport.

## Why This Design

| Problem | L9 Answer |
|---|---|
| Per-route auth bugs | One auth check at the chassis, ever |
| Inconsistent observability | Trace propagation owned by SDK + transport |
| Workflow logic leaking everywhere | Workflow authority confined to Orchestrator |
| Direct service coupling | Workers don't know peer URLs — only Gate does |
| Replay/idempotency drift | One canonical packet, one enforcement point (Gate) |

See [`CONSTELLATION.md`](CONSTELLATION.md) for module-level placement and [`ROUTING.md`](ROUTING.md) for the routing invariant.
