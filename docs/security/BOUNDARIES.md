<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, security]
tags: [L9_TEMPLATE, security, boundaries]
owner: platform
status: active
/L9_META -->

# Boundary Enforcement

> Documentation describes boundaries. Code enforces them. CI fails the build when code drifts.

## Static Enforcement

| Check | Tool | Source |
|---|---|---|
| Banned-pattern scan | `tools/contract_scanner.py` | `docs/agents/CODING_GUIDE.md` §4 |
| Architecture import boundary | `tools/review/analyzers/architecture_boundary.py` | `tools/review/policy/architecture.yaml` |
| Contract presence + wiring | `tools/verify_contracts.py` | `contracts/` |
| Type strictness | `mypy --strict engine/` | `mypy.ini` |
| L9_META present | `tools/l9_meta_injector.py --check` | per-file header |
| Cypher safety | `tests/contracts/test_cypher_safety.py` (planned) | `LAW-09` |

## Runtime Enforcement

| Check | Owner | Failure Mode |
|---|---|---|
| `TransportPacket` schema | Gate ingress validator + Runtime handler | reject with `schema_violation` |
| Routing policy provenance | Gate routing validator | reject with `INVALID_PROVENANCE` |
| Idempotency dedup | Gate | return cached response packet |
| Replay protection | Gate | reject with `REPLAY_DETECTED` |
| Delegation scope | Gate + Runtime + Orchestrator | reject with `SCOPE_WIDENING_FORBIDDEN` |
| Tenant isolation | Query layer | reject with `CROSS_TENANT_FORBIDDEN` |
| Prohibited factors | Gate compiler at domain spec validation | fail compilation |

## CI Build Fails If

(From `gate.contract.yaml.ci_enforcement_rules`)

- `PacketEnvelope` imports exist in TransportPacket-native repos
- Direct node-to-node calls exist
- Raw HTTP posts to `/v1/execute` bypass the gate-client SDK
- Runtime contains workflow logic
- Gate contains workflow state
- Orchestrator bypasses Gate
- Non-`TransportPacket` execute path exists
- Packet mutation occurs without `derive()` or `with_hop()`
- Routing policy is bypassed
- Handler signature is not `TransportPacket → TransportPacket`
- `TransportPacket` schema validation is missing at gate ingress
- Node registration `supported_actions` is empty

## Runtime Audit

- Every blocked attempt at a prohibited factor is logged with `tenant.org_id`, actor, source file, source line, rejection reason.
- Every cross-boundary reject (provenance, scope, schema) emits a metric labeled by reason.

## Boundary Diagram

```
External                             Internal trusted              Persistent
┌─────────┐    HTTPS+API key   ┌─────┐  mTLS+TransportPacket  ┌─────────┐    tenant-scoped
│ Client  │ ─────────────────▶ │Gate │ ──────────────────────▶│ Workers │ ─────────────────▶ Stores
└─────────┘                    └─────┘                        └─────────┘
            schema validate ▲           routing policy  ▲       sanitize_label ▲
            authn/authz     │           admission       │       parameterized  │
            replay guard    │           idempotency     │       tenant scope   │
```

Each `▲` is a contract-enforced check. Removing any one of them fails CI.
