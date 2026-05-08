<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, contracts]
tags: [L9_TEMPLATE, contracts, packet_types]
owner: platform
status: active
/L9_META -->

# Packet Type Registry

`header.packet_type` is a closed enum. **Values may be added; values may never be renamed or removed.** All values are lowercase snake_case.

## Canonical Transport Packet Types

| Value | Meaning |
|---|---|
| `request` | Inbound request to a node |
| `response` | Synchronous response packet |
| `event` | Fire-and-forget signal |
| `command` | Imperative directive (rare) |
| `delegation` | Authority transfer (uses delegation_chain) |
| `failure` | Structured failure result |
| `replay_request` | Orchestrator-issued replay |
| `replay_response` | Result of a replay |
| `compensation` | Saga compensation step |

## Domain Packet Types (legacy / payload-level)

These appear in earlier specs as `payload.kind` discriminators. They are **not** valid `header.packet_type` values. Use `request`/`response` at the transport layer; carry the domain semantic in the payload:

`memory_write` · `memory_read` · `reasoning_trace` · `tool_call` · `tool_result` · `tool_audit` · `insight` · `consolidation` · `world_model_update` · `identity_fact` · `graph_sync` · `graph_match` · `gds_job` · `enrichment_request` · `enrichment_result` · `score_record` · `routing_decision` · `signal_event` · `health_assessment` · `forecast_snapshot` · `handoff_document`

## Common Mistakes

| Wrong | Right |
|---|---|
| `"ENRICHMENT_RESULT"` | `"response"` with payload `kind: enrichment_result` |
| `"enrichResult"` | lowercase snake_case in payload |
| `"match_result"` | `"response"` with payload `kind: graph_match` |
| `"GRAPH_MATCH"` | `"graph_match"` (in payload, not header) |

## Adding a New Type

1. Add to this file.
2. Add to the enum in `transport/transport_packet.schema.json`.
3. Add validation in the gate ingress validator.
4. Bump the contract minor version.
5. Land an ADR if the new type implies new authority semantics.
