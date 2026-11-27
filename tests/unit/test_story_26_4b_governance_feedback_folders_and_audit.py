"""Story 26.4b — TDD Unit & AST Guard Tests: Mode A PG18, Feedback, Folders & Audit Ledger."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.orchestration.assistant_citations_and_v5_guard import (
    AssistantCitationAndV5GuardService,
    RawSourceCandidate,
)
from orcia_core.orchestration.assistant_folders_and_sharing import (
    AssistantFoldersAndSharingService,
)
from orcia_core.orchestration.assistant_governance import AssistantFourLevelGovernanceService
from orcia_core.permissions.models import UserIdentity

REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_user(user_id: str = "u-264b-1", role: str = "TEAM_LEAD") -> UserIdentity:
    return UserIdentity(
        id=user_id,
        email=f"{user_id}@orcia.io",
        display_name=user_id,
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role=role,  # type: ignore[arg-type]
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
    )


def test_zero_ram_dicts_in_governance_folders_and_citations_and_mode_b_deleted() -> None:
    """Verify H-09 & R2/R4: zero RAM dicts in governance/folders/citations and Mode B removed."""
    gov_svc = AssistantFourLevelGovernanceService()
    for forbidden_attr in (
        "_user_prefs",
        "_workspace_settings",
        "_team_instructions",
        "_team_mcp_frozen",
        "_studio_graphs",
        "_overrides",
    ):
        assert not hasattr(gov_svc, forbidden_attr), (
            f"RAM dict {forbidden_attr} must not exist on AssistantFourLevelGovernanceService"
        )
    for forbidden_method in (
        "get_studio_graph",
        "save_studio_graph_override",
        "reset_studio_graph_override",
    ):
        assert not hasattr(gov_svc, forbidden_method), (
            f"Mode B method {forbidden_method} must be deleted (R2)"
        )

    folders_svc = AssistantFoldersAndSharingService()
    assert not hasattr(folders_svc, "_folder_meta"), (
        "_folder_meta RAM dict must be removed from AssistantFoldersAndSharingService"
    )

    cit_svc = AssistantCitationAndV5GuardService()
    assert not hasattr(cit_svc, "_phantom_audit_log"), (
        "_phantom_audit_log RAM list must be replaced by audit_ledger persistence"
    )
    assert not hasattr(cit_svc, "phantom_audit_log")
    # _saved_drafts & execute_artifact_card_action removed in Story 26.7 (R5)
    assert not hasattr(cit_svc, "execute_artifact_card_action")
    assert not hasattr(cit_svc, "_saved_drafts")

    gov_router_src = (
        REPO_ROOT / "apps/api/src/orcia_api/routers/assistant_workspace_governance.py"
    ).read_text(encoding="utf-8")
    assert "/governance/mode-b/save" not in gov_router_src
    assert "/governance/mode-b/reset" not in gov_router_src

    schemas_mod = importlib.import_module("orcia_api.schemas.assistant_governance_and_three_speed")
    for deleted_schema in (
        "SaveAssistantStudioGraphRequest",
        "ResetAssistantStudioGraphRequest",
        "AssistantStudioGraphStateSchemaItem",
        "AssistantStudioNodeSchemaItem",
    ):
        assert not hasattr(schemas_mod, deleted_schema), f"{deleted_schema} must be deleted"


def test_story_26_4b_source_files_respect_300_line_cap_and_no_inmemory_in_prod() -> None:
    """Verify <= 300 L cap on all Story 26.4b files and zero InMemory* classes in prod."""
    story_files = (
        "packages/orcia-core/src/orcia_core/orchestration/assistant_governance.py",
        "packages/orcia-core/src/orcia_core/orchestration/_assistant_governance_sync.py",
        "packages/orcia-core/src/orcia_core/orchestration/assistant_governance_models.py",
        "packages/orcia-core/src/orcia_core/orchestration/assistant_governance_studio.py",
        "packages/orcia-core/src/orcia_core/orchestration/assistant_citations_and_v5_guard.py",
        "packages/orcia-core/src/orcia_core/orchestration/_assistant_citations_verifier.py",
        "packages/orcia-core/src/orcia_core/orchestration/assistant_feedback.py",
        "packages/orcia-core/src/orcia_core/orchestration/assistant_folders_and_sharing.py",
        "packages/orcia-core/src/orcia_core/orchestration/_assistant_folders_async_ops.py",
        "packages/orcia-core/src/orcia_core/orchestration/_assistant_folders_sync.py",
        "packages/orcia-core/src/orcia_core/orchestration/_internal/sql_assistant_folders.py",
        "packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_assistant_folders_queries.py",
        "packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_assistant_folders_sql.py",
        "packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_assistant_folders_mutations.py",
        "packages/orcia-core/src/orcia_core/orchestration/_internal/sql_assistant_governance.py",
        "packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_assistant_governance_queries.py",
        "packages/orcia-core/src/orcia_core/orchestration/_internal/sql_assistant_feedback.py",
        "apps/api/src/orcia_api/routers/assistant_workspace_governance.py",
        "apps/api/src/orcia_api/routers/assistant_turns.py",
        "apps/api/src/orcia_api/routers/_assistant_turn_controls_routes.py",
        "apps/api/src/orcia_api/routers/_assistant_turn_finalizer.py",
        "apps/api/src/orcia_api/routers/assistant_llm_bridge.py",
        "apps/api/src/orcia_api/routers/assistant_llm_prompts.py",
        "apps/api/src/orcia_api/schemas/assistant_governance_and_three_speed.py",
        "apps/api/src/orcia_api/dependencies/portal_and_assistant.py",
    )
    for rel in story_files:
        path = REPO_ROOT / rel
        assert path.exists(), f"Expected Story 26.4b file missing: {rel}"
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        assert line_count <= 300, f"{rel} exceeds 300-line cap ({line_count} lines)"

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.startswith("InMemory"):
                raise AssertionError(f"InMemory* class {node.name} found in {rel}")


@pytest.mark.asyncio
async def test_phantom_citation_idempotent_audit_ledger_sink_and_v5_action_preserved() -> None:
    """Verify AssistantCitationAndV5GuardService emits idempotent phantom citation audit."""
    from tests.unit.fakes.in_memory_audit_ledger import InMemoryAuditLedgerSink

    sink = InMemoryAuditLedgerSink()
    svc = AssistantCitationAndV5GuardService(audit_ledger_sink=sink)
    user = _make_user(user_id="0192c4e0-0000-7000-8000-000000009001")
    table = svc.build_evidence_table(
        sources=(
            RawSourceCandidate(
                uri="orcia://kb/adr-025.md",
                title="ADR-025",
                authority_tier="REFERENCE",
                freshness="FRESH",
                snippet="Unified turn engine",
            ),
        )
    )
    res1 = await svc.verify_and_sanitize_citations_async(
        response_text="Valid [S1] and phantom [S99].",
        evidence_table=table,
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        user_id=user.id,
        user_email=user.email,
        user_display_name=user.display_name,
        turn_id="0192c4e0-0000-7000-8000-000000007777",
    )
    res2 = await svc.verify_and_sanitize_citations_async(
        response_text="Valid [S1] and phantom [S99].",
        evidence_table=table,
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        user_id=user.id,
        user_email=user.email,
        user_display_name=user.display_name,
        turn_id="0192c4e0-0000-7000-8000-000000007777",
    )
    assert res1.stripped_phantom_tags == ("S99",)
    assert res2.stripped_phantom_tags == ("S99",)
    assert len(sink.entries) == 1
    assert sink.entries[0].event_type == "ASSISTANT_PHANTOM_CITATION_PURGED"
    assert sink.entries[0].metadata["stripped_tags"] == ["S99"]

    # R5 removed execute_artifact_card_action and _saved_drafts in Story 26.7
    assert not hasattr(svc, "execute_artifact_card_action")
    assert not hasattr(svc, "_saved_drafts")


def test_mode_b_routes_removed_and_mode_a_governance_returns_mode_a_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Mode B endpoints return 404/405 and GET /governance returns Mode A only."""
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_ENV", "local")
    app = create_app()
    ws_id = "0192c4e0-0000-7000-8000-000000000201"
    with TestClient(app, raise_server_exceptions=False) as client:
        r_get = client.get(
            "/api/v1/assistant/governance",
            params={"workspace_id": ws_id, "persona_key": "marc"},
        )
        assert r_get.status_code == 200
        body = r_get.json()
        assert "studio_graph" not in body
        assert "can_open_studio_mode_b" not in body
        assert len(body["assembled_layers"]) == 5

        r_save = client.post(
            "/api/v1/assistant/governance/mode-b/save",
            params={"persona_key": "marc"},
            json={"scope_level": "WORKSPACE", "scope_id": ws_id, "ai_pre_prompt": "x", "nodes": []},
        )
        assert r_save.status_code in (404, 405)

        r_reset = client.post(
            "/api/v1/assistant/governance/mode-b/reset",
            params={"persona_key": "marc"},
            json={"scope_level": "WORKSPACE", "scope_id": ws_id},
        )
        assert r_reset.status_code in (404, 405)

        r_fb = client.post(
            "/api/v1/assistant/turns/0192c4e0-0000-7000-8000-000000008888/feedback",
            params={"persona_key": "marc"},
            json={"workspace_id": ws_id, "rating": "up", "reason_code": "ACCURATE"},
        )
        assert r_fb.status_code == 200
        assert r_fb.json()["rating"] == "up"


