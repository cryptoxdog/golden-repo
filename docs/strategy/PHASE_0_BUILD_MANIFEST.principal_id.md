<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, strategy, build-manifest]
tags: [L9_TEMPLATE, build_manifest, phase_0, principal_id, middleware]
owner: platform
status: active
/L9_META -->

# Phase 0 — BUILD_MANIFEST.md
## Feature: `tenant_context.principal_id` propagation

> Generated under `l9_zero_stub_build_protocol.kernel.v3_0_0`, Phase 0.
> This manifest is the single contract for the implementation PR. The
> implementation phases (1–6) consume this manifest verbatim. No file appears
> in the implementation that is absent from this manifest. No file in this
> manifest is omitted from the implementation.

---

## 1. file_tree

```
chassis/
├── middleware/
│   ├── __init__.py                              # NEW
│   └── principal.py                             # NEW
├── auth/
│   └── (existing — read-only in this PR)
├── logging.py                                   # MODIFIED — add principal_id hashing processor
├── chassis_app.py                               # MODIFIED — register principal middleware in gate path
└── types.py                                     # MODIFIED — extend TenantContext

contracts/
└── governance/
    └── tenant_context.contract.yaml             # MODIFIED — add principal_id field

tests/
├── unit/
│   └── chassis/
│       ├── __init__.py                          # NEW (if absent)
│       ├── test_principal_middleware.py         # NEW
│       └── test_logging_principal_processor.py  # NEW
├── contracts/
│   └── test_principal_id_present.py             # NEW
└── compliance/
    └── test_logging_no_principal.py             # NEW

docs/
├── strategy/
│   ├── PRINCIPAL_ID_PROPAGATION.md              # already shipped (Action 2)
│   └── PHASE_0_BUILD_MANIFEST.principal_id.md   # this file
└── adr/
    └── 0003-principal-id-on-tenant-context.md   # NEW
```

**Counts:** 9 new files · 4 modified files · 13 total touchpoints.

---

## 2. public_signatures

Every public surface defined here matches `L9_CONTRACT_SPECIFICATIONS` style:
snake_case, full type hints, async where I/O is involved.

### `chassis/types.py` (modified)

```python
class TenantContext(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)

    tenant_id: str
    principal_id: str | None = None
    delegation_chain: list[DelegationGrant] = pydantic.Field(default_factory=list)
```

`principal_id` is `Optional` for the duration of rollout phase R0–R2. Phase
R3 (post-flag-flip) flips this to required and ships a follow-up migration
contract.

### `chassis/middleware/principal.py` (new)

```python
async def principal_middleware(
    request: starlette.requests.Request,
    call_next: typing.Callable[[starlette.requests.Request], typing.Awaitable[starlette.responses.Response]],
) -> starlette.responses.Response: ...
```

Behaviour:
- Runs **after** `chassis/auth/` middleware, **before** tenant binding.
- Reads the verified principal claim from `request.state.auth_principal`.
- Constructs/derives the `principal_id` (canonical form, snake_case).
- Sets `request.state.tenant_context.principal_id`.
- Raises `EngineError(action="<unknown>", tenant=..., detail="missing principal claim", client_message="unauthorized")` when the auth context is present but the principal claim is missing.
- Honours feature flag `tenant_ctx.principal_id` per `engine/features.json` semantics; when `off`, sets the field to `None` and continues.

### `chassis/chassis_app.py` (modified)

```python
def build_app(*, settings: ChassisSettings) -> fastapi.FastAPI:
    ...
    app.middleware("http")(auth_middleware)
    app.middleware("http")(principal_middleware)   # NEW — between auth and tenant
    app.middleware("http")(tenant_middleware)
    ...
```

### `chassis/logging.py` (modified)

```python
def hash_principal_id_processor(
    logger: typing.Any,
    method_name: str,
    event_dict: dict[str, typing.Any],
) -> dict[str, typing.Any]: ...
```

Behaviour:
- If `event_dict` contains `principal_id`, replace it with `principal_id_hash` (SHA-256, hex).
- Idempotent — running twice on the same record produces the same output.
- Registered into the structlog processor chain by `chassis_app.build_app`.

### `contracts/governance/tenant_context.contract.yaml` (modified)

```yaml
fields:
  ...
  principal_id:
    type: string
    required: false        # phase R0–R2; flips to true in R3
    semantics: verified caller identity, hashed in logs, never serialised raw to sinks
    pii: hashed
```

---

## 3. handler_registrations

**Zero handler-side changes.** This is the central design property of the
strategy memo: 106 endpoints inherit `principal_id` from the chassis without
touching any `register_handler('<action>', handle_<action>)` call site.

The existing chassis registration surface is unchanged.

---

## 4. domain_yaml_list

