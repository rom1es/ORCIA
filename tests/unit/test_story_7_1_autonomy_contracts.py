"""Unit & Property Tests for Story 7.1 — Autonomy Contracts, SignedApprovalToken & Runner."""

from __future__ import annotations

import json

import pytest
from hypothesis import given
from hypothesis import strategies as st

from orcia_connectors.autonomous_runner import (
    AutonomousActionRequest,
    AutonomousGateInput,
    execute_autonomous_contract_run,
)
from orcia_connectors.protocol import (
    OrciaConnectorProtocol,
    SignedApprovalToken,
    WritePreviewCard,
    compute_payload_sha256,
    verify_signed_approval_token,
)
from orcia_core.audit_finops.outbox_subscriber import (
    AUDITABLE_EVENT_TYPES,
    map_domain_event_to_ledger_entry,
)
from orcia_core.kernel.errors import (
    ObserverModeReadOnlyError,
    PolicyDeniedError,
    ValidationDomainError,
)
from orcia_core.kernel.events import (
    AutonomousContractRevoked,
    AutonomousContractSigned,
    AutonomousEscalated,
    DomainEvent,
)
from orcia_core.kernel.secret_ports import SecretProviderPort, SecretRef
from orcia_core.permissions import (
    AutonomyContract,
    AutonomyContractNotFoundError,
    AutonomyContractRepositoryPort,
    AutonomyContractService,
    AutonomyContractSignForbiddenError,
    ContractPrivilegeEscalationError,
    CriticalWorkflowRequiresHumanGateError,
    HierarchicalRbacService,
    IamAccountRecord,
    ServicePrincipalInvalidForContractError,
    SignAutonomyContractCommand,
)
from orcia_core.permissions._autonomy_confinement import (
    assert_contract_confinement,
    is_service_principal_scoped_to_workspace,
    map_action_to_required_verb,
    resolve_effective_verbs_for_roles,
    resolve_signer_role,
)
from orcia_core.permissions.connector_invoker import ConnectorInvoker
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.role_matrix import PermissionVerb, RolePermissionGrant


def _make_user(
    *,
    uid: str = "0195f000-0000-7000-8000-000000000203",
    role: str = "TEAM_LEAD",
    roles: tuple[str, ...] = (),
) -> UserIdentity:
    return UserIdentity(
        id=uid,
        email="marc.lead@orcia.io",
        display_name="Marc",
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role=role,  # type: ignore[arg-type]
        roles=roles,
        primary_org_unit_id="0195f000-0000-7000-8000-000000000103",
    )


def _make_sp(
    *,
    sp_id: str = "0195f000-0000-7000-8000-000000007101",
    roles: tuple[str, ...] = ("TEAM_LEAD",),
    team_ids: tuple[str, ...] = ("0195f000-0000-7000-8000-000000000301",),
    status: str = "ACTIVE",
    account_kind: str = "SERVICE_PRINCIPAL",
) -> IamAccountRecord:
    return IamAccountRecord(
        id=sp_id,
        principal_id="sp-docs-bot",
        display_name="Robot Documentation",
        email=None,
        account_kind=account_kind,  # type: ignore[arg-type]
        auth_source="SERVICE_TOKEN",
        roles=roles,  # type: ignore[arg-type]
        team_ids=team_ids,
        status=status,  # type: ignore[arg-type]
    )


class _DummyCatalogAdapter(OrciaConnectorProtocol):
    connector_type = "catalog"

    def __init__(self) -> None:
        self.executed: list[tuple[SignedApprovalToken, str, dict[str, object]]] = []

    async def healthcheck(self):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    async def read(self, resource_uri: str, query=None):  # type: ignore[no-untyped-def]
        del resource_uri, query
        return {}

    async def preview_write(self, action: str, payload: dict[str, object]) -> WritePreviewCard:
        return WritePreviewCard(
            connector_type=self.connector_type,
            target_resource_uri=f"catalog://{action}",
            action_summary=action,
            diff_or_payload_preview=payload,
            payload_sha256=compute_payload_sha256(action, payload),
        )

    async def execute_write(
        self, approval_token: SignedApprovalToken, action: str, payload: dict[str, object]
    ) -> dict[str, object]:
        verify_signed_approval_token(approval_token, action=action, payload=payload)
        self.executed.append((approval_token, action, payload))
        return {"ok": True, "action": action}


class _InMemSecretProvider(SecretProviderPort):
    def __init__(self, secrets: dict[str, str]) -> None:
        self._secrets = dict(secrets)

    def resolve_secret(self, ref: SecretRef) -> str:
        return self._secrets[ref.uri]

    def store_secret(
        self, ref: SecretRef, plaintext_value: str, *, actor_id: str = "system"
    ) -> SecretRef:
        del actor_id
        self._secrets[ref.uri] = plaintext_value
        return ref

    def rotate_workspace_dek(self, workspace_id: str, *, actor_id: str):  # type: ignore[no-untyped-def]
        del workspace_id, actor_id
        raise NotImplementedError


