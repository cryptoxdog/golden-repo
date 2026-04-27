<!--
L9_META:
  l9_schema: 1
  origin: l9-template
  engine: golden-repo
  layer: engine
  tags: [engine, runtime, handlers, domain-logic]
  owner: platform
  status: active
-->

# engine/

The **execution surface** of a node. Pure domain logic and packet handlers — no transport, no routing, no peer discovery.

## Purpose

`engine/` is where a node *does its job*. Every public function here takes a `TransportPacket`, returns a `TransportPacket`, and trusts that the chassis already validated, authenticated, and routed the request.

If the chassis is the **how**, the engine is the **what**.

## What lives here

| Path | Responsibility |
|---|---|
| `engine/main.py` | Node entrypoint — registers handlers, exposes `app` for the chassis to mount. |
| `engine/handlers.py` | `async def handler(packet: TransportPacket) -> TransportPacket` implementations. |
| `engine/core/` | Pure business logic. No I/O frameworks, no FastAPI, no HTTP. |
| `engine/services/` | Outbound calls to durable systems (DB, cache, object store) via injected clients. |
| `engine/models/` | Domain models — pydantic v2, immutable where possible. |
| `engine/security/` | Permission predicates, tenant guards, prohibited-factor checks. |
| `engine/compliance/` | Hooks that emit audit events through the chassis audit sink. |
| `engine/config/`, `settings.py` | Typed settings (pydantic-settings). Read once at boot. |
| `engine/features.py`, `features.json` | Feature-flag surface, read-only at request time. |
| `engine/hashing.py`, `metrics.py`, `logging.py`, `transaction.py` | Local utilities scoped to engine concerns. |

## What does NOT live here

- **No FastAPI imports.** `from fastapi import ...` in `engine/` is a CI failure. Routing belongs to the chassis.
- **No peer URLs.** Engines never call other nodes by URL. If you need another node, dispatch a `TransportPacket` through the chassis client.
- **No transport authority.** Engines do not validate signatures, mint JWTs, or enforce gate policy.
- **No orchestration.** Multi-step workflows live in the orchestrator node, not in engine handlers.
- **No `eval`, `exec`, `pickle.loads`, `yaml.load` (use `yaml.safe_load`).** Banned by `tools/auditors`.

## Contracts that govern this directory

- [`/contracts/transport/transport_packet.contract.yaml`](../contracts/transport/transport_packet.contract.yaml) — the only request/response shape allowed across the engine boundary.
- [`/contracts/runtime/runtime.contract.yaml`](../contracts/runtime/runtime.contract.yaml) — handler invariants and execution semantics.
- [`/contracts/governance/tenant_context.contract.yaml`](../contracts/governance/tenant_context.contract.yaml) — every handler must preserve `tenant_context` on the response packet.
- [`/contracts/governance/prohibited_factors.contract.yaml`](../contracts/governance/prohibited_factors.contract.yaml) — fields the engine must never read for decisioning.

## Handler contract

```python
from chassis.types import TransportPacket

async def handler(packet: TransportPacket) -> TransportPacket:
    # 1. Read inputs only from packet.payload and packet.tenant_context
    # 2. Do work (pure or via injected services)
    # 3. Return a new TransportPacket with the same correlation_id
    ...
```

Handlers must be:
- **Idempotent** for the same `(packet.id, packet.action)` tuple. The chassis may retry.
- **Pure with respect to side effects** — all writes go through `engine/services/`, never directly to a global.
- **Stateless across requests.** No module-level mutable state.
- **Trace-preserving.** Call `packet.with_child_span(...)` when emitting downstream packets.

## Quality gates

- `tools/verify_contracts.py` — every handler must declare its `action` and packet types in `engine/handlers.py` and match a contract entry.
- `tests/contracts/` — round-trip tests asserting handler I/O conforms to `transport_packet.schema.json`.
- `tests/unit/engine/` — pure-logic coverage. Target: ≥ 90% line coverage on `engine/core/`.
- `tools/auditors/` — static checks: no banned imports, no FastAPI in engine, no peer URL strings.

## Conventions

- File naming: `snake_case`. One handler module per `action_namespace`.
- All packet types and actions are lowercase `snake_case`.
- Logging: structured JSON via `engine/logging.py`. Never log raw `payload` — use redacted projections.
- Errors: raise typed exceptions from `chassis/errors.py`; the chassis converts to `TransportPacket` error responses.
