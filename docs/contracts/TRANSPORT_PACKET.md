<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, contracts]
tags: [L9_TEMPLATE, contracts, transport_packet]
owner: platform
status: active
/L9_META -->

# TransportPacket — Authoring Guide

Source contract: [`contracts/transport/transport_packet.contract.yaml`](../../contracts/transport/transport_packet.contract.yaml)
Source schema: [`contracts/transport/transport_packet.schema.json`](../../contracts/transport/transport_packet.schema.json)

## What It Is

The single canonical execution contract for every L9 system. Every packet on every wire — client→gate, gate→worker, worker→gate — is a `TransportPacket`. There are no other envelopes.

## Required Sections

| Section | Why |
|---|---|
| `header` | Identity, type, action, timing, schema version |
| `address` | Source, destination, reply path |
| `tenant` | Multi-tenant isolation and audit |
| `payload` | Action-specific data (the only field that varies per domain) |
| `security` | Hashes, classification, encryption status, PII declarations |
| `governance` | Intent, compliance tags, retention, audit flag |
| `provenance` | Origin kind, requested vs resolved action |
| `delegation_chain` | Append-only scoped authorizations |
| `hop_trace` | Append-only tamper-evident routing journal |
| `lineage` | Root, parent, generation |
| `attachments` | Out-of-band references (URI + sha256 + media type) |

## Construction Rules

- **Immutable execution record.** Once constructed, never mutated.
- **Semantic change requires `derive()`.** A new packet referencing the parent.
- **Observational hop requires `with_hop()`.** Appends to `hop_trace` without semantic change.
- Two hashes:
  - `payload_hash = sha256(canonical_json(payload))`
  - `transport_hash = sha256(canonical_json(stable core, excluding hop_trace))`

## Lineage Rules

| Packet kind | `parent_id` | `root_id` | `generation` |
|---|---|---|---|
| Root | `null` | `self.packet_id` | 0 |
| Child | `parent.packet_id` | `parent.root_id` | `parent.generation + 1` |

## Response Rules

- A response is itself a `TransportPacket` with `packet_type: response`.
- Preserve the original `packet_id`.
- Reverse `address.source_node` ↔ `address.destination_node`.
- Carry the execution result in `payload`.

## Idempotency

`header.idempotency_key` is the dedup key. Gate enforces it. Same key → same response packet, byte-for-byte.

## Replay Protection

`header.packet_id` is the replay identity. Gate's `replay_guard` rejects duplicate packet receipts at transport level.

## Anti-Patterns (rejected at CI)

- Direct node-to-node calls
- In-place packet mutation
- Multiple transport schemas
- Raw HTTP `POST /v1/execute` with untyped dicts
- `PacketEnvelope` as active canonical contract

## Common Mistakes

| Wrong | Right |
|---|---|
| `packet.payload["new_field"] = value` | `new = packet.derive(mutation={"payload": {**packet.payload, "new_field": value}})` |
| `await httpx.post(other_node_url, ...)` | `await gate_client.execute(new_packet)` |
| `packet_type: "ENRICHMENT_RESULT"` | `packet_type: "response"` (with payload semantics) |
| Setting `lineage.parent_id` to an arbitrary id | Always derive — `derive()` sets it correctly |
| Skipping `hop_trace` | Every node receiving a packet appends one entry |
