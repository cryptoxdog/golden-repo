<!--
L9_META:
  l9_schema: 1
  origin: l9-template
  engine: golden-repo
  layer: observability
  tags: [observability, otel, prometheus, grafana, loki, alloy]
  owner: platform
  status: active
-->

# observability/

The shipped observability stack: OpenTelemetry collector, Prometheus, Grafana, Loki, Alloy. Configurations, dashboards, alerts.

## Purpose

A node is only as operable as its observability surface. This directory ships the **default stack** that every node boots against locally and that production environments mirror.

## What lives here

| File / Group | Responsibility |
|---|---|
| `1_observability_telemetry.py` | Python OTel bootstrap used by `engine/main.py`; wires traces, metrics, logs. |
| `1_config_otel-collector-config.yaml` | OTel collector pipelines: receive → process → export. |
| `1_config_prometheus.yml`, `4_prometheus_config.yml`, `P2_4_prometheus_scrape.yml` | Prometheus scrape configurations. |
| `1_config_grafana_datasources.yml` | Grafana datasource provisioning. |
| `4_grafana_dashboard_metrics.json`, `P2_4_grafana_dashboard.json`, `P2_5_grafana_slo_dashboard.json` | Default dashboards: per-node SLIs, SLO error budgets. |
| `5_prometheus_alert_rules.yml` | Alert rules for the SLI set in the metrics contract. |
| `1_docker-compose.observability.yml` | Local stack — bring up the full pipeline with one command. |
| `QW1_alloy_config.alloy`, `QW1_loki_config.yaml` | Log shipping via Grafana Alloy → Loki. |
| `QW4_docker_compose_otel.yml`, `QW4_otel_collector_sampling.yaml` | Tail-based and head-based sampling configs. |

## What does NOT live here

- **No business metrics defined inline.** Domain-specific metrics are emitted from `engine/`, configured here.
- **No production credentials.** All endpoints are env-driven.
- **No source code beyond `1_observability_telemetry.py`.** This directory is config-first.

## Contracts that govern this directory

- [`/contracts/observability/metrics.contract.yaml`](../contracts/observability/metrics.contract.yaml) — required SLI metric set; every node must emit these.
- [`/contracts/observability/trace_propagation.contract.yaml`](../contracts/observability/trace_propagation.contract.yaml) — W3C trace context propagation across the gate and between nodes.
- [`/contracts/transport/transport_packet.contract.yaml`](../contracts/transport/transport_packet.contract.yaml) — `trace_id`, `span_id`, `correlation_id` fields the collector relies on.

## Required SLIs

Every node exposes:

- `transport_requests_total{action,result}` — request counter.
- `transport_request_duration_seconds{action}` — request latency histogram.
- `gate_admit_total{decision}` — gate admit/deny counter.
- `handler_errors_total{action,error_type}` — engine-side errors.
- `node_info{node_id,version,layer}` — info gauge.

Names and labels are normative. See `docs/observability/METRICS.md` for the full schema.

## Quality gates

- `tests/compliance/` asserts every required metric is exposed by the chassis.
- Dashboards are JSON-validated in CI; broken JSON blocks merge.
- Alert rules under `5_prometheus_alert_rules.yml` are linted by `promtool`.
- The OTel collector config is validated by `otelcol validate` in CI.

## Conventions

- Metric names: `snake_case`, plural counters end in `_total`, histograms end in `_seconds` or `_bytes`.
- Labels: low cardinality. `tenant_id` is **never** a metric label — it goes on traces and logs.
- Dashboards: title `[Node] <Concern> — <Audience>`, e.g. `[Node] Gate — Operators`.