@pytest.mark.asyncio
async def test_sign_contract_single_signature_without_secops_and_reject_high_critical() -> None:
    """Single TEAM_LEAD/BU_LEAD signature succeeds without SECOPS; HIGH_CRITICAL is rejected 422."""
    rbac = HierarchicalRbacService()
    svc = AutonomyContractService(rbac_service=rbac)
    ws_id = "0195f000-0000-7000-8000-000000000301"
    sp = _make_sp(team_ids=(ws_id,))
    lead = _make_user(role="TEAM_LEAD")

    # HIGH_CRITICAL -> HTTP 422 ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE
    with pytest.raises(CriticalWorkflowRequiresHumanGateError):
        await svc.sign_contract(
            SignAutonomyContractCommand(
                workspace_id=ws_id,
                workflow_id="wf-critical-release",
                workflow_version="1.0.0",
                workflow_sha256="a" * 64,
                criticality="HIGH_CRITICAL",
                service_principal_id=sp.id,
                allowed_read_sources=("catalog:read",),
                allowed_write_actions=("help_article:publish",),
                max_cost_per_run_usd=5.0,
            ),
            signer=lead,
            service_principal=sp,
        )

    # Single signature by TEAM_LEAD (no SECOPS role on signer) succeeds
    contract = await svc.sign_contract(
        SignAutonomyContractCommand(
            workspace_id=ws_id,
            workflow_id="packs/orcia-docs/workflows/generate-and-attach-help",
            workflow_version="1.0.0",
            workflow_sha256="b" * 64,
            criticality="LOW_NON_CRITICAL",
            service_principal_id=sp.id,
            allowed_read_sources=("orcia://docs",),
            allowed_write_actions=("help_article:publish", "catalog_item:create"),
            max_cost_per_run_usd=3.5,
        ),
        signer=lead,
        service_principal=sp,
    )
    assert contract.status == "ACTIVE"
    assert contract.signed_by_role == "TEAM_LEAD"
    assert len(contract.signature_sha256) == 64
    assert any(isinstance(e, AutonomousContractSigned) for e in svc.outbox_events)

    # BU_DIRECTOR maps to BU_LEAD and supersedes prior ACTIVE contract
    bu_lead = _make_user(uid="0195f000-0000-7000-8000-000000000202", role="BU_DIRECTOR")
    contract_v2 = await svc.sign_contract(
        SignAutonomyContractCommand(
            workspace_id=ws_id,
            workflow_id="packs/orcia-docs/workflows/generate-and-attach-help",
            workflow_version="1.0.1",
            workflow_sha256="c" * 64,
            criticality="STANDARD",
            service_principal_id=sp.id,
            allowed_read_sources=("orcia://docs",),
            allowed_write_actions=("help_article:publish",),
            max_cost_per_run_usd=4.0,
        ),
        signer=bu_lead,
        service_principal=sp,
    )
    assert contract_v2.signed_by_role == "BU_LEAD"
    history = await svc.list_contracts(
        workspace_id=ws_id,
        workflow_id="packs/orcia-docs/workflows/generate-and-attach-help",
    )
    assert len(history) == 2
    assert {c.status for c in history} == {"ACTIVE", "SUPERSEDED"}


