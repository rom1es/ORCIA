"""Pydantic v2 schemas for `/api/v1/health` and `/api/v1/navigation/shell` (UX-DR1, UX-DR2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ModuleKey = Literal[
    "cockpit",
    "inbox",
    "catalog",
    "ontology",
    "gates",
    "finops",
    "admin",
    "bootstrap",
]

ScopeLevel = Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]

AccessMode = Literal["CONTRIBUTOR_ACTION_REQUIRED", "READ_ONLY_OBSERVER"]


class HealthResponse(BaseModel):
    """Health check response payload for `/api/v1/health`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["ok"] = "ok"
    version: str = Field(..., description="Semantic version of the ORCIA API.")
    trace_id: str = Field(
        ...,
        min_length=32,
        max_length=32,
        description="Active 32-hex W3C OpenTelemetry trace identifier.",
    )


class ShellModuleItem(BaseModel):
    """Descriptor for one of the Global Sidebar Navigation modules (Direction C)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key: ModuleKey
    order: int = Field(..., ge=1, le=8)
    route: str
    icon: str
    contributor_badge_count: int = Field(default=0, ge=0)
    has_stale_warning: bool = False
    enabled: bool = True


class ScopeNode(BaseModel):
    """Node in the 4-level Hierarchical Scope Switcher (`⌘W`: GLOBAL -> BU -> TEAM -> WORKSPACE)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    level: ScopeLevel
    name: str
    parent_id: str | None = None
    access_mode: AccessMode = "CONTRIBUTOR_ACTION_REQUIRED"


class HumanProfileBadge(BaseModel):
    """Summary of the active user's Human Profile displayed in the Global Sidebar footer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    archetype_key: str
    display_name: str
    access_mode: AccessMode
    role: str = "TEAM_LEAD"
    org_unit_id: str = "0192c4e0-0000-7000-8000-000000000104"
    org_unit_name: str = "Sous-Équipe Checkout & Core Solutions"


class ShellNavigationResponse(BaseModel):
    """Complete navigation and scope context for the Direction C AppShell."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    active_scope_id: str
    scopes: list[ScopeNode]
    modules: list[ShellModuleItem] = Field(..., min_length=7, max_length=8)
    human_profile: HumanProfileBadge
    trace_id: str = Field(..., min_length=32, max_length=32)


def build_default_shell_navigation(
    trace_id: str,
    *,
    enabled_modules: dict[str, bool] | None = None,
    human_profile: HumanProfileBadge | None = None,
) -> ShellNavigationResponse:
    """Build the default 8-module Direction C shell topology and hierarchical scope tree."""
    scopes = [
        ScopeNode(
            id="scope-global",
            level="GLOBAL",
            name="Plateforme Globale ORCIA",
            parent_id=None,
            access_mode="READ_ONLY_OBSERVER",
        ),
        ScopeNode(
            id="scope-bu-digital",
            level="BU",
            name="BU Produits & Plateformes",
            parent_id="scope-global",
            access_mode="READ_ONLY_OBSERVER",
        ),
        ScopeNode(
            id="scope-team-core",
            level="TEAM",
            name="Équipe Architecture & Agentique",
            parent_id="scope-bu-digital",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
        ),
        ScopeNode(
            id="scope-ws-orcia",
            level="WORKSPACE",
            name="Workspace Solution ORCIA Core",
            parent_id="scope-team-core",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
        ),
    ]
    flags = enabled_modules or {}
    modules = [
        ShellModuleItem(
            key="cockpit",
            order=1,
            route="/cockpit",
            icon="message-square",
            contributor_badge_count=1,
            has_stale_warning=False,
            enabled=flags.get("cockpit", True),
        ),
        ShellModuleItem(
            key="inbox",
            order=2,
            route="/inbox",
            icon="bell",
            contributor_badge_count=2,
            has_stale_warning=False,
            enabled=flags.get("inbox", True),
        ),
        ShellModuleItem(
            key="catalog",
            order=3,
            route="/catalog",
            icon="package",
            contributor_badge_count=0,
            has_stale_warning=False,
            enabled=flags.get("catalog", True),
        ),
        ShellModuleItem(
            key="ontology",
            order=4,
            route="/ontology",
            icon="dna",
            contributor_badge_count=0,
            has_stale_warning=True,
            enabled=flags.get("ontology", True),
        ),
        ShellModuleItem(
            key="gates",
            order=5,
            route="/gates",
            icon="shield",
            contributor_badge_count=1,
            has_stale_warning=False,
            enabled=flags.get("gates", True),
        ),
        ShellModuleItem(
            key="finops",
            order=6,
            route="/finops",
            icon="bar-chart",
            contributor_badge_count=0,
            has_stale_warning=False,
            enabled=flags.get("finops", True),
        ),
        ShellModuleItem(
            key="admin",
            order=7,
            route="/workspaces",
            icon="settings",
            contributor_badge_count=0,
            has_stale_warning=False,
            enabled=flags.get("admin", True),
        ),
        ShellModuleItem(
            key="bootstrap",
            order=8,
            route="/bootstrap",
            icon="rocket",
            contributor_badge_count=0,
            has_stale_warning=False,
            enabled=flags.get("bootstrap", True),
        ),
    ]
    return ShellNavigationResponse(
        active_scope_id="scope-ws-orcia",
        scopes=scopes,
        modules=modules,
        human_profile=human_profile
        or HumanProfileBadge(
            archetype_key="TECH_LEAD",
            display_name="Tech Lead / Architecte",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
        ),
        trace_id=trace_id,
    )
