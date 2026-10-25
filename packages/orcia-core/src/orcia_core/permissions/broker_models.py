"""Data models, Markdown+YAML KB parser, and Jira URL builder for Permission Broker.

Pure hexagonal domain module (Story 1.4, AD-6, FR-22, UX-DR11) — zero framework imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast
from urllib.parse import quote

from orcia_core.domain.exceptions import ValidationDomainError
from orcia_core.domain.identifiers import new_uuid7_str
from orcia_core.permissions.models import ExecutionIdentityMode

BrokerConnectorScheme = Literal["git", "jira", "confluence", "db", "nexus", "mcp"]
BrokerStepState = Literal["PERMISSION_DENIED_STEP", "PAUSED", "REPLAYED", "GRANTED"]
BrokerTicketStatus = Literal["WAITING_FOR_PERMISSION", "PAUSED", "REPLAYED", "GRANTED"]
BrokerTicketAction = Literal["PAUSE", "REPLAY"]

ALLOWED_BROKER_SCHEMES: frozenset[str] = frozenset(
    {"git", "jira", "confluence", "db", "nexus", "mcp"}
)


def reject_control_chars(value: str, field_name: str, *, instance: str | None = None) -> str:
    """Reject empty strings or strings containing ASCII control characters."""
    cleaned = value.strip()
    if not cleaned or any(ord(ch) < 32 and ch not in ("\n", "\r", "\t") for ch in value):
        raise ValidationDomainError(
            detail_override=f"Invalid or empty value for {field_name}.", instance=instance
        )
    return cleaned


def extract_connector_scheme(
    uri_or_pattern: str, *, instance: str | None = None
) -> BrokerConnectorScheme:
    """Extract and validate the connector scheme (`git`, `jira`, `confluence`, `db`, etc.)."""
    cleaned = reject_control_chars(uri_or_pattern, "uri", instance=instance)
    if "://" not in cleaned:
        raise ValidationDomainError(
            detail_override=f"Missing scheme delimiter '://' in {cleaned!r}.", instance=instance
        )
    scheme, remainder = cleaned.split("://", 1)
    scheme_lower = scheme.lower()
    if scheme_lower not in ALLOWED_BROKER_SCHEMES or not remainder.strip():
        raise ValidationDomainError(
            detail_override=f"Unsupported or empty connector URI: {cleaned!r}.", instance=instance
        )
    return cast(BrokerConnectorScheme, scheme_lower)


def extract_connector_host(uri: str, *, instance: str | None = None) -> str:
    """Extract normalized lowercase host segment after `scheme://`."""
    extract_connector_scheme(uri, instance=instance)
    remainder = uri.strip().split("://", 1)[1]
    host = remainder.split("/", 1)[0].strip().lower()
    if not host:
        raise ValidationDomainError(
            detail_override=f"Missing host in connector URI: {uri!r}.", instance=instance
        )
    return host


@dataclass(frozen=True, slots=True)
class PermissionBrokerPolicy:
    """Permission Knowledge Base policy loaded from Markdown + YAML frontmatter (`FR-22`)."""

    id: str
    policy_key: str
    uri_pattern: str
    connector_scheme: BrokerConnectorScheme
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
class PermissionBrokerTicket:
    """Blocked step ticket tracked by the Permission Broker (`UX-DR11`, `FR-22`)."""

    id: str
    ticket_key: str
    workspace_id: str | None
    requester_user_id: str
    policy_id: str
    step_key: str
    step_number: int
    step_state: BrokerStepState
    status: BrokerTicketStatus
    target_uri: str
    connector_scheme: BrokerConnectorScheme
    execution_identity: ExecutionIdentityMode
    upstream_http_status: Literal[401, 403]
    required_role: str
    approver_team: str
    sla_hours: int
    jira_request_url: str
    permission_broker_hint: str
    procedure_markdown: str = ""


@dataclass(frozen=True, slots=True)
class PermissionCheckOutcome:
    """Outcome of a governed external connector access check (`passthrough` vs principal)."""

    allowed: bool
    status: Literal["GRANTED", "WAITING_FOR_PERMISSION"]
    execution_identity: ExecutionIdentityMode
    target_uri: str
    connector_scheme: BrokerConnectorScheme
    policy: PermissionBrokerPolicy
    ticket: PermissionBrokerTicket | None = None
    permission_broker_hint: str | None = None


def parse_permission_kb_markdown(
    markdown_text: str, *, policy_key: str | None = None, instance: str | None = None
) -> PermissionBrokerPolicy:
    """Parse and validate a Permission KB Markdown document with YAML frontmatter (`FR-22`)."""
    normalized = reject_control_chars(markdown_text, "markdown_text", instance=instance).replace(
        "\r\n", "\n"
    )
    if not normalized.startswith("---\n"):
        raise ValidationDomainError(
            detail_override="Permission KB Markdown must start with YAML frontmatter '---'.",
            instance=instance,
        )
    parts = normalized[4:].split("\n---\n", 1)
    if len(parts) != 2:
        raise ValidationDomainError(
            detail_override="Permission KB Markdown is missing closing YAML frontmatter '---'.",
            instance=instance,
        )
    frontmatter_str, body_md = parts[0], parts[1].strip()
    meta: dict[str, str] = {}
    for line in frontmatter_str.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise ValidationDomainError(
                detail_override=f"Malformed YAML frontmatter line: {stripped!r}", instance=instance
            )
        k, v = stripped.split(":", 1)
        meta[k.strip()] = v.strip().strip('"').strip("'")

    for req_key in (
        "uri_pattern",
        "required_role",
        "approver_team",
        "request_url_template",
        "sla_hours",
    ):
        if not meta.get(req_key):
            raise ValidationDomainError(
                detail_override=f"Missing mandatory YAML frontmatter key: {req_key}",
                instance=instance,
            )

    uri_pattern, required_role = meta["uri_pattern"], meta["required_role"]
    approver_team, req_url_tpl = meta["approver_team"], meta["request_url_template"]
    scheme = extract_connector_scheme(uri_pattern, instance=instance)
    if len(uri_pattern) > 255 or len(required_role) > 128 or len(approver_team) > 128:
        raise ValidationDomainError(
            detail_override="Frontmatter field exceeds maximum allowed length.", instance=instance
        )
    if not req_url_tpl.startswith("https://") or not (8 <= len(req_url_tpl) <= 1024):
        raise ValidationDomainError(
            detail_override="request_url_template must be an https:// URL (8..1024 chars).",
            instance=instance,
        )
    try:
        sla_hours, ttl_days = int(meta["sla_hours"]), int(meta.get("freshness_ttl_days", "90"))
    except ValueError as exc:
        raise ValidationDomainError(
            detail_override="sla_hours and freshness_ttl_days must be integers.", instance=instance
        ) from exc
    if not (1 <= sla_hours <= 720) or not (1 <= ttl_days <= 3650):
        raise ValidationDomainError(
            detail_override="sla_hours must be 1..720 and freshness_ttl_days must be 1..3650.",
            instance=instance,
        )

    sp_allowed = meta.get("service_principal_allowed", "false").lower() in ("true", "1", "yes")
    resolved_key = (
        reject_control_chars(policy_key, "policy_key", instance=instance)
        if policy_key
        else meta.get("policy_key") or f"pol-{scheme}-{required_role.lower()}"
    )
    if len(resolved_key) > 128:
        raise ValidationDomainError(
            detail_override="policy_key exceeds maximum length of 128 characters.",
            instance=instance,
        )
    return PermissionBrokerPolicy(
        new_uuid7_str(),
        resolved_key,
        uri_pattern,
        scheme,
        required_role,
        approver_team,
        req_url_tpl,
        sla_hours,
        body_md or normalized,
        sp_allowed,
        meta.get("approved_by_admin_id") or None,
        meta.get("human_anchor_author_id") or None,
        meta.get("human_anchor_signature") or None,
        ttl_days,
    )


def build_prefilled_jira_request_url(
    template: str,
    *,
    target_uri: str,
    required_role: str,
    approver_team: str,
    requester_email: str,
    step_key: str,
    execution_identity: str,
) -> str:
    """Build URL-encoded pre-filled Atlassian Jira access request link (`UX-DR11`, `FR-22`)."""
    summary_raw = f"[ORCIA Permission Broker] {required_role} sur {target_uri}"
    desc_raw = (
        f"Demande d'accès ({execution_identity}) pour l'étape {step_key} "
        f"par {requester_email} — Approbateur: {approver_team}"
    )
    tokens = {
        "{summary}": quote(summary_raw, safe=""),
        "{description}": quote(desc_raw, safe=""),
        "{target_uri}": quote(target_uri, safe=""),
        "{required_role}": quote(required_role, safe=""),
        "{approver_team}": quote(approver_team, safe=""),
        "{requester_email}": quote(requester_email, safe=""),
        "{step_key}": quote(step_key, safe=""),
    }
    rendered, replaced_any = template, False
    for placeholder, encoded_val in tokens.items():
        if placeholder in rendered:
            rendered, replaced_any = rendered.replace(placeholder, encoded_val), True
    if not replaced_any:
        sep = "&" if "?" in rendered else "?"
        rendered = (
            f"{rendered}{sep}summary={tokens['{summary}']}&description={tokens['{description}']}"
        )
    return rendered


build_jira_request_url = build_prefilled_jira_request_url
