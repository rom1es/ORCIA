"""Workspace Governance, DNA Starlark, Test Bench, Pack Builder & Surgical Explorer (`AD-19`)."""

from __future__ import annotations

from fastapi import Request

from orcia_api.dependencies.core_and_lifespan import get_auth_service
from orcia_connectors.surgical import SurgicalContextExplorer
from orcia_core.kernel.errors import OrciaDomainError
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
from orcia_core.ports.surgical_explorer_port import SurgicalExplorerPort


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
    """Return `PackBuilderSystemService` wired to `request.app.state.session_maker` when present."""
    svc: PackBuilderSystemService | None = getattr(
        request.app.state, "pack_builder_system_service", None
    )
    if svc is None:
        session_maker = getattr(request.app.state, "session_maker", None)
        svc = PackBuilderSystemService(session_factory=session_maker)
        request.app.state.pack_builder_system_service = svc
    return svc


def get_help_generation_and_attachment_service(
    request: Request,
) -> HelpGenerationAndHotAttachmentService:
    """Return `HelpGenerationAndHotAttachmentService` wired to `request.app.state.session_maker`."""
    svc: HelpGenerationAndHotAttachmentService | None = getattr(
        request.app.state, "help_generation_and_attachment_service", None
    )
    if svc is None:
        session_maker = getattr(request.app.state, "session_maker", None)
        svc = HelpGenerationAndHotAttachmentService(session_factory=session_maker)
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


def get_surgical_explorer_service(request: Request) -> SurgicalExplorerPort:
    """FastAPI `Depends` provider returning `SurgicalContextExplorer` wired to RBAC/ACL."""
    svc: SurgicalExplorerPort | None = getattr(request.app.state, "surgical_explorer_service", None)
    if svc is not None:
        return svc

    auth_service = get_auth_service(request)
    evaluator = auth_service.evaluator

    def _authorize_read_source(
        uri: str, workspace_id: str | None, actor_id: str | None
    ) -> tuple[bool, str | None]:
        if not actor_id:
            return True, None
        try:
            user = auth_service.get_user_by_id(actor_id)
        except OrciaDomainError:
            return True, None

        if user.platform_role == "OBSERVER":
            return False, "orcia://permissions/request-read-source?reason=observer-role"

        acl = evaluator.get_catalog_acl_by_uri(uri)
        if acl is None and uri.startswith("catalog://"):
            res_id = uri.removeprefix("catalog://").strip("/")
            acl = evaluator.get_primary_catalog_acl(res_id)

        if acl is not None:
            try:
                effective, _ = evaluator.evaluate_catalog_resource(
                    user,
                    acl.resource_id,
                    workspace_id=workspace_id,
                    require_read_source=False,
                )
            except OrciaDomainError:
                return False, f"jira://IAM/PERM-READ-SOURCE-{acl.resource_id}"
            if effective.source_masked:
                return False, f"jira://IAM/PERM-READ-SOURCE-{acl.resource_id}"

        if workspace_id is not None:
            ws = evaluator.get_workspace(workspace_id)
            if ws is not None:
                ws_access = evaluator.resolve_workspace_access(user, ws.id)
                if ws_access is None or ws_access.access_mode == "READ_ONLY_OBSERVER":
                    return (
                        False,
                        f"orcia://permissions/request-read-source?workspace={workspace_id}",
                    )
        return True, None

    def _resolve_virtual_resource(uri: str, _workspace_id: str | None) -> str | None:
        acl = evaluator.get_catalog_acl_by_uri(uri)
        if acl is None and uri.startswith("catalog://"):
            res_id = uri.removeprefix("catalog://").strip("/")
            acl = evaluator.get_primary_catalog_acl(res_id)
        if acl is not None and acl.system_prompt_secret:
            return acl.system_prompt_secret
        return None

    explorer = SurgicalContextExplorer(
        read_source_authorizer=_authorize_read_source,
        virtual_resource_resolver=_resolve_virtual_resource,
    )
    request.app.state.surgical_explorer_service = explorer
    return explorer
