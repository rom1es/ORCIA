"""Story 10.1 — Unit & API tests for 4-Level Governance & Customization of `Mon Assistant`.

Validates:
- Mode A (3 tabs):
  1. `👤 Mes préférences (Couche 5 — USER)` update & observer 403 guard.
  2. `📦 Réglages de l'Espace (Couche 4 — WORKSPACE)` editable by `TEAM_LEAD` / `PLATFORM_ADMIN`,
     read-only (`403 ERR_SCOPE_ACCESS_DENIED`) for simple `CONTRIBUTOR`, plus Funnel Rule
     (`HTTP 403 ERR_FUNNEL_RULE_VIOLATION`) when attempting to re-enable `mcp_expose_assistant`
     frozen by `TEAM` / `PLATFORM`.
  3. `👁️ Assemblage complet` returning all 5 active prompt layers (`1..5`).
- Mode B (`☍ Personnaliser dans le Studio`):
  - Enforces immutable `🔒 AssistantHarness` entry/exit boundaries (`ENTRY_BOUNDARY_HARNESS`,
    `EXIT_BOUNDARY_HARNESS` -> `HTTP 422 ERR_IMMUTABLE_HARNESS_BOUNDARY` on tamper).
  - Saves scoped override (`WORKSPACE` / `TEAM`) and restores defaults in 1 click.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tests.unit.fakes.in_memory_assistant_governance import InMemoryAssistantGovernanceStore

from orcia_api.main import app
from orcia_core.orchestration.assistant_governance import AssistantFourLevelGovernanceService
from orcia_core.orchestration.errors import (
    FunnelRuleViolationError,
    ObserverModeReadOnlyError,
    ScopeAccessDeniedError,
)
from orcia_core.permissions.models import PlatformRole, UserIdentity


def _make_user(
    *,
    user_id: str = "u-helene-01",
    org_role: PlatformRole = "CONTRIBUTOR",
    archetype: str = "PM",
) -> UserIdentity:
    return UserIdentity(
        id=user_id,
        email=f"{user_id}@orcia.local",
        display_name=user_id,
        auth_mode="LOCAL",
        human_profile_archetype=archetype,
        platform_role=org_role,
        primary_org_unit_id="org-unit-alpha",
    )


def test_story_10_1_mode_a_three_tabs_and_funnel_rule_enforcement() -> None:
    """Verify Mode A Tab 1 (USER), Tab 2 (WORKSPACE + Funnel Rule), and Tab 3 (5 layers)."""
    svc = AssistantFourLevelGovernanceService(store=InMemoryAssistantGovernanceStore())
    contributor = _make_user(user_id="u-helene", org_role="CONTRIBUTOR", archetype="PM")
    team_lead = _make_user(user_id="u-marc", org_role="TEAM_LEAD", archetype="TECH_LEAD")
    observer = _make_user(
        user_id="u-obs",
        org_role="OBSERVER",
        archetype="PM",
    )

    # Observer is rejected with 403 ERR_OBSERVER_MODE_READ_ONLY
    with pytest.raises(ObserverModeReadOnlyError):
        svc.update_user_preferences(
            observer,
            workspace_id="ws-claims-alpha",
            response_tone="SYNTHETIC",
            favorite_format="BULLETS_SUMMARY",
            default_hat="PM",
            personal_instructions="Test",
        )

    # Contributor updates Tab 1 (USER layer 5)
    prefs = svc.update_user_preferences(
        contributor,
        workspace_id="ws-claims-alpha",
        response_tone="SYNTHETIC",
        favorite_format="BULLETS_SUMMARY",
        default_hat="PM",
        personal_instructions="Synthèse en 3 puces avec citations [S1].",
    )
    assert prefs.response_tone == "SYNTHETIC"
    assert len(prefs.sha256) == 64

    # Contributor cannot edit Tab 2 (WORKSPACE layer 4) -> ScopeAccessDeniedError
    with pytest.raises(ScopeAccessDeniedError):
        svc.update_workspace_settings(
            contributor,
            workspace_id="ws-claims-alpha",
            workspace_instructions="Modification non autorisée",
            default_checked_sources=("git://repo-main",),
            recommended_agents=("@spec-architect",),
            arbitration_policy="PAUSE_AND_ESCALATE",
        )

    # Team Lead updates Tab 2 (WORKSPACE layer 4) including MCP exposure
    ws_settings = svc.update_workspace_settings(
        team_lead,
        workspace_id="ws-claims-alpha",
        workspace_instructions="Toujours vérifier la chaîne ADN DIRECTIVE -> NORME -> MÉCANISME.",
        default_checked_sources=("git://repo-main", "confluence://kb"),
        recommended_agents=("@spec-architect",),
        arbitration_policy="PAUSE_AND_ESCALATE",
        mcp_expose_assistant=True,
    )
    assert ws_settings.mcp_expose_assistant is True
    assert "assistant.ask" in ws_settings.mcp_ide_config_json

    # Funnel Rule (Principe G): freeze MCP at TEAM level -> Workspace cannot re-enable!
    svc.freeze_mcp_at_upper_layer(workspace_id="ws-claims-alpha", frozen=True, origin="TEAM")
    with pytest.raises(FunnelRuleViolationError) as exc_info:
        svc.update_workspace_settings(
            team_lead,
            workspace_id="ws-claims-alpha",
            workspace_instructions="Tentative de réouverture MCP gelé",
            default_checked_sources=("git://repo-main",),
            recommended_agents=("@spec-architect",),
            arbitration_policy="PAUSE_AND_ESCALATE",
            mcp_expose_assistant=True,
        )
    assert exc_info.value.error_code == "ERR_FUNNEL_RULE_VIOLATION"

    # Tab 3: 5 assembled layers
    layers = svc.assemble_five_layers_preview(
        workspace_id="ws-claims-alpha",
        user_id="u-helene",
    )
    assert len(layers) == 5
    assert layers[0].layer_code == "1_CONSTITUTION"
    assert layers[0].immutable is True
    assert layers[4].layer_code == "5_UTILISATEUR"
    assert "Synthèse en 3 puces" in layers[4].content


def test_story_10_1_api_endpoints_mode_a_and_mode_b_removed() -> None:
    """Verify Mode A `/governance/*` and 404/405 on deleted Mode B (`R2`, `26.4b`)."""
    ws_id = "0192c4e0-0000-7000-8000-000000000201"
    with TestClient(app) as client:
        get_resp = client.get(
            "/api/v1/assistant/governance",
            params={"workspace_id": ws_id, "persona_key": "marc"},
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert len(data["assembled_layers"]) == 5
        assert "studio_graph" not in data
        assert "can_open_studio_mode_b" not in data

        # Update user preferences (Mode A Tab 1)
        u_resp = client.put(
            "/api/v1/assistant/governance/mode-a/user",
            params={"persona_key": "marc"},
            json={
                "workspace_id": ws_id,
                "response_tone": "DETAILED_CODE",
                "favorite_format": "STEP_BY_STEP",
                "default_hat": "ARCHITECT",
                "personal_instructions": "Toujours inclure les schémas et hashes SHA-256.",
            },
        )
        assert u_resp.status_code == 200
        assert u_resp.json()["response_tone"] == "DETAILED_CODE"

        # Mode B Studio routes are deleted under R2 / R4 (Story 26.4b)
        bad_resp = client.post(
            "/api/v1/assistant/governance/mode-b/save",
            params={"persona_key": "marc"},
            json={"scope_level": "WORKSPACE", "scope_id": ws_id, "ai_pre_prompt": "x", "nodes": []},
        )
        assert bad_resp.status_code in (404, 405)

        rst_resp = client.post(
            "/api/v1/assistant/governance/mode-b/reset",
            params={"persona_key": "marc"},
            json={"scope_level": "WORKSPACE", "scope_id": ws_id},
        )
        assert rst_resp.status_code in (404, 405)
