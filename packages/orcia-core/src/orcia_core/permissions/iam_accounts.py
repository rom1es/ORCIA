"""IAM Accounts Directory, Closed 6-Role Validation & Anti-Lockout Invariants (`Story 17.3`).

Zero framework or SQL imports (`test_hexagonal_purity_permissions_package`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from orcia_core.permissions._iam_account_models import (
    DEFAULT_DAY0_ADMIN_ROLES,
    VALID_ACCOUNT_KINDS,
    VALID_ACCOUNT_STATUSES,
    VALID_AUTH_SOURCES,
    IamAccountKind,
    IamAccountRecord,
    IamAccountStatus,
    IamAuthSource,
    assert_anti_lockout_on_accounts,
    normalize_principal_id,
    normalize_team_ids,
    validate_grant_resource_kind,
    validate_iam_roles,
)
from orcia_core.permissions._permissions_locales import DAY0_ADMIN_NAME_LOCALES
from orcia_core.permissions.errors import (
    DuplicateIamPrincipalError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.permissions.role_matrix import (
    VALID_GRANT_RESOURCE_KINDS,
    VALID_IAM_ROLES,
    now_utc_iso,
)
from orcia_kernel.ids import new_uuid7_str


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
        resolved_name = (display_name or "").strip() or DAY0_ADMIN_NAME_LOCALES["fr"]
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
            raise ValidationDomainError(detail_code="ERR_IAM_EMPTY_DISPLAY_NAME", instance=instance)
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
                    detail_code="ERR_IAM_EMPTY_DISPLAY_NAME", instance=instance
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
