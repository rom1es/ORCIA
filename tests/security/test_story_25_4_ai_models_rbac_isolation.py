"""Story 25.4 Security RBAC Tests for AI Models Hub (`MAJOR-2` remediation proof).

Verifies:
- Authenticated `CONTRIBUTOR` can read `GET /api/v1/settings/ai-models/mappings` and
  `GET /api/v1/settings/ai-models/reindex-status` (`200 OK`).
- Authenticated `CONTRIBUTOR` is strictly rejected with `403 ERR_SCOPE_ACCESS_DENIED` on all
  mutations and privileged discovery/test routes (`POST /mappings`, `PATCH /mappings/{id}`,
  `DELETE /mappings/{id}` even with `?actor_role=PLATFORM_ADMIN` or `?actor_persona=karim`,
  `POST /reindex-embeddings`, `POST /mappings/{id}/test`, `POST /discover`, `GET /discover`).
- `PLATFORM_ADMIN` Bearer token succeeds cleanly (`201`/`200`).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tests.unit.fakes.in_memory_reindex import default_in_memory_reindex_manager

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_api.main import create_app
from orcia_core.permissions import UserIdentity

ROOT_OU_ID = "0192c4e0-0000-7000-8000-000000000001"


def _build_rbac_client(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TestClient, dict[str, str], dict[str, str]]:
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    default_in_memory_reindex_manager.clear()
    app = create_app()
    initialize_app_services(app)
    app.state.reindex_manager = default_in_memory_reindex_manager
    svc = app.state.auth_service

    admin = UserIdentity(
        id="0195f000-0000-7000-8000-000000002541",
        email="admin.254@orcia.ia",
        display_name="Admin 25.4",
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id=ROOT_OU_ID,
        roles=("PLATFORM_ADMIN",),
    )
    contributor = UserIdentity(
        id="0195f000-0000-7000-8000-000000002542",
        email="contrib.254@orcia.ia",
        display_name="Contributor 25.4",
        auth_mode="LOCAL",
        human_profile_archetype="DEVELOPER",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id=ROOT_OU_ID,
        roles=("CONTRIBUTOR",),
    )

    headers: dict[str, dict[str, str]] = {}
    for key, u in (("admin", admin), ("contributor", contributor)):
        svc.register_user(u)
        tokens = svc.jwt_manager.issue_token_pair(
            user_id=u.id,
            email=u.email,
            role=u.platform_role,
            org_unit_id=u.primary_org_unit_id,
            archetype=u.human_profile_archetype,
            auth_mode="LOCAL",
        )
        headers[key] = {"Authorization": f"Bearer {tokens.access_token}"}

    return TestClient(app, raise_server_exceptions=False), headers["admin"], headers["contributor"]


def test_contributor_can_read_mappings_and_reindex_status_but_403_on_all_ai_models_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, admin_headers, contrib_headers = _build_rbac_client(monkeypatch)

    # Seed one mapping as PLATFORM_ADMIN so PATCH/DELETE/TEST target a real ID
    create_admin = client.post(
        "/api/v1/settings/ai-models/mappings",
        headers=admin_headers,
        json={
            "scope_level": "GLOBAL",
            "display_name": "RBAC Target Model",
            "inference_tier": "medium",
            "effort": "balanced",
            "provider_slug": "openai",
            "model_family": "OpenAI",
            "model_name": "gpt-4o-mini",
            "endpoint_uri": "https://api.openai.com/v1",
            "auth_mode": "none_local",
            "protocol_mode": "openai_compatible",
            "usage": "chat",
        },
    )
    assert create_admin.status_code == 201, create_admin.text
    mapping_id = create_admin.json()["id"]

    # 1. Read endpoints remain 200 for authenticated CONTRIBUTOR
    r_list = client.get("/api/v1/settings/ai-models/mappings", headers=contrib_headers)
    assert r_list.status_code == 200, r_list.text
    assert len(r_list.json()["items"]) >= 1

    r_reindex_status = client.get(
        "/api/v1/settings/ai-models/reindex-status", headers=contrib_headers
    )
    assert r_reindex_status.status_code == 200, r_reindex_status.text

    # 2. All write / privileged AI Models endpoints strictly return 403 for CONTRIBUTOR
    forbidden_calls = [
        (
            "POST",
            "/api/v1/settings/ai-models/mappings",
            {
                "scope_level": "GLOBAL",
                "display_name": "Unauthorized Model",
                "inference_tier": "simple",
                "provider_slug": "openai",
                "model_family": "OpenAI",
                "model_name": "gpt-4o-nano",
                "endpoint_uri": "https://api.openai.com/v1",
                "auth_mode": "none_local",
            },
        ),
        (
            "PATCH",
            f"/api/v1/settings/ai-models/mappings/{mapping_id}",
            {"display_name": "Hijacked Name"},
        ),
        (
            "DELETE",
            f"/api/v1/settings/ai-models/mappings/{mapping_id}?mode=force&actor_role=PLATFORM_ADMIN&actor_persona=karim",
            None,
        ),
        (
            "POST",
            "/api/v1/settings/ai-models/reindex-embeddings",
            None,
        ),
        (
            "POST",
            f"/api/v1/settings/ai-models/mappings/{mapping_id}/test",
            None,
        ),
        (
            "POST",
            "/api/v1/settings/ai-models/discover",
            {
                "endpoint_uri": "https://api.openai.com/v1",
                "protocol_mode": "openai_compatible",
            },
        ),
        (
            "GET",
            "/api/v1/settings/ai-models/discover?base_url=https://api.openai.com/v1",
            None,
        ),
    ]

    for method, url, payload in forbidden_calls:
        res = client.request(method, url, headers=contrib_headers, json=payload)
        assert res.status_code == 403, (
            f"Expected 403 on {method} {url}, got {res.status_code}: {res.text}"
        )
        assert res.headers["content-type"].startswith("application/problem+json")
        assert res.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

    # 3. Verify mapping was NOT deleted by the CONTRIBUTOR attempt
    r_after = client.get("/api/v1/settings/ai-models/mappings", headers=admin_headers)
    assert any(item["id"] == mapping_id for item in r_after.json()["items"])

    # 4. PLATFORM_ADMIN can delete cleanly
    r_del_admin = client.delete(
        f"/api/v1/settings/ai-models/mappings/{mapping_id}?mode=force",
        headers=admin_headers,
    )
    assert r_del_admin.status_code == 200, r_del_admin.text
