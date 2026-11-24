"""Idempotent Permission Broker policy & ticket seeds (`AD-16`, `FR-22`)."""

from __future__ import annotations

from dataclasses import dataclass

from orcia_core.permissions._permissions_seed_locales import (
    BROKER_POLICY_APPROVERS,
    BROKER_POLICY_PROCEDURES,
)
from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale


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
    request_url: str = ""

    def __post_init__(self) -> None:
        if not self.request_url and self.jira_request_url:
            object.__setattr__(self, "request_url", self.jira_request_url)
        elif not self.jira_request_url and self.request_url:
            object.__setattr__(self, "jira_request_url", self.request_url)


def build_broker_policy_seeds(
    locale: SupportedLocale = DEFAULT_LOCALE,
) -> tuple[PermissionBrokerPolicySeed, ...]:
    """Return reference Permission Broker policies for the requested locale."""
    procs = BROKER_POLICY_PROCEDURES.get(locale, BROKER_POLICY_PROCEDURES[DEFAULT_LOCALE])
    approvers = BROKER_POLICY_APPROVERS.get(locale, BROKER_POLICY_APPROVERS[DEFAULT_LOCALE])
    jira_tpl = "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa"
    return (
        PermissionBrokerPolicySeed(
            id="0192c4e0-0000-7000-8000-000000001001",
            policy_key="pol-git-payments-checkout",
            uri_pattern="git://*/payments/*",
            connector_scheme="git",
            required_role="ROLE_GIT_PAYMENTS_MAINTAINER",
            approver_team="SecOps & Core Payments IAM",
            request_url_template=f"{jira_tpl}?pid=10420&issuetype=10002&summary={{summary}}&description={{description}}",
            sla_hours=4,
            procedure_markdown=procs["pol-git-payments-checkout"],
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
            request_url_template=f"{jira_tpl}?pid=10420&issuetype=10002&summary={{summary}}&description={{description}}",
            sla_hours=8,
            procedure_markdown=procs["pol-git-archi-security-blackbox"],
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
            approver_team=approvers["confluence_pay"],
            request_url_template=f"{jira_tpl}?pid=10421&issuetype=10002&summary={{summary}}&description={{description}}",
            sla_hours=2,
            procedure_markdown=procs["pol-confluence-pay-spaces"],
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
            request_url_template=f"{jira_tpl}?pid=10422&issuetype=10002&summary={{summary}}&description={{description}}",
            sla_hours=4,
            procedure_markdown=procs["pol-jira-secops-projects"],
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
            approver_team="Platform Engineering & DevSecOps",
            request_url_template=f"{jira_tpl}?pid=10423&issuetype=10002&summary={{summary}}&description={{description}}",
            sla_hours=4,
            procedure_markdown=(
                "### Nexus BMAD Registry\n1. Request `NEXUS_BMAD_PUBLISHER`.\n2. Replay."
            ),
            service_principal_allowed=True,
            approved_by_admin_id="0192c4e0-0000-7000-8000-000000000601",
            human_anchor_author_id="0192c4e0-0000-7000-8000-000000000601",
            human_anchor_signature="SIG-KARIM-NEXUS-BMAD-2026",
            freshness_ttl_days=90,
        ),
        PermissionBrokerPolicySeed(
            id="0192c4e0-0000-7000-8000-000000001006",
            policy_key="pol-harbor-oci-artifacts",
            uri_pattern="harbor://*",
            connector_scheme="harbor",
            required_role="HARBOR_OCI_PULLER",
            approver_team="Platform Engineering & SecOps",
            request_url_template=f"{jira_tpl}?pid=10424&issuetype=10002&summary={{summary}}&description={{description}}",
            sla_hours=4,
            procedure_markdown=(
                "### Harbor OCI Registry\n1. Request `HARBOR_OCI_PULLER`.\n2. Replay."
            ),
            service_principal_allowed=False,
            approved_by_admin_id=None,
            freshness_ttl_days=90,
        ),
        PermissionBrokerPolicySeed(
            id="0192c4e0-0000-7000-8000-000000001007",
            policy_key="pol-git-default-fallback",
            uri_pattern="git://*",
            connector_scheme="git",
            required_role="ROLE_GIT_REPOSITORY_READER",
            approver_team="SecOps & Platform IAM",
            request_url_template=f"{jira_tpl}?pid=10420&issuetype=10002&summary={{summary}}&description={{description}}",
            sla_hours=4,
            procedure_markdown=procs["pol-git-default-fallback"],
            service_principal_allowed=False,
            approved_by_admin_id=None,
            freshness_ttl_days=90,
        ),
        PermissionBrokerPolicySeed(
            id="0192c4e0-0000-7000-8000-000000001008",
            policy_key="pol-jira-default-fallback",
            uri_pattern="jira://*",
            connector_scheme="jira",
            required_role="ROLE_JIRA_PROJECT_CONTRIBUTOR",
            approver_team="SecOps & PMO IAM",
            request_url_template=f"{jira_tpl}?pid=10422&issuetype=10002&summary={{summary}}&description={{description}}",
            sla_hours=4,
            procedure_markdown=procs["pol-jira-default-fallback"],
            service_principal_allowed=False,
            approved_by_admin_id=None,
            freshness_ttl_days=90,
        ),
        PermissionBrokerPolicySeed(
            id="0192c4e0-0000-7000-8000-000000001009",
            policy_key="pol-confluence-default-fallback",
            uri_pattern="confluence://*",
            connector_scheme="confluence",
            required_role="ROLE_CONFLUENCE_SPACE_READER",
            approver_team="Knowledge & SecOps Governance",
            request_url_template=f"{jira_tpl}?pid=10421&issuetype=10002&summary={{summary}}&description={{description}}",
            sla_hours=4,
            procedure_markdown=procs["pol-confluence-default-fallback"],
            service_principal_allowed=False,
            approved_by_admin_id=None,
            freshness_ttl_days=90,
        ),
        PermissionBrokerPolicySeed(
            id="0192c4e0-0000-7000-8000-000000001010",
            policy_key="pol-mcp-default-fallback",
            uri_pattern="mcp://*",
            connector_scheme="mcp",
            required_role="ROLE_MCP_TOOL_EXECUTOR",
            approver_team="Platform Engineering & SecOps",
            request_url_template=f"{jira_tpl}?pid=10425&issuetype=10002&summary={{summary}}&description={{description}}",
            sla_hours=4,
            procedure_markdown=procs["pol-mcp-default-fallback"],
            service_principal_allowed=False,
            approved_by_admin_id=None,
            freshness_ttl_days=90,
        ),
    )


DEFAULT_PERMISSION_BROKER_POLICY_SEEDS: tuple[PermissionBrokerPolicySeed, ...] = (
    build_broker_policy_seeds(DEFAULT_LOCALE)
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
        procedure_markdown=BROKER_POLICY_PROCEDURES[DEFAULT_LOCALE]["pol-git-payments-checkout"],
    ),
)

__all__ = [
    "DEFAULT_PERMISSION_BROKER_POLICY_SEEDS",
    "DEFAULT_PERMISSION_BROKER_TICKET_SEEDS",
    "PermissionBrokerPolicySeed",
    "PermissionBrokerTicketSeed",
    "build_broker_policy_seeds",
]
