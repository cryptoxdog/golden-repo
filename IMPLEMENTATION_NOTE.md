<!--
L9_META:
  l9_schema: 1
  origin: l9-template
  engine: golden-repo
  layer: meta
  tags: [implementation-note, scaffold, docs, contracts]
  owner: platform
  status: active
-->

# Implementation Note — L9 Docs and Contracts Scaffold

**Branch:** `chore/l9-docs-contracts-scaffold`
**Scope:** Add the L9-aligned starter pack: canonical contracts, architecture and operations docs, ADR template, security and observability docs, and READMEs for every AI-system directory in the repo.
**Non-goals:** No engine, chassis, tools, or CI code is changed in this branch. No legacy file under `contracts/*.yaml` is removed; the new canonical contracts coexist with the legacy ones during migration.

This document inventories every new file added in this branch and explains its purpose.

---

## 1. Contracts pack (`/contracts/`)

The contracts pack is the **enforcement layer**. Docs explain; contracts win. Every contract YAML carries an `L9_META` header and validates against the meta-schema below.

### 1.1 Meta-schema

| File | Purpose |
|---|---|
| `contracts/README.md` | Index of the contracts pack — what each contract owns, how they relate, who reviews changes. |
| `contracts/_schemas/l9_contract_meta.schema.json` | JSON Schema 2020-12 meta-schema. Every `*.contract.yaml` validates against this. CI fails if a new contract YAML omits required L9 fields. |

### 1.2 Transport — the canonical envelope

| File | Purpose |
|---|---|
| `contracts/transport/transport_packet.contract.yaml` | The canonical TransportPacket contract: envelope fields, invariants, error shape. Replaces `PacketEnvelope` (now `superseded`). |
| `contracts/transport/transport_packet.schema.json` | JSON Schema 2020-12 for the TransportPacket envelope. Used by the chassis at runtime and by `tests/contracts/`. |
| `contracts/transport/migration_from_packet_envelope.contract.yaml` | Migration contract: maps legacy `PacketEnvelope` fields to canonical `TransportPacket`, declares deprecation timeline. |

### 1.3 Routing

| File | Purpose |
|---|---|
| `contracts/routing/routing_policy.contract.yaml` | Routing authority policy: how `action` is mapped to a target node, peer-URL hiding, fallback semantics. |

### 1.4 The three authorities — Gate / Orchestrator / Runtime

| File | Purpose |
|---|---|
| `contracts/gate/gate.contract.yaml` | Gate contract — the workflow-stateless transport authority. Defines the single execute path: `validate → route → admit → dispatch → return`. |
| `contracts/orchestrator/orchestrator.contract.yaml` | Orchestrator contract — workflow authority. Registers as a normal node. Owns multi-step state. |
| `contracts/runtime/runtime.contract.yaml` | Runtime contract — execution-only. Handler signature, idempotency, statelessness. |

### 1.5 Registration

| File | Purpose |
|---|---|
| `contracts/registration/node_registration.contract.yaml` | Node self-registration handshake at boot. Capabilities, action ids, health endpoints. |

### 1.6 Governance

| File | Purpose |
|---|---|
| `contracts/governance/tenant_context.contract.yaml` | Tenant context envelope field — required on every packet, preserved end-to-end. |
| `contracts/governance/delegation_chain.contract.yaml` | Delegation chain semantics — extended on chained calls, never overwritten. |
| `contracts/governance/prohibited_factors.contract.yaml` | Fields the engine must not read for decisioning. Static-checked by `tools/auditors/`. |

### 1.7 Observability

| File | Purpose |
|---|---|
| `contracts/observability/trace_propagation.contract.yaml` | W3C trace context propagation across the gate and between nodes. |
| `contracts/observability/metrics.contract.yaml` | Required SLI metric set every node must expose. |

---

## 2. Docs pack (`/docs/`)

Docs explain. They reference contracts; they do not redefine them. Every doc carries an L9_META header.

### 2.1 Index and architecture

