"""Workspace Governance, DNA Starlark, Test Bench & Pack Builder providers (`AD-19`)."""

from __future__ import annotations

from fastapi import Request

from orcia_core.orchestration.agents_and_skills_manager import (
    AgentsAndSkillsManagementService,
)
from orcia_core.orchestration.dna_starlark_and_glossary_lifecycle import (
    DnaStarlarkAndGlossaryLifecycleService,
)
from orcia_core.orchestration.help_generator_and_validator import (
    HelpGenerationAndHotAttachmentService,
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
    """Return `WorkspaceGovernanceAndArtifactRoutingService`."""
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
    """Return `DnaStarlarkAndGlossaryLifecycleService`."""
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
    """Return `RemoteServiceTestBenchAndGovernedMcpService`."""
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
    """Return `PackBuilderSystemService`."""
    svc: PackBuilderSystemService | None = getattr(
        request.app.state, "pack_builder_system_service", None
    )
    if svc is None:
        svc = PackBuilderSystemService()
        request.app.state.pack_builder_system_service = svc
    return svc


def get_help_generation_and_attachment_service(
    request: Request,
) -> HelpGenerationAndHotAttachmentService:
    """Return `HelpGenerationAndHotAttachmentService`."""
    svc: HelpGenerationAndHotAttachmentService | None = getattr(
        request.app.state, "help_generation_and_attachment_service", None
    )
    if svc is None:
        svc = HelpGenerationAndHotAttachmentService()
        request.app.state.help_generation_and_attachment_service = svc
    return svc


def get_agents_and_skills_service(
    request: Request,
) -> AgentsAndSkillsManagementService:
    """Return `AgentsAndSkillsManagementService`."""
    svc: AgentsAndSkillsManagementService | None = getattr(
        request.app.state, "agents_and_skills_service", None
    )
    if svc is None:
        llm = getattr(request.app.state, "llm_gateway", None)
        svc = AgentsAndSkillsManagementService(llm_gateway=llm)
        request.app.state.agents_and_skills_service = svc
    return svc
