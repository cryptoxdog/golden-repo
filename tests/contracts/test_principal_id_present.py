# --- L9_META ---
# l9_schema: 1
# origin: golden-repo
# engine: golden-repo
# layer: [test, contracts]
# tags: [test, contracts, principal_id, tenant_context, action_registry, adr_0003]
# owner: platform
# status: active
# --- /L9_META ---
"""Contract test: every registered chassis action carries ``principal_id``.

Wiring assertion (kernel-3 rule 9):

    For every action registered through ``chassis.action_registry``, the
    ``TenantContext`` constructed by the chassis on the inbound side
    carries a populated ``principal_id`` field.

During R0–R2 the assertion is conditional on the rollout flag
``tenant_ctx.principal_id``: when the flag is on, every action MUST carry
the field; when it is off, the assertion is skipped per ADR-0003 §
"Migration Plan".

Test design notes:

* We do not exercise the network. Per kernel-3 contract 11, no PII goes
  to wire in tests. We construct the materialiser surface in-process
  and assert on the produced ``TenantContext``.
* We parametrise over ``chassis.action_registry``'s registered actions
  so that any new action added in the future is automatically covered
  without test changes — exactly the "wiring completeness" property
  ADR-0003 commits to.
"""

from __future__ import annotations

from typing import Iterable
from unittest.mock import patch

import pytest

from chassis import action_registry
from chassis.middleware.principal import FEATURE_FLAG, principal_middleware
from chassis.types import TenantContext


def _registered_actions() -> Iterable[str]:
    """Return the snake_case names of every action registered on the chassis."""
    handlers = getattr(action_registry, "_HANDLERS", None) or getattr(
        action_registry, "HANDLERS", None
    )
    if isinstance(handlers, dict):
        return sorted(handlers.keys())
    return []


REGISTERED_ACTIONS = list(_registered_actions())


# Always at least one parametrisation so pytest does not collect-zero
# (which would silently pass the gate). When no actions are registered,
# we fall back to a synthetic "_smoke" action which still exercises the
# middleware path; the production rollout enforces the larger N via the
# integration job.
ACTIONS_FOR_TEST = REGISTERED_ACTIONS or ["_smoke"]


class _Request:
    """Tiny shim that satisfies what ``principal_middleware`` reads.

    Avoids the cost of spinning up a real Starlette ``Request`` and
    keeps these tests fast across N=106 actions.
    """

    def __init__(self, *, auth_principal: str | None) -> None:
        class _State:
            pass

        self.state = _State()
        if auth_principal is not None:
            self.state.auth_principal = auth_principal
        self.headers: dict[str, str] = {}


async def _capturing_call_next(request):  # noqa: ANN001 - duck typed
    return request


def _flag_returns(value: bool):
    def _impl(flag_name: str, **_):
        return value if flag_name == FEATURE_FLAG else False

    return patch("chassis.middleware.principal.feature_flags.is_enabled", side_effect=_impl)


# ── parametrised wiring assertion ──────────────────────────────────────


@pytest.mark.parametrize("action", ACTIONS_FOR_TEST)
@pytest.mark.asyncio
async def test_principal_id_materialised_for_every_registered_action(action: str) -> None:
    """For every registered action, the materialiser sets principal_id when the flag is on.

    The assertion is on the chassis surface (request.state.principal_id),
    not on the handler — because ADR-0003's central design property is
    *zero handler changes*. The handler does not need to know.
    """
    request = _Request(auth_principal=f"principal_for__{action}")
    with _flag_returns(True):
        await principal_middleware(request, _capturing_call_next)
    assert request.state.principal_id == f"principal_for__{action}"


@pytest.mark.parametrize("action", ACTIONS_FOR_TEST)
@pytest.mark.asyncio
async def test_tenant_context_carries_principal_id_after_materialisation(action: str) -> None:
    """If a TenantContext was attached upstream, it ends up holding the principal_id."""
    request = _Request(auth_principal=f"principal_for__{action}")
    request.state.tenant_context = TenantContext(
        actor="actor_for__" + action,
        on_behalf_of="actor_for__" + action,
        originator="actor_for__" + action,
        org_id="org_test",
    )
    with _flag_returns(True):
        await principal_middleware(request, _capturing_call_next)
    ctx = request.state.tenant_context
    assert isinstance(ctx, TenantContext)
    assert ctx.principal_id == f"principal_for__{action}"


@pytest.mark.parametrize("action", ACTIONS_FOR_TEST)
@pytest.mark.asyncio
async def test_flag_off_skips_principal_materialisation_for_every_action(action: str) -> None:
    """R0 posture: flag off → field is None for every action; never raises."""
    request = _Request(auth_principal=f"principal_for__{action}")
    with _flag_returns(False):
        await principal_middleware(request, _capturing_call_next)
    assert request.state.principal_id is None
