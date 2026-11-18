"""Helper functions for IAM human accounts temporary password lifecycle (`Story 17.6`).

Generates 12-char temporary passwords, computes Argon2id hashes, and enforces RBAC guards.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

import sqlalchemy as sa
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.iam_password_models import (
    TemporaryPasswordProvisionResponse,
)
from orcia_core.bootstrap import (
    sync_and_list_iam_accounts_from_postgres18,
    upsert_human_user_credentials_on_postgres18,
)
from orcia_core.observability.logging import get_logger
from orcia_core.permissions import (
    AuthAndOrganizationService,
    IamAccountRecord,
    IamAccountsGovernanceService,
    MatrixPermissionEvaluator,
    OrgUnitNode,
    UserIdentity,
    generate_temporary_password,
)
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    PrivilegeEscalationForbiddenError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)

logger = get_logger("orcia.api.iam.passwords")


_IAM_MUTATION_ROLES: frozenset[str] = frozenset({"PLATFORM_ADMIN", "SECOPS"})


def enforce_iam_accounts_access(
    request: Request,
    persona_key: str | None,
    *,
    require_write: bool = True,
) -> UserIdentity:
    """Restrict IAM accounts endpoints to `PLATFORM_ADMIN` / `SECOPS` (`403` otherwise)."""
    access_mode_hdr = request.headers.get("x-orcia-access-mode", "").strip().upper()
    observer_hdr = request.headers.get("x-orcia-observer-mode", "").strip().lower()
    active_hat = request.headers.get("x-orcia-active-hat", "").strip().upper()
    if (
        access_mode_hdr == "READ_ONLY_OBSERVER"
        or observer_hdr in ("1", "true", "yes")
        or active_hat == "OBSERVER"
    ):
        if require_write:
            raise ObserverModeReadOnlyError(instance=str(request.url.path))
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    if active_hat and active_hat not in _IAM_MUTATION_ROLES:
        raise ScopeAccessDeniedError(instance=str(request.url.path))

    effective_persona = persona_key or request.headers.get("x-orcia-persona", "").strip() or None
    user = resolve_request_user(request, persona_key=effective_persona)
    if user.platform_role in ("OBSERVER", "READ_ONLY_OBSERVER"):
        if require_write:
            raise ObserverModeReadOnlyError(instance=str(request.url.path))
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    caller_roles = {r.strip().upper() for r in (user.platform_role, *user.roles) if r}
    if not (caller_roles & _IAM_MUTATION_ROLES) and user.human_profile_archetype != "SECOPS":
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    return user


def enforce_iam_accounts_mutation_access(request: Request, persona_key: str | None) -> UserIdentity:
    """Reject `READ_ONLY_OBSERVER` (`403`) and restrict IAM writes to `PLATFORM_ADMIN`/`SECOPS`."""
    return enforce_iam_accounts_access(request, persona_key, require_write=True)


def enforce_iam_accounts_read_access(request: Request, persona_key: str | None) -> UserIdentity:
    """Restrict IAM directory read (`GET /settings/iam/accounts`) to `PLATFORM_ADMIN`/`SECOPS`."""
    return enforce_iam_accounts_access(request, persona_key, require_write=False)


def enforce_iam_anti_escalation(
    caller: UserIdentity,
    *,
    existing_roles: Sequence[str] = (),
    next_roles: Sequence[str] | None = None,
    is_delete: bool = False,
    instance: str | None = None,
) -> None:
    """Forbid a `SECOPS` caller without `PLATFORM_ADMIN` from managing `PLATFORM_ADMIN`."""
    caller_roles = {r.strip().upper() for r in (caller.platform_role, *caller.roles) if r}
    if "PLATFORM_ADMIN" in caller_roles:
        return
    existing_norm = {r.strip().upper() for r in existing_roles if r}
    if is_delete and "PLATFORM_ADMIN" in existing_norm:
        raise PrivilegeEscalationForbiddenError(
            instance=instance,
            detail_override=(
                "Seul un Administrateur Plateforme peut supprimer un compte PLATFORM_ADMIN."
            ),
        )
    if next_roles is not None:
        next_norm = {r.strip().upper() for r in next_roles if r}
        if ("PLATFORM_ADMIN" in next_norm) != ("PLATFORM_ADMIN" in existing_norm):
            raise PrivilegeEscalationForbiddenError(
                instance=instance,
                detail_override=(
                    "Seul un Administrateur Plateforme peut attribuer ou retirer "
                    "le rôle PLATFORM_ADMIN."
                ),
            )


def sync_in_memory_team_memberships(
    evaluator: MatrixPermissionEvaluator,
    principal_id: str,
    desired_team_ids: tuple[str, ...],
    *,
    remove_all: bool = False,
) -> None:
    """Sync team memberships onto in-memory evaluator org units."""
    desired_set = set() if remove_all else set(desired_team_ids)
    for node in list(evaluator.org_units):
        if remove_all:
            if principal_id in node.member_user_ids:
                next_members = tuple(m for m in node.member_user_ids if m != principal_id)
                evaluator.upsert_org_unit(
                    OrgUnitNode(
                        id=node.id,
                        slug=node.slug,
                        name=node.name,
                        unit_type=node.unit_type,
                        parent_id=node.parent_id,
                        billing_enabled=node.billing_enabled,
                        lead_user_id=node.lead_user_id,
                        lead_user_ids=node.lead_user_ids,
                        ontology_lead_user_ids=node.ontology_lead_user_ids,
                        member_user_ids=next_members,
                    )
                )
            continue
        if node.unit_type not in ("TEAM", "SUB_TEAM"):
            continue
        should_belong = (node.id in desired_set) or (node.slug in desired_set)
        has_member = principal_id in node.member_user_ids
        if should_belong and not has_member:
            next_members = (*node.member_user_ids, principal_id)
        elif not should_belong and has_member:
            next_members = tuple(m for m in node.member_user_ids if m != principal_id)
        else:
            continue
        evaluator.upsert_org_unit(
            OrgUnitNode(
                id=node.id,
                slug=node.slug,
                name=node.name,
                unit_type=node.unit_type,
                parent_id=node.parent_id,
                billing_enabled=node.billing_enabled,
                lead_user_id=node.lead_user_id,
                lead_user_ids=node.lead_user_ids,
                ontology_lead_user_ids=node.ontology_lead_user_ids,
                member_user_ids=next_members,
            )
        )


async def provision_human_temporary_password(
    account_id: str,
    email: str,
    display_name: str,
    roles: list[str] | tuple[str, ...],
    auth_svc: AuthAndOrganizationService,
    engine: AsyncEngine | None,
    *,
    primary_org_unit_id: str | None = None,
) -> str:
    """Generate 12-char temporary password, persist to `users` with must_change_password=True."""
    temp_pw = generate_temporary_password(12)  # pragma: allowlist secret
    pw_hash = await asyncio.to_thread(auth_svc.hasher.hash_password, temp_pw)

    if engine is not None:
        async with engine.begin() as conn:
            await upsert_human_user_credentials_on_postgres18(
                conn,
                email=email,
                display_name=display_name,
                roles=roles,
                password_hash_argon2id=pw_hash,
                must_change_password=True,
                primary_org_unit_id=primary_org_unit_id,
            )

    platform_role = roles[0] if roles else "CONTRIBUTOR"
    user = UserIdentity(
        id=account_id,
        email=email,
        display_name=display_name,
        auth_mode="LOCAL",
        human_profile_archetype="CONTRIBUTOR",
        platform_role=platform_role,  # type: ignore[arg-type]
        primary_org_unit_id=primary_org_unit_id or "0192c4e0-0000-7000-8000-000000000101",
        password_hash_argon2id=pw_hash,
        must_change_password=True,
        roles=tuple(roles),
    )
    auth_svc.register_user(user)
    return temp_pw


async def reset_temporary_password_for_account(
    account_id: str,
    iam_svc: IamAccountsGovernanceService,
    auth_svc: AuthAndOrganizationService,
    engine: AsyncEngine | None,
    trace_id: str,
    instance: str | None = None,
) -> TemporaryPasswordProvisionResponse:
    """Reset temporary password on existing HUMAN account and return one-time invitation model."""
    account: IamAccountRecord | None = None
    if engine is not None:
        accounts = await sync_and_list_iam_accounts_from_postgres18(engine)
        for a in accounts:
            if a.id == account_id:
                account = a
                break

    if account is None:
        try:
            account = iam_svc.get_account(account_id)
        except Exception as exc:
            logger.warning("iam_account_lookup_memory_fallback", error_type=type(exc).__name__)
            account = None

    if account is None:
        raise ResourceNotFoundError(instance=instance)

    if account.account_kind != "HUMAN" or not account.email:
        raise ValidationDomainError(
            instance=instance,
            detail_override=(
                "Seuls les comptes humains avec adresse e-mail valide "
                "peuvent recevoir un mot de passe temporaire."
            ),
        )

    temp_pw = await provision_human_temporary_password(
        account_id=account.id,
        email=account.email,
        display_name=account.display_name,
        roles=account.roles,
        auth_svc=auth_svc,
        engine=engine,
    )

    return TemporaryPasswordProvisionResponse(
        account_id=account.id,
        principal_id=account.principal_id,
        email=account.email,
        display_name=account.display_name,
        temporary_password=temp_pw,  # pragma: allowlist secret
        must_change_password=True,
        trace_id=trace_id,
    )


async def cleanup_or_disable_linked_user_on_postgres18(
    engine: AsyncEngine,
    *,
    principal_id: str | None = None,
    email: str | None = None,
) -> None:
    """Clean up or disable the linked `users` row upon IAM account deletion.

    Attempts hard delete first. If foreign keys (runs, audit ledger, etc.) prevent deletion,
    reassigns `primary_org_unit_id` to the ENTERPRISE root and marks `is_active = FALSE`.
    """
    targets = [x.strip().lower() for x in (principal_id, email) if x and x.strip()]
    if not targets:
        return

    where_clauses = ["LOWER(email) = :t0 OR id::text = :t0"]
    params: dict[str, str] = {"t0": targets[0]}
    if len(targets) > 1:
        where_clauses.append("LOWER(email) = :t1 OR id::text = :t1")
        params["t1"] = targets[1]

    async with engine.connect() as conn:
        res = await conn.execute(
            sa.text(
                f"""
                SELECT id, email, primary_org_unit_id
                FROM users
                WHERE {" OR ".join(where_clauses)}
                """
            ),
            params,
        )
        user_rows = res.fetchall()

    if not user_rows:
        return

    for u_row in user_rows:
        u_id = u_row[0]
        deleted = False
        try:
            async with engine.begin() as del_conn:
                await del_conn.execute(
                    sa.text("DELETE FROM user_transverse_groups WHERE user_id = :uid"),
                    {"uid": u_id},
                )
                await del_conn.execute(
                    sa.text("DELETE FROM users WHERE id = :uid"),
                    {"uid": u_id},
                )
                deleted = True
        except Exception as exc:
            logger.info(
                "iam_account_user_hard_delete_prevented_by_fk",
                user_id=str(u_id),
                error_type=type(exc).__name__,
            )
            deleted = False

        if not deleted:
            try:
                async with engine.begin() as upd_conn:
                    root_res = await upd_conn.execute(
                        sa.text(
                            """
                            SELECT id FROM org_units
                            WHERE unit_type = 'ENTERPRISE'
                            ORDER BY created_at ASC
                            LIMIT 1
                            """
                        )
                    )
                    root_id = root_res.scalar()
                    if root_id is not None:
                        await upd_conn.execute(
                            sa.text(
                                """
                                UPDATE users
                                SET primary_org_unit_id = :root_id,
                                    is_active = FALSE
                                WHERE id = :uid
                                """
                            ),
                            {"root_id": root_id, "uid": u_id},
                        )
                    else:
                        await upd_conn.execute(
                            sa.text("UPDATE users SET is_active = FALSE WHERE id = :uid"),
                            {"uid": u_id},
                        )
            except Exception as upd_exc:
                logger.warning(
                    "iam_account_user_deactivation_failed",
                    user_id=str(u_id),
                    error_type=type(upd_exc).__name__,
                )
