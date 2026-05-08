<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, boundaries]
tags: [L9_TEMPLATE, runtime, boundaries]
owner: platform
status: active
/L9_META -->

# Runtime Boundary

Source contract: [`contracts/runtime/runtime.contract.yaml`](../../contracts/runtime/runtime.contract.yaml)

## Identity

Runtime is the **execution-only authority**. It receives a `TransportPacket`, executes a single capability, returns a `TransportPacket`. Nothing more.

## Handler Contract

```python
async def handler(packet: TransportPacket) -> TransportPacket: ...
```

Every runtime handler accepts a `TransportPacket` and returns a `TransportPacket`. No raw dicts, no untyped envelopes, no alternate packet types.

## Authority Model

Runtime must:

- Validate the packet
- Execute the requested action
- Enforce resource budgets (tokens, GPU-seconds, cost)
- Return success or failure as a response packet
- Preserve trace context
- Respect concurrency limits
- Append exactly one entry to `hop_trace`

Runtime must not:

- Decide the next workflow step
- Trigger retries or compensation
- Perform routing
- Maintain workflow control state
- Call other nodes directly
- Call Gate without going through the SDK
- Emit follow-up packets without orchestrator authority

## State Model

**Boundedly stateful.** Allowed local state:

- Execution-local state (request-scoped)
- Caches
- Model or session state
- Tool state

Forbidden state:

- Workflow DAG
- Cross-step orchestration state
- Replay or compensation authority
- Authoritative cross-step history

## Execution Properties

- Isolated
- Bounded
- Deterministic where possible
- Stateless where possible

## Module Layout

```
execution/     agent_executor.py resource_budget.py state_manager.py
memory/        semantic_retriever.py episodic_store.py
scaling/       autoscaler.py pool_manager.py
```

## Guarantees

- Resource limits respected
- Explicit success or failure returned
- Diagnostics included in failure packets
- Trace context preserved
- `hop_trace` appended with the runtime's `node_name` exactly once per packet
