"""Story 17.4 — Unit tests for Enterprise Connectors, AES-256-GCM Passthrough & RAG Referent Health.

Covers:
1. Anti-SSRF URL validation (`HTTP 422 ERR_UNSAFE_CONNECTOR_ENDPOINT_URL` on cloud metadata /
   link-local IPs, accepts `.internal` / `.local` enterprise domains).
2. `AD-21` Write-Only `SecretStatus` (`sha256:<8-hex>`) + `AES-256-GCM` encryption via
   `PassthroughVaultCipher` (canary secret never exposed in DTO/view dicts).
3. Deterministic `TEAM_REFERENT_USER` sync health state machine (`ACTIVE` vs
   `PAUSED_REFERENT_RENEWAL_REQUIRED` with `REFERENT_LEFT_TEAM`, `REFERENT_ACCOUNT_DISABLED`,
   and `REFERENT_TOKEN_MISSING`, plus renewal back to `ACTIVE`).
"""

from __future__ import annotations

from dataclasses import asdict

import pytest

from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.enterprise_connectors import (
    EnterpriseConnectorsGovernanceService,
    evaluate_datasource_sync_health,
    pack_encrypted_secret,
    unpack_encrypted_secret,
    validate_safe_connector_base_url,
)
from orcia_core.permissions.errors import UnsafeConnectorEndpointUrlError
from orcia_core.permissions.iam_accounts import IamAccountRecord
from orcia_core.permissions.models import OrgUnitNode

CANARY_ADMIN_SECRET = "CANARY-ADMIN-SECRET-17-4-JIRA-CLIENT"  # pragma: allowlist secret
CANARY_USER_PAT = "CANARY-USER-PAT-17-4-ROMAIN-ATTLASSIAN"  # pragma: allowlist secret


@pytest.mark.parametrize(
    "unsafe_url",
    [
        "",
        "   ",
        "ftp://gitlab.ds3c.internal/api",
        "http://169.254.169.254/latest/meta-data/",
        "https://169.254.10.42/iam/security-credentials",
        "http://[fe80::1]/metadata",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://sub.google.internal/token",
        "http://100.100.100.200/latest/meta-data/",
        "http://0.0.0.0:8080/",
    ],
)
def test_validate_safe_connector_base_url_rejects_ssrf_targets(unsafe_url: str) -> None:
    with pytest.raises(UnsafeConnectorEndpointUrlError) as exc_info:
        validate_safe_connector_base_url(unsafe_url, instance="/api/v1/settings/connectors")
    assert exc_info.value.http_status == 422
    assert exc_info.value.error_code == "ERR_UNSAFE_CONNECTOR_ENDPOINT_URL"


@pytest.mark.parametrize(
    ("valid_url", "expected"),
    [
        ("https://gitlab.ds3c.internal/", "https://gitlab.ds3c.internal"),
        ("https://jira.corp.local:8443", "https://jira.corp.local:8443"),
        ("https://confluence.entreprise.fr/wiki/", "https://confluence.entreprise.fr/wiki"),
        (
            "https://sso.entreprise.internal/realms/orcia",
            "https://sso.entreprise.internal/realms/orcia",
        ),
    ],
)
def test_validate_safe_connector_base_url_accepts_internal_domains(
    valid_url: str, expected: str
) -> None:
    assert validate_safe_connector_base_url(valid_url) == expected


def test_aes_256_gcm_passthrough_encryption_and_write_only_secret_status() -> None:
    cipher = PassthroughVaultCipher("orcia-unit-test-master-key-story-17-4")
    svc = EnterpriseConnectorsGovernanceService(vault_cipher=cipher)

    jira = svc.create_connector(
        connector_kind="JIRA",
        name="Jira Entreprise DS3C",
        base_url="https://jira.ds3c.internal/",
        auth_mode="PERSONAL_ACCESS_TOKEN",
        admin_secret_value=CANARY_ADMIN_SECRET,
    )
    assert jira.admin_secret_status.configured is True
    assert jira.admin_secret_status.fingerprint is not None
    assert jira.admin_secret_status.fingerprint.startswith("sha256:")
    assert len(jira.admin_secret_status.fingerprint) == len("sha256:") + 8
    assert CANARY_ADMIN_SECRET not in repr(asdict(jira))

    # Connector without admin secret (Passthrough OAuth2 / OIDC)
    gitlab = svc.create_connector(
        connector_kind="GITLAB",
        name="GitLab Entreprise",
        base_url="https://gitlab.ds3c.internal",
        auth_mode="OAUTH2_PASSTHROUGH",
    )
    assert gitlab.admin_secret_status.configured is False
    assert gitlab.admin_secret_status.fingerprint is None

    # User personal passthrough token encrypted at rest with AES-256-GCM
    tok_view = svc.upsert_user_passthrough_token(
        user_id="romain@orcia.fr",
        connector_id=jira.id,
        external_author_login="romain.esnault",
        secret_value=CANARY_USER_PAT,
    )
    assert tok_view.connected is True
    assert tok_view.external_author_login == "romain.esnault"
    assert tok_view.secret_status.configured is True
    assert tok_view.secret_status.fingerprint is not None
    assert tok_view.secret_status.fingerprint.startswith("sha256:")
    assert CANARY_USER_PAT not in repr(asdict(tok_view))

    # Direct AES-256-GCM pack/unpack roundtrip verification
    packed = pack_encrypted_secret(
        cipher,
        owner_id="romain@orcia.fr",
        plaintext=CANARY_USER_PAT,
        scheme="jira",
        host="jira.ds3c.internal",
    )
    assert CANARY_USER_PAT not in packed
    assert (
        unpack_encrypted_secret(
            cipher,
            owner_id="romain@orcia.fr",
            packed=packed,
            scheme="jira",
            host="jira.ds3c.internal",
        )
        == CANARY_USER_PAT
    )

    # Clear admin secret via PATCH action
    patched = svc.update_connector(jira.id, clear_admin_secret=True)
    assert patched.admin_secret_status.configured is False
    assert patched.admin_secret_status.fingerprint is None


