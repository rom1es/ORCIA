"""IAM Accounts Directory, Closed 6-Role Validation & Anti-Lockout Invariants (`Story 17.3`).

Zero framework or SQL imports (`test_hexagonal_purity_permissions_package`).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal

from orcia_core.permissions.errors import (
    AdminLockoutPreventedError,
    DuplicateIamPrincipalError,
    InvalidIamRoleError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.permissions.role_matrix import (
    VALID_GRANT_RESOURCE_KINDS,
    VALID_IAM_ROLES,
    GrantResourceKind,
    OfficialIamRole,
    now_utc_iso,
)
from orcia_kernel.ids import new_uuid7_str

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
        raise ValidationDomainError(
            detail_override="Au moins un rôle officiel doit être attribué au compte.",
            instance=instance,
        )
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
            detail_override=f"Type de ressource inconnu pour l'exception IAM : '{raw_kind}'.",
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
        raise ValidationDomainError(
            detail_override="L'identifiant du compte ne peut pas être vide.",
            instance=instance,
        )
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


class IamAccountsGovernanceService:
    """Pure domain directory service for IAM accounts & anti-lockout (`Story 17.3`)."""

    def __init__(self, initial_accounts: Sequence[IamAccountRecord] = ()) -> None:
        self._accounts: dict[str, IamAccountRecord] = {a.id: a for a in initial_accounts}

    def get_account(self, account_id: str) -> IamAccountRecord | None:
        """Return IAM account by ID or None if absent."""
        return self._accounts.get(account_id)

    def list_accounts(self) -> list[IamAccountRecord]:
        return sorted(
            self._accounts.values(),
            key=lambda a: (0 if "PLATFORM_ADMIN" in a.roles else 1, a.created_at_iso, a.id),
        )

    def ensure_day0_admin_account(
        self,
        *,
        email: str | None = None,
        display_name: str | None = None,
    ) -> list[IamAccountRecord]:
        resolved_email = (email or "").strip().lower() or "admin@orcia.local"
        resolved_name = (display_name or "").strip() or "Administrateur Plateforme (Jour 0)"
        existing_match = next(
            (a for a in self._accounts.values() if a.principal_id.lower() == resolved_email),
            None,
        )
        if existing_match is not None:
            return self.list_accounts()

        has_real_admin = any("PLATFORM_ADMIN" in a.roles for a in self._accounts.values())
        if has_real_admin and email is None:
            return self.list_accounts()

        if email is not None:
            placeholder = next(
                (a for a in self._accounts.values() if a.principal_id == "admin@orcia.local"),
                None,
            )
            if placeholder is not None and resolved_email != "admin@orcia.local":
                self._accounts.pop(placeholder.id, None)

        ts = now_utc_iso()
        seeded = IamAccountRecord(
            id=new_uuid7_str(),
            principal_id=resolved_email,
            display_name=resolved_name,
            email=resolved_email,
            account_kind="HUMAN",
            auth_source="LOCAL_BOOTSTRAP",
            roles=DEFAULT_DAY0_ADMIN_ROLES,
            team_ids=(),
            status="ACTIVE",
            created_at_iso=ts,
            updated_at_iso=ts,
        )
        self._accounts[seeded.id] = seeded
        return self.list_accounts()

    def create_account(
        self,
        *,
        principal_id: str | None = None,
        display_name: str,
        email: str | None = None,
        account_kind: IamAccountKind = "HUMAN",
        auth_source: IamAuthSource | None = None,
        roles: Sequence[str],
        team_ids: Sequence[str] | None = None,
        status: IamAccountStatus = "ACTIVE",
        led_bu_ids: Sequence[str] | None = None,
        led_team_ids: Sequence[str] | None = None,
        ontology_led_bu_ids: Sequence[str] | None = None,
        instance: str | None = None,
    ) -> IamAccountRecord:
        cleaned_name = display_name.strip()
        if not cleaned_name:
            raise ValidationDomainError(
                detail_override="Le nom affiché du compte ne peut pas être vide.",
                instance=instance,
            )
        valid_roles = validate_iam_roles(roles, instance=instance)
        cleaned_email = (email or "").strip().lower() or None
        norm_principal = normalize_principal_id(
            principal_id,
            email=cleaned_email,
            display_name=cleaned_name,
            account_kind=account_kind,
            instance=instance,
        )
        if any(a.principal_id.lower() == norm_principal.lower() for a in self._accounts.values()):
            raise DuplicateIamPrincipalError(instance=instance)

        effective_source: IamAuthSource = auth_source or (
            "SERVICE_TOKEN" if account_kind == "SERVICE_PRINCIPAL" else "OIDC_FEDERATED"
        )
        ts = now_utc_iso()
        created = IamAccountRecord(
            id=new_uuid7_str(),
            principal_id=norm_principal,
            display_name=cleaned_name,
            email=cleaned_email,
            account_kind=account_kind,
            auth_source=effective_source,
            roles=valid_roles,
            team_ids=normalize_team_ids(team_ids),
            status=status,
            created_at_iso=ts,
            updated_at_iso=ts,
            led_bu_ids=normalize_team_ids(led_bu_ids),
            led_team_ids=normalize_team_ids(led_team_ids),
            ontology_led_bu_ids=normalize_team_ids(ontology_led_bu_ids),
        )
        self._accounts[created.id] = created
        return created

    def update_account(
        self,
        account_id: str,
        *,
        display_name: str | None = None,
        email: str | None = None,
        email_provided: bool = False,
        roles: Sequence[str] | None = None,
        team_ids: Sequence[str] | None = None,
        status: IamAccountStatus | None = None,
        led_bu_ids: Sequence[str] | None = None,
        led_team_ids: Sequence[str] | None = None,
        ontology_led_bu_ids: Sequence[str] | None = None,
        instance: str | None = None,
    ) -> IamAccountRecord:
        target = self._accounts.get(account_id)
        if target is None:
            raise ResourceNotFoundError(instance=instance)

        next_name = target.display_name
        if display_name is not None:
            stripped = display_name.strip()
            if not stripped:
                raise ValidationDomainError(
                    detail_override="Le nom affiché du compte ne peut pas être vide.",
                    instance=instance,
                )
            next_name = stripped

        next_email = ((email or "").strip().lower() or None) if email_provided else target.email
        next_roles = (
            validate_iam_roles(roles, instance=instance) if roles is not None else target.roles
        )
        next_teams = normalize_team_ids(team_ids) if team_ids is not None else target.team_ids
        next_status = status if status is not None else target.status
        next_led_bu = (
            normalize_team_ids(led_bu_ids) if led_bu_ids is not None else target.led_bu_ids
        )
        next_led_teams = (
            normalize_team_ids(led_team_ids) if led_team_ids is not None else target.led_team_ids
        )
        next_onto_bu = (
            normalize_team_ids(ontology_led_bu_ids)
            if ontology_led_bu_ids is not None
            else target.ontology_led_bu_ids
        )

        mutated = replace(
            target,
            display_name=next_name,
            email=next_email,
            roles=next_roles,
            team_ids=next_teams,
            status=next_status,
            led_bu_ids=next_led_bu,
            led_team_ids=next_led_teams,
            ontology_led_bu_ids=next_onto_bu,
            updated_at_iso=now_utc_iso(),
        )
        assert_anti_lockout_on_accounts(
            list(self._accounts.values()),
            mutated_account=mutated,
            instance=instance,
        )
        self._accounts[account_id] = mutated
        return mutated

    def delete_account(self, account_id: str, *, instance: str | None = None) -> str:
        target = self._accounts.get(account_id)
        if target is None:
            raise ResourceNotFoundError(instance=instance)
        assert_anti_lockout_on_accounts(
            list(self._accounts.values()),
            deleted_account_id=account_id,
            instance=instance,
        )
        self._accounts.pop(account_id)
        return account_id


__all__ = [
    "DEFAULT_DAY0_ADMIN_ROLES",
    "IamAccountKind",
    "IamAccountRecord",
    "IamAccountStatus",
    "IamAccountsGovernanceService",
    "IamAuthSource",
    "VALID_ACCOUNT_KINDS",
    "VALID_ACCOUNT_STATUSES",
    "VALID_AUTH_SOURCES",
    "VALID_GRANT_RESOURCE_KINDS",
    "VALID_IAM_ROLES",
    "assert_anti_lockout_on_accounts",
    "normalize_principal_id",
    "normalize_team_ids",
    "validate_grant_resource_kind",
    "validate_iam_roles",
]
