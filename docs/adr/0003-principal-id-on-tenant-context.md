<!-- L9_META
l9_schema: 1
origin: golden-repo
engine: golden-repo
layer: [docs, adr]
tags: [adr, principal_id, tenant_context, chassis, middleware, security, observability, pii]
owner: platform
status: active
/L9_META -->

# ADR-0003 — `principal_id` on `TenantContext`

- **Status:** Accepted
- **Date:** 2026-04-26
- **Deciders:** L9 Platform team
- **Tags:** chassis, security, observability, pii, contracts/governance
- **Supersedes:** _(none)_
- **Superseded-by:** _(pending; ADR-0004 will record the R3 promotion to required)_

## Context

The L9 chassis surfaces 106 HTTP endpoints through a single
`register_action('<action>', handle_<action>)` mechanism. Each endpoint
must, for audit, observability, and authorisation purposes, know the
**verified caller identity** — the `principal_id`. Today, this identity is
derived ad-hoc inside individual handlers from JWT claims, with three
recurring problems:

1. **Inconsistency.** Different handlers extract different shapes from the
   same JWT (raw `sub`, hashed `sub`, email, principal-DN), drifting from
   any single canonical value.
2. **Fragility.** When the auth library or claim key changes, every
   handler that derives identity must be updated; in practice some are
   missed.
3. **PII leakage.** Several handlers log raw identity strings; some sinks
   ingest them as searchable fields. Compliance review (see
   [`docs/strategy/PRINCIPAL_ID_PROPAGATION.md`](../strategy/PRINCIPAL_ID_PROPAGATION.md))
   flags this as a hashing-scheme violation under L9 contract 11.

The forces in play:

- **Architectural authority (kernel 3, contract 1):** identity belongs in
  the chassis boundary, never the engine. Engines must not import auth
  libraries.
- **Wiring completeness (kernel 3, rule 9):** any solution must reach all
  106 endpoints; partial coverage is non-conforming.
- **Zero-stub discipline (kernel 3):** the change ships with paired tests
  in the same response; no `TODO`, `PLACEHOLDER`, `FIXME`, or
  `NotImplementedError` outside `tests/`.
- **PII discipline (kernel 3, contract 11):** raw identity is a hashed
  field at-rest; the full value lives only on the request-scoped object.
- **Existing contract surface:** `contracts/governance/tenant_context.contract.yaml`
  is the single canonical home for tenant-scoped context fields.

## Decision

**Materialise `principal_id` once at the chassis, propagate it via
`TenantContext` on every TransportPacket, and leave all 106 handlers
untouched.**

Specifically:

- Extend `contracts/governance/tenant_context.contract.yaml` to declare a
  new `principal_id: string` field. **Optional** during rollout phases
  R0–R2; **required** at R3 (recorded in a follow-up ADR-0004).
- Introduce `TenantContext` as a frozen Pydantic model in `chassis/types.py`.
  This is the canonical Python shape for the `tenant_context` block of
  every TransportPacket, replacing the existing `Optional[dict]` carrier
  on `PacketEnvelope`. The new model lives alongside the existing
  dataclasses; the dataclass surface is preserved during R0–R2 and
  retired in R3.
- Convert `chassis/middleware.py` into a `chassis/middleware/` package.
  Existing middleware classes (`RequestIDMiddleware`, `TimingMiddleware`,
  `SecurityHeadersMiddleware`, `StructuredLogMiddleware`,
  `apply_chassis_middleware`) move to `chassis/middleware/__init__.py`
  to preserve every existing import site.
- Add **one new chassis middleware** at
  `chassis/middleware/principal.py` that runs **after** authentication
  and **before** tenant binding. It reads the verified principal claim
  from the auth state and sets `request.state.tenant_context.principal_id`.
  When the auth context is present but the principal claim is missing,
  it raises `EngineError(action="<unknown>", tenant=..., detail="missing principal claim", client_message="unauthorized")`.
- Wire `principal_middleware` in `chassis/chassis_app.py` between the
  existing auth middleware and the existing tenant-extraction
  middleware.
