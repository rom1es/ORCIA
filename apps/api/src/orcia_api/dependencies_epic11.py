"""FastAPI `Depends` providers for Epic 11 services (`AD-19` Composition Root)."""

from __future__ import annotations

from fastapi import Request

from orcia_core.orchestration.workspace_governance_and_rebaser import (
    WorkspaceGovernanceAndArtifactRoutingService,
)


def get_workspace_governance_and_rebaser_service(
    request: Request,
) -> WorkspaceGovernanceAndArtifactRoutingService:
    """Return `WorkspaceGovernanceAndArtifactRoutingService` (`Story 11.1`)."""
    svc: WorkspaceGovernanceAndArtifactRoutingService | None = getattr(
        request.app.state, "workspace_governance_and_rebaser_service", None
    )
    if svc is None:
        svc = WorkspaceGovernanceAndArtifactRoutingService()
        request.app.state.workspace_governance_and_rebaser_service = svc
    return svc
