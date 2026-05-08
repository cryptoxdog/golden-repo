<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, contracts]
tags: [L9_TEMPLATE, contracts, routing]
owner: platform
status: active
/L9_META -->

# Routing Policy

Source contract: [`contracts/routing/routing_policy.contract.yaml`](../../contracts/routing/routing_policy.contract.yaml)

See also: [`docs/architecture/ROUTING.md`](../architecture/ROUTING.md) for the architectural rationale.

## Hard Rule

**All node-originated follow-up traffic returns to Gate.** Workers never know peer URLs.

## Patterns

| Allowed | Forbidden |
|---|---|
| `client → gate` | `node_a → node_b` |
| `node → gate` | `orchestrator → worker (direct)` |
| `gate → worker` | `worker → worker` |

## Selection Algorithm (Gate)

```
input:    packet.header.action
step 1:   lookup action in NodeRegistry
step 2:   filter health == active
step 3:   filter priority class eligibility
step 4:   admission_controller.check(node)
step 5:   dispatcher.dispatch(node, packet)
```

## Required Provenance

| Origin | `provenance.origin_kind` | `address.source_node` | `address.destination_node` |
|---|---|---|---|
| External client | `client` | client id | `gate` |
| Node follow-up | `node` | local node | `gate` |
| Gate dispatch | `gate` | `gate` | resolved worker |

## Failure Modes

| Reason | Returned |
|---|---|
| Action not registered | `failure_packet(reason="UNROUTABLE")` |
| No healthy node | `failure_packet(reason="NODE_UNAVAILABLE")` |
| Admission denied | `failure_packet(reason="ADMISSION_DENIED")` |
