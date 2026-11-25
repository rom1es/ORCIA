"""Pydantic serializer for domain `WorkspaceAccessSummary` objects."""

from __future__ import annotations

from typing import Literal, cast

from orcia_api.schemas.auth_and_org import WorkspaceDatasourceItem, WorkspaceSummaryItem
from orcia_core.permissions import WorkspaceAccessSummary


def serialize_workspace_summary(item: WorkspaceAccessSummary) -> WorkspaceSummaryItem:
    """Convert domain `WorkspaceAccessSummary` into Pydantic `WorkspaceSummaryItem`."""
    ws = item.workspace
    is_personal = bool(ws.personal_owner_user_id is not None)
    effective_visibility: Literal["STANDARD", "CONFIDENTIAL_RESTRICTED", "PRIVATE_USER"] = (
        "PRIVATE_USER"
        if ws.ui_visibility_mode == "PRIVATE_USER" or is_personal
        else ws.visibility_mode
    )
    raw_phase = str(getattr(ws, "lifecycle_phase", "BUILD") or "BUILD").strip().upper()
    lifecycle_phase: Literal["BUILD", "RUN", "MIGRATION"] = (
        cast(Literal["BUILD", "RUN", "MIGRATION"], raw_phase)
        if raw_phase in ("BUILD", "RUN", "MIGRATION")
        else "BUILD"
    )
    return WorkspaceSummaryItem(
        id=ws.id,
        slug=ws.slug,
        name=ws.name,
        owner_org_unit_id=ws.owner_org_unit_id,
        visibility_mode=effective_visibility,
        lifecycle_phase=lifecycle_phase,
        is_personal=is_personal,
        effective_role=item.effective_role,
        access_mode=item.access_mode,
        access_origin=item.access_origin,
        finops_cost_usd=ws.finops_cost_usd if item.finops_visible else None,
        datasources=[
            WorkspaceDatasourceItem(
                id=ds.id,
                workspace_id=ds.workspace_id,
                alias=ds.alias,
                scheme=ds.scheme,
                uri=ds.uri,
                role=ds.role,
                execution_identity=ds.execution_identity,
                freshness_ttl_days=ds.freshness_ttl_days,
            )
            for ds in ws.datasources
        ],
    )


__all__ = ["serialize_workspace_summary"]
