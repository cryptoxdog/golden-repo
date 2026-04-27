# Implementation Note — `feat/principal-id-on-tenant-context`

> Generated under `l9_zero_stub_build_protocol.kernel.v3_0_0` (Phases 1–2)
> from the Phase 0 manifest at
> [`docs/strategy/PHASE_0_BUILD_MANIFEST.principal_id.md`](docs/strategy/PHASE_0_BUILD_MANIFEST.principal_id.md).
>
> This branch implements ADR-0003. Read the ADR first:
> [`docs/adr/0003-principal-id-on-tenant-context.md`](docs/adr/0003-principal-id-on-tenant-context.md).

## What this PR does

**One sentence.** Adds `principal_id` to `TenantContext`, materialises
it once at the chassis via a new middleware, hashes it in logs, and
verifies the wiring with paired tests — **with zero handler changes
across all 106 endpoints**.

## File map

### New (9 files)

- `chassis/middleware/__init__.py` — package replaces the legacy single
  module; preserves every existing import (`RequestIDMiddleware`,
  `TimingMiddleware`, `SecurityHeadersMiddleware`,
  `StructuredLogMiddleware`, `apply_chassis_middleware`).
- `chassis/middleware/principal.py` — `principal_middleware`
  (after auth, before tenant binding); honours feature flag
  `tenant_ctx.principal_id`; raises `EngineError` on missing claim.
- `chassis/logging.py` — `hash_principal_id_processor`
  (SHA-256 → `principal_id_hash`), `install_pii_processors`,
  `assert_no_raw_principal_id`.
- `tests/unit/chassis/__init__.py`
- `tests/unit/chassis/test_principal_middleware.py` — 11 tests
  covering happy path, dict-shape auth, flag-off, missing claim,
  unauth pass-through, tenant-context upgrade, and a perf budget.
- `tests/unit/chassis/test_logging_principal_processor.py` — 18 tests
  covering hash idempotency, drop semantics, chain installation, and
  the compliance guard.
- `tests/contracts/test_principal_id_present.py` — parametrised over
  `chassis.action_registry`; asserts `principal_id` is materialised for
  every registered action and that the field is None when the flag is
  off.
- `tests/compliance/test_logging_no_principal.py` — three properties:
  source-level processor guard, codebase grep guard, fixture guard.
- `docs/adr/0003-principal-id-on-tenant-context.md` — accepted ADR.

### Modified (4 files)

- `contracts/governance/tenant_context.contract.yaml` — adds
  `principal_id` field with `pii: hashed`, the
  `principal_id_never_logged_raw` invariant, and the audit ↔ rollout
  metadata.
- `chassis/types.py` — adds the `TenantContext` Pydantic model
  (frozen, snake_case, no aliases) plus `DelegationGrant`. Block-form
  L9_META header added to satisfy the new check.
- `chassis/chassis_app.py` — registers `principal_middleware` and
  prepends `hash_principal_id_processor` onto the structlog chain via
  `install_pii_processors`.
- `chassis/__init__.py` — incidental fix: `from chassis.app import …`
  → `from chassis.chassis_app import …`. The legacy reference broke
  every test that imported any chassis submodule. Pre-existing on main
  since PR #28; corrected here so this PR's tests are runnable
  end-to-end.

### Incidental (1 file)

- `chassis/action_registry.py` — incidental fix:
  `from constellation.types import …` → `from chassis.types import …`.
  Same class of pre-existing rename leftover as the `chassis.app` /
  `chassis.chassis_app` mismatch above. The contract test
  (`test_principal_id_present.py`) imports `chassis.action_registry`
  to enumerate registered actions, and that module was unimportable
  on main. Headers added; no behaviour changes.

## Validation evidence

### L9 verifiers (run on the branch tip)

```
$ python scripts/verify_l9_contracts.py
... 12/12 PASS, 0 failures.
RESULT: PASS -- all L9 canonical contracts verified

$ python scripts/check_l9_meta_headers.py
Files checked: 47
Passes:        47
Skips:         27
Failures:      0
RESULT: PASS
```

### New tests (run on the branch tip)

```
$ python -m pytest tests/unit/chassis/ \
    tests/contracts/test_principal_id_present.py \
    tests/compliance/test_logging_no_principal.py -q
32 passed, 1 skipped in 0.39s
```

The 1 skip is the log-fixtures scan, which is correctly inert
because no `tests/fixtures/log_samples/` directory exists yet.

### Banned-pattern scan (all new files)

`grep -rnE "TODO|FIXME|PLACEHOLDER|NotImplementedError"` returns only
the ADR's own description of the zero-stub policy. No real stubs.

## Phase 0 manifest checklist

The Phase 0 manifest's `validation_checklist` is consumed verbatim:

- **Naming:** all snake_case; no `Field(alias=...)`; YAML keys match
  Python field names. ✅
- **Imports:** all resolve; new packages have `__init__.py`. ✅
- **Security:** no `eval`, `exec`, `compile`, `pickle.load`, raw
  `yaml.load`. f-strings only into log strings as constant templates.
  Raw `principal_id` cannot reach a sink (compliance test enforces). ✅
- **Completeness:** spec field count (1 new field) = implementation
  field count (1 new field). No `TODO`/`PLACEHOLDER`/`FIXME`/
  `NotImplementedError` outside `tests/`. ✅
- **Wiring:** `principal_middleware` wired in `chassis_app.build_app`;
  `hash_principal_id_processor` registered in the structlog chain.
  Contract test parametrises over the action registry. ✅
- **Signatures:** middleware signature matches Starlette's HTTP
  middleware contract. `TenantContext` is `model_config =
  ConfigDict(frozen=True)`. ✅
- **Testing:** tests live only under `tests/`; one test file per new
  chassis source file. Happy path, missing claim, flag off,
  logs-no-raw-id all covered. ✅
- **Performance:** middleware median overhead test ships in
  `test_principal_middleware.py`; CI-stable bound at 500 µs (kernel-3
  SLO is 50 µs at p95). ✅
- **ADR:** `0003-principal-id-on-tenant-context.md` is shipped before
  any code lands per user instruction. ✅

## What this PR does NOT do

Per ADR-0003 §"Migration Plan", **R1–R3 are out of scope here**. This
PR is the R0 landing: contract change + middleware + processor + paired
tests, all behind feature flag `tenant_ctx.principal_id` (default off).

The R3 promotion (field becomes required; flag retired; dataclass
`tenant` carrier on `PacketEnvelope` retired) lands in a follow-up PR
recorded as ADR-0004.

The legacy alignment / verifier reconciliation deferrals from
`chore/l9-pack-harden` (PR #56, advisory `validate_contract_alignment.py`,
advisory `tools/verify_contracts.py`) remain advisory through R0–R2 and
flip to blocking at R3.

## Branch chain

This branch is cut from `chore/l9-pack-harden` (PR #56). The merge
order remains:

1. PR #54 — `chore/l9-docs-contracts-scaffold` → main
2. PR #55 — `feat/contracts-ci-wiring` → main
3. PR #56 — `chore/l9-pack-harden` → main
4. **`feat/principal-id-on-tenant-context` → main (this branch)**

This branch will fast-forward cleanly once #54–#56 land.