@pytest.mark.asyncio
async def test_double_guard_rejects_invalid_sp_observer_and_contributor() -> None:
    """Reject OBSERVER (403), CONTRIBUTOR (403), foreign/disabled/human SP (422)."""
    rbac = HierarchicalRbacService()
    svc = AutonomyContractService(rbac_service=rbac)
    ws_id = "0195f000-0000-7000-8000-000000000301"
    lead = _make_user(role="TEAM_LEAD")

    with pytest.raises(ObserverModeReadOnlyError):
        await svc.sign_contract(
            SignAutonomyContractCommand(
                workspace_id=ws_id,
                workflow_id="wf-1",
                workflow_version="1.0.0",
                workflow_sha256="a" * 64,
                criticality="STANDARD",
                service_principal_id="sp-1",
                allowed_read_sources=(),
                allowed_write_actions=("help:publish",),
                max_cost_per_run_usd=2.0,
            ),
            signer=_make_user(role="OBSERVER"),
            service_principal=_make_sp(team_ids=(ws_id,)),
        )

    with pytest.raises(AutonomyContractSignForbiddenError):
        await svc.sign_contract(
            SignAutonomyContractCommand(
                workspace_id=ws_id,
                workflow_id="wf-1",
                workflow_version="1.0.0",
                workflow_sha256="a" * 64,
                criticality="STANDARD",
                service_principal_id="sp-1",
                allowed_read_sources=(),
                allowed_write_actions=("help:publish",),
                max_cost_per_run_usd=2.0,
            ),
            signer=_make_user(role="CONTRIBUTOR"),
            service_principal=_make_sp(team_ids=(ws_id,)),
        )

    # Disabled SP, HUMAN account, and unscoped SP are all rejected 422
    for bad_sp in (
        None,
        _make_sp(team_ids=(ws_id,), status="DISABLED"),
        _make_sp(team_ids=(ws_id,), account_kind="HUMAN"),
        _make_sp(team_ids=("other-workspace",)),
    ):
        with pytest.raises(ServicePrincipalInvalidForContractError):
            await svc.sign_contract(
                SignAutonomyContractCommand(
                    workspace_id=ws_id,
                    workflow_id="wf-1",
                    workflow_version="1.0.0",
                    workflow_sha256="a" * 64,
                    criticality="STANDARD",
                    service_principal_id="sp-bad",
                    allowed_read_sources=(),
                    allowed_write_actions=("help:publish",),
                    max_cost_per_run_usd=2.0,
                ),
                signer=lead,
                service_principal=bad_sp,
            )


@given(
    requested_actions=st.lists(
        st.sampled_from(
            [
                "catalog:create",
                "catalog:update",
                "catalog:delete",
                "help_article:publish",
                "item:read",
            ]
        ),
        min_size=1,
        max_size=4,
        unique=True,
    ),
    sp_role=st.sampled_from(["OBSERVER", "CONTRIBUTOR", "TEAM_LEAD"]),
)
@pytest.mark.asyncio
async def test_hypothesis_confinement_invariant(requested_actions: list[str], sp_role: str) -> None:
    """Property test: `allowed_write_actions <= Rights(Signer) & Rights(SP)` or 403."""
    rbac = HierarchicalRbacService()
    svc = AutonomyContractService(rbac_service=rbac)
    ws_id = "0195f000-0000-7000-8000-000000000301"
    lead = _make_user(role="TEAM_LEAD")
    sp = _make_sp(roles=(sp_role,), team_ids=(ws_id,))

    # Compute expected verbs per role from native matrix
    role_verbs: dict[str, set[PermissionVerb]] = {
        "OBSERVER": {"read"},
        "CONTRIBUTOR": {"create", "read", "update", "execute"},
        "TEAM_LEAD": {"create", "read", "update", "delete", "execute"},
    }
    sp_verbs = role_verbs[sp_role]
    signer_verbs: set[PermissionVerb] = {"create", "read", "update", "delete", "execute"}
    intersection = signer_verbs & sp_verbs

    def _verb_for(act: str) -> PermissionVerb:
        if ":create" in act:
            return "create"
        if ":update" in act:
            return "update"
        if ":delete" in act:
            return "delete"
        if ":read" in act:
            return "read"
        return "execute"

    should_succeed = all(_verb_for(a) in intersection for a in requested_actions)
    cmd = SignAutonomyContractCommand(
        workspace_id=ws_id,
        workflow_id="wf-prop",
        workflow_version="1.0.0",
        workflow_sha256="d" * 64,
        criticality="STANDARD",
        service_principal_id=sp.id,
        allowed_read_sources=(),
        allowed_write_actions=tuple(requested_actions),
        max_cost_per_run_usd=5.0,
    )
    if should_succeed:
        contract = await svc.sign_contract(cmd, signer=lead, service_principal=sp)
        assert set(contract.allowed_write_actions) == set(requested_actions)
    else:
        with pytest.raises(ContractPrivilegeEscalationError):
            await svc.sign_contract(cmd, signer=lead, service_principal=sp)


def test_signed_approval_token_issue_autonomous_and_tamper_detection() -> None:
    """Verify `SignedApprovalToken.issue_autonomous` prefix, signature, and tamper check."""
    payload = {"article_id": "help-studio-v2", "lang": "fr"}
    sha = compute_payload_sha256("help_article:publish", payload)
    token = SignedApprovalToken.issue_autonomous(
        contract_id="ctr-1",
        service_principal_id="sp-1",
        action_key="help_article:publish",
        payload_sha256=sha,
        run_id="run-1",
    )
    assert token.preview_id == "autonomous:ctr-1:run-1:help_article:publish"
    assert token.approver_user_id == "sp:sp-1"
    verify_signed_approval_token(token, action="help_article:publish", payload=payload)

    with pytest.raises(PolicyDeniedError):
        verify_signed_approval_token(
            token, action="help_article:publish", payload={"article_id": "tampered"}
        )


