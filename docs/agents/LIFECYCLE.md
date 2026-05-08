<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, agents]
tags: [L9_TEMPLATE, agents, lifecycle]
owner: platform
status: active
/L9_META -->

# Agent Lifecycle

> Boot, registration, drain, shutdown — for every node type.

## Boot Sequence

1. **Typed config load** — `chassis/settings.py` reads env, validates with pydantic-settings. Fail fast on missing required env.
2. **Preflight checks** — `scripts/predeploy_check.py` runs (Neo4j reachability, Redis ping, dependent services).
3. **Runtime store init** — connection pools, model loaders, KGE embeddings, semantic retriever warmup.
4. **Handler registration** — `engine/handlers.py` registers every action handler with the chassis router.
5. **Node registration** — POST to Gate `/v1/admin/register` with the node's declared `supported_actions`.
6. **Health probe activation** — `/v1/health` returns `live=true`.
7. **Readiness flip** — `/v1/readiness` returns `ready=true` only after steps 1–5 succeed. Gate begins routing traffic on this signal.

`/v1/readiness` returning `false` is the only way Gate knows a node is not yet eligible for traffic.

## Steady State

- Handlers run under chassis middleware: auth, tenant resolution, packet inflation, trace propagation, structured logging, metrics.
- Each handler:
  1. Validates the inbound packet against `transport_packet.schema.json`.
  2. Validates the payload against the action's payload schema.
  3. Executes within the resource budget declared in `engine/execution/resource_budget.py`.
  4. Returns a derived `TransportPacket` with `packet_type=response`.
  5. Appends one entry to `hop_trace`.

## Drain (Graceful Shutdown)

1. Drain signal received (SIGTERM, autoscaler, deploy).
2. `/v1/readiness` returns `ready=false` immediately. Gate stops routing new packets to this node.
3. In-flight handlers continue to completion within `drain_timeout_ms` (default 30s).
4. Background work (consolidation, GDS, scheduled jobs) is checkpointed and stopped.
5. Connection pools closed; semantic retriever flushed; episodic store synced.
6. Process exits 0.

## Hard Shutdown

If `drain_timeout_ms` elapses with in-flight handlers, the process exits 1. The orchestrator's replay mechanism resumes any incomplete workflow steps using checkpoint state.

## Failure Modes

| Symptom | Likely Cause | Action |
|---|---|---|
| `/v1/readiness` stuck `false` | Preflight check failing | Inspect startup logs; check dependent service reachability |
| Gate marks node `unhealthy` | Health probe failing | Check `chassis/health.py` adapter status; check resource exhaustion |
| Handlers timeout | Resource budget too low or external dep slow | Tune `resource_budget`; add circuit breaker upstream |
| Memory growth | Leaking caches in runtime state | Check `state_manager.py` bounded-state guarantees |
| Trace gaps | Detached async work without trace context | Audit `LAW-08` violations; ensure SDK propagation |

## Registration Lifecycle Detail

```
boot ─→ POST /v1/admin/register
            │
            ├── 201 Created           → node visible to Gate, but not active
            ├── 200 OK (overwrite)    → existing entry replaced
            └── 409 Conflict          → registration rejected (overwrite=false)

health ─→ GET /v1/health
            │
            └── adapter healthy → Gate marks node `active`

shutdown ─→ readiness=false
            │
            └── Gate marks node `draining`, then `inactive`
```

Gate is authoritative for activation and health state. Registration is a declaration, not a guarantee.
