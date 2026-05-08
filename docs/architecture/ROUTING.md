<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, architecture]
tags: [L9_TEMPLATE, routing]
owner: platform
status: active
/L9_META -->

# Routing — The Single Invariant

> **All node-originated follow-up traffic returns to Gate.**
> Workers never call workers. Orchestrator never calls Runtime directly.

Source contract: [`contracts/routing/routing_policy.contract.yaml`](../../contracts/routing/routing_policy.contract.yaml)

## Allowed Patterns

- `client → gate`
- `node → gate`
- `gate → worker`

## Forbidden Patterns

- `node_a → node_b`
- `orchestrator → worker (direct)`
- `worker → worker`

## Why

- **Uniform observability** — every hop crosses Gate, so every hop is traced, metered, and logged identically.
- **Uniform admission** — circuit breakers, rate limits, load shedding apply once and apply consistently.
- **Decoupled deployment** — workers don't know peer URLs; nodes can be added, removed, or relocated without touching workers.
- **Replay correctness** — a single transport authority is the only place where idempotency and replay protection need to be enforced.

## Selection Algorithm

1. Lookup `header.action` in NodeRegistry.
2. Filter by `health == active`.
3. Filter by priority class eligibility.
4. Apply admission controller (CB → rate limit → load shed).
5. Dispatch via configured transport adapter.

## Failure Modes

| Condition | Failure Packet `reason` |
|---|---|
| Action not registered | `UNROUTABLE` |
| No healthy node | `NODE_UNAVAILABLE` |
| Admission denied | `ADMISSION_DENIED` |

## Provenance Rules

| Originator | `provenance.origin_kind` | `address.source_node` | `address.destination_node` |
|---|---|---|---|
| External client | `client` | client identifier | `gate` |
| Node follow-up | `node` | local node | `gate` |
| Gate dispatch | `gate` | `gate` | resolved worker |

A packet whose origin is `node` but whose destination is anything other than `gate` is a contract violation and is rejected at the gate-client boundary.

## Enforcement Points

- `sdk_gate_client` — packets are constructed correctly or not at all.
- `gate_ingress_validator` — rejects malformed provenance.
- `gate_routing_policy_validator` — rejects forbidden patterns.
- `tests/contracts/test_no_direct_node_calls.py` — static scan of imports/calls.
