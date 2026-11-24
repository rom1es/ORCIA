"""Idempotent reference seeds for Bounded Context 7: Permissions & Organization (`AD-16`, `M2`).

Owned by `orcia_core.permissions` and consumed one-way by `orcia_core.bootstrap` so that
`permissions` never imports `bootstrap` (`AD-19`).
"""

from __future__ import annotations

from dataclasses import dataclass

from orcia_core.permissions._broker_seeds import (
    DEFAULT_PERMISSION_BROKER_POLICY_SEEDS,
    DEFAULT_PERMISSION_BROKER_TICKET_SEEDS,
    PermissionBrokerPolicySeed,
    PermissionBrokerTicketSeed,
)
from orcia_core.permissions._permissions_seed_locales import (
    ORG_UNIT_SEED_NAMES,
    WORKSPACE_SEED_NAMES,
)
from orcia_kernel.enums import DEFAULT_LOCALE

INIT_USER_WORKFLOW_URI: str = "orcia://system/bootstrap/init-user"


@dataclass(frozen=True, slots=True)
class OrgUnitSeed:
    """Reference OrgUnit node for hierarchical team tree bootstrap (AD-6, AD-14)."""

    id: str
    slug: str
    name: str
    unit_type: str
    parent_id: str | None


@dataclass(frozen=True, slots=True)
class WorkspaceSeed:
    """Reference Solution Workspace seed decoupled from OrgUnits (AD-6, AD-14)."""

    id: str
    slug: str
    name: str
    owner_org_unit_id: str
    visibility_mode: str
    finops_cost_usd: float


@dataclass(frozen=True, slots=True)
class WorkspaceDatasourceSeed:
    """Reference federated datasource attached to a Solution Workspace (`1..N` per scheme)."""

    id: str
    workspace_id: str
    alias: str
    scheme: str
    uri: str
    role: str
    execution_identity: str = "passthrough"
    freshness_ttl_days: int = 90


_OU_ENT = "0192c4e0-0000-7000-8000-000000000101"
_OU_BU = "0192c4e0-0000-7000-8000-000000000102"
_OU_TEAM = "0192c4e0-0000-7000-8000-000000000103"
_OU_SUB = "0192c4e0-0000-7000-8000-000000000104"
_OU_PART = "0192c4e0-0000-7000-8000-000000000105"

_OU_NAMES = ORG_UNIT_SEED_NAMES[DEFAULT_LOCALE]
DEFAULT_ORG_UNIT_SEEDS: tuple[OrgUnitSeed, ...] = (
    OrgUnitSeed(_OU_ENT, "orcia-enterprise", _OU_NAMES["orcia-enterprise"], "ENTERPRISE", None),
    OrgUnitSeed(_OU_BU, "bu-digital-payments", _OU_NAMES["bu-digital-payments"], "BU", _OU_ENT),
    OrgUnitSeed(
        _OU_TEAM,
        "team-architecture-parent",
        _OU_NAMES["team-architecture-parent"],
        "TEAM",
        _OU_BU,
    ),
    OrgUnitSeed(
        _OU_SUB,
        "subteam-checkout-squad",
        _OU_NAMES["subteam-checkout-squad"],
        "SUB_TEAM",
        _OU_TEAM,
    ),
    OrgUnitSeed(
        _OU_PART,
        "team-partner-external",
        _OU_NAMES["team-partner-external"],
        "TEAM",
        _OU_ENT,
    ),
)

_WS_PAY = "0192c4e0-0000-7000-8000-000000000201"
_WS_LOY = "0192c4e0-0000-7000-8000-000000000202"
_WS_CONF = "0192c4e0-0000-7000-8000-000000000203"

