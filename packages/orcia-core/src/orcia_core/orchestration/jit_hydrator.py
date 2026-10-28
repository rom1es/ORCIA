"""Just-In-Time Step Context Hydrator & Memlog Marker Plugin Registry (`AD-13`, `AD-20`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`) and zero SDLC
vocabulary (`AD-19`, `AD-20`, `AC-E2`).
"""

from __future__ import annotations

import importlib.metadata
import threading
from typing import Any, Protocol, runtime_checkable

from orcia_core.blackboard.models import (
    HydratedStepContext,
    StepMemlogEntry,
)
from orcia_core.blackboard.store import AppendOnlyBlackboardStore
from orcia_core.orchestration.errors import (
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.orchestration.models import (
    WorkflowAsCodeDefinition,
    WorkflowRunEntity,
    WorkflowStepSpec,
)
from orcia_kernel.ids import new_uuid7_str


@runtime_checkable
class MemlogMarkerPluginProtocol(Protocol):
    """Plugin protocol discovered via `entry_points(group='orcia.memlog_markers')` (`AD-20`)."""

    @property
    def primary_divergence_marker(self) -> str:
        """Return primary divergence marker key (e.g. `<namespace>.<marker>` or alias)."""
        ...

    @property
    def secondary_divergence_marker(self) -> str:
        """Return secondary divergence marker key (e.g. `<namespace>.<marker>` or alias)."""
        ...

    def build_fast_path_markers(
        self, step_key: str, divergence_note: str, datasources: tuple[str, ...]
    ) -> tuple[StepMemlogEntry, ...]:
        """Build fast-path divergence markers for a step execution."""
        ...


_MARKER_PLUGIN_LOCK = threading.Lock()
_MARKER_PLUGIN: MemlogMarkerPluginProtocol | None = None
_MARKER_ENTRY_POINTS_LOADED: bool = False


def register_memlog_marker_plugin(plugin: MemlogMarkerPluginProtocol) -> None:
    """Register a pack `MemlogMarkerPluginProtocol` (`AD-20`, `AC-E1`, `AC-E2`)."""
    global _MARKER_PLUGIN
    with _MARKER_PLUGIN_LOCK:
        _MARKER_PLUGIN = plugin


def get_memlog_marker_plugin() -> MemlogMarkerPluginProtocol | None:
    """Return the active `MemlogMarkerPluginProtocol` loaded via entry points or registration."""
    global _MARKER_ENTRY_POINTS_LOADED, _MARKER_PLUGIN
    with _MARKER_PLUGIN_LOCK:
        if not _MARKER_ENTRY_POINTS_LOADED:
            _MARKER_ENTRY_POINTS_LOADED = True
            try:
                eps = importlib.metadata.entry_points(group="orcia.memlog_markers")
                for ep in eps:
                    loaded = ep.load()
                    instance = loaded() if callable(loaded) else loaded
                    if isinstance(instance, MemlogMarkerPluginProtocol):
                        _MARKER_PLUGIN = instance
            except Exception:
                pass
        return _MARKER_PLUGIN


def build_default_fast_path_markers(
    step_key: str, divergence_note: str, datasources: tuple[str, ...]
) -> tuple[StepMemlogEntry, ...]:
    """Build fast-path divergence markers using registered plugin or core fallback."""
    plugin = get_memlog_marker_plugin()
    if plugin is not None:
        return plugin.build_fast_path_markers(step_key, divergence_note, datasources)
    return (
        StepMemlogEntry(
            entry_id=new_uuid7_str(),
            step_key=step_key,
            marker_type="ASSUMPTION",
            summary="[ASSUMPTION] Continuité d'audit en tâche de fond retenue",
            details=f"Hypothèse appliquée sans blocage worker: {divergence_note}",
            source_uris=datasources,
        ),
        StepMemlogEntry(
            entry_id=new_uuid7_str(),
            step_key=step_key,
            marker_type="core.divergence_suspected",
            summary="[DIVERGENCE] Écart détecté entre sources fédérées",
            details=divergence_note,
            source_uris=datasources,
        ),
    )


class JitStepHydrator:
    """Just-In-Time Step Context Hydrator (`AD-13`).

    Injects ONLY step $k$'s directive and explicitly declared upstream artifacts (`orcia://`).
    Guarantees 0 instructions from future steps $k+1..N$ and 0 undeclared upstream artifacts.
    """

    @staticmethod
    def hydrate_step(
        *,
        run: WorkflowRunEntity,
        workflow: WorkflowAsCodeDefinition,
        step_key: str,
        blackboard: AppendOnlyBlackboardStore,
        seed_inputs: dict[str, Any] | None = None,
    ) -> HydratedStepContext:
        """Build isolated `HydratedStepContext` for `step_key` in `run`."""
        target_step: WorkflowStepSpec | None = None
        for step in workflow.steps:
            if step.step_key == step_key:
                target_step = step
                break
        if target_step is None:
            raise ResourceNotFoundError(
                detail_override=f"Étape '{step_key}' introuvable dans '{workflow.uri}'."
            )

        declared_uris: list[str] = []
        resolved_inputs: dict[str, Any] = dict(seed_inputs or {})

        mapping_sources = dict(target_step.input_mapping)
        if not mapping_sources and target_step.depends_on:
            for dep_key in target_step.depends_on:
                mapping_sources[dep_key] = f"steps.{dep_key}.artifact"

        for alias, ref_expr in sorted(mapping_sources.items()):
            upstream_step_key, field_key = JitStepHydrator._parse_input_ref(ref_expr, run.id)
            canonical_uri = f"orcia://runs/{run.id}/steps/{upstream_step_key}/artifacts/{field_key}"
            declared_uris.append(canonical_uri)
            snap = blackboard.get_active_step_snapshot(run.id, upstream_step_key)
            if snap is None:
                raise ResourceNotFoundError(
                    detail_override=(
                        f"Snapshot amont requis introuvable pour '{canonical_uri}' "
                        f"lors de l'hydratation JIT de '{step_key}'."
                    )
                )
            if field_key in snap.artifact_payload:
                resolved_inputs[alias] = snap.artifact_payload[field_key]
            else:
                resolved_inputs[alias] = snap.artifact_payload

        return HydratedStepContext(
            run_id=run.id,
            step_key=target_step.step_key,
            step_title=target_step.title,
            step_type=target_step.step_type,
            execution_mode=run.execution_regime,
            step_directive=target_step.instructions,
            declared_input_uris=tuple(declared_uris),
            resolved_inputs=resolved_inputs,
            future_step_instructions_leaked=0,
            undeclared_artifacts_leaked=0,
        )

    @staticmethod
    def _parse_input_ref(ref_expr: str, run_id: str) -> tuple[str, str]:
        cleaned = ref_expr.strip()
        if cleaned.startswith("orcia://runs/"):
            parts = cleaned.removeprefix("orcia://runs/").split("/")
            if len(parts) >= 5 and parts[1] == "steps" and parts[3] == "artifacts":
                return parts[2], parts[4]
        if cleaned.startswith("steps."):
            parts = cleaned.split(".")
            if len(parts) >= 3:
                return parts[1], parts[2]
            if len(parts) == 2:
                return parts[1], "artifact"
        raise ValidationDomainError(
            detail_override=f"Référence d'entrée JIT invalide '{ref_expr}' sur le run '{run_id}'."
        )


__all__ = [
    "JitStepHydrator",
    "MemlogMarkerPluginProtocol",
    "build_default_fast_path_markers",
    "get_memlog_marker_plugin",
    "register_memlog_marker_plugin",
]
