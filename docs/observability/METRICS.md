<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, observability]
tags: [L9_TEMPLATE, observability, metrics]
owner: platform
status: active
/L9_META -->

# Metrics

Source contract: [`contracts/observability/metrics.contract.yaml`](../../contracts/observability/metrics.contract.yaml)

## Surface

`GET /metrics` — Prometheus / OpenMetrics format. Configured by the chassis. Engines emit via `chassis.metrics`.

## SDK Metrics (every node)

- `transport_packets_received_total`
- `transport_packets_sent_total`
- `transport_packet_failures_total`
- `transport_propagation_failures_total`
- `transport_span_creation_failures_total`
- `transport_hop_duration_ms` (histogram)

## Gate Metrics

- `gate_dispatch_latency_ms` (histogram)
- `gate_routing_failures_total`
- `gate_trace_context_missing_total`
- `gate_admission_denials_total{reason}`
- `gate_circuit_breaker_state{node}`
- `gate_idempotency_cache_hits_total`

## Orchestrator Metrics

- `orchestrator_workflow_decision_latency_ms`
- `orchestrator_trace_link_failures_total`
- `workflows_started_total`
- `workflows_completed_total{terminal_status}`
- `orchestrator_replay_total{outcome}`
- `orchestrator_compensation_total{outcome}`

## Runtime Metrics

- `runtime_handler_latency_ms{action}` (histogram)
- `runtime_handler_failures_total{action,reason}`
- `runtime_resource_budget_exceeded_total{budget_kind}`
- `runtime_concurrent_executions{action}` (gauge)

## Cardinality Rules

| Rule | Reason |
|---|---|
| Never label with `packet_id` | Unbounded cardinality |
| Never label with `user_id` | Unbounded cardinality |
| Never label with free-form strings | Unbounded cardinality |
| `tenant_id` is `org_id` only | Bounded by tenant count |
| `action` is from registered set only | Bounded by registered actions |

## Default SLO Targets

| Metric | Target |
|---|---|
| `gate_dispatch_p99_ms` | ≤ 25ms |
| `runtime_handler_p99_ms` | ≤ 200ms |
| Workflow end-to-end success rate | ≥ 99.9% |
| Trace completeness | ≥ 99.5% |

SLOs are enforced by Grafana alerts in `observability/P2_5_grafana_slo_dashboard.json`.
