"""Story 26.1 — Additional Red-Team & Architecture Review Hardening Tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_api.routers.assistant_llm_prompts import build_assistant_system_instructions
from orcia_core.orchestration.assistant_citations_and_v5_guard import (
    AssistantCitationAndV5GuardService,
    RawSourceCandidate,
)
from orcia_core.permissions.models import CatalogAclEntry, UserIdentity


def _make_local_app(monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ORCIA_ENABLE_PG_SESSION_MAKER", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV", "local")
    return create_app()


def test_chat_preserves_authorized_dynamic_slices_and_blocks_unauthorized_uris(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[P0-1] /chat preserves authorized dynamic slices and filters unauthorized ones."""
    app = _make_local_app(monkeypatch)
    with TestClient(app, raise_server_exceptions=False) as client:  # type: ignore[arg-type]
        ws_id = "0192c4e0-0000-7000-8000-000000000201"
        svc = app.state.assistant_service  # type: ignore[attr-defined]
        auth_svc = app.state.auth_service  # type: ignore[attr-defined]
        auth_svc.evaluator.upsert_catalog_acl(
            CatalogAclEntry(
                id="acl-open-26-1",
                resource_id="res-open-26-1",
                resource_uri="git://gitlab.entreprise.io/payments/open-guide.md",
                title="Open Payment Guide",
                visibility_scope="SHARED_WORKSPACE",
                owner_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
                owner_workspace_id=ws_id,
                can_discover=True,
                can_execute=True,
                can_read_source=True,
                can_edit=False,
                can_admin=False,
            )
        )
        svc._context_source.register_context_slice(
            slice_id="slice-open-26-1",
            source_uri="git://gitlab.entreprise.io/payments/open-guide.md",
            source_kind="CATALOG",
            title="Open Payment Guide",
            structured_payload={"summary": "Authorized architectural guidance."},
            text_excerpt="Authorized architectural guidance.",
        )
        svc._context_source.register_context_slice(
            slice_id="slice-secret-26-1",
            source_uri="git://gitlab.entreprise.io/archi/security-audit-agent@v2.1.0",
            source_kind="CATALOG",
            title="Blackbox Audit",
            structured_payload={"summary": "Secret prompt body that must be dropped."},
            text_excerpt="Secret prompt body that must be dropped.",
        )
        from orcia_api.dependencies._assistant_guards import prepare_server_source_uri_authorizer
        from orcia_core.permissions.models import UserIdentity

        nadia = UserIdentity(
            id="0192c4e0-0000-7000-8000-000000000002",
            email="nadia@orcia.io",
            display_name="Nadia",
            auth_mode="LOCAL",
            human_profile_archetype="ARCHITECT",
            platform_role="CONTRIBUTOR",
            primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
        )
        turn = svc.run_conversation_turn(
            workspace_id=ws_id,
            user_prompt="Résume le guide paiement.",
            human_profile_archetype="ARCHITECT",
            source_uri_authorizer=lambda uris: frozenset(
                u for u in uris if u == "git://gitlab.entreprise.io/payments/open-guide.md"
            ),
        )
        assert (
            "git://gitlab.entreprise.io/payments/open-guide.md" in turn.assembled_prompt.cited_uris
        )
        assert (
            "git://gitlab.entreprise.io/archi/security-audit-agent@v2.1.0"
            not in turn.assembled_prompt.cited_uris
        )
        _ = prepare_server_source_uri_authorizer, nadia

        resp = client.post(
            "/api/v1/assistant/turns",
            params={"persona_key": "nadia"},
            json={"workspace_id": ws_id, "user_prompt": "Résume le guide paiement."},
        )
        assert resp.status_code == 202
        stream_resp = client.get(resp.json()["stream_url"], params={"persona_key": "nadia"})
        assert stream_resp.status_code == 200
        assert (
            "git://gitlab.entreprise.io/archi/security-audit-agent@v2.1.0" not in stream_resp.text
        )