- Introduce `chassis/logging.py` with a `hash_principal_id_processor`
  structlog processor that replaces any `principal_id` field on a log
  record with `principal_id_hash` (SHA-256 hex) before the record reaches
  any sink. The processor is idempotent and is registered into the
  structlog chain by `chassis_app.build_app`.
- Honour feature flag `tenant_ctx.principal_id` (read via
  `engine.features.is_enabled`). When the flag is **off**, the middleware
  sets `principal_id=None` and logs a structured warning. When **on**,
  the middleware enforces presence.

This is the **smallest change with the largest reach**: 1 contract field,
1 new middleware module, 1 new logging module, 1 new pydantic model;
**zero handler changes** for any of the 106 endpoints.

The full reasoning under `reasoning_think_strategy.kernel.v1_1` is
archived at
[`docs/strategy/PRINCIPAL_ID_PROPAGATION.md`](../strategy/PRINCIPAL_ID_PROPAGATION.md);
the file-level Phase 0 manifest under
`l9_zero_stub_build_protocol.kernel.v3_0_0` is at
[`docs/strategy/PHASE_0_BUILD_MANIFEST.principal_id.md`](../strategy/PHASE_0_BUILD_MANIFEST.principal_id.md).

## Consequences

### Positive

- **One review surface for 106 endpoints.** Future auditors trace one
  middleware, not 106 ad-hoc derivations.
- **Typed accessor.** Handlers that *want* to read `principal_id` get
  full Pydantic + mypy enforcement; handlers that don't, ignore it.
- **PII discipline by construction.** The structlog processor makes raw
  identity-in-logs structurally impossible after R0; the compliance test
  enforces it.
- **Contract-test enforced wiring.** A parametrised contract test asserts
  every action registered in `chassis.action_registry` carries the field
  on its inbound packet. Any handler added in the future is automatically
  covered.
- **Feature-flagged rollout.** `tenant_ctx.principal_id` lets us land the
  contract change and the middleware in a single PR, then promote
  through staging and canary before flipping the field to required.

### Negative

- **One additional middleware on the request path.** Budget is ≤ 50 µs at
  p95; verified by performance test in the same PR. Total chassis path
  remains within the L9 envelope (`<200 ms p95`, contract 17).
- **Dual model surface during R0–R2.** The dataclass `PacketEnvelope.tenant`
  (Optional[dict]) and the Pydantic `TenantContext` coexist. The chassis
  bridge inflates the dataclass shape into the Pydantic model on ingress
  and deflates on egress. Bridging code is in `chassis/contract_enforcement.py`
  and is exhaustively tested.
- **Migration window for in-flight packets.** During R0–R2, packets without
  `principal_id` are accepted; from R3 onward they are rejected per the
  existing
  [`contracts/transport/migration_from_packet_envelope.contract.yaml`](../../contracts/transport/migration_from_packet_envelope.contract.yaml)
  pattern.

### Neutral / Trade-offs

- **Identity resolution remains in `chassis/auth/`.** This ADR explicitly
  does **not** redesign IdP integration, JWT verification, or
  on-behalf-of delegation. Those are downstream of the middleware and
  belong in ADRs of their own.
- **Engines stay engine-shaped.** No engine package gains an auth import.
- **Logging schema gains `principal_id_hash`.** Downstream observability
  pipelines that index `tenant_context.*` fields gain one new dimension;
  no breaking changes to existing dimensions.

## Alternatives Considered

### Option A — Per-handler refactor

Add a `principal_id` parameter to every handler signature (106 files).

- **Pros:** explicit; zero indirection.
- **Cons:** O(N) effort, O(N) review surface, near-certain partial
  rollout, merge conflicts on every concurrent feature. Violates kernel-3
  rule 9 (wiring completeness) and kernel-1 leverage gate.
- **Rejected** on impact-per-LOC and rollout-coherence grounds.

### Option B — Decorator on each handler

Decorate each handler with `@with_principal` that pulls the verified
identity from the auth library and injects it.

