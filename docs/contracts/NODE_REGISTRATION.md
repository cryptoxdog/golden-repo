<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, contracts]
tags: [L9_TEMPLATE, contracts, registration]
owner: platform
status: active
/L9_META -->

# Node Registration

Source contract: [`contracts/registration/node_registration.contract.yaml`](../../contracts/registration/node_registration.contract.yaml)

## Endpoint

```
POST /v1/admin/register
Authentication: gate_admin_credential
```

## Payload Shape

A top-level JSON object keyed by node name:

```yaml
enrichment-engine:
  internal_url: "http://enrichment-engine:8001"
  supported_actions:
    - enrich
    - enrichment_request
  priority_class: P1
  max_concurrent: 16
  health_endpoint: /v1/health
  timeout_ms: 60000
  metadata:
    node_type: runtime
    version: 1.4.2
```

## Required Fields

- `internal_url` — absolute, primary route target.
- `supported_actions` — non-empty list of lowercase snake_case action strings.

## Optional Fields

`priority_class` · `max_concurrent` · `health_endpoint` · `timeout_ms` · `metadata` · `public_url` · `capability_descriptor` · `protocol_compatibility` · `node_class` · `trust_tier` · `deployment_region` · `version`

## Rules

- Node names normalized to lowercase.
- `supported_actions` must be non-empty (CI fails the build otherwise).
- `internal_url` must be absolute.
- Gate is authoritative for activation and health state — registration is a declaration, not a guarantee.
- Registration may be rejected if `overwrite=false` and the node already exists.
- Orchestrator registers as a normal node. No special treatment.

## Health Lifecycle

1. Node POSTs registration on boot.
2. Gate marks node `active` only after a successful health probe.
3. Health probe failures move the node to `unhealthy` — admission begins shedding.
4. After N consecutive failures, the node is marked `inactive` and removed from routing.
