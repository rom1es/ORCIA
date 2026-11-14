"""Story 17.4 — Domain Model for Enterprise Connectors, Passthrough & RAG Referent.

Zero SQL / FastAPI imports:
- Anti-SSRF URL validation (`validate_safe_connector_base_url`)
- `AES-256-GCM` secret packing via `PassthroughVaultCipher` + `ConnectorSecretStatus`
- Deterministic `TEAM_REFERENT_USER` RAG sync health state machine
- In-memory `EnterpriseConnectorsGovernanceService` for unit tests & non-PG mode
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlparse

from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.errors import (
    ResourceNotFoundError,
    UnsafeConnectorEndpointUrlError,
    ValidationDomainError,
)
from orcia_core.permissions.iam_accounts import IamAccountRecord
from orcia_core.permissions.models import OrgUnitNode
from orcia_kernel.ids import new_uuid7_str

EnterpriseConnectorKind = Literal["GITLAB", "JIRA", "CONFLUENCE", "OIDC_SSO", "S3_OBJECT_STORE"]
EnterpriseConnectorAuthMode = Literal[
    "OAUTH2_PASSTHROUGH", "PERSONAL_ACCESS_TOKEN", "OIDC_FEDERATION", "SERVICE_SECRET"
]
SyncIdentityMode = Literal["SERVICE_ACCOUNT", "TEAM_REFERENT_USER"]
DatasourceSyncStatus = Literal["ACTIVE", "PAUSED_REFERENT_RENEWAL_REQUIRED"]
DatasourceSyncReason = Literal[
    "REFERENT_LEFT_TEAM", "REFERENT_ACCOUNT_DISABLED", "REFERENT_TOKEN_MISSING"
]

VALID_CONNECTOR_KINDS: tuple[EnterpriseConnectorKind, ...] = (
    "GITLAB",
    "JIRA",
    "CONFLUENCE",
    "OIDC_SSO",
    "S3_OBJECT_STORE",
)
VALID_CONNECTOR_AUTH_MODES: tuple[EnterpriseConnectorAuthMode, ...] = (
    "OAUTH2_PASSTHROUGH",
    "PERSONAL_ACCESS_TOKEN",
    "OIDC_FEDERATION",
    "SERVICE_SECRET",
)
VALID_SYNC_IDENTITY_MODES: tuple[SyncIdentityMode, ...] = (
    "SERVICE_ACCOUNT",
    "TEAM_REFERENT_USER",
)

_BLOCKED_METADATA_HOSTS: frozenset[str] = frozenset(
    {
        "169.254.169.254",
        "metadata.google.internal",
        "metadata",
        "100.100.100.200",
        "instance-data",
    }
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def validate_safe_connector_base_url(base_url: str, *, instance: str | None = None) -> str:
    """Validate `base_url` against SSRF while allowing `.local` and `.internal`."""
    raw = (base_url or "").strip()
    if not raw:
        raise UnsafeConnectorEndpointUrlError(instance=instance)
    try:
        parsed = urlparse(raw)
    except ValueError as exc:
        raise UnsafeConnectorEndpointUrlError(instance=instance) from exc
    if parsed.scheme not in ("http", "https"):
        raise UnsafeConnectorEndpointUrlError(instance=instance)
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host or host in _BLOCKED_METADATA_HOSTS or host.endswith(".google.internal"):
        raise UnsafeConnectorEndpointUrlError(instance=instance)
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_link_local or ip.is_unspecified or ip.is_multicast:
            raise UnsafeConnectorEndpointUrlError(instance=instance)
    except ValueError:
        pass
    return raw.rstrip("/")


def extract_url_host(url: str) -> str:
    """Extract lowercase hostname from `url` for `AES-256-GCM` AAD binding."""
    parsed = urlparse((url or "").strip())
    return (parsed.hostname or "default").strip().lower() or "default"


def compute_secret_fingerprint(entity_id: str, plaintext_secret: str) -> str:
    """Compute a deterministic salted Write-Only fingerprint (`sha256:<8-hex>`, `AD-21`)."""
    digest = hmac.new(
        f"orcia:secret-fp:{entity_id}".encode(),
        plaintext_secret.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"sha256:{digest[:8]}"


def pack_encrypted_secret(
    cipher: PassthroughVaultCipher,
    *,
    owner_id: str,
    plaintext: str,
    scheme: str,
    host: str,
) -> str:
    """Encrypt `plaintext` with `AES-256-GCM` and pack as `ciphertext_b64:nonce_b64`."""
    ct_b64, nonce_b64 = cipher.encrypt(
        owner_id,
        plaintext,
        connector_scheme=scheme.lower(),
        target_host=host.lower(),
    )
    return f"{ct_b64}:{nonce_b64}"


def unpack_encrypted_secret(
    cipher: PassthroughVaultCipher,
    *,
    owner_id: str,
    packed: str,
    scheme: str,
    host: str,
) -> str:
    """Verify `AES-256-GCM` tag and return plaintext for internal connector execution only."""
    parts = packed.split(":", 1)
    if len(parts) != 2:
        raise ValidationDomainError(detail_override="Malformed encrypted secret envelope.")
    return cipher.decrypt(
        owner_id,
        parts[0],
        parts[1],
        connector_scheme=scheme.lower(),
        target_host=host.lower(),
    )


@dataclass(frozen=True, slots=True)
class ConnectorSecretStatus:
    """Write-Only secret metadata (`AD-21` — never exposes raw secret value)."""

    configured: bool
    fingerprint: str | None = None
    updated_at_iso: str | None = None


@dataclass(frozen=True, slots=True)
class EnterpriseConnectorRecord:
    """Immutable view of a platform-level Enterprise Connector (`Connecteurs & SSO`)."""

    id: str
    connector_kind: EnterpriseConnectorKind
    name: str
    base_url: str
    auth_mode: EnterpriseConnectorAuthMode
    enabled: bool
    admin_secret_status: ConnectorSecretStatus
    created_at_iso: str
    updated_at_iso: str


@dataclass(frozen=True, slots=True)
class UserPassthroughConnectorView:
    """Per-user Passthrough connection status for one Enterprise Connector (`Mon Compte`)."""

    connector_id: str
    connector_name: str
    connector_kind: EnterpriseConnectorKind
    base_url: str
    auth_mode: EnterpriseConnectorAuthMode
    connected: bool
    external_author_login: str | None
    secret_status: ConnectorSecretStatus


@dataclass(frozen=True, slots=True)
class WorkspaceDatasourceRecord:
    """Workspace RAG datasource with `SERVICE_ACCOUNT` or `TEAM_REFERENT_USER` sync evaluation."""

    id: str
    workspace_id: str
    alias: str
    scheme: str
    uri: str
    connector_id: str | None
    sync_identity_mode: SyncIdentityMode
    service_account_id: str | None
    referent_user_id: str | None
    sync_status: DatasourceSyncStatus
    sync_status_reason: DatasourceSyncReason | None
    created_at_iso: str


def evaluate_datasource_sync_health(
    *,
    sync_identity_mode: SyncIdentityMode,
    referent_user_id: str | None,
    connector_id: str | None,
    owner_org_unit: OrgUnitNode | None,
    iam_accounts: Iterable[IamAccountRecord],
    active_token_pairs: set[tuple[str, str]],
) -> tuple[DatasourceSyncStatus, DatasourceSyncReason | None]:
    """Deterministically compute `ACTIVE` vs `PAUSED_REFERENT_RENEWAL_REQUIRED` (`CA-17.4.3`)."""
    if sync_identity_mode != "TEAM_REFERENT_USER":
        return ("ACTIVE", None)

    ref_raw = (referent_user_id or "").strip()
    if not ref_raw:
        return ("PAUSED_REFERENT_RENEWAL_REQUIRED", "REFERENT_LEFT_TEAM")
    ref_norm = ref_raw.lower()

    matched_account: IamAccountRecord | None = None
    candidate_identities: set[str] = {ref_norm}
    for acc in iam_accounts:
        keys = {
            acc.id.lower(),
            acc.principal_id.lower(),
            (acc.email or "").lower(),
        } - {""}
        if ref_norm in keys:
            matched_account = acc
            candidate_identities |= keys
            break

    if matched_account is not None and matched_account.status == "DISABLED":
        return ("PAUSED_REFERENT_RENEWAL_REQUIRED", "REFERENT_ACCOUNT_DISABLED")

    if owner_org_unit is not None and owner_org_unit.unit_type != "ENTERPRISE":
        team_members_norm = {m.strip().lower() for m in owner_org_unit.member_user_ids if m.strip()}
        if owner_org_unit.lead_user_id and owner_org_unit.lead_user_id.strip():
            team_members_norm.add(owner_org_unit.lead_user_id.strip().lower())
        in_account_teams = matched_account is not None and (
            owner_org_unit.id in matched_account.team_ids
            or owner_org_unit.slug in matched_account.team_ids
        )
        if not (candidate_identities & team_members_norm) and not in_account_teams:
            return ("PAUSED_REFERENT_RENEWAL_REQUIRED", "REFERENT_LEFT_TEAM")
        if (owner_org_unit.member_user_ids or owner_org_unit.lead_user_id) and not (
            candidate_identities & team_members_norm
        ):
            return ("PAUSED_REFERENT_RENEWAL_REQUIRED", "REFERENT_LEFT_TEAM")

    if connector_id:
        conn_norm = connector_id.strip().lower()
        normalized_pairs = {(u.lower(), c.lower()) for u, c in active_token_pairs}
        has_token = any((ident, conn_norm) in normalized_pairs for ident in candidate_identities)
        if not has_token:
            return ("PAUSED_REFERENT_RENEWAL_REQUIRED", "REFERENT_TOKEN_MISSING")

    return ("ACTIVE", None)


class EnterpriseConnectorsGovernanceService:
    """In-memory domain service for Enterprise Connectors, Passthrough tokens & RAG datasources."""

    def __init__(self, *, vault_cipher: PassthroughVaultCipher) -> None:
        self._cipher = vault_cipher
        self._connectors: dict[str, EnterpriseConnectorRecord] = {}
        self._encrypted_admin_secrets: dict[str, str] = {}
        self._user_tokens: dict[tuple[str, str], tuple[str | None, str, ConnectorSecretStatus]] = {}
        self._datasources: dict[str, list[WorkspaceDatasourceRecord]] = {}

    def list_connectors(self) -> list[EnterpriseConnectorRecord]:
        return list(self._connectors.values())

    def create_connector(
        self,
        *,
        connector_kind: EnterpriseConnectorKind,
        name: str,
        base_url: str,
        auth_mode: EnterpriseConnectorAuthMode,
        admin_secret_value: str | None = None,
        enabled: bool = True,
        instance: str | None = None,
    ) -> EnterpriseConnectorRecord:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValidationDomainError(
                detail_override="Connector name is required.",
                instance=instance,
            )
        safe_url = validate_safe_connector_base_url(base_url, instance=instance)
        cid = new_uuid7_str()
        now = _now_iso()
        sec_status = ConnectorSecretStatus(configured=False)
        if admin_secret_value and admin_secret_value.strip():
            plain = admin_secret_value.strip()
            self._encrypted_admin_secrets[cid] = pack_encrypted_secret(
                self._cipher,
                owner_id=f"admin:{cid}",
                plaintext=plain,
                scheme=connector_kind,
                host=extract_url_host(safe_url),
            )
            sec_status = ConnectorSecretStatus(
                configured=True,
                fingerprint=compute_secret_fingerprint(cid, plain),
                updated_at_iso=now,
            )
        record = EnterpriseConnectorRecord(
            id=cid,
            connector_kind=connector_kind,
            name=cleaned_name,
            base_url=safe_url,
            auth_mode=auth_mode,
            enabled=enabled,
            admin_secret_status=sec_status,
            created_at_iso=now,
            updated_at_iso=now,
        )
        self._connectors[cid] = record
        return record

    def update_connector(
        self,
        connector_id: str,
        *,
        name: str | None = None,
        base_url: str | None = None,
        auth_mode: EnterpriseConnectorAuthMode | None = None,
        enabled: bool | None = None,
        admin_secret_value: str | None = None,
        clear_admin_secret: bool = False,
        instance: str | None = None,
    ) -> EnterpriseConnectorRecord:
        existing = self._connectors.get(connector_id)
        if existing is None:
            raise ResourceNotFoundError(instance=instance)
        now = _now_iso()
        next_url = (
            validate_safe_connector_base_url(base_url, instance=instance)
            if base_url is not None
            else existing.base_url
        )
        sec_status = existing.admin_secret_status
        if clear_admin_secret:
            self._encrypted_admin_secrets.pop(connector_id, None)
            sec_status = ConnectorSecretStatus(configured=False)
        elif admin_secret_value and admin_secret_value.strip():
            plain = admin_secret_value.strip()
            self._encrypted_admin_secrets[connector_id] = pack_encrypted_secret(
                self._cipher,
                owner_id=f"admin:{connector_id}",
                plaintext=plain,
                scheme=existing.connector_kind,
                host=extract_url_host(next_url),
            )
            sec_status = ConnectorSecretStatus(
                configured=True,
                fingerprint=compute_secret_fingerprint(connector_id, plain),
                updated_at_iso=now,
            )
        updated = replace(
            existing,
            name=name.strip() if name and name.strip() else existing.name,
            base_url=next_url,
            auth_mode=auth_mode if auth_mode is not None else existing.auth_mode,
            enabled=enabled if enabled is not None else existing.enabled,
            admin_secret_status=sec_status,
            updated_at_iso=now,
        )
        self._connectors[connector_id] = updated
        return updated

    def delete_connector(self, connector_id: str, *, instance: str | None = None) -> None:
        if connector_id not in self._connectors:
            raise ResourceNotFoundError(instance=instance)
        self._connectors.pop(connector_id, None)
        self._encrypted_admin_secrets.pop(connector_id, None)
        for key in [k for k in self._user_tokens if k[1] == connector_id]:
            self._user_tokens.pop(key, None)

    def list_user_passthrough_tokens(self, user_id: str) -> list[UserPassthroughConnectorView]:
        uid = user_id.strip().lower()
        views: list[UserPassthroughConnectorView] = []
        for conn in self._connectors.values():
            if not conn.enabled:
                continue
            tok = self._user_tokens.get((uid, conn.id))
            views.append(
                UserPassthroughConnectorView(
                    connector_id=conn.id,
                    connector_name=conn.name,
                    connector_kind=conn.connector_kind,
                    base_url=conn.base_url,
                    auth_mode=conn.auth_mode,
                    connected=tok is not None,
                    external_author_login=tok[0] if tok else None,
                    secret_status=tok[2] if tok else ConnectorSecretStatus(configured=False),
                )
            )
        return views

    def upsert_user_passthrough_token(
        self,
        *,
        user_id: str,
        connector_id: str,
        external_author_login: str | None,
        secret_value: str,
        instance: str | None = None,
    ) -> UserPassthroughConnectorView:
        conn = self._connectors.get(connector_id)
        if conn is None:
            raise ResourceNotFoundError(instance=instance)
        plain = secret_value.strip()
        if not plain:
            raise ValidationDomainError(
                detail_override="Passthrough token must not be empty.",
                instance=instance,
            )
        uid = user_id.strip().lower()
        now = _now_iso()
        encrypted = pack_encrypted_secret(
            self._cipher,
            owner_id=uid,
            plaintext=plain,
            scheme=conn.connector_kind,
            host=extract_url_host(conn.base_url),
        )
        status = ConnectorSecretStatus(
            configured=True,
            fingerprint=compute_secret_fingerprint(f"{uid}:{connector_id}", plain),
            updated_at_iso=now,
        )
        clean_login = (external_author_login or "").strip() or None
        self._user_tokens[(uid, connector_id)] = (clean_login, encrypted, status)
        return UserPassthroughConnectorView(
            connector_id=conn.id,
            connector_name=conn.name,
            connector_kind=conn.connector_kind,
            base_url=conn.base_url,
            auth_mode=conn.auth_mode,
            connected=True,
            external_author_login=clean_login,
            secret_status=status,
        )

    def revoke_user_passthrough_token(
        self, *, user_id: str, connector_id: str, instance: str | None = None
    ) -> None:
        if connector_id not in self._connectors:
            raise ResourceNotFoundError(instance=instance)
        self._user_tokens.pop((user_id.strip().lower(), connector_id), None)

    def active_token_pairs(self) -> set[tuple[str, str]]:
        return set(self._user_tokens.keys())
