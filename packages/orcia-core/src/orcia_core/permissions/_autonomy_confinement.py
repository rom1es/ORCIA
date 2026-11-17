"""Pure confinement, action-verb mapping & signer role helpers for Autonomy Contracts (`Story 7.1`).

Zero framework or SQL imports (`test_hexagonal_purity_permissions_package`).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Literal

from orcia_core.permissions.errors import ContractPrivilegeEscalationError
from orcia_core.permissions.hierarchical_rbac import HierarchicalRbacService
from orcia_core.permissions.iam_accounts import IamAccountRecord
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.role_matrix import DEFAULT_ROLE_PERMISSION_MATRIX, PermissionVerb

AutonomySignerRole = Literal["TEAM_LEAD", "BU_LEAD", "PLATFORM_ADMIN"]


def compute_contract_signature_sha256(
    *,
    contract_id: str,
    workspace_id: str,
    workflow_id: str,
    workflow_version: str,
    workflow_sha256: str,
    service_principal_id: str,
    allowed_read_sources: Sequence[str],
    allowed_write_actions: Sequence[str],
    max_cost_per_run_usd: float,
    tie_break_policy: str,
    signed_by_user_id: str,
    signed_by_role: str,
) -> str:
    """Compute canonical SHA-256 signature digest without any raw secret."""
    canonical = json.dumps(
        {
            "contract_id": contract_id,
            "workspace_id": workspace_id,
            "workflow_id": workflow_id,
            "workflow_version": workflow_version,
            "workflow_sha256": workflow_sha256,
            "service_principal_id": service_principal_id,
            "allowed_read_sources": sorted(allowed_read_sources),
            "allowed_write_actions": sorted(allowed_write_actions),
            "max_cost_per_run_usd": round(float(max_cost_per_run_usd), 6),
            "tie_break_policy": tie_break_policy,
            "signed_by_user_id": signed_by_user_id,
            "signed_by_role": signed_by_role,
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def map_action_to_required_verb(action_key: str) -> PermissionVerb:
    """Map an action identifier (e.g. `catalog_item:create`, `help:publish`) to a RBAC verb."""
    norm = action_key.strip().lower()
    if any(tok in norm for tok in (":create", ":insert", ".create", "create_")):
        return "create"
    if any(tok in norm for tok in (":delete", ":remove", ".delete", "delete_")):
        return "delete"
    if any(tok in norm for tok in (":update", ":edit", ":patch", ".update", "update_")):
        return "update"
    if any(tok in norm for tok in (":grant", ".grant")):
        return "grant"
    if any(tok in norm for tok in (":read", ":get", ":list", ".read", "read_")):
        return "read"
    return "execute"


def resolve_signer_role(signer: UserIdentity) -> AutonomySignerRole | None:
    """Resolve eligible signer role (`TEAM_LEAD`, `BU_LEAD`, `PLATFORM_ADMIN`); zero `SECOPS`."""
    raw_roles = [signer.platform_role, *signer.roles]
    mapped: list[AutonomySignerRole] = []
    for role in raw_roles:
        r = str(role).strip().upper()
        if r == "PLATFORM_ADMIN":
            mapped.append("PLATFORM_ADMIN")
        elif r in ("BU_LEAD", "BU_DIRECTOR"):
            mapped.append("BU_LEAD")
        elif r == "TEAM_LEAD":
            mapped.append("TEAM_LEAD")
    for preferred in ("PLATFORM_ADMIN", "BU_LEAD", "TEAM_LEAD"):
        if preferred in mapped:
            return preferred
    return None


def resolve_effective_verbs_for_roles(
    *,
    rbac_service: HierarchicalRbacService,
    subject_id: str,
    subject_type: Literal["USER", "SERVICE_PRINCIPAL"],
    roles: Sequence[str],
    scope_path: str,
    user: UserIdentity | None = None,
) -> set[PermissionVerb]:
    """Compute effective verbs combining explicit RBAC grants and native role matrix defaults."""
    explicit_verbs = rbac_service.resolve_effective_verbs(
        subject_id=subject_id,
        subject_type=subject_type,
        roles=tuple(roles),
        scope_path=scope_path,
        user=user,
    )
    matrix_verbs: set[PermissionVerb] = set()
    for r in roles:
        norm_role = str(r).strip().upper()
        if norm_role == "BU_DIRECTOR":
            norm_role = "BU_LEAD"
        if norm_role in DEFAULT_ROLE_PERMISSION_MATRIX:
            desc = DEFAULT_ROLE_PERMISSION_MATRIX[norm_role]
            matrix_verbs.update(desc.native_verbs)
    denied_verbs: set[PermissionVerb] = set()
    role_set = {str(r).strip().upper() for r in roles}
    for grant in rbac_service.list_grants(scope_path):
        if grant.effect == "DENY" and (
            (grant.subject_type == subject_type and grant.subject_id == subject_id)
            or (grant.subject_type == "ROLE" and grant.subject_id in role_set)
        ):
            denied_verbs.add(grant.verb)
    return (explicit_verbs | matrix_verbs) - denied_verbs


def is_service_principal_scoped_to_workspace(
    account: IamAccountRecord,
    *,
    workspace_id: str,
    allowed_scope_ids: Sequence[str] = (),
    rbac_service: HierarchicalRbacService | None = None,
    scope_path: str = "GLOBAL",
) -> bool:
    """Return True if an active `SERVICE_PRINCIPAL` is explicitly scoped to the workspace."""
    if account.account_kind != "SERVICE_PRINCIPAL" or account.status != "ACTIVE":
        return False
    accepted_ids = {
        workspace_id.strip().lower(),
        *(s.strip().lower() for s in allowed_scope_ids if s.strip()),
    }
    sp_teams = {
        t.strip().lower()
        for t in (*account.team_ids, *account.led_team_ids, *account.led_bu_ids)
        if t.strip()
    }
    if accepted_ids & sp_teams:
        return True
    if "PLATFORM_ADMIN" in account.roles:
        return True
    if rbac_service is not None:
        for grant in rbac_service.list_grants(scope_path):
            if (
                grant.subject_type == "SERVICE_PRINCIPAL"
                and grant.subject_id in (account.id, account.principal_id)
                and grant.effect == "ALLOW"
            ):
                return True
    return False


def assert_contract_confinement(
    *,
    allowed_write_actions: Sequence[str],
    signer_verbs: set[PermissionVerb],
    sp_verbs: set[PermissionVerb],
    signer_allowed_actions: set[str] | None = None,
    sp_allowed_actions: set[str] | None = None,
    instance: str | None = None,
) -> None:
    """Enforce `Actions <= Rights(Signer) & Rights(SERVICE_PRINCIPAL)` (`403` otherwise)."""
    intersection_verbs = signer_verbs & sp_verbs
    for action in allowed_write_actions:
        req_verb = map_action_to_required_verb(action)
        if req_verb not in intersection_verbs:
            raise ContractPrivilegeEscalationError(
                detail_override=(
                    f"Action '{action}' (droit '{req_verb}') hors confinement "
                    "Droits(Signataire) ∩ Droits(SERVICE_PRINCIPAL)."
                ),
                instance=instance,
            )
        if signer_allowed_actions is not None and action not in signer_allowed_actions:
            raise ContractPrivilegeEscalationError(
                detail_override=f"Action '{action}' absente des droits du signataire.",
                instance=instance,
            )
        if sp_allowed_actions is not None and action not in sp_allowed_actions:
            raise ContractPrivilegeEscalationError(
                detail_override=f"Action '{action}' absente des droits du compte de service.",
                instance=instance,
            )
