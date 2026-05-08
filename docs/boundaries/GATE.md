<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, boundaries]
tags: [L9_TEMPLATE, gate, boundaries]
owner: platform
status: active
/L9_META -->

# Gate Boundary

Source contract: [`contracts/gate/gate.contract.yaml`](../../contracts/gate/gate.contract.yaml)

## Identity

Gate is the **workflow-stateless transport authority**. One path. One job. No semantic decisions.

## Single Execute Path

```python
async def execute(packet: TransportPacket) -> TransportPacket:
    validate(packet)
    node = route(packet.header.action)
    await admit(node)
    response = await dispatch(node, packet)
    return build_response(response)
```

No `if is_workflow():`. No branch on node type. No payload inspection for semantic meaning.

## Allowed Decisions

- **Routing** — action → node selection via NodeRegistry.
- **Admission** — circuit breaker, rate limit, load shedding, backpressure.
- **Resilience** — replay guard, idempotency cache.

## Forbidden Decisions

- Workflow branching, decomposition, retry semantics, replay semantics, compensation semantics.

## State Model

| Allowed (operational) | Forbidden (workflow) |
|---|---|
| Node registry cache | Workflow DAGs |
| Circuit breaker state | Step state |
| Rate limiter state | Replay state |
| Load shedding signals | Compensation state |
| Idempotency dedup store | Mission state |
| Replay guard | Semantic retry state |

All operational state must be **bounded · non-authoritative · discardable without semantic loss**.

## Module Layout (must exist)

```
boundary/      ingress_validator.py routing_policy.py context_injector.py
               transport_codec.py response_factory.py failure_factory.py
resilience/    circuit_breaker.py rate_limiter.py load_shedding.py
               backpressure.py admission_controller.py replay_guard.py idempotency.py
routing/       node_registry.py dispatcher.py
schemas/       packet.py registry.py
runtime/       lifecycle.py http_client.py health.py
config/        settings.py node_registry.yaml priorities.yaml
api/           main.py dependencies.py
```

## Module Layout (must NOT exist in Gate)

- `orchestration/`
- `schemas/workflow.py`
- `config/workflows.yaml`
- `boundary/workflow_dispatcher.py`
- Any workflow classifier or semantic replay/compensation factory

## CI Build Fails If

- Workflow logic appears in Gate
- `PacketEnvelope` imports exist
- Direct node-to-node calls exist
- Raw HTTP posts to `/v1/execute` bypass the gate-client SDK
- Packet mutation occurs without `derive()`
- Routing policy is bypassed
- Handler signature is not `TransportPacket → TransportPacket`
- TransportPacket schema validation is missing at gate ingress
- A registered node has empty `supported_actions`

## Orchestrator Treatment

Orchestrator is a **normal node** to Gate. Gate must not have any code that distinguishes it. Registration uses the same shape as any other node.