This feature is cross-cutting (chassis-only) and ships **no domain YAML
changes**. Domains continue to consume `tenant_context.principal_id` through
the typed accessor without spec edits.

---

## 5. packet_type_list

No new packet_types are introduced. The change extends the existing
`tenant_context` block of every packet — packet_type registry remains
untouched.

The migration window for receiving packets that lack `principal_id` is
governed by the existing
[`contracts/transport/migration_from_packet_envelope.contract.yaml`](../../contracts/transport/migration_from_packet_envelope.contract.yaml)
pattern (acceptance window then rejection).

---

## 6. external_deps

| Dependency | Status | Notes |
|---|---|---|
| `pydantic >= 2.6` | already pinned | required for `TenantContext` extension |
| `starlette` | already pinned | middleware stack |
| `structlog` | already pinned | log processor surface |
| `pytest`, `pytest-asyncio` | already pinned | tests |

**No new third-party dependencies.**

---

## 7. external_utils

The implementation reuses these existing internals (no rewrite):

| Util | Path | Use |
|---|---|---|
| `chassis.errors.EngineError` | `chassis/errors.py` | error path on missing claim |
| `chassis.auth.verify_jwt` | `chassis/auth/jwt.py` | upstream claim source |
| `chassis.types.TenantContext` | `chassis/types.py` | extended in this PR |
| `engine.features.is_enabled` | `engine/features.py` | feature flag read |
| `chassis.pii.hash_token` | `chassis/pii.py` | SHA-256 hashing helper |

If any util above is missing on `main`, kernel 3 edge case applies — create
the util plus its `tests/unit/test_<util>.py` in the same PR, never stub.

---

## 8. validation_checklist

Phase 0 ships only this manifest. The implementation PR must satisfy every
item below before it can ship under kernel 3:

### Naming
- [ ] All Pydantic field names snake_case.
- [ ] YAML keys in `tenant_context.contract.yaml` match Python field names.
- [ ] No `Field(alias=...)` introduced anywhere.

### Imports
- [ ] Every new import resolves to an existing file.
- [ ] All `__init__.py` for new directories present.
- [ ] No "planned-only" imports.

### Security
- [ ] No `eval`, `exec`, `compile`, `pickle.load`, `yaml.load` (without SafeLoader).
- [ ] No f-string interpolation into Cypher / SQL / log strings.
- [ ] `principal_id` raw value never appears in any log record after the processor runs.
- [ ] No banned-pattern match anywhere in the new code (CRITICAL or HIGH).

### Completeness
- [ ] Spec field count = implementation field count.
- [ ] No `TODO`, `PLACEHOLDER`, `FIXME`, `NotImplementedError` outside `tests/`.
- [ ] Unknown / missing claim raises; never silently passes.
- [ ] Anything not implemented is in `DEFERRED.md` with a concrete owner and ticket id.

### Wiring
- [ ] `principal_middleware` registered in `chassis_app.build_app`.
- [ ] `hash_principal_id_processor` registered in the structlog chain.
- [ ] `TenantContext.principal_id` populated end-to-end from request to packet.
- [ ] All 106 actions covered by `tests/contracts/test_principal_id_present.py` (parametrised over `chassis.action_registry`).

### Signatures
- [ ] Middleware signature matches Starlette's HTTP middleware contract.
- [ ] Pydantic model frozen with `model_config = ConfigDict(frozen=True)`.
- [ ] Test fixtures use the production builders, not raw dicts.

### Testing
- [ ] Test exists per new chassis file (kernel 3, rule 10).
- [ ] Tests live only under `tests/`.
- [ ] At least one happy-path test, one missing-claim test, one
  feature-flag-off test, one logs-no-raw-id test.
- [ ] `pytest tests/contracts/test_principal_id_present.py -q` parametrises
  over **every** registered action and is green.

### Performance
- [ ] Middleware adds ≤ 50 µs at p95 over a 5-minute synthetic load.
- [ ] No regression in `transport_request_duration_seconds` p95 vs baseline.

### ADR
- [ ] `docs/adr/0003-principal-id-on-tenant-context.md` written and reviewed.

---

## Pre-submission gate (kernel 3)

Before opening the implementation PR, the engineer must confirm in the PR
body:

1. ✅ Manifest above is the single source of truth and has not been
   silently expanded.
2. ✅ All 20 contracts respected (boundary, packet, security, architecture,
   testing, observability).
3. ✅ All 10 rules respected.
4. ✅ Phase 0 manifest matches Phase 6 final file tree exactly — no orphan
   files, no missing files.
5. ✅ Banned-pattern scanner clean.
6. ✅ Pre-submission checklist fully ticked.

Anything failing any of the above triggers the kernel's stop condition:
revert, reduce scope, or move the deferred item to `DEFERRED.md` — never
stub.
