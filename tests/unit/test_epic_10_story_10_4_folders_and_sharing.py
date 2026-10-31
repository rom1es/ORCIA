"""Story 10.4 — Unit & API tests for `📁 Dossiers`, Layer 5 Memory, Sharing & Redis Turn Lock.

Validates:
- 3-tab `Mon Assistant` workspace overview (`ACTIVE_DISCUSSION`, `FOLDERS`, `HISTORY_SEARCH`).
- Layer 5 (`AD-15`) automatic continuity injecting `📌 Notes du dossier`, working attachments
  (`@draft`), and consolidated summaries of previous threads in the folder.
- 1-click Process Bridge (`☍ Lancer un Processus à partir de ce dossier →`) pre-filling
  `orcia://pack-sdlc/workflows/ticket-to-tech-spec`.
- 3 visibility modes (`PRIVATE`, `SHARED_SELECTED` with `READ_ONLY` / `CO_CONTRIBUTOR`,
  `WORKSPACE_OPEN`) strictly confined to the current Workspace (`AD-21`) + preventive warning
  when restricted sources are cited.
- Redis turn lock (`SET lock:thread:<thread_id> <user_id> NX EX 60`, `ERR_THREAD_TURN_LOCK_HELD`),
  real-time SSE banner `✍️ {Prénom} interroge l'assistant...`, and personal `Passthrough`
  identity per message author (`AD-6`).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import app
from orcia_core.orchestration.assistant_folders_and_sharing import (
    PILOT_WORKFLOW_TICKET_TO_TECH_SPEC_URI,
    AssistantFoldersAndSharingService,
    FolderShareGrant,
)
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ScopeAccessDeniedError,
    ThreadTurnLockHeldError,
)
from orcia_core.permissions.models import UserIdentity


def _make_user(
    user_id: str,
    display_name: str,
    email: str,
    role: str = "CONTRIBUTOR",
) -> UserIdentity:
    return UserIdentity(
        id=user_id,
        email=email,
        display_name=display_name,
        auth_mode="OIDC",
        human_profile_archetype="TECH_BUILDER",
        platform_role=role,  # type: ignore[arg-type]
        primary_org_unit_id="org-claims",
    )


def test_story_10_4_layer5_continuity_and_one_click_process_bridge() -> None:
    """Folder notes, working attachments, and past thread summaries feed Layer 5 & Process."""
    svc = AssistantFoldersAndSharingService()
    helene = _make_user("u-helene-01", "Hélène Martin", "helene@orcia.io", "TEAM_LEAD")

    folder = svc.create_or_update_folder(
        workspace_id="ws-checkout-01",
        user=helene,
        title="Refonte Tunnel Checkout",
        pinned_notes_markdown="Décision #1 : conserver 3DS2 frictionless sous 250 €.",
        working_attachments_uris=["orcia://workspace/ws-checkout-01/drafts/spec-psp@draft"],
        consolidated_summary="Discussion #1 : cadrage PSP Stripe vs Adyen.",
        evidence_tags=["S1", "G1"],
        has_restricted_sources=True,
    )

    svc.create_thread_in_folder(
        workspace_id="ws-checkout-01",
        user=helene,
        title="Analyse latence 3DS2",
        folder_id=folder.folder_id,
        initial_summary="Latence P95 mesurée à 410 ms sur le flux mobile.",
    )

    layer5 = svc.build_layer5_folder_memory_injection(
        workspace_id="ws-checkout-01",
        folder_id=folder.folder_id,
    )
    assert layer5.layer_number == 5
    assert layer5.layer_code == "5_UTILISATEUR"
    assert "3DS2 frictionless sous 250 €" in layer5.assembled_layer5_prompt_block
    assert "spec-psp@draft" in layer5.assembled_layer5_prompt_block
    assert "Latence P95 mesurée à 410 ms" in layer5.assembled_layer5_prompt_block

    launch = svc.prepare_workflow_launch_from_folder(
        workspace_id="ws-checkout-01",
        folder_id=folder.folder_id,
        user=helene,
    )
    assert launch.workflow_uri == PILOT_WORKFLOW_TICKET_TO_TECH_SPEC_URI
    assert launch.passthrough_identity == "passthrough:oidc:u-helene-01:helene@orcia.io"
    assert launch.prefilled_contract_inputs["source_folder_title"] == "Refonte Tunnel Checkout"
    assert "S1" in launch.prefilled_contract_inputs["cited_evidence_tags"]  # type: ignore[operator]


def test_story_10_4_sharing_workspace_confinement_turn_lock_and_passthrough_isolation() -> None:
    """Sharing is confined to Workspace; turn lock blocks peer; Passthrough is per author."""
    svc = AssistantFoldersAndSharingService()
    helene = _make_user("u-helene-01", "Hélène Martin", "helene@orcia.io", "TEAM_LEAD")
    yanis = _make_user("u-yanis-02", "Yanis Benali", "yanis@orcia.io", "CONTRIBUTOR")
    marc_ro = _make_user("u-marc-03", "Marc Leroy", "marc@orcia.io", "CONTRIBUTOR")
    svc.register_workspace_members("ws-checkout-01", [helene.id, yanis.id, marc_ro.id])

    folder = svc.create_or_update_folder(
        workspace_id="ws-checkout-01",
        user=helene,
        title="Refonte Tunnel Checkout",
        pinned_notes_markdown="Notes PSP",
        has_restricted_sources=True,
    )
    thread = svc.create_thread_in_folder(
        workspace_id="ws-checkout-01",
        user=helene,
        title="Fil collaboratif PSP",
        folder_id=folder.folder_id,
    )

    # Reject sharing outside the current Workspace (AD-21)
    with pytest.raises(ScopeAccessDeniedError):
        svc.configure_folder_sharing(
            workspace_id="ws-checkout-01",
            folder_id=folder.folder_id,
            owner_user=helene,
            visibility_mode="SHARED_SELECTED",
            shares=[
                FolderShareGrant(
                    grantee_user_id="u-external-other-ws",
                    access_role="CO_CONTRIBUTOR",
                )
            ],
            outside_workspace_user_ids=["u-external-other-ws"],
        )

    # Valid sharing inside Workspace returns preventive warning when restricted sources exist
    share_res = svc.configure_folder_sharing(
        workspace_id="ws-checkout-01",
        folder_id=folder.folder_id,
        owner_user=helene,
        visibility_mode="SHARED_SELECTED",
        shares=[
            FolderShareGrant(grantee_user_id=yanis.id, access_role="CO_CONTRIBUTOR"),
            FolderShareGrant(grantee_user_id=marc_ro.id, access_role="READ_ONLY"),
        ],
    )
    assert share_res.restricted_sources_warning is not None
    assert "🔒 Source restreinte" in share_res.restricted_sources_warning

    # READ_ONLY colleague cannot send a turn
    with pytest.raises(ObserverModeReadOnlyError):
        svc.send_collaborative_thread_turn(
            workspace_id="ws-checkout-01",
            thread_id=thread.thread_id,
            sender_user=marc_ro,
            message_text="Tentative d'écriture en lecture seule",
        )

    # Co-contributor Yanis sends a turn: acquires Redis lock & uses Yanis's personal Passthrough
    turn_yanis = svc.send_collaborative_thread_turn(
        workspace_id="ws-checkout-01",
        thread_id=thread.thread_id,
        sender_user=yanis,
        message_text="Vérifie les webhooks Stripe @jira-triage",
        release_lock_after_turn=False,
    )
    assert turn_yanis.redis_lock_key == f"lock:thread:{thread.thread_id}"
    assert turn_yanis.lock_ttl_seconds == 60
    assert turn_yanis.sse_presence_banner == "✍️ Yanis interroge l'assistant..."
    assert turn_yanis.author_passthrough_identity == "passthrough:oidc:u-yanis-02:yanis@orcia.io"
    assert turn_yanis.folder_creator_user_id == helene.id
    assert turn_yanis.author_user_id != turn_yanis.folder_creator_user_id

    # While Yanis holds the active turn lock, Hélène receives 409 ERR_THREAD_TURN_LOCK_HELD
    with pytest.raises(ThreadTurnLockHeldError):
        svc.send_collaborative_thread_turn(
            workspace_id="ws-checkout-01",
            thread_id=thread.thread_id,
            sender_user=helene,
            message_text="Message concurrent pendant le tour de Yanis",
        )


def test_story_10_4_fastapi_endpoints_and_rfc9457_errors() -> None:
    """FastAPI endpoints for Story 10.4 return 200 OK and RFC 9457 409 on turn lock contention."""
    with TestClient(app) as client:
        # 1. Create folder as karim
        folder_resp = client.post(
            "/api/v1/assistant/folders",
            params={"persona_key": "karim"},
            json={
                "workspace_id": "ws-claims-alpha",
                "title": "Refonte Tunnel Checkout",
                "pinned_notes_markdown": "Décision #1 : 3DS2 obligatoire.",
                "working_attachments_uris": ["orcia://drafts/spec-01@draft"],
                "consolidated_summary": "Résumé initial",
                "evidence_tags": ["S1"],
                "has_restricted_sources": True,
            },
        )
        assert folder_resp.status_code == 200
        folder_id = folder_resp.json()["folder_id"]
        assert "LAYER_5_FOLDER_CONTINUITY" in folder_resp.json()["assembled_layer5_prompt_block"]

        # 2. Launch process from folder in 1 click
        launch_resp = client.post(
            f"/api/v1/assistant/folders/{folder_id}/launch-process",
            params={"persona_key": "karim"},
            json={"workspace_id": "ws-claims-alpha"},
        )
        assert launch_resp.status_code == 200
        assert (
            launch_resp.json()["workflow_uri"] == "orcia://pack-sdlc/workflows/ticket-to-tech-spec"
        )

        # 3. Create thread & share folder with WORKSPACE_OPEN
        thread_resp = client.post(
            "/api/v1/assistant/threads",
            params={"persona_key": "karim"},
            json={
                "workspace_id": "ws-claims-alpha",
                "folder_id": folder_id,
                "title": "Discussion partagée Checkout",
            },
        )
        assert thread_resp.status_code == 200
        thread_id = thread_resp.json()["thread_id"]

        share_resp = client.post(
            f"/api/v1/assistant/folders/{folder_id}/share",
            params={"persona_key": "karim"},
            json={
                "workspace_id": "ws-claims-alpha",
                "visibility_mode": "WORKSPACE_OPEN",
            },
        )
        assert share_resp.status_code == 200
        assert share_resp.json()["restricted_sources_warning"] is not None

        # 4. Claire sends a turn holding the lock (`release_lock_after_turn=False`)
        turn1 = client.post(
            f"/api/v1/assistant/threads/{thread_id}/turns",
            params={"persona_key": "claire"},
            json={
                "workspace_id": "ws-claims-alpha",
                "message_text": "Synthèse des risques PSP",
                "release_lock_after_turn": False,
            },
        )
        assert turn1.status_code == 200
        assert "claire" in turn1.json()["author_passthrough_identity"]

        # 5. Karim sends a turn while Claire's lock is active -> 409 ERR_THREAD_TURN_LOCK_HELD
        turn2_conflict = client.post(
            f"/api/v1/assistant/threads/{thread_id}/turns",
            params={"persona_key": "karim"},
            json={
                "workspace_id": "ws-claims-alpha",
                "message_text": "Conflit de tour",
            },
        )
        assert turn2_conflict.status_code == 409
        assert turn2_conflict.json()["error_code"] == "ERR_THREAD_TURN_LOCK_HELD"

        # 6. Overview 3 tabs (`💬`, `📁`, `🕘`)
        overview_resp = client.get(
            "/api/v1/assistant/workspaces/ws-claims-alpha/overview",
            params={"persona_key": "karim"},
        )
        assert overview_resp.status_code == 200
        assert overview_resp.json()["folders_count"] >= 1
