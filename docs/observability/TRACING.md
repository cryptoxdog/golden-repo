<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, observability]
tags: [L9_TEMPLATE, observability, tracing]
owner: platform
status: active
/L9_META -->

# Tracing

Source contract: [`contracts/observability/trace_propagation.contract.yaml`](../../contracts/observability/trace_propagation.contract.yaml)

## Standard

W3C Trace Context, propagated through `header.trace_id`, `header.span_id`, `header.trace_flags`, `header.tracestate` on every `TransportPacket`.

## Ownership

| Owner | Responsibility |
|---|---|
| SDK | Extract / inject trace context · create boundary spans · transport metrics · hop timing |
| Gate | Preserve inbound trace context · create dispatch spans · annotate routing |
| Orchestrator | Workflow decision spans · workflow attributes · trace ↔ workflow correlation |
| Runtime | Execution spans · validation spans · execution attributes |
| Governance | Enforcement of the contract · forbidden-behavior detection |

## Required Spans

- `gate_ingress`
- `gate_dispatch`
- `node_receive`
- `node_handler`
- `node_emit`

Optional spans: `workflow_decision`, `fan_out_coordination`, `replay_evaluation`, `compensation_evaluation`, `runtime_execution`, `runtime_validation`, `persistence_write`.

## Required Attributes (every span)

- `trace_id`
- `node_name`
- `action`
- `tenant_id` (always `tenant.org_id`, never user_id)
- `packet_type`
- `root_id`

Gate-specific: `destination_node`, `requested_action`, `resolved_action`, `routing_policy_version`.
Orchestrator-specific: `workflow_id`, `step_id`, `replay_epoch`, `compensation_status`.
Runtime-specific: `execution_id`, `capability_name`, `result_status`, `execution_ms`.

## Propagation Rules

- `trace_id` is preserved across derivation. Never replaced if valid.
- Missing `trace_id` → SDK generates a new valid one.
- Malformed → replaced with new valid trace + diagnostic emission.
- `span_id` may change only at a new boundary span.
- `trace_flags` and `tracestate` preserved when present.

## Forbidden

- Detached async work creating new traces without governed policy.
- Replacing a valid inbound `trace_id`.
- Using trace data as a hidden control plane (no decisions read from spans).

## Backends

- **Local dev** — Tempo via Docker Compose
- **Production** — Grafana Tempo (or equivalent) behind OpenTelemetry Collector
- **Sampling** — head-based, configurable per environment in `observability/QW4_otel_collector_sampling.yaml`
