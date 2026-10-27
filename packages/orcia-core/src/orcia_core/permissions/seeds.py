"""Idempotent reference seeds for Bounded Context 7: Permissions & Organization (`AD-16`, `M2`).

Owned by `orcia_core.permissions` and consumed one-way by `orcia_core.bootstrap` so that
`permissions` never imports `bootstrap` (`AD-19`).
"""

from __future__ import annotations

from dataclasses import dataclass

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

DEFAULT_ORG_UNIT_SEEDS: tuple[OrgUnitSeed, ...] = (
    OrgUnitSeed(_OU_ENT, "orcia-enterprise", "Entreprise ORCIA Group", "ENTERPRISE", None),
    OrgUnitSeed(_OU_BU, "bu-digital-payments", "BU Digital & Paiements", "BU", _OU_ENT),
    OrgUnitSeed(
        _OU_TEAM, "team-architecture-parent", "Équipe Parente Architecture & Plateforme",
        "TEAM", _OU_BU,
    ),
    OrgUnitSeed(
        _OU_SUB, "subteam-checkout-squad", "Sous-Équipe Checkout & Core Solutions",
        "SUB_TEAM", _OU_TEAM,
    ),
    OrgUnitSeed(
        _OU_PART, "team-partner-external", "Équipe Partenaire Intégration", "TEAM", _OU_ENT
    ),
)  # fmt: skip

_WS_PAY = "0192c4e0-0000-7000-8000-000000000201"
_WS_LOY = "0192c4e0-0000-7000-8000-000000000202"
_WS_CONF = "0192c4e0-0000-7000-8000-000000000203"

DEFAULT_WORKSPACE_SEEDS: tuple[WorkspaceSeed, ...] = (
    WorkspaceSeed(
        _WS_PAY, "ws-solution-paiement", "Workspace 1 : Solution Paiement",
        _OU_SUB, "STANDARD", 142.50,
    ),
    WorkspaceSeed(
        _WS_LOY, "ws-solution-fidelite", "Workspace 2 : Solution Fidélité",
        _OU_SUB, "STANDARD", 87.25,
    ),
    WorkspaceSeed(
        _WS_CONF, "ws-projet-confidentiel", "Workspace 3 : Projet Confidentiel M&A",
        _OU_SUB, "CONFIDENTIAL_RESTRICTED", 310.00,
    ),
)  # fmt: skip

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


@dataclass(frozen=True, slots=True)
class PermissionBrokerPolicySeed:
    """Reference Permission Broker KB policy seed (`permission_broker_policies`, FR-22)."""

    id: str
    policy_key: str
    uri_pattern: str
    connector_scheme: str
    required_role: str
    approver_team: str
    request_url_template: str
    sla_hours: int
    procedure_markdown: str
    service_principal_allowed: bool = False
    approved_by_admin_id: str | None = None
    human_anchor_author_id: str | None = None
    human_anchor_signature: str | None = None
    freshness_ttl_days: int = 90


@dataclass(frozen=True, slots=True)
class PermissionBrokerTicketSeed:
    """Reference Permission Broker blocked step ticket seed (`permission_broker_tickets`)."""

    id: str
    ticket_key: str
    workspace_id: str | None
    requester_user_id: str
    policy_id: str
    step_key: str
    step_number: int
    step_state: str
    status: str
    target_uri: str
    connector_scheme: str
    execution_identity: str
    upstream_http_status: int
    required_role: str
    approver_team: str
    sla_hours: int
    jira_request_url: str
    permission_broker_hint: str
    procedure_markdown: str = ""