def test_cross_org_team_lead_and_archetype_contributor_rejected_on_governance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[P1-1] Non-lead archetype contributors and cross-org TEAM_LEAD get 403 on governance."""
    app = _make_local_app(monkeypatch)
    with TestClient(app, raise_server_exceptions=False) as client:  # type: ignore[arg-type]
        ws_id = "0192c4e0-0000-7000-8000-000000000201"
        auth_svc = app.state.auth_service  # type: ignore[attr-defined]
        cross_lead = UserIdentity(
            id="u-cross-lead",
            email="cross.lead@orcia.io",
            display_name="Cross Lead",
            auth_mode="LOCAL",
            human_profile_archetype="ARCHITECT",
            platform_role="TEAM_LEAD",
            primary_org_unit_id="0192c4e0-0000-7000-8000-000000000105",
            roles=("TEAM_LEAD",),
        )
        arch_contrib = UserIdentity(
            id="u-arch-contrib",
            email="arch.contrib@orcia.io",
            display_name="Arch Contrib",
            auth_mode="LOCAL",
            human_profile_archetype="SECOPS",
            platform_role="CONTRIBUTOR",
            primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
            roles=("CONTRIBUTOR",),
        )
        auth_svc.register_user(cross_lead)
        auth_svc.register_user(arch_contrib)
        auth_svc._persona_map["cross_lead"] = cross_lead.id
        auth_svc._persona_map["arch_contrib"] = arch_contrib.id

        for persona in ("cross_lead", "arch_contrib"):
            r_ws = client.put(
                "/api/v1/assistant/governance/mode-a/workspace",
                params={"persona_key": persona},
                json={
                    "workspace_id": ws_id,
                    "workspace_instructions": "Escalation attempt",
                    "default_checked_sources": [],
                    "recommended_agents": [],
                    "arbitration_policy": "PAUSE_AND_ESCALATE",
                    "mcp_expose_assistant": False,
                },
            )
            assert r_ws.status_code == 403, f"{persona}: {r_ws.status_code} {r_ws.text}"

        r_glob = client.put(
            "/api/v1/assistant/governance/mode-a/workspace",
            params={"persona_key": "marc"},
            json={
                "workspace_id": "scope-global",
                "workspace_instructions": "Global escalation",
                "default_checked_sources": [],
                "recommended_agents": [],
                "arbitration_policy": "PAUSE_AND_ESCALATE",
                "mcp_expose_assistant": False,
            },
        )
        assert r_glob.status_code == 403


def test_platform_admin_no_read_source_bypass_and_private_folder_acl_and_en_locale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[P1-2], [P1-3], [P3-1] Admin follows ACL, private folder denied, SSRF & EN locale."""
    admin = UserIdentity(
        id="u-admin",
        email="admin@orcia.io",
        display_name="Admin",
        auth_mode="LOCAL",
        human_profile_archetype="SECOPS",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000101",
    )
    cit_svc = AssistantCitationAndV5GuardService()
    table = cit_svc.build_evidence_table(
        sources=(
            RawSourceCandidate(
                uri="git://restricted/secret.md",
                title="Restricted",
                authority_tier="REFERENCE",
                freshness="FRESH",
                snippet="Sensitive snippet",
            ),
        )
    )
    filtered = cit_svc.filter_citation_map_for_reader(
        admin, evidence_table=table, reader_allowed_source_uris=frozenset()
    )
    assert filtered.sources[0].restricted_access is True
    assert filtered.sources[0].snippet is None

    prompt_en = build_assistant_system_instructions(
        hat="ARCHITECT",
        speed_mode="SPEED_1_FAST",
        response_tone="BALANCED",
        response_format="STRUCTURED_SECTIONS",
        personal_instructions="Be concise",
        locale="en",
    )
    assert "Ton attendu" not in prompt_en
    assert "Format attendu" not in prompt_en
    assert "Instructions personnelles" not in prompt_en

    app = _make_local_app(monkeypatch)
    with TestClient(app, raise_server_exceptions=False) as client:  # type: ignore[arg-type]
        ws_id = "0192c4e0-0000-7000-8000-000000000201"
        f_resp = client.post(
            "/api/v1/assistant/folders",
            params={"persona_key": "marc"},
            json={
                "workspace_id": ws_id,
                "title": "Marc Private Folder",
                "pinned_notes_markdown": "Confidential peer note",
            },
        )
        assert f_resp.status_code == 200
        folder_id = f_resp.json()["folder_id"]

        share_resp = client.post(
            f"/api/v1/assistant/folders/{folder_id}/share",
            params={"persona_key": "marc"},
            json={"workspace_id": ws_id, "visibility_mode": "PRIVATE", "shares": []},
        )
        assert share_resp.status_code == 200

        turn_res = client.post(
            "/api/v1/assistant/turns",
            params={"persona_key": "nadia"},
            json={
                "workspace_id": ws_id,
                "user_prompt": "Read peer notes",
                "folder_id": folder_id,
            },
        )
        assert turn_res.status_code == 403

        ssrf_prog = client.post(
            "/api/v1/bootstrap/welcome-setup/progressive-llm",
            json={
                "endpoint_key": "evil-meta",
                "provider_slug": "openai",
                "model_family": "OpenAI",
                "model_name": "gpt-4o",
                "endpoint_uri": "http://169.254.169.254/latest/meta-data/",
            },
        )
        assert ssrf_prog.status_code in (400, 422)

        ssrf_org = client.post(
            "/api/v1/bootstrap/init-organization",
            params={"persona_key": "karim"},
            json={
                "organization_name": "Evil SSRF Org",
                "oidc_enabled": True,
                "local_argon2id_enabled": True,
                "llm_endpoints": [
                    {
                        "endpoint_key": "evil-meta",
                        "provider_slug": "openai",
                        "model_family": "openai",
                        "model_name": "gpt-4o",
                        "endpoint_uri": "http://169.254.169.254/latest/meta-data/",
                    }
                ],
            },
        )
        assert ssrf_org.status_code == 422
