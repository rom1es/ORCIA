"""Pure domain evaluator for Workspace Pack Slots, 422 Readiness & Run Pinning (`Story 31.4`).

Zero framework or database driver imports (`AD-19`).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, Field

from orcia_core.packs.errors import PackSlotUnboundError
from orcia_core.packs.models import PackSlotSpec, PackSlotTargetKind


class SlotBindingInput(BaseModel):
    """Requested connector slot binding submitted by a Workspace Lead."""

    slot_key: str = Field(..., min_length=1, max_length=128)
    target_kind: PackSlotTargetKind
    target_id: str | None = Field(default=None, max_length=128)
    connector_scheme: str | None = Field(default=None, max_length=32)


class EffectiveSlotBindingView(BaseModel):
    """Hydrated slot binding state including live target integrity (`ON DELETE SET NULL`)."""

    id: str = ""
    workspace_id: str
    pack_bundle_id: str = ""
    pack_slug: str
    slot_key: str
    target_kind: PackSlotTargetKind = PackSlotTargetKind.UNBOUND
    target_id: str | None = None
    bound_datasource_id: str | None = None
    bound_connector_id: str | None = None
    connector_scheme: str | None = None
    bound_by: str = ""
    bound_at_iso: str = ""
    is_effective_bound: bool = False
    target_uri: str | None = None
    target_display_name: str | None = None
    target_enabled: bool = True


class ResolvedPackSlotEntry(BaseModel):
    """Pinned slot resolution record frozen inside `run_lock_manifests.manifest_jsonb`."""

    pack_slug: str
    slot_key: str
    scheme: str
    required: bool
    status: Literal["bound", "optional_unbound"]
    target_kind: PackSlotTargetKind
    target_id: str | None = None
    target_uri: str | None = None
    connector_scheme: str | None = None


class PinnedPackManifestEntry(BaseModel):
    """Immutable active pack snapshot frozen inside `run_lock_manifests.manifest_jsonb`."""

    pack_bundle_id: str
    pack_slug: str
    version: str
    archive_sha256: str
    priority_order: int
    resolved_pack_slots: list[ResolvedPackSlotEntry] = Field(default_factory=list)


class WorkspacePackView(BaseModel):
    """Workspace-visible pack bundle enriched with activation, slot bindings & readiness."""

    bundle_id: str
    pack_id: str
    slug: str
    name: str
    version: str
    bundle_kind: str
    scope_type: str
    scope_id: str
    status: str
    archive_sha256: str
    cas_object_key: str | None = None
    description: str = ""
    author: str | None = None
    is_active: bool = False
    priority_order: int | None = None
    activated_at_iso: str | None = None
    activated_by: str | None = None
    declared_slots: list[PackSlotSpec] = Field(default_factory=list)
    slot_bindings: list[EffectiveSlotBindingView] = Field(default_factory=list)
    missing_slots: list[str] = Field(default_factory=list)
    readiness_ok: bool = True


def is_binding_effectively_bound(binding: EffectiveSlotBindingView | None) -> bool:
    """Return True iff `binding` points to an active, non-detached target."""
    if binding is None or binding.target_kind == PackSlotTargetKind.UNBOUND:
        return False
    if binding.target_kind == PackSlotTargetKind.WORKSPACE_DATASOURCE:
        return bool(binding.bound_datasource_id and binding.is_effective_bound)
    if binding.target_kind == PackSlotTargetKind.ENTERPRISE_CONNECTOR:
        return bool(
            binding.bound_connector_id and binding.target_enabled and binding.is_effective_bound
        )
    return binding.target_kind == PackSlotTargetKind.INTERNAL


def is_binding_compatible_with_slot(
    binding: EffectiveSlotBindingView,
    slot: PackSlotSpec,
) -> bool:
    """Return True if an existing binding's target kind and scheme match `slot.scheme` (`P2-2`)."""
    slot_scheme = (slot.scheme or "").strip().lower()
    if slot_scheme == "internal":
        return binding.target_kind == PackSlotTargetKind.INTERNAL
    if slot_scheme and slot_scheme not in ("*", "any"):
        if binding.target_kind == PackSlotTargetKind.INTERNAL:
            return False
        if binding.connector_scheme and binding.connector_scheme.strip().lower() != slot_scheme:
            return False
    return True


