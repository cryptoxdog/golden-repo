<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, security]
tags: [L9_TEMPLATE, security, threat_model]
owner: platform
status: active
/L9_META -->

# Threat Model

> Methodology: STRIDE per data flow, applied at each authority boundary.

## Trust Boundaries

```
┌──────────────────────────────────────────────────────────┐
│  TRUST 0  │ External clients (untrusted)                  │
└──────────────────────────────────────────────────────────┘
         │ HTTPS · API key · TransportPacket schema validation
         ▼
┌──────────────────────────────────────────────────────────┐
│  TRUST 1  │ Gate (transport authority)                    │
└──────────────────────────────────────────────────────────┘
         │ Internal network · mTLS · TransportPacket
         ▼
┌──────────────────────────────────────────────────────────┐
│  TRUST 2  │ Orchestrator / Runtime (workload nodes)       │
└──────────────────────────────────────────────────────────┘
         │ Tenant-scoped · sanitize_label · parameterized queries
         ▼
┌──────────────────────────────────────────────────────────┐
│  TRUST 3  │ Persistent stores (Neo4j · Postgres · Redis)  │
└──────────────────────────────────────────────────────────┘
```

## STRIDE per Authority

### Gate

| Threat | Mitigation |
|---|---|
| **S**poofing | API key SHA-256 verify, constant-time compare, optional mTLS for node-to-gate |
| **T**ampering | `transport_hash` + transport_signature on every packet; replay guard rejects re-injection |
| **R**epudiation | `delegation_chain` + `hop_trace` are append-only and signed |
| **I**nformation disclosure | TLS in transit; PII fields declared and redacted in logs; classification flag enforced |
| **D**enial of service | Rate limiter, circuit breaker, load shedding, backpressure — all at Gate |
| **E**levation of privilege | Tenant resolved by chassis; delegation scope can only narrow, never widen |

### Orchestrator

| Threat | Mitigation |
|---|---|
| Spoofing | Reachable only via Gate; orchestrator-bound packets carry `provenance.resolved_by_gate=true` |
| Tampering | Workflow state checkpointed with content hash; replay reconstructs deterministically |
| Repudiation | All step transitions emit signed `TransportPacket` events |
| Information disclosure | Workflow state scoped by `tenant.org_id`; cross-tenant access forbidden by query layer |
| DoS | Per-workflow concurrency limits; mission kernel back-pressure |
| EoP | Step authorization checks `delegation_chain` before dispatch |

### Runtime

| Threat | Mitigation |
|---|---|
| Spoofing | Reachable only via Gate; packets validated against schema before handler |
| Tampering | Packet immutable; `derive()` is the only mutation path |
| Repudiation | Every execution appends one `hop_trace` entry with timing |
| Information disclosure | PII fields hashed/encrypted/redacted/tokenized per domain spec |
| DoS | Resource budgets (tokens, GPU-sec, cost); concurrency caps; autoscaler |
| EoP | Sanitize all dynamic identifiers (Cypher labels) before interpolation; parameterized values |

## High-Risk Surfaces

1. **Domain spec upload** (`/v1/admin`) — untrusted YAML. Mitigations: schema validation, prohibited factors compile-time block, signed admin credential.
2. **Cypher injection** — sanitize_label regex `^[A-Za-z_][A-Za-z0-9_]*$`; values always parameterized.
3. **Cross-tenant data exposure** — every query scopes by `tenant.org_id`; integration tests enforce isolation.
4. **Replay attacks** — Gate's `replay_guard` keyed on `header.packet_id`; idempotency keyed on `header.idempotency_key`.
5. **Trace as control plane** — observability data must never carry decisions; this is contract-enforced in `trace_propagation.contract.yaml`.

## Out of Scope

- Physical hardware tampering (covered by hosting provider attestation)
- Insider with full production credentials (covered by access governance)
- Quantum-resistant crypto (tracked separately under Crypto Roadmap)

## Reviews

Threat model is reviewed per release boundary or on any architectural change crossing a trust boundary.