@pytest.mark.asyncio
async def test_autonomous_runner_committed_and_escalations_with_help_validator() -> None:
    """Verify COMMITTED_AUTONOMOUS vs PAUSED_AUTONOMOUS_ESCALATION across gate/revocation/scope."""
    rbac = HierarchicalRbacService()
    svc = AutonomyContractService(rbac_service=rbac)
    ws_id = "0195f000-0000-7000-8000-000000000301"
    sp = _make_sp(team_ids=(ws_id,))
    lead = _make_user(role="TEAM_LEAD")

    contract = await svc.sign_contract(
        SignAutonomyContractCommand(
            workspace_id=ws_id,
            workflow_id="packs/orcia-docs/workflows/generate-and-attach-help",
            workflow_version="1.0.0",
            workflow_sha256="e" * 64,
            criticality="LOW_NON_CRITICAL",
            service_principal_id=sp.id,
            allowed_read_sources=("orcia://docs",),
            allowed_write_actions=("help_article:publish",),
            max_cost_per_run_usd=5.0,
        ),
        signer=lead,
        service_principal=sp,
    )

    valid_help_md = """---
id: help-studio-autonomy
bound_routes: ["/processes"]
glossary_terms: ["Contrat d'autonomie"]
---
## 1. À quoi sert cet écran ? {#what-for}
Utilisez `AutonomyContractModal` et `FourZoneDirectionCShell`.

## 2. Comment faire (Pas-à-pas) {#step-by-step}
Suivez les étapes guidées.

## 3. Questions fréquentes & Dépannage {#faq}
Contrat d'autonomie.
"""
    canary = "sk-live-" + "CANARY_SECRET_AUTONOMOUS_TOKEN_9988"  # pragma: allowlist secret
    secret_provider = _InMemSecretProvider({"secret://ws/docs-token": canary})
    adapter = _DummyCatalogAdapter()

    # 1. Nominal PASS -> COMMITTED_AUTONOMOUS
    outcome, events = await execute_autonomous_contract_run(
        contract=contract,
        criticality="LOW_NON_CRITICAL",
        actions=[
            AutonomousActionRequest(
                action_key="help_article:publish",
                scheme="catalog",
                payload={"article": "help-studio-autonomy", "api_key": canary},
                secret_ref_uri="secret://ws/docs-token",  # pragma: allowlist secret
            )
        ],
        gates=AutonomousGateInput(
            deterministic_passed=True,
            agentic_score=0.91,
            fact_verification_score=0.95,
            ontology_conflicts=0,
            stale_warnings=0,
            estimated_cost_usd=0.25,
            help_article_markdown=valid_help_md,
            help_article_lang="fr",
        ),
        connectors_by_scheme={"catalog": adapter},
        secret_provider=secret_provider,
    )
    assert outcome.status == "COMMITTED_AUTONOMOUS"
    assert len(outcome.issued_tokens) == 1
    assert len(adapter.executed) == 1
    assert canary not in json.dumps(outcome.model_dump())
    assert events[0].event_type == "RunTerminated"

    # 2. Agentic score < 0.85 -> PAUSED_AUTONOMOUS_ESCALATION (0 writes)
    adapter_esc = _DummyCatalogAdapter()
    esc_outcome, esc_events = await execute_autonomous_contract_run(
        contract=contract,
        criticality="LOW_NON_CRITICAL",
        actions=[
            AutonomousActionRequest(
                action_key="help_article:publish",
                scheme="catalog",
                payload={"article": "help-studio-autonomy"},
            )
        ],
        gates=AutonomousGateInput(agentic_score=0.80, fact_verification_score=0.95),
        connectors_by_scheme={"catalog": adapter_esc},
    )
    assert esc_outcome.status == "PAUSED_AUTONOMOUS_ESCALATION"
    assert len(adapter_esc.executed) == 0
    assert isinstance(esc_events[0], AutonomousEscalated)

    # 3. Action outside contract -> PAUSED_AUTONOMOUS_ESCALATION
    out_scope, _ = await execute_autonomous_contract_run(
        contract=contract,
        criticality="LOW_NON_CRITICAL",
        actions=[
            AutonomousActionRequest(
                action_key="unauthorized:delete",
                scheme="catalog",
                payload={},
            )
        ],
        connectors_by_scheme={"catalog": adapter_esc},
    )
    assert out_scope.status == "PAUSED_AUTONOMOUS_ESCALATION"
    assert "ACTION_OUTSIDE_CONTRACT_SCOPE" in (out_scope.escalation_reason or "")
    assert len(adapter_esc.executed) == 0

    # 4. Revoked contract -> PAUSED_AUTONOMOUS_ESCALATION immediately at next step boundary
    await svc.revoke_contract(workspace_id=ws_id, workflow_id=contract.workflow_id, actor=lead)
    revoked_outcome, _ = await execute_autonomous_contract_run(
        contract=contract,
        criticality="LOW_NON_CRITICAL",
        actions=[
            AutonomousActionRequest(
                action_key="help_article:publish",
                scheme="catalog",
                payload={},
            )
        ],
        contract_refresh_fn=lambda: svc.get_active_contract(
            workspace_id=ws_id, workflow_id=contract.workflow_id
        ),
        connectors_by_scheme={"catalog": adapter_esc},
    )
    assert revoked_outcome.status == "PAUSED_AUTONOMOUS_ESCALATION"
    assert revoked_outcome.escalation_reason == "CONTRACT_REVOKED"


