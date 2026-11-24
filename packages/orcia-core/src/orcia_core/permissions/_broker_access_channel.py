"""Access request channel fallback and URL builder for Permission Broker."""

from __future__ import annotations

from urllib.parse import quote

from orcia_core.permissions._permissions_locales import (
    ACCESS_REQUEST_DESC_LOCALES,
    ACCESS_REQUEST_SUMMARY_LOCALES,
)
from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale
from orcia_kernel.ports import AccessRequestChannelPort, get_access_request_channel


class DefaultAccessRequestChannel(AccessRequestChannelPort):
    """Generic fallback `AccessRequestChannelPort` when no vertical pack overrides it."""

    @property
    def channel_name(self) -> str:
        return "default"

    def build_access_request_url(
        self,
        template: str,
        *,
        target_uri: str,
        required_role: str,
        approver_team: str,
        requester_email: str,
        step_key: str,
        execution_identity: str,
        locale: SupportedLocale = DEFAULT_LOCALE,
    ) -> str:
        loc = locale if locale in ACCESS_REQUEST_SUMMARY_LOCALES else DEFAULT_LOCALE
        summary_raw = ACCESS_REQUEST_SUMMARY_LOCALES[loc].format(
            required_role=required_role, target_uri=target_uri
        )
        desc_raw = ACCESS_REQUEST_DESC_LOCALES[loc].format(
            execution_identity=execution_identity,
            step_key=step_key,
            requester_email=requester_email,
            approver_team=approver_team,
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
                f"{rendered}{sep}summary={tokens['{summary}']}"
                f"&description={tokens['{description}']}"
            )
        return rendered

    def build_access_request_hint(
        self,
        *,
        target_uri: str,
        required_role: str,
        approver_team: str,
        sla_hours: int,
    ) -> str:
        req_q, uri_q = quote(required_role, safe=""), quote(target_uri, safe="")
        app_q = quote(approver_team, safe="")
        return f"orcia://iam/{req_q}?target={uri_q}&approver={app_q}&sla_hours={sla_hours}"


_DEFAULT_ACCESS_CHANNEL = DefaultAccessRequestChannel()


def resolve_active_access_request_channel() -> AccessRequestChannelPort:
    """Return the registered `AccessRequestChannelPort` or the generic fallback (`DEC-ACC-01`)."""
    return get_access_request_channel() or _DEFAULT_ACCESS_CHANNEL


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
    """Build URL-encoded pre-filled access request link via `AccessRequestChannelPort`."""
    return resolve_active_access_request_channel().build_access_request_url(
        template,
        target_uri=target_uri,
        required_role=required_role,
        approver_team=approver_team,
        requester_email=requester_email,
        step_key=step_key,
        execution_identity=execution_identity,
    )


build_jira_request_url = build_prefilled_jira_request_url

__all__ = [
    "DefaultAccessRequestChannel",
    "build_jira_request_url",
    "build_prefilled_jira_request_url",
    "resolve_active_access_request_channel",
]
