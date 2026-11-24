"""Validation and resolution of known organization users (`Story 17.2` / `CAP-067`).

Enforces strict existence checks on `lead_user_id` and `member_user_ids` against
active known accounts (`iam_accounts` and `users`), preventing ghost users or arbitrary strings.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from orcia_core.permissions.errors import OrgUnitUnknownUserError


@dataclass(frozen=True, slots=True)
class KnownOrgUser:
    """Active known platform user (human) suitable for org unit attachment."""

    principal_id: str
    display_name: str
    email: str | None = None


def resolve_and_validate_org_unit_leads(
    lead_user_ids: Sequence[str] | None,
    lead_user_id: str | None,
    known_users: Sequence[KnownOrgUser],
) -> tuple[tuple[str, ...], str | None]:
    """Validate and resolve multiple or single lead user identifiers to canonical `principal_id`."""
    index: dict[str, str] = {}
    for user in known_users:
        canon = user.principal_id.strip()
        if canon:
            index[canon.lower()] = canon
        if user.email:
            clean_email = user.email.strip().lower()
            if clean_email:
                index[clean_email] = canon

    candidates: list[str] = []
    if lead_user_ids is not None:
        candidates.extend([str(x).strip() for x in lead_user_ids if str(x).strip()])
    elif lead_user_id is not None:
        c = lead_user_id.strip()
        if c:
            candidates.append(c)

    resolved: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        matched = index.get(item.lower())
        if matched is None:
            raise OrgUnitUnknownUserError(
                detail_code="ERR_ORG_UNKNOWN_LEAD_USER",
                detail_params={"user_ref": item},
            )
        if matched not in seen:
            seen.add(matched)
            resolved.append(matched)

    t = tuple(resolved)
    primary = t[0] if t else None
    return t, primary


def resolve_and_validate_org_unit_users(
    lead_user_id: str | None,
    member_user_ids: Sequence[str],
    known_users: Sequence[KnownOrgUser],
) -> tuple[str | None, tuple[str, ...]]:
    """Validate and resolve lead and member identifiers to canonical `principal_id`.

    Lookup matches case-insensitively on `user.principal_id` and `user.email` ONLY.
    Plain `display_name` values (such as a first name) never match unless they equal
    the canonical `principal_id` or `email`.
    Raises `OrgUnitUnknownUserError` (HTTP 422) if any non-empty input is unknown.
    """
    _, resolved_lead = resolve_and_validate_org_unit_leads(
        lead_user_ids=None,
        lead_user_id=lead_user_id,
        known_users=known_users,
    )

    index: dict[str, str] = {}
    for user in known_users:
        canon = user.principal_id.strip()
        if canon:
            index[canon.lower()] = canon
        if user.email:
            clean_email = user.email.strip().lower()
            if clean_email:
                index[clean_email] = canon

    resolved_members: list[str] = []
    seen_members: set[str] = set()
    for raw_member in member_user_ids:
        cleaned_member = (raw_member or "").strip()
        if not cleaned_member:
            continue
        matched_member = index.get(cleaned_member.lower())
        if matched_member is None:
            raise OrgUnitUnknownUserError(
                detail_code="ERR_ORG_UNKNOWN_MEMBER_USER",
                detail_params={"user_ref": cleaned_member},
            )
        if matched_member not in seen_members:
            seen_members.add(matched_member)
            resolved_members.append(matched_member)

    return resolved_lead, tuple(resolved_members)


__all__ = [
    "KnownOrgUser",
    "resolve_and_validate_org_unit_leads",
    "resolve_and_validate_org_unit_users",
]
