"""Story 18.1 — Workspace Sources Multi-Nature & Codegraph Governance Domain Model.

Zero SQL / FastAPI / RAG / Connectors imports:
- Multi-nature definitions (`DOCUMENT_KB`, `WORK_TRACKER`, `SOURCE_CODE`, `RELATIONAL_SCHEMA`)
- Pure inference from scheme (`infer_source_nature_from_scheme`)
- Role governance predicate for GitNexus (`can_manage_workspace_codegraph`)
- Dual-token health evaluation (`evaluate_codegraph_governance_health`)
- Dataclass `WorkspaceDatasourceRecord` with default fields for full backward compatibility
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from orcia_core.permissions.iam_accounts import IamAccountRecord
from orcia_core.permissions.models import OrgUnitNode

SourceNature = Literal["DOCUMENT_KB", "WORK_TRACKER", "SOURCE_CODE", "RELATIONAL_SCHEMA"]
SourceSyncMode = Literal["WEBHOOK_PUSH", "POLLING_24H"]
SourceFreshnessStatus = Literal["SYNCED", "STALE", "SYNC_ERROR", "PENDING_INITIAL_SYNC"]
CodegraphAuthMode = Literal["SERVICE_ACCOUNT", "WORKSPACE_LEAD_TOKEN"]
CodegraphStatus = Literal[
    "DISABLED", "INDEXING", "READY", "PAUSED_REFERENT_RENEWAL_REQUIRED", "ERROR"
]
SyncIdentityMode = Literal["SERVICE_ACCOUNT", "TEAM_REFERENT_USER"]
DatasourceSyncStatus = Literal["ACTIVE", "PAUSED_REFERENT_RENEWAL_REQUIRED"]
DatasourceSyncReason = Literal[
    "REFERENT_LEFT_TEAM", "REFERENT_ACCOUNT_DISABLED", "REFERENT_TOKEN_MISSING"
]

VALID_SOURCE_NATURES: tuple[SourceNature, ...] = (
    "DOCUMENT_KB",
    "WORK_TRACKER",
    "SOURCE_CODE",
    "RELATIONAL_SCHEMA",
)
VALID_SOURCE_SYNC_MODES: tuple[SourceSyncMode, ...] = ("WEBHOOK_PUSH", "POLLING_24H")
VALID_FRESHNESS_STATUSES: tuple[SourceFreshnessStatus, ...] = (
    "SYNCED",
    "STALE",
    "SYNC_ERROR",
    "PENDING_INITIAL_SYNC",
)
VALID_CODEGRAPH_AUTH_MODES: tuple[CodegraphAuthMode, ...] = (
    "SERVICE_ACCOUNT",
    "WORKSPACE_LEAD_TOKEN",
)
VALID_CODEGRAPH_STATUSES: tuple[CodegraphStatus, ...] = (
    "DISABLED",
    "INDEXING",
    "READY",
    "PAUSED_REFERENT_RENEWAL_REQUIRED",
    "ERROR",
)
VALID_SYNC_IDENTITY_MODES: tuple[SyncIdentityMode, ...] = (
    "SERVICE_ACCOUNT",
    "TEAM_REFERENT_USER",
)

CODEGRAPH_GOVERNOR_ROLES: frozenset[str] = frozenset(
    {"TEAM_LEAD", "BU_LEAD", "PLATFORM_ADMIN", "SECOPS"}
)


def infer_source_nature_from_scheme(scheme: str) -> SourceNature:
    """Infer `SourceNature` from connection `scheme` with deterministic fallback."""
    norm = (scheme or "").strip().lower()
    if norm in ("confluence", "docs", "nexus", "s3", "knowledge"):
        return "DOCUMENT_KB"
    if norm in ("jira", "tracker", "linear", "issues"):
        return "WORK_TRACKER"
    if norm in ("git", "gitlab", "github", "source", "code"):
        return "SOURCE_CODE"
    if norm in ("sql", "postgres", "postgresql", "db", "mysql"):
        return "RELATIONAL_SCHEMA"
    return "DOCUMENT_KB"


def can_manage_workspace_codegraph(roles: Iterable[str]) -> bool:
    """True if user has at least one Workspace Lead or Governance role."""
    normalized = {r.strip().upper() for r in roles if r and r.strip()}
    return bool(normalized & CODEGRAPH_GOVERNOR_ROLES)


@dataclass(frozen=True, slots=True)
class WorkspaceDatasourceRecord:
    """Workspace Datasource with Multi-Nature, Freshness, and Codegraph Governance."""

    id: str
    workspace_id: str
    alias: str
    scheme: str
    uri: str
    connector_id: str | None = None
    sync_identity_mode: SyncIdentityMode = "SERVICE_ACCOUNT"
    service_account_id: str | None = None
    referent_user_id: str | None = None
    sync_status: DatasourceSyncStatus = "ACTIVE"
    sync_status_reason: DatasourceSyncReason | None = None
    created_at_iso: str = ""
    # Story 18.1 Multi-Nature & Codegraph fields:
    source_nature: SourceNature = "DOCUMENT_KB"
    sync_mode: SourceSyncMode = "POLLING_24H"
    target_scope: str | None = None
    target_ref: str | None = None
    last_sync_at_iso: str | None = None
    last_probe_at_iso: str | None = None
    fingerprint_hash: str | None = None
    freshness_status: SourceFreshnessStatus = "PENDING_INITIAL_SYNC"
    codegraph_enabled: bool = False
    codegraph_auth_mode: CodegraphAuthMode = "SERVICE_ACCOUNT"
    codegraph_owner_user_id: str | None = None
    codegraph_status: CodegraphStatus = "DISABLED"
    codegraph_status_reason: str | None = None
    codegraph_last_indexed_at_iso: str | None = None
    codegraph_head_sha: str | None = None


def evaluate_codegraph_governance_health(
    *,
    codegraph_enabled: bool,
    codegraph_auth_mode: CodegraphAuthMode = "SERVICE_ACCOUNT",
    codegraph_owner_user_id: str | None = None,
    connector_id: str | None = None,
    owner_org_unit: OrgUnitNode | None = None,
    iam_accounts: Iterable[IamAccountRecord] = (),
    active_token_pairs: set[tuple[str, str]] | None = None,
    current_status: CodegraphStatus = "DISABLED",
) -> tuple[CodegraphStatus, str | None]:
    """Compute deterministic GitNexus governance status (`Story 18.1`)."""
    if not codegraph_enabled:
        return ("DISABLED", None)

    tokens = active_token_pairs or set()

    if codegraph_auth_mode == "WORKSPACE_LEAD_TOKEN":
        owner_raw = (codegraph_owner_user_id or "").strip()
        if not owner_raw:
            return ("PAUSED_REFERENT_RENEWAL_REQUIRED", "REFERENT_USER_REQUIRED")
        owner_norm = owner_raw.lower()

        matched_account: IamAccountRecord | None = None
        candidate_identities: set[str] = {owner_norm}
        for acc in iam_accounts:
            keys = {
                acc.id.lower(),
                acc.principal_id.lower(),
                (acc.email or "").lower(),
            } - {""}
            if owner_norm in keys:
                matched_account = acc
                candidate_identities |= keys
                break

        if matched_account is not None and matched_account.status == "DISABLED":
            return ("PAUSED_REFERENT_RENEWAL_REQUIRED", "REFERENT_ACCOUNT_DISABLED")

        if owner_org_unit is not None and owner_org_unit.unit_type != "ENTERPRISE":
            team_members_norm = {
                m.strip().lower() for m in owner_org_unit.member_user_ids if m.strip()
            }
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
            normalized_pairs = {(u.lower(), c.lower()) for u, c in tokens}
            has_token = any(
                (ident, conn_norm) in normalized_pairs for ident in candidate_identities
            )
            if not has_token:
                return ("PAUSED_REFERENT_RENEWAL_REQUIRED", "REFERENT_TOKEN_MISSING")

        if current_status in ("INDEXING", "READY"):
            return (current_status, None)
        return ("READY", None)

    # SERVICE_ACCOUNT mode
    if current_status in ("INDEXING", "READY"):
        return (current_status, None)
    return ("READY", None)


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
