<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, boundaries]
tags: [L9_TEMPLATE, orchestrator, boundaries]
owner: platform
status: active
/L9_META -->

# Orchestrator Boundary

Source contract: [`contracts/orchestrator/orchestrator.contract.yaml`](../../contracts/orchestrator/orchestrator.contract.yaml)

## Identity

Orchestrator is the **workflow authority**. From Gate's perspective it is a normal node — addressed by `action`, dispatched like any other. From the system's perspective it is the only place where workflow meaning lives.

## Authority Model

Orchestrator owns:

- Decomposition of tasks into steps
- Sequencing of step execution
- Branching logic on workflow state
- Retry, replay, and compensation semantics
- Result aggregation
- Terminal outcome production

Orchestrator must not:

- Route packets directly
- Bypass Gate
- Own transport logic
- Maintain a private node registry
- Perform admission control

## State Model

Orchestrator is **authoritatively stateful**. All workflow state is durable, replayable, and auditable.

Owned state:

- workflow_dag · step_state · execution_history
- replay_state · compensation_state · terminal_outcomes
- mission_state · checkpoint_state

## Execution Loop

```
1. receive transport packet
2. load or create workflow state
3. evaluate next step(s)
4. emit subtask transport packet via gate-client
5. update state
6. repeat until terminal
```

All sub-task dispatch goes through Gate. No direct calls to runtime nodes.

## Mission Kernel

The mission kernel — `load_or_create_mission_state`, `checkpoint`, `restore`, `branch`, `merge`, `aggregate`, `decide_next_step` — is **exclusively** owned by the Orchestrator. It must not appear in Gate, in runtime nodes, or in the gate-client.

## Module Layout

```
engine/         orchestration_engine.py condition_evaluator.py
                decomposability_classifier.py payload_transformer.py
                deadline_propagator.py
compensation/   saga_manager.py checkpoint_store.py
schemas/        workflow.py
config/         workflows.yaml orchestrator_settings.py
api/            main.py transport_adapter.py
```

## Forbidden

- Direct runtime node calls
- Custom transport routing logic
- Private node registry
- Admission control
- Special semantic ingress like `/v1/orchestrate` as architectural identity

The Orchestrator's HTTP surface is `POST /v1/execute` and `GET /v1/health`. Period.

## Integration Rules

- All outbound packets go through Gate via the SDK transport layer.
- Preserve `trace_id` and `lineage` across all derived packets.
- Never fork traces arbitrarily — one workflow hop, one trace.
