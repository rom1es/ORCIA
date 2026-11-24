"""Dataclasses, constants & repository port for Autonomy Contracts (`Story 7.1`, `AD-18`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from orcia_core.permissions._autonomy_confinement import (
    AutonomySignerRole,
    compute_contract_signature_sha256,
)
from orcia_core.permissions.role_matrix import now_utc_iso
from orcia_kernel.enums import TieBreakPolicy
from orcia_kernel.events import DomainEvent
from orcia_kernel.ids import new_uuid7_str

ContractCriticality = Literal["LOW_NON_CRITICAL", "STANDARD"]
AutonomyContractStatus = Literal["ACTIVE", "REVOKED", "SUPERSEDED"]

ALLOWED_SIGNER_ROLES: frozenset[str] = frozenset({"TEAM_LEAD", "BU_LEAD", "PLATFORM_ADMIN"})
ALLOWED_TIE_BREAK_POLICIES: frozenset[str] = frozenset(
    {
        "ONTOLOGY_AXIOM_FIRST",
        "DEFER_AND_CONTINUE_WITH_ASSUMPTION",
        "PAUSE_AND_ESCALATE",
    }
)


@dataclass(frozen=True, slots=True)
class AutonomyContract:
    """Signed autonomy contract authorizing `AUTONOMOUS_CONTRACT` runs (`autonomy_contracts`)."""

    id: str
    workspace_id: str
    workflow_id: str
    workflow_version: str
    workflow_sha256: str
    criticality: ContractCriticality
    service_principal_id: str
    allowed_read_sources: tuple[str, ...]
    allowed_write_actions: tuple[str, ...]
    max_cost_per_run_usd: float
    tie_break_policy: TieBreakPolicy
    post_hoc_sampling_rate: float
    status: AutonomyContractStatus
    signed_by_user_id: str
    signed_by_role: AutonomySignerRole
    signature_sha256: str
    signed_at_iso: str
    revoked_at_iso: str | None = None
    revoked_by_user_id: str | None = None


@dataclass(frozen=True, slots=True)
class SignAutonomyContractCommand:
    """Command payload to sign or supersede an active autonomy contract."""

    workspace_id: str
    workflow_id: str
    workflow_version: str
    workflow_sha256: str
    criticality: str
    service_principal_id: str
    allowed_read_sources: tuple[str, ...]
    allowed_write_actions: tuple[str, ...]
    max_cost_per_run_usd: float
    tie_break_policy: TieBreakPolicy = "ONTOLOGY_AXIOM_FIRST"
    post_hoc_sampling_rate: float = 0.15
    scope_path: str = "GLOBAL"


@runtime_checkable
class AutonomyContractRepositoryPort(Protocol):
    """Hexagonal persistence port for `autonomy_contracts` and transactional Outbox events."""

    async def get_active_contract(
        self, *, workspace_id: str, workflow_id: str
    ) -> AutonomyContract | None: ...

    async def list_contracts(
        self, *, workspace_id: str, workflow_id: str
    ) -> list[AutonomyContract]: ...

    async def save_signed_contract(
        self, contract: AutonomyContract, event: DomainEvent
    ) -> AutonomyContract: ...

    async def mark_contract_revoked(
        self,
        *,
        contract_id: str,
        revoked_by_user_id: str,
        revoked_at_iso: str,
        event: DomainEvent,
    ) -> AutonomyContract: ...


def build_signed_autonomy_contract(
    cmd: SignAutonomyContractCommand,
    *,
    crit_norm: str,
    service_principal_id: str,
    signer_id: str,
    signer_role: AutonomySignerRole,
) -> AutonomyContract:
    """Compute SHA-256 signature and construct a signed `AutonomyContract` entity."""
    contract_id = new_uuid7_str()
    signed_at_iso = now_utc_iso()
    sig_sha256 = compute_contract_signature_sha256(
        contract_id=contract_id,
        workspace_id=cmd.workspace_id,
        workflow_id=cmd.workflow_id,
        workflow_version=cmd.workflow_version,
        workflow_sha256=cmd.workflow_sha256,
        service_principal_id=service_principal_id,
        allowed_read_sources=cmd.allowed_read_sources,
        allowed_write_actions=cmd.allowed_write_actions,
        max_cost_per_run_usd=cmd.max_cost_per_run_usd,
        tie_break_policy=cmd.tie_break_policy,
        signed_by_user_id=signer_id,
        signed_by_role=signer_role,
    )
    return AutonomyContract(
        id=contract_id,
        workspace_id=cmd.workspace_id,
        workflow_id=cmd.workflow_id,
        workflow_version=cmd.workflow_version,
        workflow_sha256=cmd.workflow_sha256,
        criticality="LOW_NON_CRITICAL" if crit_norm == "LOW_NON_CRITICAL" else "STANDARD",
        service_principal_id=service_principal_id,
        allowed_read_sources=tuple(
            dict.fromkeys(s.strip() for s in cmd.allowed_read_sources if s.strip())
        ),
        allowed_write_actions=tuple(
            dict.fromkeys(a.strip() for a in cmd.allowed_write_actions if a.strip())
        ),
        max_cost_per_run_usd=float(cmd.max_cost_per_run_usd),
        tie_break_policy=cmd.tie_break_policy,
        post_hoc_sampling_rate=float(cmd.post_hoc_sampling_rate),
        status="ACTIVE",
        signed_by_user_id=signer_id,
        signed_by_role=signer_role,
        signature_sha256=sig_sha256,
        signed_at_iso=signed_at_iso,
    )


__all__ = [
    "ALLOWED_SIGNER_ROLES",
    "ALLOWED_TIE_BREAK_POLICIES",
    "AutonomyContract",
    "AutonomyContractRepositoryPort",
    "AutonomyContractStatus",
    "ContractCriticality",
    "SignAutonomyContractCommand",
    "build_signed_autonomy_contract",
]
