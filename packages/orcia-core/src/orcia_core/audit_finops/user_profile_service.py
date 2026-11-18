"""Pure hexagonal domain models & streak calculation for Personal User Profile (`Story 20.4`).

Zero framework/SDK dependencies (`AD-19`).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal

PopularItemType = Literal["AGENT", "PROCESS", "SKILL", "TOOL"]

_HANDLE_SANITIZE_RE = re.compile(r"[^a-z0-9._-]+")


@dataclass(frozen=True, slots=True)
class PopularUsageItem:
    """Most frequently used agent, process, skill, or tool by a specific user."""

    item_type: PopularItemType
    item_key: str
    title: str
    usage_count: int
    target_route: str


@dataclass(frozen=True, slots=True)
class UserProfileSummary:
    """Personal profile overview strictly confined to the authenticated user."""

    user_id: str
    display_name: str
    handle: str
    email: str
    primary_role: str
    roles: tuple[str, ...]
    led_business_units: tuple[str, ...]
    ontology_business_units: tuple[str, ...]
    led_teams: tuple[str, ...]
    member_teams: tuple[str, ...]
    total_tokens: int
    peak_daily_tokens: int
    longest_streak_days: int
    current_streak_days: int
    popular_items: tuple[PopularUsageItem, ...]


def derive_user_handle(email: str, display_name: str) -> str:
    """Derive a deterministic `@handle`-ready slug from email local-part or display name."""
    raw = (email or "").strip().split("@", 1)[0].lower()
    if not raw:
        raw = (display_name or "").strip().lower().replace(" ", ".")
    cleaned = _HANDLE_SANITIZE_RE.sub("-", raw).strip(".-_")
    return cleaned or "user"


def compute_activity_streaks(
    active_dates: Sequence[date],
    today: date | None = None,
) -> tuple[int, int]:
    """Compute `(longest_streak_days, current_streak_days)` from UTC active dates.

    A current streak stays active if the user had activity `today` or `today - 1 day`.
    Returns `(0, 0)` when `active_dates` is empty.
    """
    unique_sorted = sorted(set(active_dates))
    if not unique_sorted:
        return 0, 0

    longest = 1
    run_len = 1
    for idx in range(1, len(unique_sorted)):
        if unique_sorted[idx] == unique_sorted[idx - 1] + timedelta(days=1):
            run_len += 1
            if run_len > longest:
                longest = run_len
        else:
            run_len = 1

    ref_day = today if today is not None else datetime.now(UTC).date()
    active_set = set(unique_sorted)
    if ref_day in active_set:
        cursor = ref_day
    elif (ref_day - timedelta(days=1)) in active_set:
        cursor = ref_day - timedelta(days=1)
    else:
        return longest, 0

    current = 0
    while cursor in active_set:
        current += 1
        cursor -= timedelta(days=1)
    return longest, current


def rank_popular_usage_items(
    items: Sequence[PopularUsageItem],
    *,
    limit: int = 5,
) -> tuple[PopularUsageItem, ...]:
    """Deduplicate by `(item_type, item_key)`, sort by usage count desc, and cap to `limit`."""
    merged: dict[tuple[PopularItemType, str], PopularUsageItem] = {}
    for item in items:
        if item.usage_count <= 0:
            continue
        key = (item.item_type, item.item_key)
        existing = merged.get(key)
        if existing is None:
            merged[key] = item
        else:
            merged[key] = PopularUsageItem(
                item_type=item.item_type,
                item_key=item.item_key,
                title=existing.title or item.title,
                usage_count=existing.usage_count + item.usage_count,
                target_route=existing.target_route or item.target_route,
            )
    ordered = sorted(
        merged.values(),
        key=lambda x: (-x.usage_count, x.title.lower(), x.item_key),
    )
    return tuple(ordered[: max(0, limit)])


def empty_user_profile_summary(
    *,
    user_id: str,
    user_email: str,
    display_name: str,
    roles: Sequence[str],
) -> UserProfileSummary:
    """Construct a zeroed Day-0 `UserProfileSummary` for an authenticated user."""
    roles_tuple = tuple(r for r in roles if r) or ("CONTRIBUTOR",)
    eff_name = display_name or derive_user_handle(user_email, display_name)
    return UserProfileSummary(
        user_id=user_id,
        display_name=eff_name,
        handle=derive_user_handle(user_email, eff_name),
        email=user_email,
        primary_role=roles_tuple[0],
        roles=roles_tuple,
        led_business_units=(),
        ontology_business_units=(),
        led_teams=(),
        member_teams=(),
        total_tokens=0,
        peak_daily_tokens=0,
        longest_streak_days=0,
        current_streak_days=0,
        popular_items=(),
    )


__all__ = [
    "PopularItemType",
    "PopularUsageItem",
    "UserProfileSummary",
    "compute_activity_streaks",
    "derive_user_handle",
    "empty_user_profile_summary",
    "rank_popular_usage_items",
]
