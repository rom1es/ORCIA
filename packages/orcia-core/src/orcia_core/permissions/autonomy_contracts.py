"""Autonomy Contracts Domain Service & Repository Port (`Story 7.1`, `AD-18`).

Enforces single signature (`TEAM_LEAD`, `BU_LEAD`, or `PLATFORM_ADMIN` — zero `SECOPS`
co-signature), rejection of `HIGH_CRITICAL` workflows (`422`), and double confinement guard.
Zero framework or SQL imports (`test_hexagonal_purity_permissions_package`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from orcia_core.permissions._autonomy_confinement import (
    AutonomySignerRole,
    assert_contract_confinement,
    compute_contract_signature_sha256,
    is_service_principal_scoped_to_workspace,
    map_action_to_required_verb,
    resolve_effective_verbs_for_roles,
    resolve_signer_role,
)
from orcia_core.permissions._autonomy_contract_models import (
    ALLOWED_SIGNER_ROLES,
    ALLOWED_TIE_BREAK_POLICIES,
    AutonomyContract,
    AutonomyContractRepositoryPort,
    AutonomyContractStatus,
    ContractCriticality,
    SignAutonomyContractCommand,
    build_signed_autonomy_contract,
)
from orcia_core.permissions.errors import (
    AutonomyContractNotFoundError,
    AutonomyContractSignForbiddenError,
    CriticalWorkflowRequiresHumanGateError,
    ObserverModeReadOnlyError,
    ServicePrincipalInvalidForContractError,
    ValidationDomainError,
)
from orcia_core.permissions.hierarchical_rbac import HierarchicalRbacService
from orcia_core.permissions.iam_accounts import IamAccountRecord
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.role_matrix import now_utc_iso
from orcia_kernel.events import (
    AutonomousContractRevoked,
    AutonomousContractSigned,
    DomainEvent,
)


class AutonomyContractService:
    """Domain service orchestrating autonomy contract signing, revocation & confinement."""

    def __init__(
        self,
        *,
        rbac_service: HierarchicalRbacService,
        repository: AutonomyContractRepositoryPort | None = None,
    ) -> None:
        self._rbac = rbac_service
        self._repo = repository
        self._contracts_by_id: dict[str, AutonomyContract] = {}
        self._outbox_events: list[DomainEvent] = []

    @property
    def outbox_events(self) -> tuple[DomainEvent, ...]:
        return tuple(self._outbox_events)

    async def get_active_contract(
        self, *, workspace_id: str, workflow_id: str
    ) -> AutonomyContract | None:
        if self._repo is not None:
            return await self._repo.get_active_contract(
                workspace_id=workspace_id, workflow_id=workflow_id
            )
        return next(
            (
                c
                for c in self._contracts_by_id.values()
                if c.workspace_id == workspace_id
                and c.workflow_id == workflow_id
                and c.status == "ACTIVE"
            ),
            None,
        )

    async def list_contracts(
        self, *, workspace_id: str, workflow_id: str
    ) -> list[AutonomyContract]:
        if self._repo is not None:
            return await self._repo.list_contracts(
                workspace_id=workspace_id, workflow_id=workflow_id
            )
        items = [
            c
            for c in self._contracts_by_id.values()
            if c.workspace_id == workspace_id and c.workflow_id == workflow_id
        ]
        items.sort(key=lambda c: c.signed_at_iso, reverse=True)
        return items

    async def sign_contract(
        self,
        cmd: SignAutonomyContractCommand,
        *,
        signer: UserIdentity,
        service_principal: IamAccountRecord | None,
        allowed_scope_ids: Sequence[str] = (),
        signer_allowed_actions: set[str] | None = None,
        sp_allowed_actions: set[str] | None = None,
        trace_id: str = "00000000000000000000000000000000",
        instance: str | None = None,
    ) -> AutonomyContract:
        """Validate criticality, single signer role, double SP guard & persist contract."""
        if signer.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)

        crit_norm = cmd.criticality.strip().upper()
        if crit_norm == "HIGH_CRITICAL":
            raise CriticalWorkflowRequiresHumanGateError(instance=instance)
        if crit_norm not in ("LOW_NON_CRITICAL", "STANDARD"):
            raise ValidationDomainError(
                detail_code="ERR_CONTRACT_INVALID_CRITICALITY",
                detail_params={"criticality": cmd.criticality},
                instance=instance,
            )

        signer_role = resolve_signer_role(signer)
        if signer_role is None:
            raise AutonomyContractSignForbiddenError(instance=instance)
        if cmd.max_cost_per_run_usd <= 0:
            raise ValidationDomainError(
                detail_code="ERR_CONTRACT_INVALID_BUDGET",
                instance=instance,
            )
        if not (0.10 <= cmd.post_hoc_sampling_rate <= 0.20):
            raise ValidationDomainError(
                detail_code="ERR_CONTRACT_INVALID_SAMPLING_RATE",
                instance=instance,
            )
        if cmd.tie_break_policy not in ALLOWED_TIE_BREAK_POLICIES:
            raise ValidationDomainError(
                detail_code="ERR_CONTRACT_INVALID_TIE_BREAK",
                detail_params={"policy": cmd.tie_break_policy},
                instance=instance,
            )
        if service_principal is None or not is_service_principal_scoped_to_workspace(
            service_principal,
            workspace_id=cmd.workspace_id,
            allowed_scope_ids=allowed_scope_ids,
            rbac_service=self._rbac,
            scope_path=cmd.scope_path,
        ):
            raise ServicePrincipalInvalidForContractError(instance=instance)

        signer_verbs = resolve_effective_verbs_for_roles(
            rbac_service=self._rbac,
            subject_id=signer.id,
            subject_type="USER",
            roles=(signer.platform_role, *signer.roles),
            scope_path=cmd.scope_path,
            user=signer,
        )
        sp_verbs = resolve_effective_verbs_for_roles(
            rbac_service=self._rbac,
            subject_id=service_principal.id,
            subject_type="SERVICE_PRINCIPAL",
            roles=service_principal.roles,
            scope_path=cmd.scope_path,
        )
        assert_contract_confinement(
            allowed_write_actions=cmd.allowed_write_actions,
            signer_verbs=signer_verbs,
            sp_verbs=sp_verbs,
            signer_allowed_actions=signer_allowed_actions,
            sp_allowed_actions=sp_allowed_actions,
            instance=instance,
        )

        contract = build_signed_autonomy_contract(
            cmd,
            crit_norm=crit_norm,
            service_principal_id=service_principal.id,
            signer_id=signer.id,
            signer_role=signer_role,
        )
        event = AutonomousContractSigned.create(
            contract_id=contract.id,
            workspace_id=contract.workspace_id,
            workflow_id=contract.workflow_id,
            workflow_version=contract.workflow_version,
            service_principal_id=contract.service_principal_id,
            signed_by_user_id=contract.signed_by_user_id,
            signed_by_role=contract.signed_by_role,
            signature_sha256=contract.signature_sha256,
            scope_path=cmd.scope_path,
            trace_id=trace_id,
        )
        self._outbox_events.append(event)

        if self._repo is not None:
            return await self._repo.save_signed_contract(contract, event)

        for existing_id, existing in list(self._contracts_by_id.items()):
            if (
                existing.workspace_id == contract.workspace_id
                and existing.workflow_id == contract.workflow_id
                and existing.status == "ACTIVE"
            ):
                self._contracts_by_id[existing_id] = replace(existing, status="SUPERSEDED")
        self._contracts_by_id[contract.id] = contract
        return contract

    async def revoke_contract(
        self,
        *,
        workspace_id: str,
        workflow_id: str,
        actor: UserIdentity,
        scope_path: str = "GLOBAL",
        trace_id: str = "00000000000000000000000000000000",
        instance: str | None = None,
    ) -> AutonomyContract:
        """Immediately revoke the active autonomy contract for `(workspace_id, workflow_id)`."""
        if actor.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        if resolve_signer_role(actor) is None:
            raise AutonomyContractSignForbiddenError(instance=instance)
        active = await self.get_active_contract(workspace_id=workspace_id, workflow_id=workflow_id)
        if active is None:
            raise AutonomyContractNotFoundError(instance=instance)

        revoked_at_iso = now_utc_iso()
        event = AutonomousContractRevoked.create(
            contract_id=active.id,
            workspace_id=workspace_id,
            workflow_id=workflow_id,
            revoked_by_user_id=actor.id,
            scope_path=scope_path,
            trace_id=trace_id,
        )
        self._outbox_events.append(event)
        if self._repo is not None:
            return await self._repo.mark_contract_revoked(
                contract_id=active.id,
                revoked_by_user_id=actor.id,
                revoked_at_iso=revoked_at_iso,
                event=event,
            )
        revoked = replace(
            active, status="REVOKED", revoked_at_iso=revoked_at_iso, revoked_by_user_id=actor.id
        )
        self._contracts_by_id[active.id] = revoked
        return revoked


__all__ = [
    "ALLOWED_SIGNER_ROLES",
    "ALLOWED_TIE_BREAK_POLICIES",
    "AutonomyContract",
    "AutonomyContractRepositoryPort",
    "AutonomyContractService",
    "AutonomyContractStatus",
    "AutonomySignerRole",
    "ContractCriticality",
    "SignAutonomyContractCommand",
    "assert_contract_confinement",
    "compute_contract_signature_sha256",
    "is_service_principal_scoped_to_workspace",
    "map_action_to_required_verb",
    "resolve_effective_verbs_for_roles",
    "resolve_signer_role",
]
