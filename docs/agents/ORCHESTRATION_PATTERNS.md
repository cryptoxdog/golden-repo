<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, agents]
tags: [L9_TEMPLATE, agents, orchestration_patterns]
owner: platform
status: active
/L9_META -->

# Orchestration Patterns

> Canonical recipes for common workflow shapes. Every pattern below routes every sub-step through Gate.

## Pattern 1 — Single Action

A single action handler runs to completion in one runtime node.

```
client → gate → runtime → gate → client
```

Use when: the work is a single bounded capability (e.g., `match`, `enrich`, `score`).

## Pattern 2 — Sequential Workflow

Decompose a goal into ordered steps. Orchestrator emits each sub-task via the gate-client.

```
client → gate → orchestrator
                    │
                    ├── gate → runtime_a → gate → orchestrator
                    ├── gate → runtime_b → gate → orchestrator
                    └── gate → runtime_c → gate → orchestrator
                                                       │
                                                       ▼
                                                client (terminal)
```

Use when: the steps depend on each other and order matters.

## Pattern 3 — Fan-Out / Fan-In

Orchestrator dispatches N parallel sub-tasks and merges results.

```
                ┌─ gate → runtime_x ─┐
orchestrator ───┼─ gate → runtime_y ─┤── orchestrator (merge)
                └─ gate → runtime_z ─┘
```

Mission kernel handles fan-in semantics: `branch`, `merge`, `aggregate`, `decide_next_step`.

## Pattern 4 — Conditional Branch

Orchestrator's `condition_evaluator` decides the next step based on prior results.

```
orchestrator ─→ gate → runtime_classifier ─→ orchestrator
                                                  │
                                  ┌───────────────┴───────────────┐
                                  ▼                               ▼
                          gate → runtime_path_a         gate → runtime_path_b
```

The conditional logic lives in the orchestrator's `engine/condition_evaluator.py`. Runtime nodes know nothing about the branch.

## Pattern 5 — Saga (Compensating Transaction)

A multi-step workflow with compensation on failure.

```
orchestrator ─→ step_1 (commit)
              ─→ step_2 (commit)
              ─→ step_3 (fail) ──→ saga_manager
                                      │
                                      ├── compensate(step_2)
                                      └── compensate(step_1)
```

Compensation steps are themselves `TransportPacket` with `packet_type: compensation` and route through Gate like any other step.

## Pattern 6 — Replay

Orchestrator replays a workflow from a checkpoint.

```
orchestrator.load(workflow_id, checkpoint=N)
  └── re-emit step_N+1 with packet_type=replay_request
        └── runtime executes → packet_type=replay_response
              └── orchestrator updates state
```

Replay never bypasses Gate. Replay protection at the transport level uses `header.packet_id`; semantic replay logic lives in the orchestrator.

## Pattern 7 — Long-Running with Status

Orchestrator returns a synthetic `accepted` response immediately, then progresses asynchronously. Client polls a status action.

```
client → gate → orchestrator (returns "accepted" with workflow_id)
                    │
                    ▼ (background)
                  gate → runtime_step_1 ...

client → gate → orchestrator(action="get_status", workflow_id=...) → "running" | "complete" | "failed"
```

Status is `action`-addressed — never a separate HTTP route.

## Anti-Patterns

- ❌ Orchestrator calling Runtime directly (bypasses Gate)
- ❌ Runtime emitting follow-up packets without orchestrator authority
- ❌ Branching logic inside Gate ("`if is_workflow():`")
- ❌ Workflow state inside Runtime
- ❌ A separate `/v1/orchestrate` ingress
- ❌ Detached async traces — every span chain stays under one root `trace_id` per workflow hop
