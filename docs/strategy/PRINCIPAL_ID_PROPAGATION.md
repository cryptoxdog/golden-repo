<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, strategy]
tags: [L9_TEMPLATE, strategy, principal_id, identity, middleware, reasoning_8_block]
owner: platform
status: active
/L9_META -->

# Strategy Memo: `principal_id` propagation across 106 endpoints

> Reasoning produced under `reasoning_think_strategy.kernel.v1_1`.
> The 8 blocks below are the kernel's mandatory structure. They are reasoning,
> not implementation. The corresponding Phase 0 build manifest is at
> [`docs/strategy/PHASE_0_BUILD_MANIFEST.principal_id.md`](./PHASE_0_BUILD_MANIFEST.principal_id.md).

---

## Block 1 — Objective

Deliver a stable, auditable `principal_id` (the verified identity of the
caller) into every handler invocation across all 106 HTTP endpoints, with
**zero handler-side changes** required for adoption and **zero PII in logs**.

Out of scope for this memo: the federated identity resolver, multi-IdP token
exchange, and on-behalf-of delegation deepening (those graduate from
`contracts/governance/delegation_chain.contract.yaml`).

---

## Block 2 — Context

- **Surface area:** 106 endpoints registered through the chassis
  `register_handler('<action>', handle_<action>)` mechanism.
- **Existing identity surface:** `chassis/auth/` resolves a `tenant_context`
  (kernel 3, contract 3). `principal_id` is currently **not** materialised on
  the request — handlers that need it derive it ad-hoc from JWT claims, which
  is fragile, inconsistent, and forks PII handling.
- **Authority order (kernel 3):** `principal_id` belongs in
  `contracts/governance/` and is enforced at the gate (chassis), never the
  engine. Engines must not import auth libraries.
- **Constraints from the active kernels:**
  - **Kernel 3, rule 9 (wiring completeness):** every handler reachable, no
    orphan path. Any solution must hit all 106 or it's incomplete.
  - **Kernel 3, contract 11 (PII):** `principal_id` is treated as PII —
    hashed for logs, full value only inside the request-scoped context.
  - **Kernel 3, contract 6–8 (PacketEnvelope):** `principal_id` rides inside
    `TransportPacket.tenant_context` — never as a query string or header
    leak.
  - **Kernel 1, rabbit-hole gate:** "rebuild auth" is the rabbit hole — the
    answer must be a *propagation* change, not a *resolution* change.

---

## Block 3 — Decomposition

The problem decomposes into five orthogonal sub-questions:

| # | Sub-question | Single best answer (justified below) |
|---|---|---|
| D1 | Where does `principal_id` get materialised? | One chassis middleware, one entry point. |
| D2 | How does it travel to handlers? | Inside `TransportPacket.tenant_context.principal_id`. |
| D3 | How do existing handlers see it without code change? | They don't read it directly — the chassis injects it before dispatch. |
| D4 | How do handlers that *want* it read it? | A typed accessor `tenant_context.principal_id`; mypy enforces the field. |
| D5 | How do we make adoption mandatory across all 106? | Contract test asserts every action has the field on its inbound packet. |

This decomposition reduces 106 individual changes to **one middleware + one
contract field + one contract test**.

---

## Block 4 — Leverage

We are looking for the **smallest change with the largest reach**. Three
candidates ranked by leverage:

| Approach | Surface touched | Risk | Leverage |
|---|---|---|---|
| **A. Per-handler refactor** — add a `principal_id` parameter to every handler | 106 files | High; merge conflicts; partial rollout | Low — linear effort, linear value |
| **B. Decorator on each handler** — `@with_principal` reads JWT and injects | 106 imports | Medium; decorator drift; auth lib bleeds into engine | Medium |
| **C. Chassis middleware that hydrates `tenant_context.principal_id` once at the gate** | 1 middleware + 1 contract field + 1 contract test | Low; single review surface; contract-tested | **High — exactly what kernel 3 contracts 1–4 prescribe** |

**Approach C wins on every kernel-1 gate:**
- *Impact gate:* covers all 106 endpoints in one merge.
- *Effort/coverage:* O(1) effort to O(N) coverage.
- *Dependency gate:* depends only on the existing `auth/` resolver and
  `tenant_context` contract — no new external systems.
- *Rabbit-hole gate:* explicitly does not touch identity resolution.
- *Prompt-quality:* the user's "simplest change" framing maps 1:1 to C.

---

## Block 5 — Strategy

The kernel requires three nested strategy lenses: 5A (mechanism), 5B
(rollout), 5C (verification).

### 5A. Mechanism

1. **Extend the contract.** Add `principal_id` to
   `contracts/governance/tenant_context.contract.yaml`. Required, opaque
   string, non-PII at-rest format (hash). The full value lives only on the
   request-scoped object, never serialised to logs.
