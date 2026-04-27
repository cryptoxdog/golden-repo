<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, adr]
tags: [L9_TEMPLATE, adr, gate]
owner: platform
status: active
/L9_META -->

# ADR-0002 — Gate Is Workflow-Stateless

- **Status:** Accepted
- **Date:** 2026-04-26
- **Deciders:** Platform team
- **Tags:** gate, boundaries, authority

## Context

Earlier iterations of Gate had begun acquiring workflow-coupled responsibilities: a workflow classifier (`is_workflow()`), a workflow dispatcher, special handling for the orchestrator, and persistence of workflow DAG fragments for replay convenience.

This drift introduced four problems:

1. Gate's execution path branched on payload semantics, which the routing policy explicitly forbids.
2. Replay and compensation logic lived in two places (Gate and Orchestrator), creating divergent semantics.
3. Orchestrator became a "special" node, breaking the symmetry that allows Gate to dispatch any node uniformly.
4. Boundary regression became cheap — adding workflow-aware code to Gate became a routine PR.

## Decision

Gate is **workflow-stateless**. It may hold operational state (rate limits, circuit breakers, idempotency dedup, replay guard, registry cache) but **no workflow state**.

Concretely:

- Gate's execute path is a single function: `validate → route → admit → dispatch → return`.
- Gate has no `if is_workflow():` branches.
- Gate does not import `orchestration/`, `schemas/workflow.py`, or `config/workflows.yaml`. CI fails the build if it does.
- Orchestrator registers as a normal node. Gate has no code that distinguishes it.
- All workflow authority — decomposition, branching, retry semantics, replay semantics, compensation semantics — lives in the Orchestrator.
- Mission kernel (`load_or_create_mission_state`, `checkpoint`, `restore`, `branch`, `merge`, `aggregate`, `decide_next_step`) is exclusively owned by the Orchestrator.

## Consequences

### Positive

- Gate's path is testable in isolation; no payload-semantic dependencies.
- Workflow logic has exactly one home.
- Orchestrator can be added, removed, replaced, or scaled independently of Gate.
- Boundary regression is detected at CI, not at runtime.

### Negative

- Some convenience features previously in Gate (e.g., implicit retry on transient failures with workflow awareness) move to Orchestrator and become explicit.
- Orchestrator must be highly available — but this was true regardless.

### Neutral

- Operational replay protection (transport-level packet_id dedup) stays in Gate. Semantic replay (workflow-level) is Orchestrator's.

## Alternatives Considered

### Option A — Allow Gate to hold workflow DAG fragments for replay efficiency

Rejected: turns Gate into a co-owner of workflow truth. Two co-owners produce divergent state.

### Option B — Combine Gate and Orchestrator into a single "control plane" service

Rejected: collapses the routing-vs-workflow boundary. Independent scaling, deployment, and failure isolation are lost.

## Migration Plan

This ADR documents a state to be enforced going forward; specific migration steps are in [`contracts/transport/migration_from_packet_envelope.contract.yaml`](../../contracts/transport/migration_from_packet_envelope.contract.yaml) Wave 1 (1F/1G/1H — delete `orchestration/`, `schemas/workflow.py`, `config/workflows.yaml` from Gate).

## References

- Contracts: `contracts/gate/gate.contract.yaml`, `contracts/orchestrator/orchestrator.contract.yaml`
- Boundary doc: `docs/boundaries/GATE.md`
- Related: ADR-0001 (TransportPacket canonical)
