"""Day-0 System Bootstrap Workflows & Autonomous Team/Workspace Onboarding Router (Story 1.5)."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query, Request

from orcia_api.dependencies import get_bootstrap_service
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas import bootstrap as bs
from orcia_api.schemas.auth_and_org import (
    PassthroughSecretMetadataResponse,
    WorkspaceDatasourceItem,
    WorkspaceSummaryItem,
)
from orcia_api.schemas.catalog import CatalogItemResponse
from orcia_api.schemas.permission_broker import PermissionBrokerPolicyItem
from orcia_core import bootstrap as bm
from orcia_core.observability.logging import get_current_trace_id

router = APIRouter(prefix="/api/v1/bootstrap", tags=["bootstrap"])


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _serialize_workflow(wf: bm.SystemBootstrapWorkflowSpec) -> bs.SystemBootstrapWorkflowItem:
    return bs.SystemBootstrapWorkflowItem(
        id=wf.id, uri=wf.uri, title=wf.title, description=wf.description,
        required_role=wf.required_role, scope_level=wf.scope_level,
        deterministic_gate_rules=list(wf.deterministic_gate_rules), sha256=wf.sha256,
    )  # fmt: skip


def _serialize_run(run: bm.SystemBootstrapRunRecord) -> bs.SystemBootstrapRunItem:
    return bs.SystemBootstrapRunItem(**asdict(run))


def _serialize_onboarding(st: bm.UserOnboardingState) -> bs.UserOnboardingStateItem:
    return bs.UserOnboardingStateItem(
        id=st.id, user_email=st.user_email, user_id=st.user_id,
        invited_by_user_id=st.invited_by_user_id, org_unit_id=st.org_unit_id,
        human_profile_archetype=st.human_profile_archetype, assigned_role=st.assigned_role,
        workspace_ids=list(st.workspace_ids), init_user_completed=st.init_user_completed,
        linked_connectors=list(st.linked_connectors),
    )  # fmt: skip


@router.get(
    "/state",
    response_model=bs.SystemBootstrapStateResponse,
    summary="List Day-0 System Bootstrap workflows, orthogonal LLM endpoints, runs & onboarding",
    responses=PROBLEM_RESPONSES,
)
async def get_system_bootstrap_state(
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> bs.SystemBootstrapStateResponse:
    resolve_request_user(request, persona_key=persona_key)
    svc = get_bootstrap_service(request)
    orth = svc.model_router.evaluate_orthogonality()
    return bs.SystemBootstrapStateResponse(
        workflows=[_serialize_workflow(w) for w in svc.list_workflows()],
        llm_endpoints=[
            bs.LlmModelEndpointItem(**asdict(ep)) for ep in svc.model_router.list_endpoints()
        ],
        orthogonal_families=list(orth.distinct_families),
        is_model_orthogonal=orth.is_orthogonal,
        runs=[_serialize_run(r) for r in svc.list_runs()],
        onboarding_states=[_serialize_onboarding(s) for s in svc.list_onboarding_states()],
        trace_id=_trace(request),
    )


@router.post(
    "/init-organization",
    response_model=bs.InitOrganizationResponse,
    summary="Execute Day-0 governed `orcia://system/bootstrap/init-organization` (`AD-10`)",
    responses=PROBLEM_RESPONSES,
)
async def execute_init_organization(
    payload: bs.InitOrganizationRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> bs.InitOrganizationResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_bootstrap_service(request)
    run = svc.execute_init_organization(
        user,
        bm.InitOrganizationInput(
            organization_name=payload.organization_name,
            oidc_enabled=payload.oidc_enabled,
            local_argon2id_enabled=payload.local_argon2id_enabled,
            rbac_role_mappings=dict(payload.rbac_role_mappings),
            llm_endpoints=tuple(
                bm.LlmModelEndpoint(**ep.model_dump()) for ep in payload.llm_endpoints
            ),
        ),
        instance=str(request.url.path),
    )
    orth = svc.model_router.evaluate_orthogonality()
    return bs.InitOrganizationResponse(
        run=_serialize_run(run),
        orthogonal_families=list(orth.distinct_families),
        trace_id=_trace(request),
    )


@router.post(
    "/init-workspace",
    response_model=bs.InitWorkspaceResponse,
    summary="Execute autonomous `TEAM_LEAD` `orcia://system/bootstrap/init-workspace` (`AD-14`)",
    responses=PROBLEM_RESPONSES,
)
async def execute_init_workspace(
    payload: bs.InitWorkspaceRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> bs.InitWorkspaceResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_bootstrap_service(request)
    ws_inputs = tuple(
        bm.WorkspaceBootstrapInput(
            slug=w.slug, name=w.name, visibility_mode=w.visibility_mode,
            notification_channel=w.notification_channel,
            workspace_override_scalars=dict(w.workspace_override_scalars),
            workspace_ontology_terms=tuple(
                bm.OntologyTermSpec(t.term_key, t.definition, t.level)
                for t in w.workspace_ontology_terms
            ),
        )
        for w in payload.workspaces
    )  # fmt: skip
    outcome = svc.execute_init_workspace(
        user,
        bm.InitWorkspaceInput(
            team_slug=payload.team_slug,
            team_name=payload.team_name,
            parent_org_unit_id=payload.parent_org_unit_id,
            subteam_slug=payload.subteam_slug,
            subteam_name=payload.subteam_name,
            team_override_scalars=dict(payload.team_override_scalars),
            team_ontology_terms=tuple(
                bm.OntologyTermSpec(t.term_key, t.definition, t.level)
                for t in payload.team_ontology_terms
            ),
            workspaces=ws_inputs,
            invited_members=tuple(
                bm.MemberInvitationInput(m.email, m.display_name, m.human_profile_archetype, m.role)
                for m in payload.invited_members
            ),
        ),
        instance=str(request.url.path),
    )
    ws_items = [
        WorkspaceSummaryItem(
            id=w.id, slug=w.slug, name=w.name, owner_org_unit_id=w.owner_org_unit_id,
            visibility_mode=w.visibility_mode, effective_role=user.platform_role,
            access_mode="CONTRIBUTOR_ACTION_REQUIRED", access_origin="DIRECT_TEAM",
            finops_cost_usd=w.finops_cost_usd,
            datasources=[WorkspaceDatasourceItem(**asdict(d)) for d in w.datasources],
        )
        for w in outcome.workspaces
    ]  # fmt: skip
    return bs.InitWorkspaceResponse(
        run=_serialize_run(outcome.run),
        workspaces=ws_items,
        onboarding_states=[_serialize_onboarding(s) for s in outcome.onboarding_states],
        trace_id=_trace(request),
    )


@router.post(
    "/init-datasource",
    response_model=bs.InitDatasourceResponse,
    summary="Execute governed `orcia://system/bootstrap/init-datasource` with Human Anchor",
    responses=PROBLEM_RESPONSES,
)
async def execute_init_datasource(
    payload: bs.InitDatasourceRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> bs.InitDatasourceResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_bootstrap_service(request)
    outcome = svc.execute_init_datasource(
        user,
        bm.InitDatasourceInput(**payload.model_dump()),
        instance=str(request.url.path),
    )
    ds, pol, item = outcome.datasource, outcome.policy, outcome.catalog_item
    return bs.InitDatasourceResponse(
        run=_serialize_run(outcome.run),
        datasource=WorkspaceDatasourceItem(**asdict(ds)),
        policy=PermissionBrokerPolicyItem(**asdict(pol)),
        catalog_item=CatalogItemResponse(
            id=item.id, resource_id=item.resource_id, uri=item.uri, scheme=item.scheme,
            title=item.title, description=item.description, resource_type=item.resource_type,
            source_format=item.source_format, version=item.version, sha256=item.sha256,
            sha256_short=item.sha256_short, cas_key=item.cas_key,
            visibility_scope=item.visibility_scope,
            granted_permissions=["DISCOVER", "EXECUTE", "READ_SOURCE", "EDIT", "ADMIN"],
            source_masked=False,
        ),
        trace_id=_trace(request),
    )  # fmt: skip


@router.post(
    "/init-user",
    response_model=bs.InitUserResponse,
    summary="Execute first-login `orcia://system/bootstrap/init-user` Passthrough Vault pairing",
    responses=PROBLEM_RESPONSES,
)
async def execute_init_user(
    payload: bs.InitUserRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> bs.InitUserResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_bootstrap_service(request)
    outcome = svc.execute_init_user(
        user,
        bm.InitUserInput(
            user_email=payload.user_email,
            confirmed_human_profile_archetype=payload.confirmed_human_profile_archetype,
            passthrough_secrets=tuple(
                bm.InitUserPassthroughSecretInput(
                    s.connector_scheme, s.target_host, s.plaintext_secret
                )
                for s in payload.passthrough_secrets
            ),
        ),
        instance=str(request.url.path),
    )
    creds = [
        PassthroughSecretMetadataResponse(
            id=c.id, user_id=c.user_id, connector_scheme=c.connector_scheme,
            target_host=c.target_host, key_version=c.key_version,
            encrypted_at_rest=True, trace_id=_trace(request),
        )
        for c in outcome.credentials
    ]  # fmt: skip
    return bs.InitUserResponse(
        run=_serialize_run(outcome.run),
        onboarding_state=_serialize_onboarding(outcome.onboarding_state),
        credentials=creds,
        trace_id=_trace(request),
    )


async def _sync_first_admin_with_postgres18(
    svc: bm.ProgressiveDay0AccostageService,
) -> None:
    """Synchronize `svc.first_admin` with PostgreSQL 18 `users` table when reachable."""
    import os

    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") == "1":
        return
    try:
        from sqlalchemy.ext.asyncio import create_async_engine

        from orcia_core.config import resolve_database_url

        engine = create_async_engine(resolve_database_url(), connect_args={"timeout": 1.5})
        try:
            db_record = await bm.get_first_platform_admin_from_postgres18(
                engine, orcia_env=svc.orcia_env
            )
            svc.set_first_platform_admin_record(db_record)
        finally:
            await engine.dispose()
    except Exception:
        return


def _serialize_accostage_status(
    rep: bm.AccostageStatusReport, trace_id: str
) -> bs.AccostageStatusResponse:
    return bs.AccostageStatusResponse(
        completed_count=rep.completed_count, total_count=rep.total_count,
        badge_label=rep.badge_label, llm_tier_mode=rep.llm_tier_mode,
        distinct_families=list(rep.distinct_families),
        assistant_trial_enabled=rep.assistant_trial_enabled,
        agentic_gates_ad10_enabled=rep.agentic_gates_ad10_enabled,
        amber_warning_badge=rep.amber_warning_badge,
        completed_milestone_keys=list(rep.completed_milestone_keys),
        first_admin_initialized=rep.first_admin_initialized,
        first_admin_email=rep.first_admin_email,
        first_admin_display_name=rep.first_admin_display_name,
        trace_id=trace_id,
    )  # fmt: skip


@router.get(
    "/accostage-status",
    response_model=bs.AccostageStatusResponse,
    summary="Get progressive Day-0 Accostage (1/6) status and LLM tier unlock state (`Story 9.2`)",
    responses=PROBLEM_RESPONSES,
)
async def get_accostage_status(request: Request) -> bs.AccostageStatusResponse:
    from orcia_api.dependencies import get_accostage_service

    svc = get_accostage_service(request)
    await _sync_first_admin_with_postgres18(svc)
    return _serialize_accostage_status(svc.get_accostage_status(), _trace(request))


@router.post(
    "/welcome-setup/first-admin",
    response_model=bs.WelcomeSetupFirstAdminResponse,
    summary="Create first PLATFORM_ADMIN under LOCK TABLE users IN EXCLUSIVE MODE (`Story 9.2`)",
    responses=PROBLEM_RESPONSES,
)
async def create_welcome_setup_first_admin(
    payload: bs.WelcomeSetupFirstAdminRequest,
    request: Request,
) -> bs.WelcomeSetupFirstAdminResponse:
    import os

    from orcia_api.dependencies import get_accostage_service, get_auth_service

    svc = get_accostage_service(request)
    password_hash = get_auth_service(request).hasher.hash_password(payload.password)

    rec: bm.FirstPlatformAdminRecord | None = None
    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1":
        try:
            from sqlalchemy.ext.asyncio import create_async_engine

            from orcia_core.bootstrap.errors import OrciaDomainError
            from orcia_core.config import resolve_database_url

            engine = create_async_engine(resolve_database_url(), connect_args={"timeout": 1.5})
            try:
                rec = await bm.create_first_platform_admin_on_postgres18(
                    engine, email=payload.email, display_name=payload.display_name,
                    password_hash=password_hash, orcia_env=payload.orcia_env,
                    expected_bootstrap_token=svc.expected_bootstrap_token,
                    provided_bootstrap_token=payload.bootstrap_token,
                    instance=str(request.url.path),
                )  # fmt: skip
                svc.set_first_platform_admin_record(rec)
            finally:
                await engine.dispose()
        except OrciaDomainError:
            raise
        except Exception:
            rec = None

    if rec is None:
        rec = await svc.create_first_platform_admin_async(
            email=payload.email, display_name=payload.display_name, password_hash=password_hash,
            bootstrap_token=payload.bootstrap_token, orcia_env_override=payload.orcia_env,
            instance=str(request.url.path),
        )  # fmt: skip
    return bs.WelcomeSetupFirstAdminResponse(
        user_id=rec.user_id, email=rec.email, display_name=rec.display_name,
        platform_role=rec.platform_role, orcia_env=rec.orcia_env,
        sql_lock_statement=rec.sql_lock_statement, trace_id=_trace(request),
    )  # fmt: skip


@router.post(
    "/welcome-setup/progressive-llm",
    response_model=bs.AccostageStatusResponse,
    summary="Register progressive LLM endpoint (1 family -> Quick Trial; >= 2 -> AD-10 Gates)",
    responses=PROBLEM_RESPONSES,
)
async def register_welcome_setup_progressive_llm(
    payload: bs.ProgressiveLlmEndpointRequest,
    request: Request,
) -> bs.AccostageStatusResponse:
    import os

    from orcia_api.dependencies import get_accostage_service
    from orcia_kernel.ids import new_uuid7_str

    svc = get_accostage_service(request)
    endpoint = bm.LlmModelEndpoint(
        id=new_uuid7_str(), endpoint_key=payload.endpoint_key,
        provider_slug=payload.provider_slug, model_family=payload.model_family,
        model_name=payload.model_name, endpoint_uri=payload.endpoint_uri,
    )  # fmt: skip
    rep = svc.register_progressive_llm_endpoint(endpoint)
    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1":
        try:
            from sqlalchemy.ext.asyncio import create_async_engine

            from orcia_core.config import resolve_database_url

            engine = create_async_engine(resolve_database_url(), connect_args={"timeout": 1.5})
            try:
                await bm.persist_progressive_llm_endpoint_to_postgres18(engine, endpoint)
            finally:
                await engine.dispose()
        except Exception:
            pass
    return _serialize_accostage_status(rep, _trace(request))


def _sync_accostage_from_snapshot(
    svc: bm.ProgressiveDay0AccostageService, snap: bm.PlatformSetupSnapshotRecord
) -> None:
    from orcia_kernel.ids import new_uuid7_str

    endpoints: list[bm.LlmModelEndpoint] = []
    for idx, t in enumerate(snap.llm_tiers):
        provider_raw = str(t.get("provider", "anthropic")).strip().lower()
        family = (
            "anthropic" if "anthropic" in provider_raw or "claude" in provider_raw
            else "openai" if "openai" in provider_raw or "gpt" in provider_raw
            else "google" if "google" in provider_raw or "gemini" in provider_raw
            else "mistral" if "mistral" in provider_raw else provider_raw or "anthropic"
        )  # fmt: skip
        endpoints.append(
            bm.LlmModelEndpoint(
                id=str(t.get("id", "")).strip() or new_uuid7_str(),
                endpoint_key=str(t.get("tierKey", f"tier-{idx + 1}")).strip() or f"tier-{idx + 1}",
                provider_slug=provider_raw or family,
                model_family=family,
                model_name=str(t.get("model", "claude-3-7-sonnet")).strip() or "claude-3-7-sonnet",
                endpoint_uri=f"https://api.{family}.local/v1",
            )
        )
    svc.sync_platform_setup_snapshot(
        llm_endpoints=tuple(endpoints),
        has_workspace=len(snap.workspaces) > 0,
        has_datasource=len(snap.datasources) > 0,
        has_pilot_run=len(snap.runs) > 0,
    )


def _serialize_setup_snapshot(
    snap: bm.PlatformSetupSnapshotRecord, trace_id: str
) -> bs.PlatformSetupStateResponse:
    return bs.PlatformSetupStateResponse(
        first_admin_initialized=snap.first_admin_initialized,
        first_admin_email=snap.first_admin_email,
        first_admin_display_name=snap.first_admin_display_name,
        org_units=list(snap.org_units), rbac_grants=list(snap.rbac_grants),
        llm_tiers=list(snap.llm_tiers), workspaces=list(snap.workspaces),
        datasources=list(snap.datasources), packs=list(snap.packs),
        workflows=list(snap.workflows), runs=list(snap.runs),
        catalog_items=list(snap.catalog_items), ontology_concepts=list(snap.ontology_concepts),
        audit_events=list(snap.audit_events), trace_id=trace_id,
    )  # fmt: skip


@router.get(
    "/platform-setup-state",
    response_model=bs.PlatformSetupStateResponse,
    summary="Load persisted Day-0 / Epics 8-12 Platform Setup state from PostgreSQL 18",
    responses=PROBLEM_RESPONSES,
)
async def get_platform_setup_state(request: Request) -> bs.PlatformSetupStateResponse:
    import os

    from orcia_api.dependencies import get_accostage_service

    svc = get_accostage_service(request)
    snap: bm.PlatformSetupSnapshotRecord | None = None
    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1":
        try:
            from sqlalchemy.ext.asyncio import create_async_engine

            from orcia_core.config import resolve_database_url

            engine = create_async_engine(resolve_database_url(), connect_args={"timeout": 1.5})
            try:
                snap = await bm.load_platform_setup_state_from_postgres18(
                    engine, orcia_env=svc.orcia_env
                )
                db_admin = await bm.get_first_platform_admin_from_postgres18(
                    engine, orcia_env=svc.orcia_env
                )
                svc.set_first_platform_admin_record(db_admin)
            finally:
                await engine.dispose()
        except Exception:
            snap = None

    if snap is None:
        cached: bm.PlatformSetupSnapshotRecord | None = getattr(
            request.app.state, "platform_setup_snapshot", None
        )
        admin = svc.first_admin
        snap = cached or bm.PlatformSetupSnapshotRecord(
            first_admin_initialized=admin is not None,
            first_admin_email=admin.email if admin else None,
            first_admin_display_name=admin.display_name if admin else None,
        )
    request.app.state.platform_setup_snapshot = snap
    _sync_accostage_from_snapshot(svc, snap)
    return _serialize_setup_snapshot(snap, _trace(request))


@router.put(
    "/platform-setup-state",
    response_model=bs.PlatformSetupStateResponse,
    summary="Persist Day-0 / Epics 8-12 Platform Setup state to PostgreSQL 18",
    responses=PROBLEM_RESPONSES,
)
async def put_platform_setup_state(
    payload: bs.PlatformSetupStatePutRequest,
    request: Request,
) -> bs.PlatformSetupStateResponse:
    import os

    from orcia_api.dependencies import get_accostage_service

    svc = get_accostage_service(request)
    admin = svc.first_admin
    candidate = bm.PlatformSetupSnapshotRecord(
        first_admin_initialized=admin is not None,
        first_admin_email=admin.email if admin else None,
        first_admin_display_name=admin.display_name if admin else None,
        org_units=list(payload.org_units), rbac_grants=list(payload.rbac_grants),
        llm_tiers=list(payload.llm_tiers), workspaces=list(payload.workspaces),
        datasources=list(payload.datasources), packs=list(payload.packs),
        workflows=list(payload.workflows), runs=list(payload.runs),
        catalog_items=list(payload.catalog_items),
        ontology_concepts=list(payload.ontology_concepts),
        audit_events=list(payload.audit_events),
    )  # fmt: skip
    saved: bm.PlatformSetupSnapshotRecord | None = None
    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1":
        try:
            from sqlalchemy.ext.asyncio import create_async_engine

            from orcia_core.config import resolve_database_url

            engine = create_async_engine(resolve_database_url(), connect_args={"timeout": 1.5})
            try:
                saved = await bm.save_platform_setup_state_to_postgres18(
                    engine, candidate, orcia_env=svc.orcia_env
                )
            finally:
                await engine.dispose()
        except Exception:
            saved = None

    final_snap = saved or candidate
    request.app.state.platform_setup_snapshot = final_snap
    _sync_accostage_from_snapshot(svc, final_snap)
    return _serialize_setup_snapshot(final_snap, _trace(request))