2. **One new chassis middleware:** `chassis/middleware/principal.py`.
   Position in the gate execute path: **after** auth verification, **before**
   tenant binding. Reads the verified principal claim from the auth context,
   sets `request.state.tenant_context.principal_id`.
3. **TransportPacket envelope hydration.** The chassis already calls
   `inflate_ingress`; extend it to copy `principal_id` from
   `request.state.tenant_context` onto the packet's `tenant_context` block.
4. **Typed accessor for engines.** `principal_id` is exposed as a typed
   pydantic field on `TenantContext`. mypy --strict will refuse the merge
   if any handler that uses it gets the wrong type.
5. **Logging discipline.** `chassis/logging.py` registers a structlog
   processor that hashes `principal_id` to `principal_id_hash` for emission;
   the raw value is dropped from log records before they reach any sink.

### 5B. Rollout

| Phase | Action | Gate |
|---|---|---|
| R0 | Land the contract change + middleware behind feature flag `tenant_ctx.principal_id=off`. Field is `Optional` for one release. | Contract test only asserts presence when flag is on. |
| R1 | Flip the flag to `on` in staging. All 106 endpoints now receive the field. | Integration smoke at `/v1/health` plus 5 representative actions. |
| R2 | Promote to production behind a 1% canary; monitor `gate_admit_total{decision}` and the new SLI `principal_id_present_total`. | Canary green for 24 hours. |
| R3 | Make the field required in the contract. Drop the feature flag. | Contract test asserts presence on every action. |

### 5C. Verification

- **Unit:** `tests/unit/chassis/test_principal_middleware.py` — middleware
  runs after auth, before tenant; sets the field; raises on missing claim.
- **Contract:** `tests/contracts/test_principal_id_present.py` — for every
  registered action, generate a happy-path packet through the gate and
  assert `tenant_context.principal_id` is set and is a non-empty string.
- **Compliance:** `tests/compliance/test_logging_no_principal.py` — assert
  no log record under `tests/fixtures/log_samples/` contains a raw
  `principal_id`; only `principal_id_hash`.
- **Performance:** middleware adds ≤ 50 µs to the gate path (kernel 3,
  contract 17 — `<200ms p95`).
- **Banned-pattern scan:** must remain clean (kernel 3, banned patterns).

---

## Block 6 — Execution

Single-path execution, no branching:

1. Open issue `feat/tenant-context-principal-id`.
2. Land contract change + middleware on a feature flag (R0). One PR.
3. Land contract test asserting the field's presence on every action. Same
   PR if it stays small; a follow-up PR if it grows the diff above 400 LOC.
4. Wire the structlog processor that hashes the value; add the compliance
   test. Same PR.
5. Flip the flag in staging; observe SLI; promote.
6. Make the field required; drop the flag; close the loop.

The corresponding Phase 0 build manifest (Action 3 of this turn) lists the
exact files to write in the implementation PR.

---

## Block 7 — Synthesis (with kernel addons)

**The simplest change that delivers `principal_id` across 106 endpoints is
one chassis middleware that hydrates `tenant_context.principal_id` on the
TransportPacket inside the existing gate execute path.**

Addon checks:

- **Kernel 1, all 5 silent gates:** PASS — high impact, O(1) effort, low
  dependency, no rabbit-hole, prompt-quality clean.
- **Kernel 3, contract 1:** middleware lives in `chassis/`; engines never
  import auth.
- **Kernel 3, contract 3:** tenant resolution stays at the chassis; this
  change extends the same pattern to `principal_id`.
- **Kernel 3, contract 11:** PII discipline preserved via the hashing
  processor.
- **Kernel 3, rule 9 (wiring):** the contract test enforces 100%
  endpoint coverage.
- **Kernel 3, rule 10:** test ships with the code in the same PR.
- **Pack-audit kernel:** no terminology drift introduced;
  `tenant_context.principal_id` matches the existing snake_case convention.

---

## Block 8 — Sum, Anticipate, Deliver

**Sum.** One middleware, one contract field, one contract test, one
compliance test. Four files of new code. Zero changes to handlers.

**Anticipate.** The two questions that will land next:
1. *Do we backfill `principal_id` on packets that pre-date the change?*
   No — the migration contract pattern (see
   `contracts/transport/migration_from_packet_envelope.contract.yaml`)
   applies. Pre-flag-flip packets carry no `principal_id`; they are accepted
   for one release window then rejected.
2. *Does this affect the orchestrator?* No — orchestrator is a normal node;
   it inherits the field via the same packet envelope.

**Deliver.** Action 3 of this turn — the Phase 0 BUILD_MANIFEST.md — lists
every file to write, every public signature, and every test, ready for the
implementation PR.
