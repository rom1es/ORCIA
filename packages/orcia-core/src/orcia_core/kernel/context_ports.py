"""Hexagonal Ports for Context Sources, Vector Store, Indexer Regimes & Assistant Templates.

Implements `DEC-CTX-01` (`AD-8`, `AD-20`) and `Story 3.3`:
- `ContextSourcePort` & `ContextSliceRecord` (JSON, CAS, KB documents, Blackboard, Catalog,
  Permissions — never raw local Markdown file paths).
- `VectorStorePort` & `VectorSearchHitRecord` (`halfvec(1024)` + BM25 RRF abstraction).
- Dynamic `orcia.indexers` regime registry (`register_indexer_regime`,
  `get_registered_indexer_regime`, `list_registered_indexer_regimes`).
- Dynamic `orcia.assistant_templates` registry (`AssistantWorkflowTemplatePort`) so domain
  packs (`orcia-pack-sdlc`, Finance, etc.) supply workflow blueprints without any domain
  vocabulary inside `orcia-core`.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from typing import Any, Literal, Protocol, runtime_checkable

ContextSliceKind = Literal[
    "JSON_PAYLOAD",
    "CAS_BLOB",
    "KB_DOCUMENT",
    "BLACKBOARD_SNAPSHOT",
    "CATALOG_ITEM",
    "PERMISSION_POLICY",
]


@dataclass(frozen=True, slots=True)
class ContextSliceRecord:
    """Normalized context slice injected into `AssistantHarness` (`DEC-CTX-01`)."""

    slice_id: str
    source_uri: str
    source_kind: ContextSliceKind
    content_sha256: str
    title: str
    structured_payload: dict[str, Any] = field(default_factory=dict)
    text_excerpt: str = ""
    is_stale: bool = False
    stale_warning_marker: str | None = None


@runtime_checkable
class ContextSourcePort(Protocol):
    """Port abstracting structured context retrieval (JSON, CAS, KB, Blackboard, Catalog)."""

    def fetch_context_slices(
        self,
        *,
        workspace_id: str,
        query: str,
        uris: tuple[str, ...] = (),
        include_sources: tuple[str, ...] = ("catalog", "blackboard", "permissions", "cas"),
    ) -> tuple[ContextSliceRecord, ...]:
        """Retrieve structured context slices for `workspace_id` without local file reads."""
        ...


@dataclass(frozen=True, slots=True)
class VectorSearchHitRecord:
    """Normalized vector + lexical RRF search hit returned by `VectorStorePort` (`DEC-CTX-01`)."""

    chunk_key: str
    document_key: str
    source_uri: str
    contextual_header: str
    injected_content: str
    rrf_score: float
    is_stale: bool = False
    stale_warning_marker: str | None = None


@runtime_checkable
class VectorStorePort(Protocol):
    """Port abstracting hybrid vector + BM25 search (`DEC-CTX-01`, `AD-8`)."""

    def hybrid_search(
        self,
        *,
        workspace_id: str,
        query_text: str,
        allowed_datasource_aliases: frozenset[str],
        top_k: int = 5,
    ) -> tuple[VectorSearchHitRecord, ...]:
        """Execute hybrid vector + BM25 search scoped to `workspace_id` and allowed aliases."""
        ...


@dataclass(frozen=True, slots=True)
class IndexerRegimeDescriptor:
    """Descriptor for an indexing regime registered via `orcia.indexers` (`DEC-CTX-01`)."""

    regime_key: str
    display_name: str
    pack_name: str
    handler: Any = None


_INDEXER_LOCK = threading.RLock()
_INDEXER_REGISTRY: dict[str, IndexerRegimeDescriptor] = {
    "DOC_PARENT_CHILD": IndexerRegimeDescriptor(
        regime_key="DOC_PARENT_CHILD",
        display_name="Parent-Child Document Indexer",
        pack_name="orcia-core",
    ),
    "DB_DDL_ONLY": IndexerRegimeDescriptor(
        regime_key="DB_DDL_ONLY",
        display_name="Database DDL Schema Indexer (Zero Transactional Rows)",
        pack_name="orcia-core",
    ),
}
_INDEXER_ENTRY_POINTS_LOADED = False


def register_indexer_regime(descriptor: IndexerRegimeDescriptor) -> None:
    """Register an indexing regime descriptor (`DEC-CTX-01`)."""
    norm = descriptor.regime_key.strip().upper()
    if not norm:
        raise ValueError("Indexer regime_key must not be empty.")
    with _INDEXER_LOCK:
        _INDEXER_REGISTRY[norm] = descriptor


def _ensure_indexer_entry_points_loaded() -> None:
    global _INDEXER_ENTRY_POINTS_LOADED
    with _INDEXER_LOCK:
        if _INDEXER_ENTRY_POINTS_LOADED:
            return
        _INDEXER_ENTRY_POINTS_LOADED = True
    try:
        for ep in entry_points(group="orcia.indexers"):
            loaded = ep.load()
            instance = loaded() if callable(loaded) else loaded
            if isinstance(instance, IndexerRegimeDescriptor):
                register_indexer_regime(instance)
            else:
                regime_key = ep.name.strip().upper()
                register_indexer_regime(
                    IndexerRegimeDescriptor(
                        regime_key=regime_key,
                        display_name=f"Plugin Indexer ({ep.name})",
                        pack_name=getattr(ep.dist, "name", "plugin") if ep.dist else "plugin",
                        handler=instance,
                    )
                )
    except Exception:
        pass


def get_registered_indexer_regime(regime_key: str) -> IndexerRegimeDescriptor | None:
    """Return the registered `IndexerRegimeDescriptor` for `regime_key` (`DEC-CTX-01`)."""
    _ensure_indexer_entry_points_loaded()
    norm = regime_key.strip().upper()
    with _INDEXER_LOCK:
        return _INDEXER_REGISTRY.get(norm)


def list_registered_indexer_regimes() -> frozenset[str]:
    """Return all registered indexing regime keys (`DEC-CTX-01`)."""
    _ensure_indexer_entry_points_loaded()
    with _INDEXER_LOCK:
        return frozenset(_INDEXER_REGISTRY.keys())


@dataclass(frozen=True, slots=True)
class AssistantWorkflowBlueprint:
    """Workflow blueprint returned by an `AssistantWorkflowTemplatePort` plugin (`Story 3.3`)."""

    template_key: str
    workflow_uri: str
    title: str
    description: str
    default_execution_regime: Literal[
        "INTERACTIVE_COACHING",
        "BACKGROUND_FAST_PATH",
        "AUTONOMOUS_CONTRACT",
    ]
    manifest_yaml: str
    steps_summary: tuple[dict[str, Any], ...]


@runtime_checkable
class AssistantWorkflowTemplatePort(Protocol):
    """Plugin port supplying domain-specific workflow blueprints to `AssistantAgentService`."""

    @property
    def template_key(self) -> str: ...

    def matches_intent(self, prompt_lower: str) -> bool: ...

    def build_blueprint(
        self,
        *,
        workspace_id: str,
        modification_instruction: str | None = None,
    ) -> AssistantWorkflowBlueprint: ...


_ASSISTANT_TEMPLATE_LOCK = threading.RLock()
_ASSISTANT_TEMPLATE_REGISTRY: dict[str, AssistantWorkflowTemplatePort] = {}
_ASSISTANT_TEMPLATE_EP_LOADED = False


def register_assistant_template(template: AssistantWorkflowTemplatePort) -> None:
    """Register an `AssistantWorkflowTemplatePort` blueprint provider (`Story 3.3`)."""
    key = template.template_key.strip().lower()
    if not key:
        raise ValueError("AssistantWorkflowTemplatePort.template_key must not be empty.")
    with _ASSISTANT_TEMPLATE_LOCK:
        _ASSISTANT_TEMPLATE_REGISTRY[key] = template


def unregister_assistant_template(template_key: str) -> None:
    """Remove an `AssistantWorkflowTemplatePort` from the registry."""
    key = template_key.strip().lower()
    with _ASSISTANT_TEMPLATE_LOCK:
        _ASSISTANT_TEMPLATE_REGISTRY.pop(key, None)


def _ensure_assistant_template_entry_points_loaded() -> None:
    global _ASSISTANT_TEMPLATE_EP_LOADED
    with _ASSISTANT_TEMPLATE_LOCK:
        if _ASSISTANT_TEMPLATE_EP_LOADED:
            return
        _ASSISTANT_TEMPLATE_EP_LOADED = True
    try:
        for ep in entry_points(group="orcia.assistant_templates"):
            loaded = ep.load()
            instance = loaded() if callable(loaded) else loaded
            if isinstance(instance, AssistantWorkflowTemplatePort):
                register_assistant_template(instance)
    except Exception:
        pass


def list_registered_assistant_templates() -> tuple[AssistantWorkflowTemplatePort, ...]:
    """Return all registered `AssistantWorkflowTemplatePort` providers (`Story 3.3`)."""
    _ensure_assistant_template_entry_points_loaded()
    with _ASSISTANT_TEMPLATE_LOCK:
        return tuple(_ASSISTANT_TEMPLATE_REGISTRY.values())
