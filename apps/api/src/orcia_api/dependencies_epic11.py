"""FastAPI `Depends` providers for Epic 11 services (`AD-19` Composition Root)."""

from __future__ import annotations

from fastapi import Request

from orcia_core.orchestration.dna_starlark_and_glossary_lifecycle import (
    DnaStarlarkAndGlossaryLifecycleService,
)
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


def get_dna_starlark_and_glossary_service(
    request: Request,
) -> DnaStarlarkAndGlossaryLifecycleService:
    """Return `DnaStarlarkAndGlossaryLifecycleService` (`Story 11.2`)."""
    svc: DnaStarlarkAndGlossaryLifecycleService | None = getattr(
        request.app.state, "dna_starlark_and_glossary_service", None
    )
    if svc is None:
        svc = DnaStarlarkAndGlossaryLifecycleService()
        request.app.state.dna_starlark_and_glossary_service = svc
    return svc
