<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, boundaries]
tags: [L9_TEMPLATE, boundaries, placement]
owner: platform
status: active
/L9_META -->

# What Lives Where — Canonical Placement

| Concern | Lives In | Forbidden In |
|---|---|---|
| HTTP routes (FastAPI) | `chassis/` | `engine/`, runtime modules |
| Auth (API keys, signature) | `chassis/auth.py` | engines |
| Tenant resolution | `chassis/tenant.py` | engines |
| Rate limiting / circuit breaker / load shedding | Gate `resilience/` | runtime, orchestrator |
| Node registry | Gate `routing/node_registry.py` | runtime, orchestrator |
| Workflow DAG, step state, replay, compensation | Orchestrator `engine/`, `compensation/` | gate, runtime |
| Mission kernel | Orchestrator only | everywhere else |
| Capability execution | Runtime `execution/` | gate, orchestrator |
| Resource budgets | Runtime `execution/resource_budget.py` | gate, orchestrator |
| Vector / KG retrieval | Runtime `memory/` | gate |
| Autoscaling | Runtime `scaling/` | gate |
| Trace context propagation | SDK + transport (gate-client) | nodes redefining propagation |
| Span creation at boundaries | SDK | nodes redefining boundaries |
| Workflow attributes on spans | Orchestrator | gate, runtime |
| Execution attributes on spans | Runtime | gate, orchestrator |
| Idempotency dedup | Gate | nodes |
| Replay protection | Gate (transport-level), Orchestrator (semantic) | runtime |
| Domain spec | `domains/<id>/spec.yaml` | hardcoded values |
| Dockerfile / CI / Terraform | `l9-template`, `infrastructure/`, `deploy/` | per-engine repos |

## Quick Decision Table

| If you are about to write… | Stop and put it in… |
|---|---|
| `from fastapi import APIRouter` in an engine | the chassis or remove it |
| A workflow check inside Gate | the orchestrator |
| A direct `httpx.post` to another node | the gate-client SDK |
| A new transport envelope class | nowhere — use `TransportPacket` |
| Mission state in a runtime handler | the orchestrator |
| A custom `/v1/orchestrate` route | nowhere — orchestrator uses `/v1/execute` like every node |
| Retry semantics in runtime | the orchestrator |
| Workflow DAG persistence in Gate | the orchestrator |
