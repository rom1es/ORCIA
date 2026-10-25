"""Layer 1 Unit, Property-Based (`hypothesis`), and FastAPI Route Tests for Story 1.4 (`AD-17`).

Covers:
- `parse_permission_kb_markdown`: YAML frontmatter validation (`uri_pattern`, `required_role`,
  `approver_team`, `request_url_template`, `sla_hours <= 720`, `freshness_ttl_days <= 3650`).
- `build_prefilled_jira_request_url`: URL encoding safety (`hypothesis` property test).
- `PermissionBrokerService`: `passthrough` default vs `service_principal` anti-Confused Deputy
  guard (`ConfusedDeputyBlockedError`), `401/403` interception (`PermissionBrokerDeniedError`
  with RFC 9457 `permission_broker_hint`), `PassthroughVaultCipher` credential validation,
  `PAUSE` / `REPLAY` / `GRANTED` lifecycle, and `READ_ONLY_OBSERVER` + `workspace_id` guards.
- FastAPI `/api/v1/permissions/broker/*` routes.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from orcia_api.main import create_app
from orcia_core.domain.exceptions import (
    ConfusedDeputyBlockedError,
    ObserverModeReadOnlyError,
    PermissionBrokerDeniedError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)
from orcia_core.permissions import (
    CatalogAclEntry,
    PermissionBrokerService,
    build_default_auth_and_org_service,
    build_default_permission_broker_service,
    build_prefilled_jira_request_url,
    extract_connector_scheme,
    parse_permission_kb_markdown,
)

VALID_KB_MARKDOWN = """---
uri_pattern: "git://github.enterprise/payments/*"
required_role: "ROLE_GIT_PAYMENTS_CORE"
approver_team: "SecOps & Payments IAM"
request_url_template: "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa?pid=10420&summary={summary}&description={description}"
sla_hours: 4
service_principal_allowed: false
human_anchor_author_id: "0192c4e0-0000-7000-8000-000000000601"
human_anchor_signature: "SIG-KARIM-2026"
freshness_ttl_days: 60
---
### Procédure d'accès Git Payments
Valider via Jira IAM.
"""


def test_parse_permission_kb_markdown_valid_and_invalid_cases() -> None:
    """Verify KB Markdown+YAML parsing and rejection of malformed frontmatter or bounds."""
    policy = parse_permission_kb_markdown(VALID_KB_MARKDOWN, policy_key="pol-custom-git")
    assert policy.policy_key == "pol-custom-git"
    assert policy.connector_scheme == "git"
    assert policy.required_role == "ROLE_GIT_PAYMENTS_CORE"
    assert policy.approver_team == "SecOps & Payments IAM"
    assert policy.sla_hours == 4
    assert policy.freshness_ttl_days == 60
    assert policy.human_anchor_signature == "SIG-KARIM-2026"
    assert extract_connector_scheme("mcp:// enterprise-gateway/tool") == "mcp"

    invalid_docs = (
        "No frontmatter at all",
        "---\nuri_pattern: git://a/b\nOnly opening delimiter",
        "---\nmalformed_line_without_colon\n---\nbody",
        "---\nuri_pattern: git://a/b\nrequired_role: R\n---\nmissing keys",
        VALID_KB_MARKDOWN.replace("https://", "http://"),
        VALID_KB_MARKDOWN.replace("sla_hours: 4", "sla_hours: not_an_int"),
        VALID_KB_MARKDOWN.replace("sla_hours: 4", "sla_hours: 0"),
        VALID_KB_MARKDOWN.replace("sla_hours: 4", "sla_hours: 721"),
        VALID_KB_MARKDOWN.replace("freshness_ttl_days: 60", "freshness_ttl_days: 3651"),
        VALID_KB_MARKDOWN.replace("ROLE_GIT_PAYMENTS_CORE", "R" * 130),
        VALID_KB_MARKDOWN.replace("git://", "ftp://"),
        VALID_KB_MARKDOWN.replace("git://github.enterprise/payments/*", "git://"),
        VALID_KB_MARKDOWN.replace("git://github.enterprise/payments/*", "no-scheme"),
        VALID_KB_MARKDOWN.replace("ROLE_GIT_PAYMENTS_CORE", "ROLE\x00BAD"),
    )
    for bad_doc in invalid_docs:
        with pytest.raises(ValidationDomainError):
            parse_permission_kb_markdown(bad_doc)
    with pytest.raises(ValidationDomainError):
        parse_permission_kb_markdown(VALID_KB_MARKDOWN, policy_key="k" * 130)


@given(
    role=st.text(
        alphabet=st.characters(blacklist_categories=("Cc", "Cs")), min_size=1, max_size=40
    ),
    team=st.text(
        alphabet=st.characters(blacklist_categories=("Cc", "Cs")), min_size=1, max_size=40
    ),
    email=st.emails(),
)
@settings(max_examples=20)
def test_hypothesis_jira_request_url_never_contains_raw_spaces_or_unencoded_injections(
    role: str, team: str, email: str
) -> None:
    """Property test: generated Jira request URLs are always URL-encoded without raw spaces."""
    tpl = "https://jira.enterprise.internal/create?summary={summary}&description={description}"
    url = build_prefilled_jira_request_url(
        tpl,
        target_uri="git://github.enterprise/payments/checkout-core.git?foo=1&bar=2",
        required_role=role,
        approver_team=team,
        requester_email=email,
        step_key="step-02-execution",
        execution_identity="passthrough",
    )
    assert url.startswith("https://jira.enterprise.internal/create?")
    assert " " not in url

    fallback_url = build_prefilled_jira_request_url(
        "https://jira.enterprise.internal/secure/CreateIssue!default.jspa",
        target_uri="jira://SECOPS/SEC-108",
        required_role="ROLE_SEC",
        approver_team="CSIRT",
        requester_email=email,
        step_key="step-01",
        execution_identity="passthrough",
    )
    assert "summary=" in fallback_url and "description=" in fallback_url


def test_permission_broker_passthrough_vs_service_principal_and_ticket_lifecycle() -> None:
    """Verify passthrough default, Confused Deputy block, 401/403 interception, and Replay Step."""
    auth_svc = build_default_auth_and_org_service()
    broker = build_default_permission_broker_service(
        evaluator=auth_svc.evaluator, vault_cipher=auth_svc.vault_cipher
    )

    karim = auth_svc.resolve_user(persona_key="karim")
    nadia = auth_svc.resolve_user(persona_key="nadia")
    claire = auth_svc.resolve_user(persona_key="claire")
    marc = auth_svc.resolve_user(persona_key="marc")
    partenaire = auth_svc.resolve_user(persona_key="partenaire")

    # 1. Unapproved service_principal raises ConfusedDeputyBlockedError (HTTP 403)
    with pytest.raises(ConfusedDeputyBlockedError) as exc_cd:
        broker.check_or_intercept_access(
            nadia,
            target_uri="git://github.enterprise/payments/checkout-core.git",
            execution_identity="service_principal",
        )
    assert exc_cd.value.error_code == "ERR_CONFUSED_DEPUTY_BLOCKED"

    # Non-admin cannot import a policy with service_principal_allowed=True
    sp_md = VALID_KB_MARKDOWN.replace(
        "service_principal_allowed: false", "service_principal_allowed: true"
    )
    with pytest.raises(ConfusedDeputyBlockedError):
        broker.import_policy_markdown(marc, sp_md)
    sp_pol = broker.import_policy_markdown(karim, sp_md, policy_key="pol-git-payments-checkout")
    assert sp_pol.id == "0192c4e0-0000-7000-8000-000000001001"
    assert sp_pol.approved_by_admin_id == karim.id

    # 2. Approved service_principal on git://*/archi/* succeeds
    sp_outcome = broker.check_or_intercept_access(
        marc,
        target_uri="git://gitlab.entreprise.io/archi/security-audit-agent@v2.1.0",
        execution_identity="service_principal",
        simulated_upstream_status=200,
    )
    assert sp_outcome.allowed is True
    assert sp_outcome.status == "GRANTED"

    # 3. Passthrough status=None: denied without role, granted with role or vault
    no_role = broker.check_or_intercept_access(
        nadia,
        target_uri="confluence://PAY/Architecture-PCI@v4",
        execution_identity="passthrough",
        simulated_upstream_status=None,
        raise_on_denied=False,
    )
    assert no_role.allowed is False
    with_role = broker.check_or_intercept_access(
        nadia,
        target_uri="confluence://PAY/Architecture-PCI@v4",
        execution_identity="passthrough",
        granted_external_roles=("CONFLUENCE_PAY_ADR_READER",),
    )
    assert with_role.allowed is True and with_role.status == "GRANTED"

    cred = auth_svc.store_passthrough_credential(
        nadia,
        connector_scheme="git",
        target_host="github.enterprise",
        plaintext_secret="pat-secret",
    )
    broker.register_passthrough_credential(cred)
    with_cred = broker.check_or_intercept_access(
        nadia,
        target_uri="git://github.enterprise/payments/checkout-core.git",
        execution_identity="passthrough",
    )
    assert with_cred.allowed is True

    # 4. Passthrough with missing role raises PermissionBrokerDeniedError with hint
    with pytest.raises(PermissionBrokerDeniedError) as exc_denied:
        broker.check_or_intercept_access(
            nadia,
            target_uri="confluence://PAY/Architecture-PCI@v4",
            execution_identity="passthrough",
            simulated_upstream_status=403,
            raise_on_denied=True,
        )
    assert exc_denied.value.error_code == "ERR_PERMISSION_BROKER_INTERCEPTED"
    assert exc_denied.value.permission_broker_hint is not None
    assert "CONFLUENCE_PAY_ADR_READER" in exc_denied.value.permission_broker_hint

    # 5. Non-raising check returns WAITING_FOR_PERMISSION ticket, then PAUSE, REPLAY, and GRANTED
    outcome = broker.check_or_intercept_access(
        nadia,
        target_uri="jira://SECOPS/SEC-108",
        execution_identity="passthrough",
        step_key="step-04-jira",
        step_number=4,
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        simulated_upstream_status=401,
        raise_on_denied=False,
    )
    assert outcome.allowed is False and outcome.ticket is not None
    assert outcome.ticket.upstream_http_status == 401

    with pytest.raises(ObserverModeReadOnlyError):
        broker.apply_ticket_action(claire, outcome.ticket.id, "PAUSE")
    with pytest.raises(ObserverModeReadOnlyError):
        broker.import_policy_markdown(claire, VALID_KB_MARKDOWN)
    with pytest.raises(ScopeAccessDeniedError):
        broker.list_tickets("0192c4e0-0000-7000-8000-000000000202", user=partenaire)

    paused = broker.apply_ticket_action(
        nadia, outcome.ticket.id, "PAUSE", workspace_id="0192c4e0-0000-7000-8000-000000000201"
    )
    assert paused.step_state == "PAUSED" and paused.status == "PAUSED"

    replayed = broker.apply_ticket_action(nadia, outcome.ticket.ticket_key, "REPLAY")
    assert replayed.step_state == "REPLAYED" and replayed.status == "REPLAYED"
    with pytest.raises(ValidationDomainError):
        broker.apply_ticket_action(nadia, outcome.ticket.id, "PAUSE")
    granted = broker.apply_ticket_action(nadia, outcome.ticket.id, "REPLAY", grant_permission=True)
    assert granted.status == "GRANTED"

    with pytest.raises(ResourceNotFoundError):
        broker.apply_ticket_action(nadia, "non-existent-ticket", "REPLAY")
    with pytest.raises(ValidationDomainError):
        broker.check_or_intercept_access(
            nadia, target_uri="git://github.enterprise/payments/checkout-core.git", step_number=0
        )

    # 6. Catalog resource missing EXECUTE is intercepted even when resource_id is None (by URI)
    auth_svc.evaluator.upsert_catalog_acl(
        CatalogAclEntry(
            id="0192c4e0-0000-7000-8000-000000000599",
            resource_id="res-discover-only-git",
            resource_uri="git://github.enterprise/payments/locked-skill",
            title="Skill Discover Only",
            visibility_scope="SHARED_TEAM",
            owner_org_unit_id=nadia.primary_org_unit_id,
            can_discover=True,
            can_execute=False,
        )
    )
    no_exec = broker.check_or_intercept_access(
        nadia,
        target_uri="git://github.enterprise/payments/locked-skill",
        raise_on_denied=False,
    )
    assert no_exec.allowed is False

    # Unmapped URI on existing scheme raises ResourceNotFoundError (no cross-pattern fallback)
    with pytest.raises(ResourceNotFoundError):
        broker.resolve_matching_policy("git://github.enterprise/hr/payroll.git")
    empty_broker = PermissionBrokerService(policies=())
    with pytest.raises(ResourceNotFoundError):
        empty_broker.resolve_matching_policy("mcp://unknown/server")


def test_fastapi_permission_broker_endpoints_and_rfc9457_hint() -> None:
    """Verify FastAPI `/api/v1/permissions/broker/*` routes, RFC 9457 hint, and workspace filter."""
    client = TestClient(create_app())

    state_resp = client.get(
        "/api/v1/permissions/broker/state?persona_key=marc&workspace_id=0192c4e0-0000-7000-8000-000000000201"
    )
    assert state_resp.status_code == 200
    assert len(state_resp.json()["policies"]) >= 6
    assert len(state_resp.json()["tickets"]) >= 1

    # Partenaire cannot query Workspace 2 state -> 403 ERR_SCOPE_ACCESS_DENIED
    unauth_ws = client.get(
        "/api/v1/permissions/broker/state?persona_key=partenaire&workspace_id=0192c4e0-0000-7000-8000-000000000202"
    )
    assert unauth_ws.status_code == 403
    assert unauth_ws.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

    imp_resp = client.post(
        "/api/v1/permissions/broker/policies/import-markdown?persona_key=marc",
        json={"markdown_text": VALID_KB_MARKDOWN, "policy_key": "pol-git-payments-checkout"},
    )
    assert imp_resp.status_code == 200
    assert imp_resp.json()["policy"]["id"] == "0192c4e0-0000-7000-8000-000000001001"
    assert imp_resp.json()["policy"]["required_role"] == "ROLE_GIT_PAYMENTS_CORE"

    obs_resp = client.post(
        "/api/v1/permissions/broker/policies/import-markdown?persona_key=claire",
        json={"markdown_text": VALID_KB_MARKDOWN},
    )
    assert obs_resp.status_code == 403
    assert obs_resp.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    denied_resp = client.post(
        "/api/v1/permissions/broker/check-access?persona_key=nadia",
        json={
            "target_uri": "git://github.enterprise/payments/checkout-core.git",
            "execution_identity": "passthrough",
            "simulated_upstream_status": 403,
            "raise_on_denied": True,
        },
        headers={"Accept-Language": "fr"},
    )
    assert denied_resp.status_code == 403
    assert denied_resp.json()["error_code"] == "ERR_PERMISSION_BROKER_INTERCEPTED"
    assert denied_resp.json()["permission_broker_hint"].startswith("jira://IAM/")

    ticket_resp = client.post(
        "/api/v1/permissions/broker/check-access?persona_key=nadia",
        json={
            "target_uri": "confluence://PAY/Architecture-PCI@v4",
            "execution_identity": "passthrough",
            "simulated_upstream_status": 403,
            "raise_on_denied": False,
        },
    )
    assert ticket_resp.status_code == 200
    ticket_id = ticket_resp.json()["ticket"]["id"]

    replay_resp = client.post(
        f"/api/v1/permissions/broker/tickets/{ticket_id}/action?persona_key=nadia",
        json={"action": "REPLAY"},
    )
    assert replay_resp.status_code == 200
    assert replay_resp.json()["ticket"]["status"] == "REPLAYED"
