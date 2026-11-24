"""Workflow policy plugin protocol & entry-point registry (`AD-20`, `AC-E1`, `AC-E2`)."""

from __future__ import annotations

import importlib.metadata
import threading
from typing import Any, Protocol, runtime_checkable

from orcia_core.orchestration.models import (
    WorkflowStepSpec,
    WorkflowValidationFinding,
)


@runtime_checkable
class WorkflowPolicyPluginProtocol(Protocol):
    """Plugin protocol discovered via `entry_points(group='orcia.workflow_policies')` (`AD-20`)."""

    @property
    def policy_keys(self) -> tuple[str, ...]:
        """Return namespaced policy keys handled by this plugin."""
        ...

    @property
    def allowed_modes(self) -> tuple[str, ...]:
        """Return additional workflow engineering modes registered by this plugin."""
        ...

    def normalize_raw_step(
        self, raw_step: dict[str, Any]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Extract pack-specific step tags and policies from a raw step dict."""
        ...

    def validate_dag(
        self,
        parsed_steps: list[WorkflowStepSpec],
        steps_by_key: dict[str, WorkflowStepSpec],
        mode: str,
        findings: list[WorkflowValidationFinding],
    ) -> None:
        """Validate pack-specific DAG policies and append findings if violated."""
        ...


_POLICY_LOCK = threading.Lock()
_WORKFLOW_POLICY_PLUGINS: dict[str, WorkflowPolicyPluginProtocol] = {}
_REGISTERED_POLICY_KEYS: set[str] = {
    "core.standard",
    "core.require_human_gate",
}
_REGISTERED_WORKFLOW_MODES: set[str] = {"standard"}
_POLICY_ENTRY_POINTS_LOADED: bool = False


def register_workflow_policy_plugin(plugin_id: str, plugin: WorkflowPolicyPluginProtocol) -> None:
    """Register a `WorkflowPolicyPluginProtocol` instance (`AD-20`, `AC-E1`, `AC-E2`)."""
    with _POLICY_LOCK:
        _WORKFLOW_POLICY_PLUGINS[plugin_id] = plugin
        for p_key in plugin.policy_keys:
            _REGISTERED_POLICY_KEYS.add(p_key.strip())
        for m_key in plugin.allowed_modes:
            _REGISTERED_WORKFLOW_MODES.add(m_key.strip())


def _ensure_policy_entry_points_loaded() -> None:
    global _POLICY_ENTRY_POINTS_LOADED
    with _POLICY_LOCK:
        if _POLICY_ENTRY_POINTS_LOADED:
            return
        _POLICY_ENTRY_POINTS_LOADED = True
    try:
        eps = importlib.metadata.entry_points(group="orcia.workflow_policies")
        for ep in eps:
            loaded = ep.load()
            instance = loaded() if callable(loaded) else loaded
            if isinstance(instance, WorkflowPolicyPluginProtocol):
                register_workflow_policy_plugin(ep.name, instance)
    except Exception:  # noqa: S110 - optional third-party pack entrypoint discovery
        pass


def get_workflow_policy_plugins() -> tuple[WorkflowPolicyPluginProtocol, ...]:
    """Return all registered workflow policy plugins."""
    _ensure_policy_entry_points_loaded()
    with _POLICY_LOCK:
        return tuple(_WORKFLOW_POLICY_PLUGINS.values())


def is_registered_workflow_policy(policy_key: str) -> bool:
    """Return True if `policy_key` is registered by Core or an installed pack (`AC-E2`)."""
    _ensure_policy_entry_points_loaded()
    with _POLICY_LOCK:
        return policy_key.strip() in _REGISTERED_POLICY_KEYS


def get_valid_workflow_modes() -> frozenset[str]:
    """Return valid workflow engineering modes registered by Core and installed packs."""
    _ensure_policy_entry_points_loaded()
    with _POLICY_LOCK:
        return frozenset(_REGISTERED_WORKFLOW_MODES)


__all__ = [
    "WorkflowPolicyPluginProtocol",
    "get_valid_workflow_modes",
    "get_workflow_policy_plugins",
    "is_registered_workflow_policy",
    "register_workflow_policy_plugin",
]