| File | Purpose |
|---|---|
| `docs/README.md` | Index of the docs pack — section map, audience guide, contract pointers. |
| `docs/architecture/OVERVIEW.md` | One-page overview: a node, a constellation, the gate, the canonical packet. |
| `docs/architecture/CONSTELLATION.md` | How nodes compose into a constellation — orchestrator role, peer discovery, packet flow. |
| `docs/architecture/ROUTING.md` | Routing model: action → target resolution; why workers must not know peer URLs. |

### 2.2 Boundaries

| File | Purpose |
|---|---|
| `docs/boundaries/GATE.md` | Gate boundary — what crosses, what doesn't, the single execute path. |
| `docs/boundaries/ORCHESTRATOR.md` | Orchestrator boundary — workflow state lives here, not in the chassis. |
| `docs/boundaries/RUNTIME.md` | Runtime boundary — handler invariants, idempotency, no transport authority. |
| `docs/boundaries/WHAT_LIVES_WHERE.md` | The "what lives where" map — directory by directory, contract by contract. |

### 2.3 Contracts companions

Plain-English companions to the YAML contracts. Useful for onboarding.

| File | Purpose |
|---|---|
| `docs/contracts/TRANSPORT_PACKET.md` | Companion to `transport_packet.contract.yaml`. Field walkthrough, examples, anti-patterns. |
| `docs/contracts/ROUTING_POLICY.md` | Companion to `routing_policy.contract.yaml`. |
| `docs/contracts/NODE_REGISTRATION.md` | Companion to `node_registration.contract.yaml`. |
| `docs/contracts/DELEGATION_PROTOCOL.md` | Companion to `delegation_chain.contract.yaml`. Worked examples. |
| `docs/contracts/PACKET_TYPE_REGISTRY.md` | Registry conventions: how to name and version packet types. |
| `docs/contracts/BREAKING_CHANGE_POLICY.md` | When a change is breaking, how to ship migrations, deprecation windows. |

Pre-existing files in `docs/contracts/` (e.g. `TEST_QUALITY.md`, `QUERY_PERFORMANCE.md`, `LOG_SAFETY.md`, `API_REGRESSION.md`, plus `docs/review/`, `docs/audit/`, `docs/agent-tasks/`) are preserved unchanged.

### 2.4 Agents

| File | Purpose |
|---|---|
| `docs/agents/CODING_GUIDE.md` | The coding guide for engine/handler authors. Banned imports, idempotency rules, packet patterns. |
| `docs/agents/ORCHESTRATION_PATTERNS.md` | Patterns for multi-step workflows — saga, fan-out, retry, compensation. |
| `docs/agents/LIFECYCLE.md` | Node lifecycle — boot, register, serve, drain, terminate. |

### 2.5 Architecture decision records

| File | Purpose |
|---|---|
| `docs/adr/README.md` | ADR index, process, status definitions. |
| `docs/adr/TEMPLATE.md` | ADR template — context, decision, consequences, alternatives. |
| `docs/adr/0001-transport-packet-canonical.md` | ADR-0001: TransportPacket is canonical; PacketEnvelope is superseded. |
| `docs/adr/0002-gate-workflow-stateless.md` | ADR-0002: The gate is workflow-stateless; orchestration is a separate authority. |

### 2.6 Runbooks

| File | Purpose |
|---|---|
| `docs/runbooks/DEPLOY.md` | Deploy runbook — promotion gates, readiness checks, rollback steps. |
| `docs/runbooks/INCIDENT.md` | Incident runbook — declare, triage, mitigate, retro. |
| `docs/runbooks/ON_CALL.md` | On-call expectations — alert routing, response SLOs, handoff. |

### 2.7 Security

| File | Purpose |
|---|---|
| `docs/security/THREAT_MODEL.md` | Threat model for a node and a constellation. STRIDE pass over the gate path. |
| `docs/security/SECRETS.md` | How secrets are stored, rotated, and referenced. No embedding. |
| `docs/security/BOUNDARIES.md` | Trust boundaries: who can call what, intra-platform credentials, tenant isolation. |

