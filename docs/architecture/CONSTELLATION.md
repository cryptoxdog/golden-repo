<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, architecture]
tags: [L9_TEMPLATE, architecture, constellation]
owner: platform
status: active
/L9_META -->

# Constellation Topology

The Constellation is the runtime graph: **Gate** at the center, **Orchestrator** and **Runtime** nodes registered as peers. Gate sees no difference between them — both are nodes addressed by `action`.

## Logical Diagram

```
                External Request
                       │
                       ▼
              ┌────────────────┐
              │      GATE      │  WORKFLOW-STATELESS
              │                │  OPERATIONALLY STATEFUL
              │  1. Parse      │  raw JSON → TransportPacket
              │  2. Validate   │  IngressValidator
              │  3. Route      │  RoutingPolicy → NodeRegistry
              │  4. Admit      │  CB · rate limit · load shed
              │  5. Dispatch   │  HTTP/NATS/Kafka adapter
              │  6. Return     │  response packet
              └───────┬────────┘
                      │
            ┌─────────┴──────────┐
            ▼                    ▼
   ┌─────────────────┐  ┌────────────────┐
   │  ORCHESTRATOR   │  │    RUNTIME     │
   │   (stateful)    │  │ (bounded state)│
   │                 │  │                │
   │  Decomposes     │  │  Executes      │
   │  Sequences      │  │  Isolates      │
   │  Branches       │  │  Budgets       │
   │  Tracks DAGs    │  │  Scales        │
   │  Compensates    │  │                │
   └────────┬────────┘  └────────────────┘
            │
            │ Sub-tasks route BACK through Gate
            │ via SDK transport boundary (gate-client)
            ▼
         ┌──────┐
         │ GATE │ → routes to Runtime (or another Orchestrator)
         └──────┘
```

## Module Placement

### Gate (`constellation_gate/`)

```
boundary/      ingress_validator · routing_policy · context_injector · transport_codec · response_factory · failure_factory
resilience/    circuit_breaker · rate_limiter · load_shedding · backpressure · admission_controller · replay_guard · idempotency
routing/       node_registry · dispatcher
schemas/       packet · registry
runtime/       lifecycle · http_client · health
config/        settings · node_registry.yaml · priorities.yaml
api/           main · dependencies
```

### Orchestrator (`constellation_orchestrator/`)

```
engine/        orchestration_engine · condition_evaluator · decomposability_classifier · payload_transformer · deadline_propagator
compensation/  saga_manager · checkpoint_store
schemas/       workflow
config/        workflows.yaml · orchestrator_settings
api/           main · transport_adapter
```

### Runtime (`constellation_runtime/`)

```
execution/     agent_executor · resource_budget · state_manager
memory/        semantic_retriever · episodic_store
scaling/       autoscaler · pool_manager
```

## Registration

Every node — including Orchestrator — registers via `POST /v1/admin/register` with the same payload shape (see [`contracts/registration/node_registration.contract.yaml`](../../contracts/registration/node_registration.contract.yaml)).

## Boundary Enforcement

- Gate **MUST NOT** import `orchestration/`, `schemas/workflow.py`, or `config/workflows.yaml`. CI fails the build if it does.
- Runtime **MUST NOT** import other runtime nodes. Workers don't know peer URLs.
- Orchestrator **MUST NOT** dispatch except via the gate-client SDK boundary.

See [`docs/boundaries/`](../boundaries/) for the per-authority enforcement details.