_WS_NAMES = WORKSPACE_SEED_NAMES[DEFAULT_LOCALE]
DEFAULT_WORKSPACE_SEEDS: tuple[WorkspaceSeed, ...] = (
    WorkspaceSeed(
        _WS_PAY,
        "ws-solution-paiement",
        _WS_NAMES["ws-solution-paiement"],
        _OU_SUB,
        "STANDARD",
        142.50,
    ),
    WorkspaceSeed(
        _WS_LOY,
        "ws-solution-fidelite",
        _WS_NAMES["ws-solution-fidelite"],
        _OU_SUB,
        "STANDARD",
        87.25,
    ),
    WorkspaceSeed(
        _WS_CONF,
        "ws-projet-confidentiel",
        _WS_NAMES["ws-projet-confidentiel"],
        _OU_SUB,
        "CONFIDENTIAL_RESTRICTED",
        310.00,
    ),
)

_DS_PREFIX = "0192c4e0-0000-7000-8000-000000000"
DEFAULT_WORKSPACE_DATASOURCE_SEEDS: tuple[WorkspaceDatasourceSeed, ...] = (
    WorkspaceDatasourceSeed(f"{_DS_PREFIX}301", _WS_PAY, "git-payment-frontend", "git", "git://gitlab.entreprise.io/payments/checkout-web", "code_frontend"),  # noqa: E501
    WorkspaceDatasourceSeed(f"{_DS_PREFIX}302", _WS_PAY, "git-payment-api", "git", "git://gitlab.entreprise.io/payments/ledger-api", "code_backend"),  # noqa: E501
    WorkspaceDatasourceSeed(f"{_DS_PREFIX}303", _WS_PAY, "git-payment-infra", "git", "git://gitlab.entreprise.io/payments/infra-terraform", "infra_iac"),  # noqa: E501
    WorkspaceDatasourceSeed(f"{_DS_PREFIX}304", _WS_PAY, "jira-pay-build", "jira", "jira://jira.entreprise.io/projects/PAYBUILD", "backlog_build"),  # noqa: E501
    WorkspaceDatasourceSeed(f"{_DS_PREFIX}305", _WS_PAY, "jira-pay-run", "jira", "jira://jira.entreprise.io/projects/PAYSEC", "incidents_secops"),  # noqa: E501
    WorkspaceDatasourceSeed(f"{_DS_PREFIX}306", _WS_PAY, "confluence-pay-product", "confluence", "confluence://wiki.entreprise.io/spaces/PAYPROD", "kb_product"),  # noqa: E501
    WorkspaceDatasourceSeed(f"{_DS_PREFIX}307", _WS_PAY, "confluence-pay-adr", "confluence", "confluence://wiki.entreprise.io/spaces/PAYADR", "kb_architecture"),  # noqa: E501
    WorkspaceDatasourceSeed(f"{_DS_PREFIX}308", _WS_LOY, "git-loyalty-core", "git", "git://gitlab.entreprise.io/loyalty/rewards-engine", "code_backend"),  # noqa: E501
    WorkspaceDatasourceSeed(f"{_DS_PREFIX}309", _WS_LOY, "jira-loyalty-backlog", "jira", "jira://jira.entreprise.io/projects/LOYALTY", "backlog_build"),  # noqa: E501
    WorkspaceDatasourceSeed(f"{_DS_PREFIX}310", _WS_LOY, "confluence-loyalty-kb", "confluence", "confluence://wiki.entreprise.io/spaces/LOYKB", "kb_product"),  # noqa: E501
)  # fmt: skip

__all__ = [
    "DEFAULT_ORG_UNIT_SEEDS",
    "DEFAULT_PERMISSION_BROKER_POLICY_SEEDS",
    "DEFAULT_PERMISSION_BROKER_TICKET_SEEDS",
    "DEFAULT_WORKSPACE_DATASOURCE_SEEDS",
    "DEFAULT_WORKSPACE_SEEDS",
    "INIT_USER_WORKFLOW_URI",
    "OrgUnitSeed",
    "PermissionBrokerPolicySeed",
    "PermissionBrokerTicketSeed",
    "WorkspaceDatasourceSeed",
    "WorkspaceSeed",
]