def evaluate_pack_slot_readiness(
    declared_slots: Sequence[PackSlotSpec],
    bindings_by_key: Mapping[str, EffectiveSlotBindingView],
    *,
    pack_slug: str,
    raise_on_missing: bool = False,
    instance: str | None = None,
) -> tuple[list[ResolvedPackSlotEntry], list[str]]:
    """Evaluate pack declared slots against workspace bindings (`R4`, `R5`, `A2`)."""
    resolved: list[ResolvedPackSlotEntry] = []
    missing_required: list[str] = []

    for slot in declared_slots:
        binding = bindings_by_key.get(slot.slot_key)
        if (
            is_binding_effectively_bound(binding)
            and binding is not None
            and is_binding_compatible_with_slot(binding, slot)
        ):
            resolved.append(
                ResolvedPackSlotEntry(
                    pack_slug=pack_slug,
                    slot_key=slot.slot_key,
                    scheme=slot.scheme,
                    required=slot.required,
                    status="bound",
                    target_kind=binding.target_kind,
                    target_id=(
                        binding.bound_datasource_id
                        or binding.bound_connector_id
                        or binding.target_id
                    ),
                    target_uri=binding.target_uri,
                    connector_scheme=binding.connector_scheme or slot.scheme,
                )
            )
            continue

        if slot.required:
            missing_required.append(slot.slot_key)
            continue

        resolved.append(
            ResolvedPackSlotEntry(
                pack_slug=pack_slug,
                slot_key=slot.slot_key,
                scheme=slot.scheme,
                required=False,
                status="optional_unbound",
                target_kind=PackSlotTargetKind.UNBOUND,
                target_id=None,
                target_uri=None,
                connector_scheme=slot.scheme,
            )
        )

    if raise_on_missing and missing_required:
        raise PackSlotUnboundError(
            pack_slug=pack_slug,
            missing_slots=missing_required,
            instance=instance,
        )
    return resolved, missing_required


def build_pinned_run_lock_payload(
    *,
    run_id: str,
    workspace_id: str,
    workflow_id: str,
    workflow_slug: str,
    workflow_version: str,
    workflow_sha256: str,
    pinned_packs: Sequence[PinnedPackManifestEntry],
) -> tuple[dict[str, Any], str]:
    """Assemble deterministic JSONB payload and SHA-256 digest for `run_lock_manifests`."""
    flat_slots: list[dict[str, Any]] = [
        slot.model_dump(mode="json") for p in pinned_packs for slot in p.resolved_pack_slots
    ]
    body: dict[str, Any] = {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "workflow_id": workflow_id,
        "workflow_slug": workflow_slug,
        "workflow_version": workflow_version,
        "workflow_sha256": workflow_sha256,
        "pinned_packs": [p.model_dump(mode="json") for p in pinned_packs],
        "resolved_pack_slots": flat_slots,
    }
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False)
    manifest_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    body["manifest_sha256"] = manifest_sha256
    return body, manifest_sha256


def sanitize_workflow_inputs_for_slots(
    inputs: dict[str, Any],
    pinned_packs: Sequence[PinnedPackManifestEntry],
) -> dict[str, Any]:
    """Strip unbound optional `slot://<key>` URIs from workflow run dispatch inputs (`P2-1`)."""
    unbound_keys = {
        slot.slot_key.strip().lower()
        for pack in pinned_packs
        for slot in pack.resolved_pack_slots
        if slot.status == "optional_unbound"
    }
    if not unbound_keys or not inputs:
        return dict(inputs)

    def _is_unbound_uri(val: Any) -> bool:
        if not isinstance(val, str):
            return False
        s = val.strip()
        if not s.lower().startswith("slot://"):
            return False
        key = s[7:].strip().strip("/").lower()
        return key in unbound_keys

    def _clean(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items() if not _is_unbound_uri(v)}
        if isinstance(obj, list):
            return [_clean(item) for item in obj if not _is_unbound_uri(item)]
        return obj

    cleaned = _clean(inputs)
    return cleaned if isinstance(cleaned, dict) else dict(inputs)


__all__ = [
    "EffectiveSlotBindingView",
    "PinnedPackManifestEntry",
    "ResolvedPackSlotEntry",
    "SlotBindingInput",
    "WorkspacePackView",
    "build_pinned_run_lock_payload",
    "evaluate_pack_slot_readiness",
    "is_binding_compatible_with_slot",
    "is_binding_effectively_bound",
    "sanitize_workflow_inputs_for_slots",
]
