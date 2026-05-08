<!--
L9_META:
  l9_schema: 1
  origin: l9-template
  engine: golden-repo
  layer: chassis
  tags: [chassis, transport, gate, dispatch, middleware]
  owner: platform
  status: active
-->

# chassis/

The **transport authority** of a node. Owns the wire, the gate, and the dispatch path. Engines plug into it; they do not replace it.

## Purpose

`chassis/` is the only code in a node allowed to:

1. Bind HTTP/gRPC sockets and parse incoming bytes.
2. Validate `TransportPacket` envelopes against the canonical schema.
3. Run the gate: `validate → route → admit → dispatch → return`.
4. Emit transport-level audit events, metrics, and traces.
5. Mint and verify intra-platform credentials.

Everything past the gate is the engine's job.

## What lives here

| File | Responsibility |
|---|---|
| `chassis_app.py` | Builds the FastAPI app, mounts engine handlers, wires middleware. |
| `engine_boot.py` | Loads engine settings, initialises services, runs startup hooks. |
| `entrypoint.sh`, `Dockerfile.chassis` | Container boot path. |
| `router.py` | Single execute path; resolves `action` → registered handler. |
| `action_registry.py`, `actions.py` | Handler registration surface used by `engine/main.py`. |
| `middleware.py` | Auth, tenant binding, trace propagation, rate limits. |
| `health.py` | `/health/live`, `/health/ready`, `/health/startup` per the healthcheck spec. |
| `audit.py` | Emits `audit.transport.*` events; never logs raw payload bodies. |
| `pii.py` | Redaction helpers used before logs and audits leave the process. |
| `contract_enforcement.py` | Schema validation hooks at request and response boundaries. |
| `errors.py` | Typed exceptions; mapped to `TransportPacket` error responses. |
| `orchestrator.py` | Local helper for nodes that participate in orchestrated flows (client-side; the **orchestrator authority** is a separate node). |
| `auth/` | Credential verification, signing, key rotation. |
| `types.py`, `config.py` | Shared transport types and chassis-only settings. |

## What does NOT live here

- **No business logic.** If it knows what a "user" or "invoice" is, it belongs in `engine/`.
- **No domain handlers.** Handlers are imported from `engine/`; the chassis never defines them.
- **No direct database calls.** The chassis does not own data; it owns transport.
- **No workflow state.** Multi-step coordination lives in the orchestrator node.

## Contracts that govern this directory

- [`/contracts/transport/transport_packet.contract.yaml`](../contracts/transport/transport_packet.contract.yaml) — canonical envelope. The chassis is the only enforcement point.
- [`/contracts/gate/gate.contract.yaml`](../contracts/gate/gate.contract.yaml) — single-execute-path semantics.
- [`/contracts/registration/node_registration.contract.yaml`](../contracts/registration/node_registration.contract.yaml) — startup self-registration with the routing authority.
- [`/contracts/observability/trace_propagation.contract.yaml`](../contracts/observability/trace_propagation.contract.yaml) — every packet enters and exits with a propagated W3C trace context.
- [`/contracts/observability/metrics.contract.yaml`](../contracts/observability/metrics.contract.yaml) — required SLI metric set per node.

## Single execute path

```
inbound bytes
   │
   ▼
[ validate ] ── schema, signature, replay, size
   │
   ▼
[ route    ] ── action → handler in action_registry
   │
   ▼
[ admit    ] ── tenant guard, rate limit, gate policy
   │
   ▼
[ dispatch ] ── handler(packet) → packet'
   │
   ▼
[ return   ] ── audit, metrics, response envelope
```

Any deviation — e.g. a side-channel that bypasses `validate` — is a **gate violation** and a CI failure.

## Quality gates

- `tools/verify_contracts.py` enforces gate contract invariants.
- `tests/contracts/` round-trips packets through the chassis to assert envelope stability.
- `tests/integration/` runs the full execute path against a stubbed engine.
- `tools/auditors/` static rules:
  - No `engine/` import is allowed to bypass the chassis dispatch.
  - No raw `requests`/`httpx` to peer node URLs from inside `engine/`.
  - All logs that touch `payload` must route through `chassis/pii.py`.

## Conventions

- The chassis is **workflow-stateless**. Any per-request memory is held only for the lifetime of that request.
- Packet IDs are immutable on the gate path; the chassis never rewrites `packet.id`.
- The chassis preserves `correlation_id` and `delegation_chain` end-to-end.
- All exits are typed: success returns a `TransportPacket`; failure returns a `TransportPacket` with `error` set, never an HTTP-only error body.
