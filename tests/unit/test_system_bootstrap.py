"""Layer 1 Unit and FastAPI Route Tests for Story 1.5 (`AD-17`)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.bootstrap import (
    InitDatasourceInput,
    InitOrganizationInput,
    InitUserInput,
    InitUserPassthroughSecretInput,
    InitWorkspaceInput,
    LlmModelEndpoint,
    MemberInvitationInput,
    ModelRouterService,
    OntologyTermSpec,
    WorkspaceBootstrapInput,
    build_default_system_bootstrap_service,
)
from orcia_core.bootstrap.errors import (
    HumanAnchorRequiredError,
    ModelOrthogonalityViolationError,
    ObserverModeReadOnlyError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)
from orcia_core.catalog import build_default_federated_catalog_service
from orcia_core.permissions import (
    build_default_auth_and_org_service,
    build_default_permission_broker_service,
)

VALID_POLICY_MD = """---
policy_key: policy-3ds-multi-source
scheme: git
uri_pattern: git://gitlab.entreprise.io/payments/*
required_role: Maintainer GitLab Payments
approver_team: SecOps & Architecture Paiement
approver_email: secops-paiement@entreprise.io
sla_hours: 4
request_url_template: https://jira.entreprise.io/secure/CreateIssueDetails!init.jspa?pid=PAYSEC
jira_project_key: PAYSEC
jira_issue_type: Access Request
freshness_ttl_days: 14
---
# Politique Permission Broker 3DS
Autorisation gouvernée pour les sources 3DS et SEPA de l'équipe Paiement.
"""


def _load_script_04() -> Any:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = (
        repo_root / "infra" / "scripts" / "maintenance" / "04_backfill_system_bootstrap.py"
    )
    spec = importlib.util.spec_from_file_location("backfill_system_bootstrap_04", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_model_router_orthogonality_and_executor_evaluator_pair() -> None:
    """Verify ModelRouterService enforces >= 2 distinct LLM families and pair orthogonality."""
    ep_claude = LlmModelEndpoint("1", "ep-claude", "anthropic", "anthropic-claude", "claude-sonnet-4-6", "https://api.a.com")  # noqa: E501  # fmt: skip
    ep_gemini = LlmModelEndpoint("2", "ep-gemini", "google", "google-gemini", "gemini-2.5-pro", "https://api.g.com")  # noqa: E501  # fmt: skip
    router = ModelRouterService((ep_claude,))
    router.register_endpoint(ep_gemini)
    assert len(router.list_endpoints()) == 2
    report = router.enforce_orthogonality_gate()
    assert report.is_orthogonal is True and report.distinct_families == (
        "anthropic-claude",
        "google-gemini",
    )
    ModelRouterService.verify_executor_evaluator_pair("anthropic-claude", "google-gemini")

    with pytest.raises(ModelOrthogonalityViolationError):
        router.enforce_orthogonality_gate((ep_claude,))
    with pytest.raises(ModelOrthogonalityViolationError):
        ModelRouterService.verify_executor_evaluator_pair("anthropic-claude", "anthropic-claude")


def test_system_bootstrap_workflows_domain_and_guards() -> None:
    """Verify init-organization, init-workspace, init-datasource, and init-user domain rules."""
    auth_svc = build_default_auth_and_org_service()
    cat_svc = build_default_federated_catalog_service(evaluator=auth_svc.evaluator)
    broker_svc = build_default_permission_broker_service(
        evaluator=auth_svc.evaluator, vault_cipher=auth_svc.vault_cipher
    )  # fmt: skip
    svc = build_default_system_bootstrap_service(
        auth_service=auth_svc, catalog_service=cat_svc, permission_broker_service=broker_svc
    )  # fmt: skip
    karim = auth_svc.resolve_user(persona_key="karim")
    marc = auth_svc.resolve_user(persona_key="marc")
    claire = auth_svc.resolve_user(persona_key="claire")

    assert len(svc.list_workflows()) == 6 and len(svc.list_runs()) == 2
    assert len(svc.list_onboarding_states()) == 2

    org_payload = InitOrganizationInput(
        "ORCIA Enterprise Holding", True, True,
        {"PLATFORM_ADMIN": "orcia-admins", "TEAM_LEAD": "orcia-leads"},
        tuple(svc.model_router.list_endpoints()),
    )  # fmt: skip
    with pytest.raises(ScopeAccessDeniedError):
        svc.execute_init_organization(marc, org_payload)
    with pytest.raises(ObserverModeReadOnlyError):
        svc.execute_init_organization(claire, org_payload)
    org_run = svc.execute_init_organization(karim, org_payload)
    assert org_run.status == "COMPLETED" and org_run.gate_passed is True

    ws_payload = InitWorkspaceInput(
        team_slug="team-archi-paiement", team_name="Équipe Architecture Paiement",
        parent_org_unit_id="0192c4e0-0000-7000-8000-000000000102",
        subteam_slug="subteam-fraud-ops", subteam_name="Sous-Équipe Fraud Ops",
        team_override_scalars={"squad_channel": "#fraud-ops"},
        team_ontology_terms=(OntologyTermSpec("fraud_score", "Score de risque", "3_TEAM"),),
        workspaces=(
            WorkspaceBootstrapInput(
                "ws-paiement-3ds", "WS 3DS", workspace_override_scalars={"slug": "3ds"}
            ),
            WorkspaceBootstrapInput(
                "ws-paiement-sepa", "WS SEPA", workspace_override_scalars={"slug": "sepa"}
            ),
        ),
        invited_members=(
            MemberInvitationInput("nadia.dev@orcia.io", "Nadia Dev", "DEVELOPER", "CONTRIBUTOR"),
        ),
    )  # fmt: skip
    ws_outcome = svc.execute_init_workspace(marc, ws_payload)
    assert ws_outcome.run.status == "COMPLETED" and len(ws_outcome.workspaces) == 2
    eff_wf = cat_svc.resolve_effective_workflow(
        marc,
        workflow_uri="db://orcia/catalog/payment-delivery-workflow@v1.2.0",
        workspace_id=ws_outcome.workspaces[0].id,
    )  # fmt: skip
    assert "ovr-team-team-archi-paiement" in eff_wf.applied_override_keys
    assert "ovr-ws-ws-paiement-3ds" in eff_wf.applied_override_keys

    bad_ws = InitWorkspaceInput(
        team_slug="team-archi-paiement", team_name="Équipe Architecture Paiement",
        parent_org_unit_id="0192c4e0-0000-7000-8000-000000000102",
        team_ontology_terms=(OntologyTermSpec("term_x", "Définition Équipe", "3_TEAM"),),
        workspaces=(
            WorkspaceBootstrapInput(
                "ws-conflict", "WS Conflict",
                workspace_ontology_terms=(OntologyTermSpec("term_x", "Conflit", "3_WORKSPACE"),),
            ),
        ),
    )  # fmt: skip
    with pytest.raises(ValidationDomainError, match="Ontology conflict"):
        svc.execute_init_workspace(marc, bad_ws)

    ws_id = ws_outcome.workspaces[0].id
    uri_3ds = "git://gitlab.entreprise.io/payments/3ds-engine@v1.0.0"
    with pytest.raises(HumanAnchorRequiredError):
        svc.execute_init_datasource(marc, InitDatasourceInput(ws_id, "git-3ds", "git", uri_3ds, "3DS", 14, VALID_POLICY_MD, "Court", ""))  # noqa: E501  # fmt: skip
    ds_outcome = svc.execute_init_datasource(
        marc,
        InitDatasourceInput(
            ws_id, "git-3ds-engine", "git", uri_3ds, "Dépôt 3DS Engine", 14, VALID_POLICY_MD,
            "Validation humaine explicite par Marc (Tech Lead) pour les sources 3DS Engine.",
            "sig-marc-lead-3ds-2026", visibility_scope="SHARED_TEAM",
        ),
    )  # fmt: skip
    assert ds_outcome.run.status == "COMPLETED" and ds_outcome.datasource.alias == "git-3ds-engine"
    assert ds_outcome.catalog_item.visibility_scope == "SHARED_TEAM"

    with pytest.raises(ScopeAccessDeniedError):
        svc.execute_init_user(marc, InitUserInput("TECH_LEAD", (InitUserPassthroughSecretInput("git", "gitlab.entreprise.io", "sec"),), "karim.admin@orcia.io"))  # noqa: E501  # fmt: skip
    user_outcome = svc.execute_init_user(
        marc,
        InitUserInput(
            confirmed_human_profile_archetype="TECH_LEAD",
            passthrough_secrets=(
                InitUserPassthroughSecretInput("git", "gitlab.entreprise.io", "glpat-secret-12345"),
                InitUserPassthroughSecretInput("jira", "PAYSEC", "jira-pat-secret-67890"),
            ),
        ),
    )  # fmt: skip
    assert user_outcome.run.status == "COMPLETED"
    assert user_outcome.onboarding_state.init_user_completed is True
    assert len(user_outcome.credentials) == 2


async def test_fastapi_bootstrap_routes_and_maintenance_script_04() -> None:
    """Verify `/api/v1/bootstrap/*` endpoints (200/422) and `04_backfill_system_bootstrap.py`."""
    client = TestClient(create_app())
    state_res = client.get("/api/v1/bootstrap/state?persona_key=marc")
    assert state_res.status_code == 200 and len(state_res.json()["workflows"]) == 6

    org_base = {
        "organization_name": "ORCIA Root", "oidc_enabled": True,
        "local_argon2id_enabled": True, "rbac_role_mappings": {"PLATFORM_ADMIN": "admins"},
    }  # fmt: skip
    bad_org = client.post(
        "/api/v1/bootstrap/init-organization?persona_key=karim",
        json={**org_base, "llm_endpoints": [state_res.json()["llm_endpoints"][0]]},
    )
    assert bad_org.status_code == 422
    assert bad_org.json()["error_code"] == "ERR_MODEL_ORTHOGONALITY_VIOLATION"

    ws_id = "0192c4e0-0000-7000-8000-000000000201"
    ds_base = {
        "workspace_id": ws_id, "alias": "git-core", "scheme": "git",
        "uri": "git://gitlab.entreprise.io/payments/core@v1.0.0", "role": "Core Repo",
        "freshness_ttl_days": 14, "permission_broker_markdown": VALID_POLICY_MD,
    }  # fmt: skip
    bad_ds = client.post(
        "/api/v1/bootstrap/init-datasource?persona_key=marc",
        json={**ds_base, "human_anchor_justification": "trop court", "human_anchor_signature": "s"},
    )
    assert bad_ds.status_code == 422 and bad_ds.json()["error_code"] == "ERR_HUMAN_ANCHOR_REQUIRED"

    ok_org = client.post(
        "/api/v1/bootstrap/init-organization?persona_key=karim",
        json={**org_base, "llm_endpoints": state_res.json()["llm_endpoints"]},
    )
    assert ok_org.status_code == 200
    ok_ws = client.post(
        "/api/v1/bootstrap/init-workspace?persona_key=marc",
        json={
            "team_slug": "team-archi-paiement", "team_name": "Équipe Architecture Paiement",
            "parent_org_unit_id": "0192c4e0-0000-7000-8000-000000000102",
            "workspaces": [{"slug": "ws-api-test", "name": "WS API Test"}],
        },
    )  # fmt: skip
    assert ok_ws.status_code == 200 and len(ok_ws.json()["workspaces"]) == 1
    ok_ds = client.post(
        "/api/v1/bootstrap/init-datasource?persona_key=marc",
        json={
            **ds_base,
            "human_anchor_justification": "Validation humaine par Marc du dépôt Core Repo.",
            "human_anchor_signature": "sig-marc-core",
        },
    )  # fmt: skip
    assert ok_ds.status_code == 200 and ok_ds.json()["datasource"]["alias"] == "git-core"
    ok_usr = client.post(
        "/api/v1/bootstrap/init-user?persona_key=nadia",
        json={
            "confirmed_human_profile_archetype": "DEVELOPER",
            "passthrough_secrets": [
                {
                    "connector_scheme": "git", "target_host": "gitlab.entreprise.io",
                    "plaintext_secret": "glpat-nadia-secret-999",
                }
            ],
        },
    )  # fmt: skip
    assert ok_usr.status_code == 200 and ok_usr.json()["onboarding_state"]["init_user_completed"]
    chk = client.post(
        "/api/v1/permissions/broker/check-access?persona_key=nadia",
        json={
            "target_uri": "git://gitlab.entreprise.io/payments/core@v1.0.0",
            "step_key": "step-01", "execution_identity": "passthrough", "workspace_id": ws_id,
            "granted_external_roles": ["Maintainer GitLab Payments"],
        },
    )  # fmt: skip
    assert chk.status_code == 200 and chk.json()["allowed"] is True

    mod04 = _load_script_04()
    ns = mod04.build_arg_parser().parse_args(["--dry-run", "--batch-size", "10"])
    assert ns.apply is False and ns.batch_size == 10
    mock_conn, mock_res, mock_engine, mock_ctx = AsyncMock(), MagicMock(), MagicMock(), AsyncMock()
    mock_res.scalar.return_value = 6
    mock_conn.execute.return_value = mock_res
    mock_ctx.__aenter__.return_value = mock_conn
    mock_engine.connect.return_value = mock_ctx
    mock_engine.dispose = AsyncMock()
    with patch.object(mod04, "create_async_engine", return_value=mock_engine):
        assert await mod04._async_main(["--dry-run"]) == 0