### 2.8 Observability

| File | Purpose |
|---|---|
| `docs/observability/TRACING.md` | Trace propagation walkthrough. W3C `traceparent` rules. |
| `docs/observability/METRICS.md` | Required SLI catalog with names, labels, units, semantics. |
| `docs/observability/LOGGING.md` | Structured logging rules; what is loggable; PII redaction. |

---

## 3. Directory READMEs (12 files)

Each README states purpose, what lives there, what does NOT live there, governing contracts, quality gates, and conventions. L9_META header on every file.

| File | Directory it documents |
|---|---|
| `engine/README.md` | Execution surface — handlers and domain logic. |
| `chassis/README.md` | Transport authority — gate, dispatch, middleware. |
| `scripts/README.md` | Operational scripts — boot, deploy, audit. |
| `tools/README.md` | Auditors, reviewers, contract verifiers. |
| `domains/README.md` | Bounded contexts — one slice of capability per directory. |
| `tests/README.md` | Test pyramid — unit, contracts, integration, compliance. |
| `observability/README.md` | OTel, Prometheus, Grafana, Loki configs and dashboards. |
| `deploy/README.md` | Release plumbing — Terraform and deploy scripts. |
| `infrastructure/README.md` | Local Compose stacks and shared container assets. |
| `templates/README.md` | Scaffolding generators for new services and docs. |
| `client/README.md` | The canonical SDK — packet builder, parser, transport client. |
| `.github/README.md` | CI workflows, code owners, dependency policy. |

The repo root `README.md` is **unchanged**.

---

## 4. Conventions enforced by every file in this scaffold

- **L9_META header** on every Markdown (HTML comment) and YAML (YAML comment) file: `l9_schema`, `origin`, `engine`, `layer`, `tags`, `owner`, `status`.
- **No emojis** in any artifact.
- **Frontier-lab voice** — terse, declarative, no filler.
- **Contracts referenced, not duplicated.** Docs link to YAML; YAML is the source of truth.
- **Canonical names**: `TransportPacket`, `gate`, `orchestrator`, `runtime`. Lowercase `snake_case` for actions and packet types.
- **Banned**: PacketEnvelope as canonical, peer-URL knowledge in workers, FastAPI imports in `engine/`, `eval`/`exec`/`pickle.loads`/`yaml.load`.

---

## 5. Next steps

1. **Open a PR** from `chore/l9-docs-contracts-scaffold` into `main`.
2. **Wire contract verification into CI**:
   - Ensure `.github/workflows/` runs `tools/verify_contracts.py` against `contracts/_schemas/l9_contract_meta.schema.json` for every YAML under `contracts/`.
   - Wire `scripts/validate_contract_alignment.py` into the `contracts` workflow.
3. **Owner sign-offs**:
   - Platform owner: contracts pack and architecture docs.
   - Security owner: `docs/security/`, `contracts/governance/`.
   - SRE owner: `docs/runbooks/`, `docs/observability/`, `observability/`.
4. **Migrate handlers** to declare against canonical `transport_packet.contract.yaml`. Track via `docs/contracts/BREAKING_CHANGE_POLICY.md`.
5. **Deprecate legacy** `contracts/*.yaml` (top-level) per `migration_from_packet_envelope.contract.yaml`. Set a removal date in the next ADR.
6. **Backfill domain contracts** under `contracts/domains/<name>/<action>.contract.yaml` for every action exposed by `domains/`.
7. **Update CODEOWNERS** to require platform review on `contracts/` and `docs/adr/`.

---

## 6. What this branch does not change

- No engine, chassis, tools, or CI source is modified.
- No legacy contract file is removed.
- No production behaviour changes — this branch is documentation and contracts only.
- No tests are added or removed.

The expected next branch is `feat/contracts-ci-wiring` to attach `tools/verify_contracts.py` and `scripts/validate_contract_alignment.py` to required CI checks.
