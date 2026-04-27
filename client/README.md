<!--
L9_META:
  l9_schema: 1
  origin: l9-template
  engine: golden-repo
  layer: client
  tags: [client, packet-builder, sdk, transport]
  owner: platform
  status: active
-->

# client/

The canonical SDK for talking to a node. Everything callers need to construct, sign, send, and parse a `TransportPacket` — and nothing else.

## Purpose

Callers (other nodes, scripts, tests, JS frontends) must never hand-roll packets. `client/` ships the one true builder so wire compatibility is a code dependency, not a stylistic choice.

## What lives here

| File | Responsibility |
|---|---|
| `packet_builder.py` | Builds canonical `TransportPacket` objects with required envelope fields, trace context, tenant context. |
| `request_models.py` | Typed request models for common actions; pydantic v2. |
| `response_parser.py` | Parses inbound `TransportPacket` envelopes; raises typed errors on malformed responses. |
| `auth.py` | Signs outbound packets and verifies inbound credentials per the chassis auth contract. |
| `execute_client.py` | Async transport client — `await client.execute(packet)`; retries, timeouts, circuit breaker. |
| `js/` | JavaScript SDK mirror for browser and Node consumers. |

## What does NOT live here

- **No business logic.** The client builds and parses; it never decides.
- **No peer URL hardcoding.** Targets are resolved through the routing authority, not literals.
- **No engine imports.** The SDK must be consumable as a standalone package.

## Contracts that govern this directory

- [`/contracts/transport/transport_packet.contract.yaml`](../contracts/transport/transport_packet.contract.yaml) — every packet built here must conform.
- [`/contracts/transport/transport_packet.schema.json`](../contracts/transport/transport_packet.schema.json) — JSON Schema referenced by `response_parser.py` for validation.
- [`/contracts/observability/trace_propagation.contract.yaml`](../contracts/observability/trace_propagation.contract.yaml) — `packet_builder.py` propagates W3C trace context.
- [`/contracts/governance/delegation_chain.contract.yaml`](../contracts/governance/delegation_chain.contract.yaml) — chained calls extend `delegation_chain` rather than overwriting.

## Quality gates

- `tests/contracts/test_packet_builder.py` round-trips every packet shape.
- `tools/auditors/` flags any module outside `client/` that constructs `TransportPacket` directly.
- The Python SDK and JS SDK are tested against the same canonical fixtures under `tests/review_fixtures/`.
- Any breaking change to the SDK ships an ADR under `docs/adr/` and a migration note in `docs/contracts/BREAKING_CHANGE_POLICY.md`.

## Conventions

- One way to build a packet: `packet_builder.build(action=..., payload=..., parent=...)`.
- Idempotency: every outbound call carries a stable `idempotency_key` derived from inputs.
- Retries are bounded and jittered; default policy is in `execute_client.py`.
- The JS SDK mirrors the Python API surface 1:1; divergence requires an ADR.