def test_audit_outbox_subscriber_maps_all_epic7_events() -> None:
    """Verify all 3 Epic 7 Outbox events map cleanly to audit_ledger entries without secrets."""
    for evt_type in (
        "AutonomousContractSigned",
        "AutonomousContractRevoked",
        "AutonomousEscalated",
    ):
        assert evt_type in AUDITABLE_EVENT_TYPES

    signed_evt = AutonomousContractSigned.create(
        contract_id="ctr-1",
        workspace_id="ws-1",
        workflow_id="wf-1",
        workflow_version="1.0.0",
        service_principal_id="sp-1",
        signed_by_user_id="u-1",
        signed_by_role="TEAM_LEAD",
        signature_sha256="a" * 64,
    )
    entry = map_domain_event_to_ledger_entry(signed_evt)
    assert entry.event_type == "AutonomousContractSigned"
    assert "Contrat d'autonomie signé" in entry.summary

    revoked_evt = AutonomousContractRevoked.create(
        contract_id="ctr-1",
        workspace_id="ws-1",
        workflow_id="wf-1",
        revoked_by_user_id="u-1",
    )
    rev_entry = map_domain_event_to_ledger_entry(revoked_evt)
    assert rev_entry.event_type == "AutonomousContractRevoked"

    esc_evt = AutonomousEscalated.create(
        run_id="run-1",
        workspace_id="ws-1",
        workflow_id="wf-1",
        reason="AGENTIC_SCORE_BELOW_THRESHOLD",
    )
    esc_entry = map_domain_event_to_ledger_entry(esc_evt)
    assert esc_entry.event_type == "AutonomousEscalated"


