<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, adr]
tags: [L9_TEMPLATE, adr, transport_packet]
owner: platform
status: active
/L9_META -->

# ADR-0001 — TransportPacket as Canonical Execution Contract

- **Status:** Accepted
- **Date:** 2026-04-26
- **Deciders:** Platform team
- **Tags:** transport, contracts, migration

## Context

L9 has historically used `PacketEnvelope` as its execution contract. As the platform grew to include Gate (transport authority), Orchestrator (workflow authority), and Runtime (execution authority), the envelope needed:

- Mandatory transport-level fields (`provenance`, `hop_trace`, `delegation_chain`) that were optional or absent in `PacketEnvelope`.
- A clear separation of `payload_hash` (semantic) and `transport_hash` (envelope integrity).
- Append-only `hop_trace` as a tamper-evident routing journal.
- Strict `lineage` reconstruction from any derived packet.

`PacketEnvelope` was directionally correct but accumulated workflow-coupled fields and lacked the routing-level guarantees Gate requires.

## Decision

`TransportPacket` is the **only** canonical network execution contract for L9. `PacketEnvelope` is superseded.

Specifically:

- All ingress, egress, and inter-node traffic uses `TransportPacket`.
- Schema: `contracts/transport/transport_packet.schema.json`.
- Contract: `contracts/transport/transport_packet.contract.yaml`.
- Migration: `contracts/transport/migration_from_packet_envelope.contract.yaml`.
- Handler signature: `async def handler(packet: TransportPacket) -> TransportPacket`.
- `transport_hash` excludes `hop_trace` to allow append-only hops without breaking envelope integrity.
- `payload_hash` stands alone for semantic deduplication.

## Consequences

### Positive

- Uniform validation surface across all nodes.
- Hop-by-hop tamper evidence without breaking envelope hash.
- Replay protection and idempotency become Gate-only enforcement.
- Lineage is reconstructable from any derived packet.

### Negative

- One-time migration cost: every handler signature changes; every persisted packet store needs schema migration.
- Dual-read window required for systems running mixed versions.

### Neutral

- `PacketEnvelope` artifacts (database tables, type aliases) remain only behind explicitly-scoped adapters during the migration window.

## Alternatives Considered

### Option A — Extend `PacketEnvelope` in place

Add the missing fields, deprecate the old shape silently. Rejected: silent breaking changes are the worst-case L9 failure mode (see `BREAKING_CHANGE_POLICY.md`).

### Option B — Multiple envelope types per concern

Separate `RoutingPacket`, `WorkflowPacket`, `ExecutionPacket`. Rejected: Gate must remain workflow-stateless, which means it cannot dispatch on packet type semantics. One canonical packet keeps Gate's path single.

## Migration Plan

1. Land `TransportPacket` schema and contract (this ADR).
2. Implement gate-client SDK that constructs `TransportPacket` correctly.
3. Migrate Gate's `ExecuteService` to single-path `TransportPacket → TransportPacket`.
4. Migrate every node's handler signature.
5. Land dual-read adapter at `chassis/legacy/packet_envelope_adapter.py`.
6. Roll out producers.
7. Verify all consumers report `contract.version == 1.0.0`.
8. Remove the adapter; mark `PacketEnvelope` contract `superseded`.

## References

- Contracts: `contracts/transport/`
- Supersedes: legacy `contracts/packet_envelope_v1.yaml`
- Related: ADR-0002 (Gate is workflow-stateless)
- Boundary docs: `docs/boundaries/GATE.md`, `ORCHESTRATOR.md`, `RUNTIME.md`
