<!--
L9_META:
  l9_schema: 1
  origin: l9-template
  engine: golden-repo
  layer: domains
  tags: [domains, bounded-context, capabilities]
  owner: platform
  status: active
-->

# domains/

One bounded context per subdirectory. Each domain declares its **packet types**, **actions**, **handlers**, and **schemas** — and nothing else.

## Purpose

Domains are how a node grows without becoming a monolith. A domain is a **slice of the engine** focused on one capability, with its own packet types, fixtures, and tests. Multiple domains compose into a node; multiple nodes compose into a constellation.

## What lives in each domain

A domain directory must contain:

```
domains/<domain_name>/
├── README.md                  # Purpose, owners, packet types exposed
├── actions.py                 # Action ids registered with the chassis
├── handlers.py                # Handler functions; one per action
├── models.py                  # Pydantic v2 domain models
├── schemas/                   # JSON schemas for inbound/outbound payloads
└── tests/                     # Domain-scoped unit and contract tests
```

`domains/example_domain/` is the canonical scaffold — copy it, do not branch from it.

## What does NOT live here

- **No transport.** Domains never import FastAPI, never bind sockets.
- **No cross-domain reach.** A domain talks to another domain only by emitting a `TransportPacket` through the chassis client. No direct python imports across domain boundaries.
- **No global state.** Domains are pure functions over packets and injected services.
- **No infra config.** Database URLs, queue names, secrets — all come from the chassis settings layer.

## Contracts that govern this directory

- [`/contracts/transport/transport_packet.contract.yaml`](../contracts/transport/transport_packet.contract.yaml) — every action's I/O is a TransportPacket.
- [`/contracts/runtime/runtime.contract.yaml`](../contracts/runtime/runtime.contract.yaml) — handler invariants apply per domain.
- [`/contracts/governance/tenant_context.contract.yaml`](../contracts/governance/tenant_context.contract.yaml) — domains must not strip tenant context from responses.
- Each domain SHOULD ship its own contract YAML under `contracts/domains/<domain_name>/<action>.contract.yaml` once the action stabilises.

## Quality gates

- Every domain action is covered by a contract test in `tests/contracts/`.
- Every domain has ≥ 1 unit test per handler in `tests/unit/domains/<domain_name>/`.
- `tools/auditors/` checks for cross-domain imports and fails CI on violations.
- Domain README must enumerate the actions it exposes.

## Conventions

- Domain names: lowercase `snake_case`, no plurals.
- Action ids: `<domain>.<verb>` — e.g. `billing.invoice_create`. Lowercase, snake_case throughout.
- Packet types are versioned: `billing.invoice.v1`. Breaking changes ship a new version per the breaking-change policy.
- A domain's public surface is its action ids — not its module layout. Refactor freely behind the action boundary.