@pytest.mark.asyncio
async def test_confinement_helpers_repository_port_and_runner_edge_cases() -> None:
    """Cover verb mappings, DENY grants, explicit confinement, repo port, and runner paths."""
    assert map_action_to_required_verb("role:grant") == "grant"
    assert map_action_to_required_verb("item:read") == "read"
    assert map_action_to_required_verb("item:update") == "update"
    assert map_action_to_required_verb("item:delete") == "delete"
    assert map_action_to_required_verb("custom_exec") == "execute"

    bu_dir = _make_user(role="BU_DIRECTOR")
    assert resolve_signer_role(bu_dir) == "BU_LEAD"
    admin = _make_user(role="PLATFORM_ADMIN")
    assert resolve_signer_role(admin) == "PLATFORM_ADMIN"

    ws_id = "0195f000-0000-7000-8000-000000000301"
    rbac = HierarchicalRbacService(
        initial_grants=(
            RolePermissionGrant(
                id="g-deny",
                subject_type="ROLE",
                subject_id="CONTRIBUTOR",
                scope_path="GLOBAL",
                verb="execute",
                effect="DENY",
            ),
            RolePermissionGrant(
                id="g-sp-allow",
                subject_type="SERVICE_PRINCIPAL",
                subject_id="sp-by-grant",
                scope_path="GLOBAL",
                verb="execute",
                effect="ALLOW",
            ),
        )
    )
    verbs = resolve_effective_verbs_for_roles(
        rbac_service=rbac,
        subject_id="u-1",
        subject_type="USER",
        roles=("BU_DIRECTOR", "CONTRIBUTOR"),
        scope_path="GLOBAL",
    )
    assert "execute" not in verbs
    assert "update" in verbs

    sp_grant = _make_sp(sp_id="sp-by-grant", roles=("CONTRIBUTOR",), team_ids=())
    sp_admin = _make_sp(sp_id="sp-admin", roles=("PLATFORM_ADMIN",), team_ids=())
    sp_human = _make_sp(sp_id="sp-human", account_kind="HUMAN", team_ids=(ws_id,))
    assert is_service_principal_scoped_to_workspace(
        sp_grant, workspace_id=ws_id, rbac_service=rbac, scope_path="GLOBAL"
    )
    assert not is_service_principal_scoped_to_workspace(sp_admin, workspace_id=ws_id)
    assert not is_service_principal_scoped_to_workspace(sp_human, workspace_id=ws_id)

    with pytest.raises(ContractPrivilegeEscalationError):
        assert_contract_confinement(
            allowed_write_actions=["help:publish"],
            signer_verbs={"execute"},
            sp_verbs={"execute"},
            signer_allowed_actions={"other:act"},
        )
    with pytest.raises(ContractPrivilegeEscalationError):
        assert_contract_confinement(
            allowed_write_actions=["help:publish"],
            signer_verbs={"execute"},
            sp_verbs={"execute"},
            sp_allowed_actions={"other:act"},
        )

    svc = AutonomyContractService(rbac_service=rbac)
    lead = _make_user(role="TEAM_LEAD")
    obs = _make_user(role="OBSERVER")
    sp_ok = _make_sp(sp_id="sp-ok", roles=("TEAM_LEAD",), team_ids=(ws_id,))

    for bad_cmd in (
        SignAutonomyContractCommand(
            workspace_id=ws_id,
            workflow_id="wf-1",
            workflow_version="1.0.0",
            workflow_sha256="a" * 64,
            criticality="UNKNOWN",
            service_principal_id=sp_ok.id,
            allowed_read_sources=(),
            allowed_write_actions=("help:publish",),
            max_cost_per_run_usd=1.0,
        ),
        SignAutonomyContractCommand(
            workspace_id=ws_id,
            workflow_id="wf-1",
            workflow_version="1.0.0",
            workflow_sha256="a" * 64,
            criticality="STANDARD",
            service_principal_id=sp_ok.id,
            allowed_read_sources=(),
            allowed_write_actions=("help:publish",),
            max_cost_per_run_usd=0.0,
        ),
        SignAutonomyContractCommand(
            workspace_id=ws_id,
            workflow_id="wf-1",
            workflow_version="1.0.0",
            workflow_sha256="a" * 64,
            criticality="STANDARD",
            service_principal_id=sp_ok.id,
            allowed_read_sources=(),
            allowed_write_actions=("help:publish",),
            max_cost_per_run_usd=1.0,
            post_hoc_sampling_rate=0.5,
        ),
        SignAutonomyContractCommand(
            workspace_id=ws_id,
            workflow_id="wf-1",
            workflow_version="1.0.0",
            workflow_sha256="a" * 64,
            criticality="STANDARD",
            service_principal_id=sp_ok.id,
            allowed_read_sources=(),
            allowed_write_actions=("help:publish",),
            max_cost_per_run_usd=1.0,
            tie_break_policy="INVALID_POLICY",  # type: ignore[arg-type]
        ),
    ):
        with pytest.raises(ValidationDomainError):
            await svc.sign_contract(bad_cmd, signer=lead, service_principal=sp_ok)

    with pytest.raises(ObserverModeReadOnlyError):
        await svc.revoke_contract(workspace_id=ws_id, workflow_id="wf-1", actor=obs)
    with pytest.raises(AutonomyContractSignForbiddenError):
        await svc.revoke_contract(
            workspace_id=ws_id, workflow_id="wf-1", actor=_make_user(role="CONTRIBUTOR")
        )
    with pytest.raises(AutonomyContractNotFoundError):
        await svc.revoke_contract(workspace_id=ws_id, workflow_id="wf-1", actor=lead)

    c1 = await svc.sign_contract(
        SignAutonomyContractCommand(
            workspace_id=ws_id,
            workflow_id="wf-1",
            workflow_version="1.0.0",
            workflow_sha256="a" * 64,
            criticality="STANDARD",
            service_principal_id=sp_ok.id,
            allowed_read_sources=(),
            allowed_write_actions=("help:publish",),
            max_cost_per_run_usd=2.0,
        ),
        signer=lead,
        service_principal=sp_ok,
    )
    c2 = await svc.sign_contract(
        SignAutonomyContractCommand(
            workspace_id=ws_id,
            workflow_id="wf-1",
            workflow_version="1.1.0",
            workflow_sha256="b" * 64,
            criticality="STANDARD",
            service_principal_id=sp_ok.id,
            allowed_read_sources=(),
            allowed_write_actions=("help:publish",),
            max_cost_per_run_usd=2.0,
        ),
        signer=lead,
        service_principal=sp_ok,
    )
    assert len(await svc.list_contracts(workspace_id=ws_id, workflow_id="wf-1")) == 2
    assert c1.id != c2.id

    class _FakeRepo(AutonomyContractRepositoryPort):
        def __init__(self) -> None:
            self.items: dict[str, AutonomyContract] = {}

        async def get_active_contract(
            self, *, workspace_id: str, workflow_id: str
        ) -> AutonomyContract | None:
            return next(
                (
                    item
                    for item in self.items.values()
                    if item.workspace_id == workspace_id
                    and item.workflow_id == workflow_id
                    and item.status == "ACTIVE"
                ),
                None,
            )

        async def list_contracts(
            self, *, workspace_id: str, workflow_id: str
        ) -> list[AutonomyContract]:
            return [
                item
                for item in self.items.values()
                if item.workspace_id == workspace_id and item.workflow_id == workflow_id
            ]

        async def save_signed_contract(
            self, contract: AutonomyContract, event: DomainEvent
        ) -> AutonomyContract:
            del event
            self.items[contract.id] = contract
            return contract

        async def mark_contract_revoked(
            self,
            *,
            contract_id: str,
            revoked_by_user_id: str,
            revoked_at_iso: str,
            event: DomainEvent,
        ) -> AutonomyContract:
            del revoked_by_user_id, revoked_at_iso, event
            cur = self.items[contract_id]
            self.items[contract_id] = AutonomyContract(
                id=cur.id,
                workspace_id=cur.workspace_id,
                workflow_id=cur.workflow_id,
                workflow_version=cur.workflow_version,
                workflow_sha256=cur.workflow_sha256,
                criticality=cur.criticality,
                service_principal_id=cur.service_principal_id,
                allowed_read_sources=cur.allowed_read_sources,
                allowed_write_actions=cur.allowed_write_actions,
                max_cost_per_run_usd=cur.max_cost_per_run_usd,
                tie_break_policy=cur.tie_break_policy,
                post_hoc_sampling_rate=cur.post_hoc_sampling_rate,
                status="REVOKED",
                signed_by_user_id=cur.signed_by_user_id,
                signed_by_role=cur.signed_by_role,
                signature_sha256=cur.signature_sha256,
                signed_at_iso=cur.signed_at_iso,
            )
            return self.items[contract_id]

    repo_svc = AutonomyContractService(rbac_service=rbac, repository=_FakeRepo())
    saved = await repo_svc.sign_contract(
        SignAutonomyContractCommand(
            workspace_id=ws_id,
            workflow_id="wf-repo",
            workflow_version="1.0.0",
            workflow_sha256="c" * 64,
            criticality="LOW_NON_CRITICAL",
            service_principal_id=sp_ok.id,
            allowed_read_sources=(),
            allowed_write_actions=("help:publish",),
            max_cost_per_run_usd=3.0,
        ),
        signer=lead,
        service_principal=sp_ok,
    )
    assert len(await repo_svc.list_contracts(workspace_id=ws_id, workflow_id="wf-repo")) == 1
    revoked_repo = await repo_svc.revoke_contract(
        workspace_id=ws_id, workflow_id="wf-repo", actor=lead
    )
    assert revoked_repo.status == "REVOKED"

    # Runner branches: revoked, HIGH_CRITICAL, deterministic fail, low fact, conflict, etc.
    with pytest.raises(CriticalWorkflowRequiresHumanGateError):
        await execute_autonomous_contract_run(
            contract=saved,
            criticality="HIGH_CRITICAL",
            actions=[
                AutonomousActionRequest(action_key="help:publish", scheme="catalog", payload={})
            ],
        )

    for kw, expected_reason in (
        ({"contract": revoked_repo}, "CONTRACT_REVOKED"),
        (
            {"gates": AutonomousGateInput(deterministic_passed=False)},
            "DETERMINISTIC_GATE_FAILED",
        ),
        (
            {
                "gates": AutonomousGateInput(
                    deterministic_passed=True,
                    agentic_score=0.95,
                    fact_verification_score=0.50,
                )
            },
            "FACT_VERIFICATION_BELOW_THRESHOLD:0.50",
        ),
        (
            {
                "gates": AutonomousGateInput(
                    deterministic_passed=True,
                    agentic_score=0.95,
                    fact_verification_score=0.95,
                    ontology_conflicts=1,
                )
            },
            "ONTOLOGY_CONFLICTS_PRESENT:1",
        ),
        (
            {
                "gates": AutonomousGateInput(
                    deterministic_passed=True,
                    agentic_score=0.95,
                    fact_verification_score=0.95,
                    stale_warnings=2,
                )
            },
            "STALE_WARNINGS_PRESENT:2",
        ),
        (
            {
                "gates": AutonomousGateInput(
                    deterministic_passed=True,
                    agentic_score=0.95,
                    fact_verification_score=0.95,
                    estimated_cost_usd=99.0,
                )
            },
            "CONTRACT_COST_CEILING_EXCEEDED:99.0000",
        ),
        (
            {
                "gates": AutonomousGateInput(
                    deterministic_passed=True,
                    agentic_score=0.95,
                    fact_verification_score=0.95,
                    help_article_markdown="# Incomplete article",
                )
            },
            "HELP_ARTICLE_VALIDATION_FAILED",
        ),
        (
            {
                "actions": [
                    AutonomousActionRequest(
                        action_key="forbidden:write", scheme="catalog", payload={}
                    )
                ]
            },
            "ACTION_OUTSIDE_CONTRACT_SCOPE:forbidden:write",
        ),
    ):
        res, _evts = await execute_autonomous_contract_run(
            contract=kw.get("contract", saved),  # type: ignore[arg-type]
            criticality="LOW_NON_CRITICAL",
            gates=kw.get(  # type: ignore[arg-type]
                "gates",
                AutonomousGateInput(
                    deterministic_passed=True,
                    agentic_score=0.92,
                    fact_verification_score=0.96,
                ),
            ),
            actions=kw.get(  # type: ignore[arg-type]
                "actions",
                [AutonomousActionRequest(action_key="help:publish", scheme="catalog", payload={})],
            ),
        )
        assert res.status == "PAUSED_AUTONOMOUS_ESCALATION"
        assert res.escalation_reason is not None
        assert res.escalation_reason.startswith(expected_reason)

    # Mid-run revocation check (boundary 1 returns active, boundary 2 returns None)
    active_c = await svc.get_active_contract(workspace_id=ws_id, workflow_id="wf-1")
    assert active_c is not None
    calls = {"n": 0}

    async def _revoke_mid_run() -> AutonomyContract | None:
        calls["n"] += 1
        return active_c if calls["n"] == 1 else None

    mid_res, _ = await execute_autonomous_contract_run(
        contract=active_c,
        criticality="STANDARD",
        gates=AutonomousGateInput(
            deterministic_passed=True,
            agentic_score=0.92,
            fact_verification_score=0.96,
        ),
        actions=[AutonomousActionRequest(action_key="help:publish", scheme="catalog", payload={})],
        contract_refresh_fn=_revoke_mid_run,
    )
    assert mid_res.escalation_reason == "CONTRACT_REVOKED_MID_RUN"

    # Fallback ConnectorInvoker path + SecretProviderPort + PolicyDenied + Exception
    class _StubOutcome:
        def __init__(self, idempotency_key: str) -> None:
            self.idempotency_key = idempotency_key
            self.sanitized_output = {"ok": True}

    class _FakeInvoker(ConnectorInvoker):
        def __init__(self, mode: str) -> None:
            super().__init__()
            self._mode = mode

        async def invoke_async(self, **kwargs: object) -> object:  # type: ignore[override]
            if self._mode == "deny":
                raise PolicyDeniedError(detail_override="denied")
            if self._mode == "boom":
                raise RuntimeError("boom")
            return _StubOutcome(str(kwargs.get("idempotency_key", "idem-1")))

    ok_res, _ = await execute_autonomous_contract_run(
        contract=active_c,
        criticality="STANDARD",
        gates=AutonomousGateInput(
            deterministic_passed=True,
            agentic_score=0.92,
            fact_verification_score=0.96,
        ),
        actions=[
            AutonomousActionRequest(
                action_key="help:publish",
                scheme="custom",
                payload={"k": "v"},
                secret_ref_uri="secret://ws/token",  # pragma: allowlist secret
            )
        ],
        connector_invoker=_FakeInvoker("ok"),
        secret_provider=_InMemSecretProvider({"secret://ws/token": "tok-val"}),
    )
    assert ok_res.status == "COMMITTED_AUTONOMOUS"

    denied_res, _ = await execute_autonomous_contract_run(
        contract=active_c,
        criticality="STANDARD",
        gates=AutonomousGateInput(
            deterministic_passed=True,
            agentic_score=0.92,
            fact_verification_score=0.96,
        ),
        actions=[AutonomousActionRequest(action_key="help:publish", scheme="custom", payload={})],
        connector_invoker=_FakeInvoker("deny"),
    )
    assert denied_res.escalation_reason == "POLICY_DENIED:help:publish"

    boom_res, _ = await execute_autonomous_contract_run(
        contract=active_c,
        criticality="STANDARD",
        gates=AutonomousGateInput(
            deterministic_passed=True,
            agentic_score=0.92,
            fact_verification_score=0.96,
        ),
        actions=[AutonomousActionRequest(action_key="help:publish", scheme="custom", payload={})],
        connector_invoker=_FakeInvoker("boom"),
    )
    assert boom_res.escalation_reason == "CONNECTOR_EXECUTION_FAILED:RuntimeError"
