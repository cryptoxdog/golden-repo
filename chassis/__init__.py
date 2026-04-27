"""
--- L9_META ---
l9_schema: 1
origin: chassis
engine: "*"
layer: [api]
tags: [chassis, engine-agnostic]
owner: platform-team
status: active
--- /L9_META ---

L9 Chassis — Engine-Agnostic Integration Layer.

Bridges the HTTP boundary to any L9 constellation engine
via the LifecycleHook + action router pattern.
"""

from chassis.actions import execute_action, register_handler, register_handlers
# ADR-0003 incidental fix: the chassis package init referenced ``chassis.app``
# but the FastAPI factory module was renamed to ``chassis.chassis_app`` in PR
# #28 without updating the package root. Tests that touch any chassis
# submodule (e.g. ``chassis.logging``) were unimportable as a result. We
# correct the reference and keep the public API names (``create_app``,
# ``LifecycleHook``) unchanged.
from chassis.chassis_app import LifecycleHook, create_app
from chassis.errors import (
    AuthorizationError,
    ChassisError,
    ExecutionError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from chassis.health import HealthAggregator

__all__ = [
    # App factory
    "create_app",
    "LifecycleHook",
    # Action routing
    "execute_action",
    "register_handler",
    "register_handlers",
    # Health
    "HealthAggregator",
    # Errors
    "ChassisError",
    "ValidationError",
    "NotFoundError",
    "AuthorizationError",
    "RateLimitError",
    "ExecutionError",
]