def test_team_referent_rag_sync_health_state_machine() -> None:
    team_portail = OrgUnitNode(
        id="team-portail",
        slug="equipe-portail",
        name="Équipe Portail",
        unit_type="TEAM",
        parent_id="bu-ds3c",
        billing_enabled=True,
        lead_user_id="alice@orcia.fr",
        member_user_ids=("romain@orcia.fr", "claire@orcia.fr"),
    )
    romain_active = IamAccountRecord(
        id="acc-romain",
        principal_id="romain@orcia.fr",
        display_name="Romain",
        email="romain@orcia.fr",
        account_kind="HUMAN",
        auth_source="OIDC_FEDERATED",
        roles=("CONTRIBUTOR",),
        team_ids=("team-portail",),
        status="ACTIVE",
        created_at_iso="2026-11-11T10:00:00+00:00",
        updated_at_iso="2026-11-11T10:00:00+00:00",
    )
    claire_active = IamAccountRecord(
        id="acc-claire",
        principal_id="claire@orcia.fr",
        display_name="Claire",
        email="claire@orcia.fr",
        account_kind="HUMAN",
        auth_source="OIDC_FEDERATED",
        roles=("TEAM_LEAD",),
        team_ids=("team-portail",),
        status="ACTIVE",
        created_at_iso="2026-11-11T10:00:00+00:00",
        updated_at_iso="2026-11-11T10:00:00+00:00",
    )

    # 1. SERVICE_ACCOUNT mode is always ACTIVE
    assert evaluate_datasource_sync_health(
        sync_identity_mode="SERVICE_ACCOUNT",
        referent_user_id=None,
        connector_id="conn-jira",
        owner_org_unit=team_portail,
        iam_accounts=[romain_active],
        active_token_pairs=set(),
    ) == ("ACTIVE", None)

    # 2. TEAM_REFERENT_USER with active member + active token -> ACTIVE
    assert evaluate_datasource_sync_health(
        sync_identity_mode="TEAM_REFERENT_USER",
        referent_user_id="romain@orcia.fr",
        connector_id="conn-jira",
        owner_org_unit=team_portail,
        iam_accounts=[romain_active, claire_active],
        active_token_pairs={("romain@orcia.fr", "conn-jira")},
    ) == ("ACTIVE", None)

    # 3. Referent leaves team -> PAUSED_REFERENT_RENEWAL_REQUIRED (REFERENT_LEFT_TEAM)
    team_without_romain = OrgUnitNode(
        id="team-portail",
        slug="equipe-portail",
        name="Équipe Portail",
        unit_type="TEAM",
        parent_id="bu-ds3c",
        billing_enabled=True,
        lead_user_id="alice@orcia.fr",
        member_user_ids=("claire@orcia.fr",),
    )
    assert evaluate_datasource_sync_health(
        sync_identity_mode="TEAM_REFERENT_USER",
        referent_user_id="romain@orcia.fr",
        connector_id="conn-jira",
        owner_org_unit=team_without_romain,
        iam_accounts=[romain_active, claire_active],
        active_token_pairs={("romain@orcia.fr", "conn-jira")},
    ) == ("PAUSED_REFERENT_RENEWAL_REQUIRED", "REFERENT_LEFT_TEAM")

    # 4. Referent account disabled -> PAUSED_REFERENT_RENEWAL_REQUIRED (REFERENT_ACCOUNT_DISABLED)
    romain_disabled = IamAccountRecord(
        id="acc-romain",
        principal_id="romain@orcia.fr",
        display_name="Romain",
        email="romain@orcia.fr",
        account_kind="HUMAN",
        auth_source="OIDC_FEDERATED",
        roles=("CONTRIBUTOR",),
        team_ids=("team-portail",),
        status="DISABLED",
        created_at_iso="2026-11-11T10:00:00+00:00",
        updated_at_iso="2026-11-11T10:00:00+00:00",
    )
    assert evaluate_datasource_sync_health(
        sync_identity_mode="TEAM_REFERENT_USER",
        referent_user_id="romain@orcia.fr",
        connector_id="conn-jira",
        owner_org_unit=team_portail,
        iam_accounts=[romain_disabled, claire_active],
        active_token_pairs={("romain@orcia.fr", "conn-jira")},
    ) == ("PAUSED_REFERENT_RENEWAL_REQUIRED", "REFERENT_ACCOUNT_DISABLED")

    # 5. Referent token revoked/missing -> PAUSED_REFERENT_RENEWAL_REQUIRED (REFERENT_TOKEN_MISSING)
    assert evaluate_datasource_sync_health(
        sync_identity_mode="TEAM_REFERENT_USER",
        referent_user_id="romain@orcia.fr",
        connector_id="conn-jira",
        owner_org_unit=team_portail,
        iam_accounts=[romain_active, claire_active],
        active_token_pairs=set(),
    ) == ("PAUSED_REFERENT_RENEWAL_REQUIRED", "REFERENT_TOKEN_MISSING")

    # 6. Renewing referent to Claire (active member + active token) restores ACTIVE
    assert evaluate_datasource_sync_health(
        sync_identity_mode="TEAM_REFERENT_USER",
        referent_user_id="claire@orcia.fr",
        connector_id="conn-jira",
        owner_org_unit=team_without_romain,
        iam_accounts=[romain_active, claire_active],
        active_token_pairs={("claire@orcia.fr", "conn-jira")},
    ) == ("ACTIVE", None)
