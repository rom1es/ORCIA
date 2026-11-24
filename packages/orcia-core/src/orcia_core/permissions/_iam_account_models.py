"""IAM account domain records, validation & anti-lockout guards (`Story 17.3`)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from orcia_core.permissions.errors import (
    AdminLockoutPreventedError,
    InvalidIamRoleError,
    ValidationDomainError,
)
from orcia_core.permissions.role_matrix import (
    VALID_GRANT_RESOURCE_KINDS,
    VALID_IAM_ROLES,
    GrantResourceKind,
    OfficialIamRole,
)

IamAccountKind = Literal["HUMAN", "SERVICE_PRINCIPAL"]
IamAuthSource = Literal["LOCAL_BOOTSTRAP", "LOCAL_PASSWORD", "OIDC_FEDERATED", "SERVICE_TOKEN"]
IamAccountStatus = Literal["ACTIVE", "INVITED", "DISABLED"]

VALID_ACCOUNT_KINDS: tuple[IamAccountKind, ...] = ("HUMAN", "SERVICE_PRINCIPAL")
VALID_AUTH_SOURCES: tuple[IamAuthSource, ...] = (
    "LOCAL_BOOTSTRAP",
    "LOCAL_PASSWORD",
    "OIDC_FEDERATED",
    "SERVICE_TOKEN",
)
VALID_ACCOUNT_STATUSES: tuple[IamAccountStatus, ...] = ("ACTIVE", "INVITED", "DISABLED")
DEFAULT_DAY0_ADMIN_ROLES: tuple[OfficialIamRole, ...] = ("PLATFORM_ADMIN", "SECOPS")


@dataclass(frozen=True, slots=True)
class IamAccountRecord:
    """Domain entity for a human or service principal IAM account (`iam_accounts`, `Story 17.3`)."""

    id: str
    principal_id: str
    display_name: str
    email: str | None
    account_kind: IamAccountKind
    auth_source: IamAuthSource
    roles: tuple[OfficialIamRole, ...]
    team_ids: tuple[str, ...] = ()
    status: IamAccountStatus = "ACTIVE"
    created_at_iso: str = ""
    updated_at_iso: str = ""
    led_bu_ids: tuple[str, ...] = ()
    led_team_ids: tuple[str, ...] = ()
    ontology_led_bu_ids: tuple[str, ...] = ()


def validate_iam_roles(
    raw_roles: Sequence[str],
    *,
    instance: str | None = None,
) -> tuple[OfficialIamRole, ...]:
    """Validate and order roles against the closed 6-role set (`422 ERR_IAM_INVALID_ROLE`)."""
    cleaned = [str(r).strip().upper() for r in raw_roles if str(r).strip()]
    if not cleaned:
        raise ValidationDomainError(detail_code="ERR_IAM_EMPTY_ROLES", instance=instance)
    valid_set = set(VALID_IAM_ROLES)
    for role in cleaned:
        if role not in valid_set:
            raise InvalidIamRoleError(instance=instance)
    selected = set(cleaned)
    return tuple(r for r in VALID_IAM_ROLES if r in selected)


def validate_grant_resource_kind(
    raw_kind: str | None,
    *,
    instance: str | None = None,
) -> GrantResourceKind:
    if raw_kind is None or not raw_kind.strip():
        return "ALL"
    norm = raw_kind.strip().upper()
    if norm not in VALID_GRANT_RESOURCE_KINDS:
        raise ValidationDomainError(
            detail_code="ERR_IAM_UNKNOWN_RESOURCE_KIND",
            detail_params={"kind": raw_kind},
            instance=instance,
        )
    return norm


def normalize_principal_id(
    principal_id: str | None,
    *,
    email: str | None,
    display_name: str,
    account_kind: IamAccountKind,
    instance: str | None = None,
) -> str:
    candidate = (principal_id or "").strip()
    if not candidate and email and email.strip():
        candidate = email.strip().lower()
    if not candidate:
        slug = re.sub(r"[^a-z0-9._-]+", "-", display_name.strip().lower()).strip("-")
        prefix = "sp-" if account_kind == "SERVICE_PRINCIPAL" and not slug.startswith("sp-") else ""
        candidate = f"{prefix}{slug}" if slug else ""
    if not candidate:
        raise ValidationDomainError(detail_code="ERR_IAM_EMPTY_PRINCIPAL_ID", instance=instance)
    return candidate[:128]


def normalize_team_ids(raw_team_ids: Sequence[str] | None) -> tuple[str, ...]:
    if not raw_team_ids:
        return ()
    seen: list[str] = []
    for item in raw_team_ids:
        cleaned = str(item).strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return tuple(seen)


def assert_anti_lockout_on_accounts(
    existing_accounts: Sequence[IamAccountRecord],
    *,
    mutated_account: IamAccountRecord | None = None,
    deleted_account_id: str | None = None,
    instance: str | None = None,
) -> None:
    """Reject any mutation or deletion leaving `0` `ACTIVE` `PLATFORM_ADMIN` (`AD-21`)."""
    initial_active_admins = [
        acc for acc in existing_accounts if acc.status == "ACTIVE" and "PLATFORM_ADMIN" in acc.roles
    ]
    projected: list[IamAccountRecord] = []
    for acc in existing_accounts:
        if deleted_account_id is not None and acc.id == deleted_account_id:
            continue
        if mutated_account is not None and acc.id == mutated_account.id:
            projected.append(mutated_account)
        else:
            projected.append(acc)

    active_admins = [
        acc for acc in projected if acc.status == "ACTIVE" and "PLATFORM_ADMIN" in acc.roles
    ]
    if len(initial_active_admins) >= 1 and len(active_admins) < 1:
        raise AdminLockoutPreventedError(instance=instance)


__all__ = [
    "DEFAULT_DAY0_ADMIN_ROLES",
    "IamAccountKind",
    "IamAccountRecord",
    "IamAccountStatus",
    "IamAuthSource",
    "VALID_ACCOUNT_KINDS",
    "VALID_ACCOUNT_STATUSES",
    "VALID_AUTH_SOURCES",
    "assert_anti_lockout_on_accounts",
    "normalize_principal_id",
    "normalize_team_ids",
    "validate_grant_resource_kind",
    "validate_iam_roles",
]
