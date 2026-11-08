"""Story 10.1 — 4-Level Governance & Customization of `Mon Assistant` (Mode A & Mode B).

Implements (`Principes B, G, H, K, M.4`, `AD-14`, `AD-15`, `AD-19`, `AD-21`):
- 4-level override hierarchy (`PLATFORM -> TEAM -> WORKSPACE -> USER`) for
  `orcia://system/workflows/assistant-agent` stored in `workspace_customization_overrides`.
- Mode A (`⚙ Réglages de l'assistant`, 3 tabs):
  1. `👤 Mes préférences (Couche 5 — USER)`
  2. `📦 Réglages de l'Espace (Couche 4 — WORKSPACE)` + `🔌 Exposer l'Assistant en MCP`
     (`assistant.ask` on `/api/v1/mcp`, governed by the Funnel Rule `Principe G`)
  3. `👁️ Assemblage complet (Lecture seule)` of the 5 active prompt layers (`1..5`).
- Mode B (`☍ Personnaliser dans le Studio`, `@xyflow/react`):
  - Enforces immutable `🔒 AssistantHarness` entry/exit boundaries (`ENTRY_BOUNDARY_HARNESS`,
    `EXIT_BOUNDARY_HARNESS` -> `HTTP 422 ERR_IMMUTABLE_HARNESS_BOUNDARY` on tamper).
  - Supports sub-layer edits (`COUCHES · N`), sub-agent insertion, dry-run (`▷ Tester`),
    scoped save (`TEAM` / `WORKSPACE`), and 1-click reset (`↺ Réinitialiser`).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal

from orcia_core.orchestration.assistant_agent import ASSISTANT_WORKFLOW_URI
from orcia_core.orchestration.assistant_harness import (
    CONSTITUTIONAL_LAYER_1_TEXT,
    resolve_profile_adaptation,
)
from orcia_core.orchestration.errors import (
    FunnelRuleViolationError,
    ImmutableHarnessBoundaryError,
    ObserverModeReadOnlyError,
    ScopeAccessDeniedError,
)
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str

AssistantResponseTone = Literal["SYNTHETIC", "BALANCED", "DETAILED_CODE"]
AssistantResponseFormat = Literal["BULLETS_SUMMARY", "STRUCTURED_SECTIONS", "STEP_BY_STEP"]
AssistantOverrideScope = Literal["TEAM", "WORKSPACE", "USER"]
AssistantArbitrationPolicy = Literal["PAUSE_AND_ESCALATE", "AUTO_RESOLVE_WITH_TRACE"]

ENTRY_HARNESS_NODE_ID: str = "ENTRY_BOUNDARY_HARNESS"
EXIT_HARNESS_NODE_ID: str = "EXIT_BOUNDARY_HARNESS"
REQUIRED_CORE_NODE_IDS: tuple[str, ...] = (
    "1_INTENT_ROUTER",
    "2_QUERY_PLANNER_AND_ONTOLOGY_EXPANSION",
    "3_PARALLEL_FAN_OUT",
    "4_CRITICAL_TRIAGE_AND_AXIOM_VERIFICATION",
    "5_PROFILE_ADAPTIVE_SYNTHESIZER",
)


def _compute_sha256_hex(payload: Any) -> str:
    raw = (
        payload
        if isinstance(payload, str)
        else json.dumps(payload, sort_keys=True, ensure_ascii=False)
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class UserLayerPreferences:
    """Tab 1 (`👤 Mes préférences — Couche 5 USER`) settings (`Story 10.1`)."""

    user_id: str
    workspace_id: str
    response_tone: AssistantResponseTone = "BALANCED"
    favorite_format: AssistantResponseFormat = "STRUCTURED_SECTIONS"
    default_hat: str = "PM"
    personal_instructions: str = "Toujours citer les preuves [S1] et synthétiser les risques."
    sha256: str = ""


@dataclass(frozen=True, slots=True)
class WorkspaceLayerSettings:
    """Tab 2 (`📦 Réglages de l'Espace — Couche 4 WORKSPACE`) settings (`Story 10.1`)."""

    workspace_id: str
    workspace_instructions: str = (
        "Respecter le glossaire actif de l'Espace et privilégier les sources RÉFÉRENCE."
    )
    default_checked_sources: tuple[str, ...] = (
        "orcia://sources/repo-main",
        "orcia://sources/architecture-kb",
        "orcia://sources/project-delivery",
    )
    recommended_agents: tuple[str, ...] = ("@spec-architect", "@security-reviewer")
    arbitration_policy: AssistantArbitrationPolicy = "PAUSE_AND_ESCALATE"
    welcome_suggestions: tuple[str, ...] = (
        "Synthétiser les derniers écarts documentaires de l'Espace",
        "Vérifier la conformité d'un ticket avec l'ontologie N1–N3",
        "Préparer un dossier de cadrage technique",
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
    """Single layer displayed in Tab 3 (`👁️ Assemblage complet — Lecture seule`)."""

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
class AssistantStudioNodeSpec:
    """Node in Mode B (`☍ Personnaliser dans le Studio` `@xyflow/react` graph)."""

    node_id: str
    title: str
    node_order: int
    is_harness_boundary: bool
    locked_by: Literal["HARNESS", "PLATFORM", "TEAM"] | None
    enabled: bool = True
    sub_layers_count: int = 3
    enabled_sub_layers: tuple[str, ...] = (
        "1_INPUT_VALIDATION",
        "2_CORE_PROCESSING",
        "3_OUTPUT_TRIAGE",
    )
    sub_agent_uri: str | None = None


@dataclass(frozen=True, slots=True)
class AssistantStudioGraphState:
    """Mode B Studio state for `orcia://system/workflows/assistant-agent` (`Story 10.1`)."""

    workflow_uri: str
    scope_level: Literal["DEFAULT", "TEAM", "WORKSPACE"]
    scope_id: str
    ai_pre_prompt: str
    nodes: tuple[AssistantStudioNodeSpec, ...]
    override_key: str | None
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
    """Consolidated response for `GET /api/v1/assistant/governance` (`Story 10.1`)."""

    workspace_id: str
    can_edit_workspace_layer: bool
    can_open_studio_mode_b: bool
    user_preferences: UserLayerPreferences
    workspace_settings: WorkspaceLayerSettings
    assembled_layers: tuple[AssembledLayerPreviewItem, ...]
    studio_graph: AssistantStudioGraphState
    override_records: tuple[AssistantCustomizationOverrideRecord, ...] = field(
        default_factory=tuple
    )


def build_default_studio_nodes() -> tuple[AssistantStudioNodeSpec, ...]:
    """Return the canonical 5 nodes wrapped inside the 2 immutable `🔒 AssistantHarness` bounds."""
    return (
        AssistantStudioNodeSpec(
            node_id=ENTRY_HARNESS_NODE_ID,
            title="🔒 Borne d'Entrée — AssistantHarness (PII/Secrets & Contexte)",
            node_order=0,
            is_harness_boundary=True,
            locked_by="HARNESS",
            enabled=True,
            sub_layers_count=2,
            enabled_sub_layers=("1_PASSTHROUGH_IDENTITY", "2_PII_REVERSIBLE_SCRUBBER"),
        ),
        AssistantStudioNodeSpec(
            node_id="1_INTENT_ROUTER",
            title="1. Routeur d'Intention & Casquette",
            node_order=1,
            is_harness_boundary=False,
            locked_by="PLATFORM",
            enabled=True,
            sub_layers_count=3,
        ),
        AssistantStudioNodeSpec(
            node_id="2_QUERY_PLANNER_AND_ONTOLOGY_EXPANSION",
            title="2. Query Planner & Expansion Ontologique",
            node_order=2,
            is_harness_boundary=False,
            locked_by=None,
            enabled=True,
            sub_layers_count=3,
        ),
        AssistantStudioNodeSpec(
            node_id="3_PARALLEL_FAN_OUT",
            title="3. Fan-Out Parallèle (RAG, Glossaire, Outils MCP)",
            node_order=3,
            is_harness_boundary=False,
            locked_by=None,
            enabled=True,
            sub_layers_count=4,
        ),
        AssistantStudioNodeSpec(
            node_id="4_CRITICAL_TRIAGE_AND_AXIOM_VERIFICATION",
            title="4. Tri Critique & Vérification d'Axiomes",
            node_order=4,
            is_harness_boundary=False,
            locked_by=None,
            enabled=True,
            sub_layers_count=3,
        ),
        AssistantStudioNodeSpec(
            node_id="5_PROFILE_ADAPTIVE_SYNTHESIZER",
            title="5. Synthétiseur Adaptatif au Profil Humain",
            node_order=5,
            is_harness_boundary=False,
            locked_by=None,
            enabled=True,
            sub_layers_count=3,
        ),
        AssistantStudioNodeSpec(
            node_id=EXIT_HARNESS_NODE_ID,
            title="🔒 Borne de Sortie — AssistantHarness (Anti-Citation Fantôme & Verrou V5)",
            node_order=6,
            is_harness_boundary=True,
            locked_by="HARNESS",
            enabled=True,
            sub_layers_count=2,
            enabled_sub_layers=("1_CITATION_VERIFIER", "2_HUMAN_ANCHOR_AND_V5_GUARD"),
        ),
    )


class AssistantFourLevelGovernanceService:
    """Manages Mode A (3-tab modal) & Mode B (Studio graph) for `Mon Assistant` (`Story 10.1`)."""

    def __init__(self) -> None:
        self._user_prefs: dict[tuple[str, str], UserLayerPreferences] = {}
        self._workspace_settings: dict[str, WorkspaceLayerSettings] = {}
        self._team_instructions: dict[str, str] = {}
        self._team_mcp_frozen: dict[str, tuple[bool, Literal["PLATFORM", "TEAM"]]] = {}
        self._studio_graphs: dict[tuple[str, str], AssistantStudioGraphState] = {}
        self._overrides: dict[str, AssistantCustomizationOverrideRecord] = {}
        self._version_counter: int = 1

    @property
    def version_counter(self) -> int:
        """Monotonic counter incremented whenever any assistant governance setting changes."""
        return self._version_counter

    def freeze_mcp_at_upper_layer(
        self,
        *,
        workspace_id: str,
        frozen: bool,
        origin: Literal["PLATFORM", "TEAM"] = "TEAM",
    ) -> None:
        """Freeze or unfreeze MCP exposure from `TEAM` or `PLATFORM` (`Principe G`)."""
        if frozen:
            self._team_mcp_frozen[workspace_id] = (True, origin)
            existing = self.get_workspace_settings(workspace_id)
            self._workspace_settings[workspace_id] = WorkspaceLayerSettings(
                workspace_id=workspace_id,
                workspace_instructions=existing.workspace_instructions,
                default_checked_sources=existing.default_checked_sources,
                recommended_agents=existing.recommended_agents,
                arbitration_policy=existing.arbitration_policy,
                welcome_suggestions=existing.welcome_suggestions,
                mcp_expose_assistant=False,
                mcp_frozen_by_upper_layer=True,
                mcp_frozen_origin=origin,
                mcp_endpoint_url=existing.mcp_endpoint_url,
                mcp_tool_name=existing.mcp_tool_name,
                mcp_ide_config_json=existing.mcp_ide_config_json,
                sha256=existing.sha256,
            )
        else:
            self._team_mcp_frozen.pop(workspace_id, None)
        self._version_counter += 1

    def get_user_preferences(self, *, workspace_id: str, user_id: str) -> UserLayerPreferences:
        key = (workspace_id, user_id)
        if key not in self._user_prefs:
            default = UserLayerPreferences(user_id=user_id, workspace_id=workspace_id)
            digest = _compute_sha256_hex(
                {
                    "tone": default.response_tone,
                    "format": default.favorite_format,
                    "hat": default.default_hat,
                    "instructions": default.personal_instructions,
                }
            )
            self._user_prefs[key] = UserLayerPreferences(
                user_id=user_id,
                workspace_id=workspace_id,
                response_tone=default.response_tone,
                favorite_format=default.favorite_format,
                default_hat=default.default_hat,
                personal_instructions=default.personal_instructions,
                sha256=digest,
            )
        return self._user_prefs[key]

    def update_user_preferences(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        response_tone: AssistantResponseTone,
        favorite_format: AssistantResponseFormat,
        default_hat: str,
        personal_instructions: str,
    ) -> UserLayerPreferences:
        """Update Tab 1 (`👤 Mes préférences — Couche 5 USER`)."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError()

        default_hat_str = default_hat.strip().upper() or "PM"
        personal_instr_str = personal_instructions.strip()
        manifest: dict[str, object] = {
            "response_tone": response_tone,
            "favorite_format": favorite_format,
            "default_hat": default_hat_str,
            "personal_instructions": personal_instr_str,
        }
        digest = _compute_sha256_hex(manifest)
        prefs = UserLayerPreferences(
            user_id=user.id,
            workspace_id=workspace_id,
            response_tone=response_tone,
            favorite_format=favorite_format,
            default_hat=default_hat_str,
            personal_instructions=personal_instr_str,
            sha256=digest,
        )
        self._user_prefs[(workspace_id, user.id)] = prefs
        ov_key = f"assistant-user-{workspace_id}-{user.id}"
        self._overrides[ov_key] = AssistantCustomizationOverrideRecord(
            id=new_uuid7_str(),
            override_key=ov_key,
            org_unit_id=None,
            workspace_id=workspace_id,
            user_id=user.id,
            target_uri=ASSISTANT_WORKFLOW_URI,
            override_layer="USER",
            override_manifest_jsonb=manifest,
            sha256=digest,
        )
        self._version_counter += 1
        return prefs

    def get_workspace_settings(self, workspace_id: str) -> WorkspaceLayerSettings:
        if workspace_id not in self._workspace_settings:
            endpoint_url = f"/api/v1/mcp/spaces/{workspace_id}"
            ide_cfg = json.dumps(
                {
                    "mcpServers": {
                        f"orcia-assistant-{workspace_id}": {
                            "url": endpoint_url,
                            "tool": "assistant.ask",
                            "headers": {"Authorization": "Bearer pat_mcp_<votre_jeton>"},
                        }
                    }
                },
                indent=2,
            )
            default = WorkspaceLayerSettings(
                workspace_id=workspace_id,
                mcp_endpoint_url=endpoint_url,
                mcp_ide_config_json=ide_cfg,
            )
            digest = _compute_sha256_hex(
                {
                    "workspace_instructions": default.workspace_instructions,
                    "default_checked_sources": default.default_checked_sources,
                    "recommended_agents": default.recommended_agents,
                    "arbitration_policy": default.arbitration_policy,
                    "mcp_expose_assistant": default.mcp_expose_assistant,
                }
            )
            self._workspace_settings[workspace_id] = WorkspaceLayerSettings(
                workspace_id=workspace_id,
                workspace_instructions=default.workspace_instructions,
                default_checked_sources=default.default_checked_sources,
                recommended_agents=default.recommended_agents,
                arbitration_policy=default.arbitration_policy,
                welcome_suggestions=default.welcome_suggestions,
                mcp_expose_assistant=default.mcp_expose_assistant,
                mcp_frozen_by_upper_layer=False,
                mcp_frozen_origin=None,
                mcp_endpoint_url=endpoint_url,
                mcp_tool_name="assistant.ask",
                mcp_ide_config_json=ide_cfg,
                sha256=digest,
            )
        return self._workspace_settings[workspace_id]

    def update_workspace_settings(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        workspace_instructions: str,
        default_checked_sources: tuple[str, ...],
        recommended_agents: tuple[str, ...],
        arbitration_policy: AssistantArbitrationPolicy,
        welcome_suggestions: tuple[str, ...] | None = None,
        mcp_expose_assistant: bool = True,
    ) -> WorkspaceLayerSettings:
        """Update Tab 2 (`📦 Réglages de l'Espace — Couche 4 WORKSPACE`), enforcing Funnel Rule."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError()
        if not self._can_manage_workspace_or_team(user):
            raise ScopeAccessDeniedError(
                detail_override=(
                    "Seul un Responsable d'Espace (TEAM_LEAD) ou Administrateur Plateforme "
                    "peut modifier les réglages d'Espace de Mon Assistant."
                )
            )

        frozen_entry = self._team_mcp_frozen.get(workspace_id)
        if frozen_entry is not None and frozen_entry[0] and mcp_expose_assistant:
            raise FunnelRuleViolationError()

        current = self.get_workspace_settings(workspace_id)
        suggestions = (
            welcome_suggestions if welcome_suggestions is not None else current.welcome_suggestions
        )
        ws_instr_str = workspace_instructions.strip()
        manifest: dict[str, object] = {
            "workspace_instructions": ws_instr_str,
            "default_checked_sources": list(default_checked_sources),
            "recommended_agents": list(recommended_agents),
            "arbitration_policy": arbitration_policy,
            "welcome_suggestions": list(suggestions),
            "mcp_expose_assistant": mcp_expose_assistant,
        }
        digest = _compute_sha256_hex(manifest)
        updated = WorkspaceLayerSettings(
            workspace_id=workspace_id,
            workspace_instructions=ws_instr_str,
            default_checked_sources=tuple(default_checked_sources),
            recommended_agents=tuple(recommended_agents),
            arbitration_policy=arbitration_policy,
            welcome_suggestions=tuple(suggestions),
            mcp_expose_assistant=mcp_expose_assistant,
            mcp_frozen_by_upper_layer=bool(frozen_entry and frozen_entry[0]),
            mcp_frozen_origin=frozen_entry[1] if frozen_entry else None,
            mcp_endpoint_url=current.mcp_endpoint_url,
            mcp_tool_name=current.mcp_tool_name,
            mcp_ide_config_json=current.mcp_ide_config_json,
            sha256=digest,
        )
        self._workspace_settings[workspace_id] = updated
        ov_key = f"assistant-workspace-{workspace_id}"
        self._overrides[ov_key] = AssistantCustomizationOverrideRecord(
            id=new_uuid7_str(),
            override_key=ov_key,
            org_unit_id=None,
            workspace_id=workspace_id,
            user_id=None,
            target_uri=ASSISTANT_WORKFLOW_URI,
            override_layer="WORKSPACE",
            override_manifest_jsonb=manifest,
            sha256=digest,
        )
        self._version_counter += 1
        return updated

    def assemble_five_layers_preview(
        self,
        *,
        workspace_id: str,
        user_id: str,
        pack_key: str = "orcia-pack-sdlc",
    ) -> tuple[AssembledLayerPreviewItem, ...]:
        """Build Tab 3 (`👁️ Assemblage complet`) showing the 5 active prompt layers (`AD-15`)."""
        user_prefs = self.get_user_preferences(workspace_id=workspace_id, user_id=user_id)
        ws_settings = self.get_workspace_settings(workspace_id)
        profile_spec = resolve_profile_adaptation(user_prefs.default_hat)
        team_instr = self._team_instructions.get(
            workspace_id,
            "Standards d'équipe : traçabilité systématique des décisions et revues croisées.",
        )

        l1_content = CONSTITUTIONAL_LAYER_1_TEXT
        l2_content = (
            f"[PACK_METIER_ACTIVE: {pack_key}]\n"
            "Conventions de domaine et axiomes N1–N3 chargés depuis le Pack Métier actif."
        )
        l3_content = (
            f"[EQUIPE_ET_CASQUETTE: {profile_spec.archetype}]\n"
            f"Registre: {profile_spec.register_label}\n"
            f"Instructions Équipe: {team_instr}"
        )
        l4_content = (
            f"[ESPACE: {workspace_id}]\n"
            f"Instructions Espace: {ws_settings.workspace_instructions}\n"
            f"Sources par défaut: {', '.join(ws_settings.default_checked_sources)}\n"
            f"Agents recommandés: {', '.join(ws_settings.recommended_agents)}"
        )
        l5_content = (
            f"[UTILISATEUR: {user_id}]\n"
            f"Ton: {user_prefs.response_tone} | Format: {user_prefs.favorite_format}\n"
            f"Instructions personnelles: {user_prefs.personal_instructions}"
        )

        return (
            AssembledLayerPreviewItem(
                layer_number=1,
                layer_code="1_CONSTITUTION",
                label="1. 🔒 Constitution (AssistantHarness Socle)",
                immutable=True,
                origin_badge="SOCLE",
                content=l1_content,
                sha256=_compute_sha256_hex(l1_content),
            ),
            AssembledLayerPreviewItem(
                layer_number=2,
                layer_code="2_PACK_METIER",
                label="2. Pack Métier & Ontologie",
                immutable=True,
                origin_badge="PACK",
                content=l2_content,
                sha256=_compute_sha256_hex(l2_content),
            ),
            AssembledLayerPreviewItem(
                layer_number=3,
                layer_code="3_EQUIPE",
                label="3. Équipe & Casquette",
                immutable=False,
                origin_badge="EQUIPE",
                content=l3_content,
                sha256=_compute_sha256_hex(l3_content),
            ),
            AssembledLayerPreviewItem(
                layer_number=4,
                layer_code="4_ESPACE",
                label="4. Espace & Glossaire",
                immutable=False,
                origin_badge="ESPACE",
                content=l4_content,
                sha256=_compute_sha256_hex(l4_content),
            ),
            AssembledLayerPreviewItem(
                layer_number=5,
                layer_code="5_UTILISATEUR",
                label="5. Utilisateur (Préférences & Continuité Dossier)",
                immutable=False,
                origin_badge="UTILISATEUR",
                content=l5_content,
                sha256=_compute_sha256_hex(l5_content),
            ),
        )

    def get_studio_graph(
        self,
        *,
        workspace_id: str,
        team_id: str = "team-default",
    ) -> AssistantStudioGraphState:
        """Return active Mode B Studio graph (`WORKSPACE` -> `TEAM` -> `DEFAULT`)."""
        ws_key = ("WORKSPACE", workspace_id)
        if ws_key in self._studio_graphs:
            return self._studio_graphs[ws_key]
        team_key = ("TEAM", team_id)
        if team_key in self._studio_graphs:
            return self._studio_graphs[team_key]

        nodes = build_default_studio_nodes()
        pre_prompt = (
            "Exécuter le graphe assistant-agent à 5 nœuds entre les bornes 🔒 AssistantHarness."
        )
        return AssistantStudioGraphState(
            workflow_uri=ASSISTANT_WORKFLOW_URI,
            scope_level="DEFAULT",
            scope_id=workspace_id,
            ai_pre_prompt=pre_prompt,
            nodes=nodes,
            override_key=None,
            sha256=_compute_sha256_hex(
                {"pre_prompt": pre_prompt, "nodes": [n.node_id for n in nodes]}
            ),
        )

    def save_studio_graph_override(
        self,
        user: UserIdentity,
        *,
        scope_level: Literal["TEAM", "WORKSPACE"],
        scope_id: str,
        ai_pre_prompt: str,
        nodes: tuple[AssistantStudioNodeSpec, ...],
    ) -> AssistantStudioGraphState:
        """Validate `🔒 AssistantHarness` boundaries and persist Mode B graph override."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError()
        if not self._can_manage_workspace_or_team(user):
            raise ScopeAccessDeniedError(
                detail_override=(
                    "Seul un TEAM_LEAD ou PLATFORM_ADMIN peut enregistrer une surcharge "
                    "Mode B dans le Studio."
                )
            )

        self._validate_harness_boundaries(nodes)

        manifest: dict[str, object] = {
            "workflow_uri": ASSISTANT_WORKFLOW_URI,
            "scope_level": scope_level,
            "scope_id": scope_id,
            "ai_pre_prompt": ai_pre_prompt.strip(),
            "nodes": [
                {
                    "node_id": n.node_id,
                    "title": n.title,
                    "node_order": n.node_order,
                    "is_harness_boundary": n.is_harness_boundary,
                    "locked_by": n.locked_by,
                    "enabled": n.enabled,
                    "sub_layers_count": n.sub_layers_count,
                    "enabled_sub_layers": list(n.enabled_sub_layers),
                    "sub_agent_uri": n.sub_agent_uri,
                }
                for n in nodes
            ],
        }
        digest = _compute_sha256_hex(manifest)
        ov_key = f"assistant-studio-{scope_level.lower()}-{scope_id}"
        state = AssistantStudioGraphState(
            workflow_uri=ASSISTANT_WORKFLOW_URI,
            scope_level=scope_level,
            scope_id=scope_id,
            ai_pre_prompt=ai_pre_prompt.strip(),
            nodes=nodes,
            override_key=ov_key,
            sha256=digest,
        )
        self._studio_graphs[(scope_level, scope_id)] = state
        self._overrides[ov_key] = AssistantCustomizationOverrideRecord(
            id=new_uuid7_str(),
            override_key=ov_key,
            org_unit_id=scope_id if scope_level == "TEAM" else None,
            workspace_id=scope_id if scope_level == "WORKSPACE" else None,
            user_id=None,
            target_uri=ASSISTANT_WORKFLOW_URI,
            override_layer=scope_level,
            override_manifest_jsonb=manifest,
            sha256=digest,
        )
        self._version_counter += 1
        return state

    def reset_studio_graph_override(
        self,
        user: UserIdentity,
        *,
        scope_level: Literal["TEAM", "WORKSPACE"],
        scope_id: str,
    ) -> AssistantStudioGraphState:
        """1-click `↺ Réinitialiser à la configuration par défaut` (`Story 10.1`)."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError()
        if not self._can_manage_workspace_or_team(user):
            raise ScopeAccessDeniedError()

        self._studio_graphs.pop((scope_level, scope_id), None)
        ov_key = f"assistant-studio-{scope_level.lower()}-{scope_id}"
        self._overrides.pop(ov_key, None)
        self._version_counter += 1
        return self.get_studio_graph(workspace_id=scope_id)

    def get_governance_view(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        pack_key: str = "orcia-pack-sdlc",
    ) -> AssistantGovernanceView:
        """Assemble full Mode A & Mode B governance view for `user` and `workspace_id`."""
        can_edit = self._can_manage_workspace_or_team(user) and (user.platform_role != "OBSERVER")
        return AssistantGovernanceView(
            workspace_id=workspace_id,
            can_edit_workspace_layer=can_edit,
            can_open_studio_mode_b=can_edit,
            user_preferences=self.get_user_preferences(workspace_id=workspace_id, user_id=user.id),
            workspace_settings=self.get_workspace_settings(workspace_id),
            assembled_layers=self.assemble_five_layers_preview(
                workspace_id=workspace_id,
                user_id=user.id,
                pack_key=pack_key,
            ),
            studio_graph=self.get_studio_graph(workspace_id=workspace_id),
            override_records=tuple(self._overrides.values()),
        )

    @staticmethod
    def _validate_harness_boundaries(nodes: tuple[AssistantStudioNodeSpec, ...]) -> None:
        if len(nodes) < 3:
            raise ImmutableHarnessBoundaryError()

        first = nodes[0]
        last = nodes[-1]
        if (
            first.node_id != ENTRY_HARNESS_NODE_ID
            or not first.is_harness_boundary
            or not first.enabled
            or first.locked_by != "HARNESS"
        ):
            raise ImmutableHarnessBoundaryError(
                detail_override=(
                    "La borne d'entrée 🔒 AssistantHarness (ENTRY_BOUNDARY_HARNESS) doit "
                    "impérativement rester active en première position du graphe."
                )
            )
        if (
            last.node_id != EXIT_HARNESS_NODE_ID
            or not last.is_harness_boundary
            or not last.enabled
            or last.locked_by != "HARNESS"
        ):
            raise ImmutableHarnessBoundaryError(
                detail_override=(
                    "La borne de sortie 🔒 AssistantHarness (EXIT_BOUNDARY_HARNESS) doit "
                    "impérativement rester active en dernière position du graphe."
                )
            )

        node_ids = {n.node_id: n for n in nodes}
        for core_id in REQUIRED_CORE_NODE_IDS:
            core_node = node_ids.get(core_id)
            if core_node is None:
                raise ImmutableHarnessBoundaryError(
                    detail_override=f"Le nœud système obligatoire {core_id} a été supprimé."
                )
            if core_node.locked_by in ("HARNESS", "PLATFORM", "TEAM") and not core_node.enabled:
                raise ImmutableHarnessBoundaryError(
                    detail_override=(
                        f"Le nœud verrouillé {core_id} ({core_node.locked_by}) ne peut pas être "
                        "désactivé."
                    )
                )

    @staticmethod
    def _can_manage_workspace_or_team(user: UserIdentity) -> bool:
        allowed_roles = {"PLATFORM_ADMIN", "TEAM_LEAD", "BU_DIRECTOR"}
        if user.platform_role in allowed_roles:
            return True
        return user.human_profile_archetype in {"ARCHITECT", "TECH_LEAD", "EXECUTIVE", "SECOPS"}