def test_folder_row_mapper_decodes_attachments_and_evidence_tags() -> None:
    """Verify row_to_folder hydrates working_attachments_uris and evidence_tags from SQL rows."""
    from orcia_core.orchestration._internal._sql_assistant_folders_queries import row_to_folder

    row = {
        "folder_id": "0192c4e0-0000-7000-8000-000000001111",
        "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
        "owner_user_id": "0192c4e0-0000-7000-8000-000000000001",
        "title": "Folder Row",
        "pinned_notes_markdown": "Note",
        "visibility_mode": "PRIVATE",
        "consolidated_summary": "Summary",
        "has_restricted_sources": False,
        "working_attachments_uris": '["orcia://drafts/a@draft"]',
        "evidence_tags": ["S1", "O2"],
    }
    rec = row_to_folder(row, ())  # type: ignore[arg-type]
    assert rec.working_attachments_uris == ("orcia://drafts/a@draft",)
    assert rec.evidence_tags == ("S1", "O2")


@pytest.mark.asyncio
async def test_persona_private_folder_isolation_in_seeded_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Persona PRIVATE folders remain visible to owner and hidden from peers."""
    karim = _make_user("0192c4e0-0000-7000-8000-000000000601", "PLATFORM_ADMIN")

    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_ENV", "local")
    app = create_app()
    ws_id = "0192c4e0-0000-7000-8000-000000000201"
    with TestClient(app) as client:
        r_create = client.post(
            "/api/v1/assistant/folders",
            params={"persona_key": "karim"},
            json={"workspace_id": ws_id, "title": "Karim Secret Folder"},
        )
        assert r_create.status_code == 200
        fid = r_create.json()["folder_id"]
        assert r_create.json()["owner_user_id"] == karim.id

        r_owner = client.get(
            f"/api/v1/assistant/workspaces/{ws_id}/overview",
            params={"persona_key": "karim"},
        )
        assert r_owner.status_code == 200
        assert any(f["folder_id"] == fid for f in r_owner.json()["folders"])

        r_peer = client.get(
            f"/api/v1/assistant/workspaces/{ws_id}/overview",
            params={"persona_key": "marc"},
        )
        assert r_peer.status_code == 200
        assert not any(f["folder_id"] == fid for f in r_peer.json()["folders"])
