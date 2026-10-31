"""FastAPI `Depends` providers for Epic 11 services (`AD-19` Composition Root)."""

from __future__ import annotations

from fastapi import Request

from orcia_core.orchestration.dna_starlark_and_glossary_lifecycle import (
    DnaStarlarkAndGlossaryLifecycleService,
)
from orcia_core.orchestration.pack_builder_processes import (
    PackBuilderSystemService,
)
from orcia_core.orchestration.remote_test_bench_and_mcp_exposure import (
    RemoteServiceTestBenchAndGovernedMcpService,
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


def get_remote_test_bench_and_mcp_service(
    request: Request,
) -> RemoteServiceTestBenchAndGovernedMcpService:
    """Return `RemoteServiceTestBenchAndGovernedMcpService` (`Story 11.3`)."""
    svc: RemoteServiceTestBenchAndGovernedMcpService | None = getattr(
        request.app.state, "remote_test_bench_and_mcp_service", None
    )
    if svc is None:
        svc = RemoteServiceTestBenchAndGovernedMcpService()
        request.app.state.remote_test_bench_and_mcp_service = svc
    return svc


def get_pack_builder_system_service(
    request: Request,
) -> PackBuilderSystemService:
    """Return `PackBuilderSystemService` (`Story 11.4`)."""
    svc: PackBuilderSystemService | None = getattr(
        request.app.state, "pack_builder_system_service", None
    )
    if svc is None:
        svc = PackBuilderSystemService()
        request.app.state.pack_builder_system_service = svc
    return svc
