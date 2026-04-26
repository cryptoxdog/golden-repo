<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [contracts]
tags: [L9_TEMPLATE, contracts, canonical]
owner: platform
status: active
/L9_META -->

# L9 Contracts — Canonical Source of Truth

> Contracts in this directory are **canonical**. Code conforms to contracts; contracts do not conform to code.
> Every CI build re-validates source against these specs. A build that passes lint but violates a contract is a broken build.

---

## Authority Model

| Layer | Role | State Model | Owns |
|---|---|---|---|
| **Gate** | Workflow-stateless transport authority | Operationally stateful, workflow-stateless | Validation, routing, admission, dispatch |
| **Orchestrator** | Workflow authority (a normal node from Gate's view) | Durably stateful | Workflow DAG, replay, compensation, mission state |
| **Runtime** | Execution-only node | Boundedly stateful | Capability execution, resource budgets, local caches |

The **TransportPacket** is the single canonical execution contract. `PacketEnvelope` is superseded and exists only behind explicitly-scoped adapters.

---

## Directory Layout

```
contracts/
├── README.md                          ← this file
├── transport/
│   ├── transport_packet.contract.yaml ← TransportPacket schema, hashing, lineage
│   ├── transport_packet.schema.json   ← JSON Schema for runtime validation
│   └── migration_from_packet_envelope.contract.yaml
├── routing/
│   └── routing_policy.contract.yaml   ← node-to-gate-to-node invariant
├── gate/
│   └── gate.contract.yaml             ← workflow-stateless authority RFC
├── orchestrator/
│   └── orchestrator.contract.yaml     ← workflow authority RFC
├── runtime/
│   └── runtime.contract.yaml          ← execution-only node RFC
├── registration/
│   └── node_registration.contract.yaml
├── governance/
│   ├── tenant_context.contract.yaml
│   ├── delegation_chain.contract.yaml
│   └── prohibited_factors.contract.yaml
├── observability/
│   ├── trace_propagation.contract.yaml
│   └── metrics.contract.yaml
└── _schemas/
    └── l9_contract_meta.schema.json   ← meta-schema all contract YAMLs validate against
```

Legacy contracts (`packet_envelope_v1.yaml`, `node_registration_contract.yaml`, `conformant_node_contract.yaml`, `HEALTHCHECK_READINESS_SPEC.md`, `conformance_checklist.md`) remain at the top level for backward compatibility during migration to the TransportPacket-canonical surface.

---

## Versioning Policy

- Contracts use **semantic versioning**: `{major}.{minor}.{patch}`.
- **Major** — breaking field rename, removal, or semantic change. Requires migration plan + dual-read window.
- **Minor** — additive fields, new enum values, additional optional sections.
- **Patch** — clarifications, typos, non-normative examples.
- Every contract carries `contract.id`, `contract.version`, `contract.status` in its frontmatter.
- Statuses: `draft` → `canonical` → `superseded`. Only `canonical` is enforced in CI.

---

## Validation Flow

1. **Authoring** — write/modify a contract YAML under the appropriate subdirectory.
2. **Meta-schema check** — `make verify-contracts` validates the contract against `_schemas/l9_contract_meta.schema.json`.
3. **Runtime schema check** — `transport_packet.schema.json` validates every packet on the wire (gate ingress, runtime ingress).
4. **Architecture tests** — `tests/contracts/` enforces boundary invariants (no node-to-node calls, hop_trace growing, gate workflow-stateless).
5. **CI gate** — build fails if any of the above fail. See `ci_enforcement_rules` in `gate/gate.contract.yaml`.

---

## Breaking-Change Procedure

1. Open an ADR under `docs/adr/` describing the change, motivation, and migration path.
2. Bump the contract `version` major component and mark previous version `status: superseded`.
3. Land a dual-read adapter behind a feature flag.
4. Migrate all consumers; remove the adapter only after every consumer reports the new contract version.
5. Delete the superseded contract file in a follow-up release.

---

## Cross-Reference

| Topic | Contract | Doc |
|---|---|---|
| Packet schema | `transport/transport_packet.contract.yaml` | `docs/contracts/TRANSPORT_PACKET.md` |
| Routing invariant | `routing/routing_policy.contract.yaml` | `docs/architecture/ROUTING.md` |
| Gate boundary | `gate/gate.contract.yaml` | `docs/boundaries/GATE.md` |
| Orchestrator boundary | `orchestrator/orchestrator.contract.yaml` | `docs/boundaries/ORCHESTRATOR.md` |
| Runtime boundary | `runtime/runtime.contract.yaml` | `docs/boundaries/RUNTIME.md` |
| Node registration | `registration/node_registration.contract.yaml` | `docs/contracts/NODE_REGISTRATION.md` |
| Trace propagation | `observability/trace_propagation.contract.yaml` | `docs/observability/TRACING.md` |

---

L9 Contracts · Canonical · Quantum AI Partners
