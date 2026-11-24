"""Dataclasses, milestone specs & visibility helpers for Day-0 Accostage (`Story 9.2`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from orcia_core.bootstrap._bootstrap_locales import (
    ACCOSTAGE_MILESTONE_TITLES,
    SINGLE_FAMILY_AMBER_WARNING_LOCALES,
)
from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale

LlmProgressiveTierMode = Literal[
    "UNCONFIGURED",
    "QUICK_TRIAL_SINGLE_FAMILY",
    "FULL_ORTHOGONAL_AD10",
]

SINGLE_FAMILY_AMBER_WARNING_FR: str = SINGLE_FAMILY_AMBER_WARNING_LOCALES["fr"]
EXCLUSIVE_USERS_LOCK_SQL: str = "LOCK TABLE users IN EXCLUSIVE MODE"


@dataclass(frozen=True, slots=True)
class AccostageMilestoneSpec:
    """One of the 6 progressive Day-0 Accostage milestones (`Accostage 1/6`..`6/6`)."""

    index: int
    key: str
    title_fr: str
    title_en: str
    target_route: str


@dataclass(frozen=True, slots=True)
class AccostageVisibleMilestone:
    """Role-filtered progressive Accostage milestone exposed to the active session."""

    index: int
    key: str
    title_fr: str
    title_en: str
    target_route: str
    completed: bool
    is_accessible: bool


_MILESTONE_META: tuple[tuple[int, str, str], ...] = (
    (1, "first-admin", "/profile"),
    (2, "first-llm-model", "/settings/ai-models"),
    (3, "first-org-unit", "/organization"),
    (4, "first-space", "/spaces"),
    (5, "first-datasource", "/spaces"),
    (6, "pilot-workflow-run", "/processes"),
)

ACCOSTAGE_SIX_MILESTONES: tuple[AccostageMilestoneSpec, ...] = tuple(
    AccostageMilestoneSpec(
        index=idx,
        key=key,
        title_fr=ACCOSTAGE_MILESTONE_TITLES["fr"][key],
        title_en=ACCOSTAGE_MILESTONE_TITLES["en"][key],
        target_route=route,
    )
    for idx, key, route in _MILESTONE_META
)

_ADMIN_ONLY_MILESTONE_KEYS: frozenset[str] = frozenset(
    {"first-admin", "first-llm-model", "first-datasource"}
)
_ORG_MILESTONE_ROLES: frozenset[str] = frozenset(
    {"PLATFORM_ADMIN", "BU_LEAD", "BU_DIRECTOR", "TEAM_LEAD"}
)


def is_accostage_milestone_accessible(
    milestone_key: str,
    *,
    user_role: str | None = None,
    read_only_observer: bool = False,
    first_admin_initialized: bool = False,
) -> bool:
    """Return True if the active role is allowed to see and open the milestone."""
    if read_only_observer:
        return False
    if user_role is None:
        return not first_admin_initialized
    normalized_role = user_role.strip().upper()
    if normalized_role in ("OBSERVER", "READ_ONLY_OBSERVER"):
        return False
    if normalized_role == "PLATFORM_ADMIN":
        return True
    if milestone_key in _ADMIN_ONLY_MILESTONE_KEYS:
        return False
    if milestone_key == "first-org-unit":
        return normalized_role in _ORG_MILESTONE_ROLES
    return True


@dataclass(frozen=True, slots=True)
class FirstPlatformAdminRecord:
    """Created initial `PLATFORM_ADMIN` account under `LOCK TABLE users IN EXCLUSIVE MODE`."""

    user_id: str
    email: str
    display_name: str
    platform_role: Literal["PLATFORM_ADMIN"]
    orcia_env: str
    sql_lock_statement: str


@dataclass(frozen=True, slots=True)
class AccostageStatusReport:
    """Current Day-0 progressive Accostage status (`Accostage k/6` + LLM tier state)."""

    completed_count: int
    total_count: int
    badge_label: str
    llm_tier_mode: LlmProgressiveTierMode
    distinct_families: tuple[str, ...]
    assistant_trial_enabled: bool
    agentic_gates_ad10_enabled: bool
    amber_warning_badge: str | None
    completed_milestone_keys: tuple[str, ...]
    first_admin_initialized: bool = False
    first_admin_email: str | None = None
    first_admin_display_name: str | None = None
    platform_admin_display_name: str | None = None
    visible_milestones: tuple[AccostageVisibleMilestone, ...] = ()


def build_accostage_status_report(
    *,
    distinct_families: tuple[str, ...],
    completed_keys: set[str],
    first_admin: FirstPlatformAdminRecord | None,
    user_role: str | None = None,
    read_only_observer: bool = False,
    locale: SupportedLocale = DEFAULT_LOCALE,
) -> AccostageStatusReport:
    """Build current `Accostage k/6` report and role-scoped visible milestones."""
    fam_count = len(distinct_families)
    if fam_count == 0:
        tier_mode: LlmProgressiveTierMode = "UNCONFIGURED"
        trial_ok, ad10_ok, amber_badge = False, False, None
    elif fam_count == 1:
        tier_mode = "QUICK_TRIAL_SINGLE_FAMILY"
        trial_ok, ad10_ok = True, False
        amber_badge = SINGLE_FAMILY_AMBER_WARNING_LOCALES.get(
            locale, SINGLE_FAMILY_AMBER_WARNING_FR
        )
    else:
        tier_mode = "FULL_ORTHOGONAL_AD10"
        trial_ok, ad10_ok, amber_badge = True, True, None

    ordered_completed = tuple(m.key for m in ACCOSTAGE_SIX_MILESTONES if m.key in completed_keys)
    completed_count, total_count = len(ordered_completed), len(ACCOSTAGE_SIX_MILESTONES)
    admin_initialized = first_admin is not None
    admin_display_name = first_admin.display_name if first_admin is not None else None
    completed_set = set(ordered_completed)
    visible_milestones = tuple(
        AccostageVisibleMilestone(
            index=spec.index,
            key=spec.key,
            title_fr=spec.title_fr,
            title_en=spec.title_en,
            target_route=(
                ("/profile" if admin_initialized else "/cockpit")
                if spec.key == "first-admin"
                else spec.target_route
            ),
            completed=spec.key in completed_set,
            is_accessible=True,
        )
        for spec in ACCOSTAGE_SIX_MILESTONES
        if is_accostage_milestone_accessible(
            spec.key,
            user_role=user_role,
            read_only_observer=read_only_observer,
            first_admin_initialized=admin_initialized,
        )
    )
    return AccostageStatusReport(
        completed_count=completed_count,
        total_count=total_count,
        badge_label=f"Accostage {completed_count}/{total_count}",
        llm_tier_mode=tier_mode,
        distinct_families=distinct_families,
        assistant_trial_enabled=trial_ok,
        agentic_gates_ad10_enabled=ad10_ok,
        amber_warning_badge=amber_badge,
        completed_milestone_keys=ordered_completed,
        first_admin_initialized=admin_initialized,
        first_admin_email=first_admin.email if first_admin is not None else None,
        first_admin_display_name=admin_display_name,
        platform_admin_display_name=admin_display_name,
        visible_milestones=visible_milestones,
    )


__all__ = [
    "ACCOSTAGE_SIX_MILESTONES",
    "AccostageMilestoneSpec",
    "AccostageStatusReport",
    "AccostageVisibleMilestone",
    "EXCLUSIVE_USERS_LOCK_SQL",
    "FirstPlatformAdminRecord",
    "LlmProgressiveTierMode",
    "SINGLE_FAMILY_AMBER_WARNING_FR",
    "build_accostage_status_report",
    "is_accostage_milestone_accessible",
]
