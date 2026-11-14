"""Story 17.4 & 18.1 — Domain Model for Enterprise Connectors, Passthrough & RAG Referent."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Literal

from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.enterprise_connectors_crypto import (
    compute_secret_fingerprint as compute_secret_fingerprint,
    extract_url_host as extract_url_host,
    pack_encrypted_secret as pack_encrypted_secret,
    unpack_encrypted_secret as unpack_encrypted_secret,
    validate_safe_connector_base_url as validate_safe_connector_base_url,
)
from orcia_core.permissions.errors import (
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.permissions.workspace_sources_governance import (
    DatasourceSyncReason as DatasourceSyncReason,
    DatasourceSyncStatus as DatasourceSyncStatus,
    SyncIdentityMode as SyncIdentityMode,
    WorkspaceDatasourceRecord as WorkspaceDatasourceRecord,
    evaluate_datasource_sync_health as evaluate_datasource_sync_health,
)
from orcia_kernel.ids import new_uuid7_str

EnterpriseConnectorKind = Literal["GITLAB", "JIRA", "CONFLUENCE", "OIDC_SSO", "S3_OBJECT_STORE"]
EnterpriseConnectorAuthMode = Literal[
    "OAUTH2_PASSTHROUGH", "PERSONAL_ACCESS_TOKEN", "OIDC_FEDERATION", "SERVICE_SECRET"
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


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


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

    def list_workspace_datasources(self, workspace_id: str) -> list[WorkspaceDatasourceRecord]:
        return list(self._datasources.get(workspace_id, []))

    def register_workspace_datasource(
        self, datasource: WorkspaceDatasourceRecord
    ) -> WorkspaceDatasourceRecord:
        sources = self._datasources.setdefault(datasource.workspace_id, [])
        sources.append(datasource)
        return datasource

    def delete_workspace_datasource(
        self, workspace_id: str, datasource_id: str, *, instance: str | None = None
    ) -> None:
        sources = self._datasources.get(workspace_id, [])
        for idx, src in enumerate(sources):
            if src.id == datasource_id:
                sources.pop(idx)
                return
        raise ResourceNotFoundError(instance=instance)

    def request_workspace_datasource_sync(
        self, workspace_id: str, datasource_id: str, *, instance: str | None = None
    ) -> WorkspaceDatasourceRecord:
        sources = self._datasources.get(workspace_id, [])
        for idx, src in enumerate(sources):
            if src.id == datasource_id:
                now = _now_iso()
                new_cg_status = src.codegraph_status
                new_cg_indexed_at = src.codegraph_last_indexed_at_iso
                if src.codegraph_enabled:
                    new_cg_indexed_at = now
                    if src.codegraph_status != "PAUSED_REFERENT_RENEWAL_REQUIRED":
                        new_cg_status = "READY"
                updated = replace(
                    src,
                    last_sync_at_iso=now,
                    freshness_status="SYNCED",
                    codegraph_status=new_cg_status,
                    codegraph_last_indexed_at_iso=new_cg_indexed_at,
                )
                sources[idx] = updated
                return updated
        raise ResourceNotFoundError(instance=instance)
