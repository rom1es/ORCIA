"""Data Models & Store Port for Assistant Mode A Governance (`Story 10.1`, `Story 26.4b`)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from orcia_core.orchestration._assistant_locales import ASSISTANT_FOLDER_LOCALES

AssistantResponseTone = Literal["SYNTHETIC", "BALANCED", "DETAILED_CODE"]
AssistantResponseFormat = Literal["BULLETS_SUMMARY", "STRUCTURED_SECTIONS", "STEP_BY_STEP"]
AssistantOverrideScope = Literal["TEAM", "WORKSPACE", "USER"]
AssistantArbitrationPolicy = Literal["PAUSE_AND_ESCALATE", "AUTO_RESOLVE_WITH_TRACE"]


def _compute_sha256_hex(payload: Any) -> str:
    raw = (
        payload
        if isinstance(payload, str)
        else json.dumps(payload, sort_keys=True, ensure_ascii=False)
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


_FLOC_FR = ASSISTANT_FOLDER_LOCALES["fr"]


@dataclass(frozen=True, slots=True)
class UserLayerPreferences:
    """Tab 1 (`Mes préférences — Couche 5 USER`) settings (`Story 10.1`)."""

    user_id: str
    workspace_id: str
    response_tone: AssistantResponseTone = "BALANCED"
    favorite_format: AssistantResponseFormat = "STRUCTURED_SECTIONS"
    default_hat: str = ""
    personal_instructions: str = _FLOC_FR["user_default_instructions"]
    sha256: str = ""


@dataclass(frozen=True, slots=True)
class WorkspaceLayerSettings:
    """Tab 2 (`Réglages de l'Espace — Couche 4 WORKSPACE`) settings (`Story 10.1`)."""

    workspace_id: str
    workspace_instructions: str = _FLOC_FR["ws_default_instructions"]
    default_checked_sources: tuple[str, ...] = ()
    recommended_agents: tuple[str, ...] = ()
    arbitration_policy: AssistantArbitrationPolicy = "PAUSE_AND_ESCALATE"
    welcome_suggestions: tuple[str, ...] = (
        *_FLOC_FR["ws_suggestions"].split("|"),
        "Analyser l'impact d'une modification d'API",
    )
    mcp_expose_assistant: bool = True
    mcp_frozen_by_upper_layer: bool = False
    mcp_frozen_origin: Literal["PLATFORM", "TEAM"] | None = None
    mcp_endpoint_url: str = "/api/v1/mcp/spaces/default"
    mcp_tool_name: str = "assistant.ask"
    mcp_ide_config_json: str = ""
    sha256: str = ""


@dataclass(frozen=True, slots=True)
class AssembledLayerPreviewItem:
    """Single layer displayed in Tab 3 (`Assemblage complet — Lecture seule`)."""

    layer_number: int
    layer_code: Literal[
        "1_CONSTITUTION",
        "2_PACK_METIER",
        "3_EQUIPE",
        "4_ESPACE",
        "5_UTILISATEUR",
    ]
    label: str
    immutable: bool
    origin_badge: Literal["SOCLE", "PACK", "EQUIPE", "ESPACE", "UTILISATEUR"]
    content: str
    sha256: str


@dataclass(frozen=True, slots=True)
class AssistantCustomizationOverrideRecord:
    """Row representation for `workspace_customization_overrides` (`Story 10.1`)."""

    id: str
    override_key: str
    org_unit_id: str | None
    workspace_id: str | None
    user_id: str | None
    target_uri: str
    override_layer: AssistantOverrideScope
    override_manifest_jsonb: dict[str, Any]
    sha256: str


@dataclass(frozen=True, slots=True)
class AssistantGovernanceView:
    """Mode A governance response for `GET /api/v1/assistant/governance` (`Story 26.4b`)."""

    workspace_id: str
    can_edit_workspace_layer: bool
    user_preferences: UserLayerPreferences
    workspace_settings: WorkspaceLayerSettings
    assembled_layers: tuple[AssembledLayerPreviewItem, ...]
    override_records: tuple[AssistantCustomizationOverrideRecord, ...] = field(
        default_factory=tuple
    )


class AssistantGovernanceStorePort(Protocol):
    """Port for unit-test governance store fakes (`tests/unit/fakes/`)."""

    def get_user_preferences(self, *, workspace_id: str, user_id: str) -> UserLayerPreferences: ...

    def save_user_preferences(
        self,
        *,
        workspace_id: str,
        user_id: str,
        prefs: UserLayerPreferences,
        record: AssistantCustomizationOverrideRecord,
    ) -> UserLayerPreferences: ...

    def get_workspace_settings(self, workspace_id: str) -> WorkspaceLayerSettings: ...

    def save_workspace_settings(
        self,
        *,
        workspace_id: str,
        settings: WorkspaceLayerSettings,
        record: AssistantCustomizationOverrideRecord,
    ) -> WorkspaceLayerSettings: ...

    def get_team_mcp_frozen(
        self, workspace_id: str
    ) -> tuple[bool, Literal["PLATFORM", "TEAM"]] | None: ...

    def set_team_mcp_frozen(
        self,
        *,
        workspace_id: str,
        frozen: bool,
        origin: Literal["PLATFORM", "TEAM"] = "TEAM",
    ) -> None: ...

    def get_team_instructions(self, workspace_id: str) -> str | None: ...

    def list_overrides(self) -> tuple[AssistantCustomizationOverrideRecord, ...]: ...
