"""Pydantic v2 schemas for Datasource Webhooks & Staleness Reconciliation (`Story 18.2`).

Transports HTTP requests and responses exclusively inside `apps/api` (`AD-19`).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DatasourceWebhookIngressRequest(BaseModel):
    """Payload for `POST /api/v1/webhooks/datasources/{datasource_id}`."""

    model_config = ConfigDict(extra="allow")

    delivery_key: str = Field(..., min_length=1, max_length=128)
    provider_event: str = Field(default="push", max_length=64)
    remote_fingerprint_sha256: str = Field(..., min_length=1, max_length=64)
    commit_message: str | None = Field(default=None, max_length=500)
    ref: str | None = Field(default=None, max_length=128)
    payload_preview: dict[str, Any] | None = None


class DatasourceWebhookIngressResponse(BaseModel):
    """Response for `POST /api/v1/webhooks/datasources/{datasource_id}`."""

    model_config = ConfigDict(extra="forbid")

    accepted: bool
    outcome: str
    delivery_key: str
    datasource_id: str
    outbox_published: bool
    trace_id: str


class ReconcileWorkspaceStalenessItem(BaseModel):
    """Evaluation summary for a single datasource during 24h staleness reconciliation."""

    model_config = ConfigDict(extra="forbid")

    datasource_id: str
    alias: str
    freshness_status: str
    outcome: str
    elapsed_hours: float
    delta_sync_needed: bool
    probed_fingerprint: str | None = None


class ReconcileWorkspaceStalenessResponse(BaseModel):
    """Response for `POST /api/v1/workspaces/{workspace_id}/datasources/reconcile-staleness`."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    evaluated_count: int
    stale_count: int
    synced_count: int
    results: list[ReconcileWorkspaceStalenessItem]
    trace_id: str
