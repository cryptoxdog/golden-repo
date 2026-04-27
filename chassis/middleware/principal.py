# --- L9_META ---
# l9_schema: 1
# origin: chassis
# engine: "*"
# layer: [api, security]
# tags: [chassis, middleware, principal_id, identity, security, pii, engine-agnostic]
# owner: platform
# status: active
# --- /L9_META ---
"""chassis/middleware/principal — principal_id materialisation middleware.

Position in the chassis middleware chain (see ``chassis/chassis_app.py``):

    request
       │
       ▼
    auth (BearerAuthMiddleware)
       │     ┌──────────────────────────────────────────┐
       ▼     │ this module                              │
    principal_middleware  ◄── runs HERE: after auth,    │
       │                       before tenant binding    │
       ▼                                                │
    tenant binding (extracts tenant_context onto state) │
       │                                                │
       ▼     └──────────────────────────────────────────┘
    handler (one of the 106 registered actions)

Behaviour:

* Reads the verified principal claim from
  ``request.state.auth_principal`` (or ``request.state.auth.sub``;
  whichever the auth middleware set).
* Honours feature flag ``tenant_ctx.principal_id`` via
  ``engine.features.is_enabled``. When the flag is **off**, sets the
  field to ``None`` and continues (R0 rollout posture).
* When the flag is **on** and the auth context is present:
    - if the claim is missing, raises
      ``EngineError(action="<unknown>", tenant=..., detail="missing principal claim",
      client_message="unauthorized")``;
    - otherwise stores the canonical principal_id on
      ``request.state.principal_id`` and on
      ``request.state.tenant_context`` (if present) via
      ``TenantContext.with_principal_id``.

The middleware never serialises the raw value to logs; that is enforced
by ``chassis/logging.py:hash_principal_id_processor``.

Performance budget: ≤ 50 µs at p95 (kernel-3 contract 17). Verified by
``tests/unit/chassis/test_principal_middleware.py``.

See ADR-0003 for the full rationale and rollout plan.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable, Optional

from starlette.requests import Request
from starlette.responses import Response

# These two are the ONLY engine-side imports in this module:
#   - EngineError is the canonical error type (engine/core/errors.py).
#   - is_enabled is the feature-flag read surface (engine/features.py).
# Both are read-only at request time and contain no business logic.
from engine.core.errors import EngineError
from engine.features import feature_flags

from chassis.types import TenantContext

logger = logging.getLogger(__name__)

# Feature flag name. Owned by `engine/features.json`.
FEATURE_FLAG = "tenant_ctx.principal_id"


def _read_principal_claim(request: Request) -> Optional[str]:
    """Pull the verified principal claim from the auth state.

    Looked up in this order, first non-empty wins:

    1. ``request.state.auth_principal`` — the canonical key set by
       ``chassis/auth/auth.py``. New code uses this.
    2. ``request.state.auth.sub`` — legacy key kept for code that
       predates ADR-0003.
    3. ``request.state.auth.principal`` — alternate legacy key.

    Returns ``None`` when no auth state has been attached to the
    request (e.g. unauthenticated endpoints like ``/v1/health``).
    """
    direct = getattr(request.state, "auth_principal", None)
    if isinstance(direct, str) and direct:
        return direct

    auth_obj = getattr(request.state, "auth", None)
    if auth_obj is None:
        return None

    # Support both attribute access (object) and key access (dict).
    if hasattr(auth_obj, "sub"):
        sub = getattr(auth_obj, "sub", None)
        if isinstance(sub, str) and sub:
            return sub
    if hasattr(auth_obj, "principal"):
        principal = getattr(auth_obj, "principal", None)
        if isinstance(principal, str) and principal:
            return principal
    if isinstance(auth_obj, dict):
        for key in ("sub", "principal", "principal_id"):
            value = auth_obj.get(key)
            if isinstance(value, str) and value:
                return value

    return None


def _is_authenticated(request: Request) -> bool:
    """Return True if the auth middleware ran and attached state."""
    return (
        getattr(request.state, "auth_principal", None) is not None
        or getattr(request.state, "auth", None) is not None
    )


def _tenant_id_for_error(request: Request) -> str:
    """Best-effort tenant id for the EngineError envelope.

    The tenant-extraction middleware runs *after* this one, so
    ``request.state.tenant_context`` may not exist yet. We fall back to
    headers used by the resolver in ``contracts/governance/tenant_context.contract.yaml``.
    """
    ctx: Optional[TenantContext] = getattr(request.state, "tenant_context", None)
    if isinstance(ctx, TenantContext):
        return ctx.org_id
    for header in ("x-domain-key", "x-tenant-key"):
        value = request.headers.get(header)
        if value:
            return value
    return "unknown"


async def principal_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Materialise ``principal_id`` once per request.

    See module docstring for behaviour and ADR-0003 for rationale.
    """
    flag_on = feature_flags.is_enabled(FEATURE_FLAG)

    # Endpoints reached without going through auth (e.g. /healthz) are
    # passed through with principal_id=None regardless of flag state.
    if not _is_authenticated(request):
        request.state.principal_id = None
        return await call_next(request)

    claim = _read_principal_claim(request)

    if not flag_on:
        # R0 rollout posture: flag off → field is None; warn once per
        # request that the materialiser was a no-op so observability can
        # see the rollout state.
        request.state.principal_id = None
        logger.debug(
            "principal_middleware: feature flag '%s' is off; principal_id=None",
            FEATURE_FLAG,
        )
        return await call_next(request)

    if claim is None:
        # Flag is on AND we have an auth context but no principal claim.
        # That is an inconsistent auth state. Refuse the request.
        raise EngineError(
            action="<unknown>",
            tenant=_tenant_id_for_error(request),
            client_message="unauthorized",
            detail="missing principal claim",
        )

    request.state.principal_id = claim

    # If the tenant-extraction middleware has *already* attached a
    # TenantContext (e.g. during a re-entrant call), upgrade it in place
    # via the immutable ``with_principal_id`` helper. The downstream
    # tenant middleware reads this field if present; otherwise it reads
    # ``request.state.principal_id`` and constructs the TenantContext.
    ctx: Optional[TenantContext] = getattr(request.state, "tenant_context", None)
    if isinstance(ctx, TenantContext) and ctx.principal_id is None:
        request.state.tenant_context = ctx.with_principal_id(claim)

    return await call_next(request)
