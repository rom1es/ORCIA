"""SDLC Memlog Marker Plugin (`sdlc.bug_code_suspected`, `sdlc.doc_obsolete_suspected`, `AD-20`)."""

from __future__ import annotations

from orcia_core.blackboard.models import StepMemlogEntry
from orcia_core.orchestration.engine import (
    MemlogMarkerPluginProtocol,
    register_memlog_marker_plugin,
)
from orcia_kernel.enums import register_memlog_marker
from orcia_kernel.ids import new_uuid7_str

SDLC_BUG_CODE_MARKER = "sdlc.bug_code_suspected"
SDLC_DOC_OBSOLETE_MARKER = "sdlc.doc_obsolete_suspected"


class SdlcMemlogMarkerPlugin(MemlogMarkerPluginProtocol):
    """Registers `sdlc.*` memlog markers and legacy aliases (`AD-20`)."""

    @property
    def primary_divergence_marker(self) -> str:
        return SDLC_BUG_CODE_MARKER

    @property
    def secondary_divergence_marker(self) -> str:
        return SDLC_DOC_OBSOLETE_MARKER

    def build_fast_path_markers(
        self, step_key: str, divergence_note: str, datasources: tuple[str, ...]
    ) -> tuple[StepMemlogEntry, ...]:
        """Build fast-path divergence markers for SDLC runs (`UJ-10`)."""
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
                marker_type="BUG_CODE_SUSPECTED",
                summary="[BUG_CODE_SUSPECTED] Écart d'implémentation détecté dans le code",
                details=divergence_note,
                source_uris=datasources,
            ),
            StepMemlogEntry(
                entry_id=new_uuid7_str(),
                step_key=step_key,
                marker_type="DOC_OBSOLETE_SUSPECTED",
                summary="[DOC_OBSOLETE_SUSPECTED] Spécification Confluence possiblement obsolète",
                details=divergence_note,
                source_uris=datasources,
            ),
        )


def create_sdlc_memlog_marker_plugin() -> SdlcMemlogMarkerPlugin:
    register_memlog_marker(SDLC_BUG_CODE_MARKER, legacy_aliases=("BUG_CODE_SUSPECTED",))
    register_memlog_marker(SDLC_DOC_OBSOLETE_MARKER, legacy_aliases=("DOC_OBSOLETE_SUSPECTED",))
    plugin = SdlcMemlogMarkerPlugin()
    register_memlog_marker_plugin(plugin)
    return plugin