DEFAULT_PERMISSION_BROKER_POLICY_SEEDS: tuple[PermissionBrokerPolicySeed, ...] = (
    PermissionBrokerPolicySeed(
        id="0192c4e0-0000-7000-8000-000000001001",
        policy_key="pol-git-payments-checkout",
        uri_pattern="git://*/payments/*",
        connector_scheme="git",
        required_role="ROLE_GIT_PAYMENTS_MAINTAINER",
        approver_team="SecOps & Core Payments IAM",
        request_url_template=(
            "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa"
            "?pid=10420&issuetype=10002&summary={summary}&description={description}"
        ),
        sla_hours=4,
        procedure_markdown=(
            "### Procédure d'habilitation Dépôts Git Paiement\n"
            "1. Ouvrir le ticket Jira IAM pré-rempli.\n"
            "2. Faire valider `ROLE_GIT_PAYMENTS_MAINTAINER` par `SecOps & Core Payments IAM`.\n"
            "3. Cliquer sur **Rejouer l'étape** dans le Dock Permission Broker."
        ),
        service_principal_allowed=False,
        approved_by_admin_id=None,
        human_anchor_author_id="0192c4e0-0000-7000-8000-000000000601",
        human_anchor_signature="SIG-KARIM-SECOPS-GIT-PAYMENTS-2026",
        freshness_ttl_days=90,
    ),
    PermissionBrokerPolicySeed(
        id="0192c4e0-0000-7000-8000-000000001002",
        policy_key="pol-git-archi-security-blackbox",
        uri_pattern="git://*/archi/*",
        connector_scheme="git",
        required_role="ROLE_GIT_ARCHI_EXECUTOR",
        approver_team="Architecture & Security Board",
        request_url_template=(
            "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa"
            "?pid=10420&issuetype=10002&summary={summary}&description={description}"
        ),
        sla_hours=8,
        procedure_markdown=(
            "### Procédure d'habilitation Agents Architecture & SecOps\n"
            "Validation par le comité Architecture & Security Board (SLA 8h)."
        ),
        service_principal_allowed=True,
        approved_by_admin_id="0192c4e0-0000-7000-8000-000000000601",
        human_anchor_author_id="0192c4e0-0000-7000-8000-000000000601",
        human_anchor_signature="SIG-KARIM-SERVICE-PRINCIPAL-APPROVED",
        freshness_ttl_days=60,
    ),
    PermissionBrokerPolicySeed(
        id="0192c4e0-0000-7000-8000-000000001003",
        policy_key="pol-confluence-pay-spaces",
        uri_pattern="confluence://PAY*",
        connector_scheme="confluence",
        required_role="CONFLUENCE_PAY_ADR_READER",
        approver_team="Architecture Paiement & Conformité PCI",
        request_url_template=(
            "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa"
            "?pid=10421&issuetype=10002&summary={summary}&description={description}"
        ),
        sla_hours=2,
        procedure_markdown=(
            "### Accès Espace Confluence Architecture PCI\n"
            "Octroi du groupe `CONFLUENCE_PAY_ADR_READER` sous 2h ouvrées."
        ),
        service_principal_allowed=False,
        approved_by_admin_id=None,
        human_anchor_author_id="0192c4e0-0000-7000-8000-000000000603",
        human_anchor_signature="SIG-MARC-TECH-LEAD-CONFLUENCE-PAY",
        freshness_ttl_days=90,
    ),
    PermissionBrokerPolicySeed(
        id="0192c4e0-0000-7000-8000-000000001004",
        policy_key="pol-jira-secops-projects",
        uri_pattern="jira://*SEC*",
        connector_scheme="jira",
        required_role="JIRA_SECOPS_TRANSITION_ACTOR",
        approver_team="CSIRT & SecOps Governance",
        request_url_template=(
            "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa"
            "?pid=10422&issuetype=10002&summary={summary}&description={description}"
        ),
        sla_hours=4,
        procedure_markdown=(
            "### Habilitation Transitions Jira SecOps\n"
            "Requiert le rôle `JIRA_SECOPS_TRANSITION_ACTOR` validé par CSIRT."
        ),
        service_principal_allowed=False,
        approved_by_admin_id=None,
        human_anchor_author_id="0192c4e0-0000-7000-8000-000000000601",
        human_anchor_signature="SIG-KARIM-SECOPS-JIRA-2026",
        freshness_ttl_days=30,
    ),
    PermissionBrokerPolicySeed(
        id="0192c4e0-0000-7000-8000-000000001005",
        policy_key="pol-nexus-bmad-registry",
        uri_pattern="nexus://*",
        connector_scheme="nexus",
        required_role="NEXUS_BMAD_PUBLISHER",
        approver_team="Platform Engineering Registry Team",
        request_url_template=(
            "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa"
            "?pid=10423&issuetype=10002&summary={summary}&description={description}"
        ),
        sla_hours=6,
        procedure_markdown=(
            "### Habilitation Registre Nexus BMAD\n"
            "Approbation par Platform Engineering Registry Team."
        ),
        service_principal_allowed=True,
        approved_by_admin_id="0192c4e0-0000-7000-8000-000000000601",
        freshness_ttl_days=120,
    ),
    PermissionBrokerPolicySeed(
        id="0192c4e0-0000-7000-8000-000000001006",
        policy_key="pol-db-orcia-catalog",
        uri_pattern="db://*",
        connector_scheme="db",
        required_role="DB_CATALOG_WORKFLOW_OPERATOR",
        approver_team="Data Governance & DBA Team",
        request_url_template=(
            "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa"
            "?pid=10424&issuetype=10002&summary={summary}&description={description}"
        ),
        sla_hours=4,
        procedure_markdown=(
            "### Habilitation Base Catalogue ORCIA\nApprobation par Data Governance & DBA Team."
        ),
        service_principal_allowed=False,
        approved_by_admin_id=None,
        freshness_ttl_days=90,
    ),
)

DEFAULT_PERMISSION_BROKER_TICKET_SEEDS: tuple[PermissionBrokerTicketSeed, ...] = (
    PermissionBrokerTicketSeed(
        id="0192c4e0-0000-7000-8000-000000001101",
        ticket_key="tkt-perm-step-02-git-checkout-core",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        requester_user_id="0192c4e0-0000-7000-8000-000000000604",
        policy_id="0192c4e0-0000-7000-8000-000000001001",
        step_key="step-02-execution",
        step_number=2,
        step_state="PERMISSION_DENIED_STEP",
        status="WAITING_FOR_PERMISSION",
        target_uri="git://github.enterprise/payments/checkout-core.git",
        connector_scheme="git",
        execution_identity="passthrough",
        upstream_http_status=403,
        required_role="ROLE_GIT_PAYMENTS_MAINTAINER",
        approver_team="SecOps & Core Payments IAM",
        sla_hours=4,
        jira_request_url=(
            "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa"
            "?pid=10420&issuetype=10002"
            "&summary=%5BORCIA%20Permission%20Broker%5D%20ROLE_GIT_PAYMENTS_MAINTAINER"
            "%20sur%20git%3A//github.enterprise/payments/checkout-core.git"
            "&description=Demande%20d%27acc%C3%A8s%20Passthrough%20pour%20step-02-execution"
        ),
        permission_broker_hint=(
            "jira://IAM/ROLE_GIT_PAYMENTS_MAINTAINER"
            "?target=git%3A//github.enterprise/payments/checkout-core.git"
            "&approver=SecOps%20%26%20Core%20Payments%20IAM&sla_hours=4"
        ),
        procedure_markdown=(
            "### Procédure d'habilitation Dépôts Git Paiement\n"
            "1. Ouvrir le ticket Jira IAM pré-rempli.\n"
            "2. Faire valider `ROLE_GIT_PAYMENTS_MAINTAINER` par `SecOps & Core Payments IAM`.\n"
            "3. Cliquer sur **Rejouer l'étape** dans le Dock Permission Broker."
        ),
    ),
)