- **Pros:** less ceremonial than Option A.
- **Cons:** still touches 106 import sites; auth library leaks into the
  engine boundary (kernel-3 contract 1 violation); decorator drift
  guarantees identity-shape inconsistency over time.
- **Rejected** on boundary-violation grounds.

### Option C — Chassis middleware on `TenantContext` (this ADR)

One middleware, one contract field, one Pydantic field, one structlog
processor.

- **Pros:** O(1) effort, O(N) coverage; single review surface;
  contract-tested across all 106 actions; engines stay clean.
- **Cons:** introduces dual model surface during R0–R2 (resolved at R3).
- **Accepted.**

## Migration Plan

**Phased rollout, single migration ADR.** Reversibility at every phase.

| Phase | Action | Gate to advance |
|---|---|---|
| **R0** | Land contract change + middleware + logging processor + paired tests, all behind feature flag `tenant_ctx.principal_id=off`. Field is `Optional[str]`. Contract test asserts presence only when the flag is on. | All required CI checks green on `feat/principal-id-on-tenant-context`. |
| **R1** | Flip the flag to `on` in staging. All 106 endpoints now receive `principal_id`. | Integration smoke at `/v1/health` plus 5 representative actions; SLI `principal_id_present_total` matches `transport_request_total` for 24 hours. |
| **R2** | Promote to production behind a 1% canary. | Canary green on `gate_admit_total{decision}` and `principal_id_present_total` for 24 hours; no regression in `transport_request_duration_seconds` p95. |
| **R3** | Make the field required in the contract; drop the feature flag; record promotion in ADR-0004; retire the dataclass `tenant` carrier on `PacketEnvelope`. | Contract test asserts presence on every action (no flag check); R3 migration contract published. |

### Rollback procedure

Each phase has its own rollback path:

- **R0 → revert PR.** Single squash commit; no consumers depend on the
  field while the flag is off.
- **R1 → flip the flag back to off.** Runtime-only; no redeploy needed.
- **R2 → reduce canary to 0%.** Runtime-only; no redeploy needed. If the
  regression is in the middleware itself, also revert.
- **R3 → revert the "required" promotion ADR-0004 and re-introduce the
  flag.** This is the only phase where the rollback is itself a code change.

## References

- **Contracts touched:** `contracts/governance/tenant_context.contract.yaml`
- **Code touched (this ADR's PR):**
  - `chassis/types.py` (extend with `TenantContext` Pydantic model)
  - `chassis/middleware/__init__.py` (NEW; absorbs existing `chassis/middleware.py`)
  - `chassis/middleware/principal.py` (NEW)
  - `chassis/logging.py` (NEW)
  - `chassis/chassis_app.py` (register `principal_middleware`)
- **Tests added:**
  - `tests/unit/chassis/test_principal_middleware.py`
  - `tests/unit/chassis/test_logging_principal_processor.py`
  - `tests/contracts/test_principal_id_present.py`
  - `tests/compliance/test_logging_no_principal.py`
- **Related ADRs:**
  - [ADR-0001 — TransportPacket is canonical](./0001-transport-packet-canonical.md)
  - [ADR-0002 — Gate workflow stateless](./0002-gate-workflow-stateless.md)
  - ADR-0004 — _(pending)_ R3 promotion of `principal_id` to required
- **Strategy:**
  - [`docs/strategy/PRINCIPAL_ID_PROPAGATION.md`](../strategy/PRINCIPAL_ID_PROPAGATION.md)
    — full 8-block reasoning under `reasoning_think_strategy.kernel.v1_1`
  - [`docs/strategy/PHASE_0_BUILD_MANIFEST.principal_id.md`](../strategy/PHASE_0_BUILD_MANIFEST.principal_id.md)
    — Phase 0 file tree, public signatures, validation checklist
- **Kernels in force:**
  - `l9_first_order_thinking_enforcement.kernel.v1`
  - `reasoning_think_strategy.kernel.v1_1`
  - `l9_zero_stub_build_protocol.kernel.v3_0_0`
  - `pack_audit_harden_regenerate.kernel.v1`
- **Authority order:** user_latest_instruction > active_artifact >
  source_files > most_specific_kernel > general_kernels.
