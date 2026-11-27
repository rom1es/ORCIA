"""Story 31.7 Red-Team Security Suite for Declarative APM Packs (`<= 300 L`)."""

from __future__ import annotations

import base64
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from tests.security._packs_red_team_fixtures import (
    ORG_B,
    WS_A,
    WS_B,
    apm_yml,
    setup_packs_red_team_app,
    zip_of,
)
from uuid_utils import uuid7


@pytest.mark.asyncio
async def test_archive_red_team_zip_slip_symlink_and_hooks_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject zip-slip traversal, symlinks, scripts (.sh/.py), and YAML hooks with 422."""
    app, tokens = setup_packs_red_team_app(monkeypatch, draft_id=str(uuid7()), leak_desc="Clean")
    hdr = {"Authorization": f"Bearer {tokens['karim']}"}
    cases: list[tuple[str, bytes, str | None]] = [
        ("zip-slip-rel", zip_of({"apm.yml": apm_yml(), "../evil.md": b"x"}), None),
        ("zip-slip-abs", zip_of({"apm.yml": apm_yml(), "/etc/passwd": b"x"}), None),
        ("symlink", zip_of({"apm.yml": apm_yml()}, symlink_name="link.md"), None),
        (
            "shell",
            zip_of({"apm.yml": apm_yml(), "scripts/r.sh": b"#!/bin/sh\n"}),
            "ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN",
        ),
        (
            "python",
            zip_of({"apm.yml": apm_yml(), "agents/h.py": b"print(1)\n"}),
            "ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN",
        ),
        (
            "hooks-yml",
            zip_of({"apm.yml": apm_yml(extra="hooks:\n  post_install: id\n")}),
            "ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN",
        ),
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for label, payload, code in cases:
            b64 = base64.b64encode(payload).decode("ascii")
            body = {"zip_base64": b64, "scope_type": "WORKSPACE", "scope_id": WS_A}
            resp = await client.post("/api/v1/packs/import", headers=hdr, json=body)
            assert resp.status_code == 422, f"{label}: {resp.text}"
            assert resp.headers["content-type"].startswith("application/problem+json")
            if code is not None:
                assert resp.json()["error_code"] == code, f"{label}: {resp.text}"


@pytest.mark.asyncio
async def test_export_red_team_blocks_pii_and_internal_infra_leaks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject PII emails and internal tenant hosts in exported pack metadata (422)."""
    draft_id = str(uuid7())
    leak = "Contact admin@tenant.internal and sync https://git.corp.internal/org/repo"
    app, tokens = setup_packs_red_team_app(
        monkeypatch, draft_id=draft_id, leak_desc=leak, draft_scope_id=WS_A
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/packs/composer/{draft_id}/export",
            headers={"Authorization": f"Bearer {tokens['karim']}"},
            json={"auto_include_dependencies": False},
        )
        assert resp.status_code == 422, resp.text
        assert resp.json()["error_code"] == "ERR_PACK_PII_OR_INFRA_LEAK"


@pytest.mark.asyncio
async def test_cross_workspace_isolation_and_observer_mode_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enforce 403 ERR_SCOPE_ACCESS_DENIED cross-tenant and 403 ERR_OBSERVER_MODE_READ_ONLY."""
    draft_b = str(uuid7())
    app, tokens = setup_packs_red_team_app(
        monkeypatch, draft_id=draft_b, leak_desc="Scoped", draft_scope_id=WS_B
    )
    marc_hdr = {"Authorization": f"Bearer {tokens['marc']}"}
    claire_hdr = {"Authorization": f"Bearer {tokens['claire']}"}
    obs_hdr = {**marc_hdr, "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"}
    uid = str(uuid7())
    slot_body = {"bindings": [{"slot_key": "git_repo", "target_kind": "UNBOUND"}]}
    valid_b64 = base64.b64encode(zip_of({"apm.yml": apm_yml()})).decode("ascii")
    wsb_manifest_b64 = base64.b64encode(zip_of({"apm.yml": apm_yml(scope_id=WS_B)})).decode("ascii")

    cross_calls: list[tuple[str, str, dict[str, Any] | None]] = [
        (
            "POST",
            "/api/v1/packs/import",
            {"zip_base64": valid_b64, "scope_type": "WORKSPACE", "scope_id": WS_B},
        ),  # noqa: E501
        (
            "POST",
            "/api/v1/packs/import",
            {"zip_base64": valid_b64, "scope_type": "BU", "scope_id": ORG_B},
        ),  # noqa: E501
        ("POST", "/api/v1/packs/import", {"zip_base64": wsb_manifest_b64}),
        ("DELETE", f"/api/v1/packs/{draft_b}", None),
        ("POST", f"/api/v1/packs/{draft_b}/export", {"auto_include_dependencies": False}),
        ("GET", f"/api/v1/agents-and-skills?workspace_id={WS_B}", None),
        ("GET", f"/api/v1/agents-and-skills/resolve?ref=@reviewer&workspace_id={WS_B}", None),
        ("GET", f"/api/v1/workspaces/{WS_B}/packs", None),
        ("POST", f"/api/v1/workspaces/{WS_B}/packs/sdlc/activate", {}),
        ("PUT", f"/api/v1/workspaces/{WS_B}/packs/sdlc/slots", slot_body),
        (
            "POST",
            "/api/v1/packs/composer",
            {"slug": "x", "name": "X", "scope_type": "WORKSPACE", "scope_id": WS_B},
        ),
        ("GET", f"/api/v1/packs/composer/{draft_b}", None),
        ("PATCH", f"/api/v1/packs/composer/{draft_b}", {"name": "Hijack"}),
        ("PUT", f"/api/v1/packs/composer/{draft_b}/members", {"members": []}),
        ("POST", f"/api/v1/packs/composer/{draft_b}/publish", {}),
        ("DELETE", f"/api/v1/packs/composer/{draft_b}", None),
    ]
    obs_calls: list[tuple[str, str, dict[str, Any] | None]] = [
        ("POST", "/api/v1/packs/import", {"zip_base64": valid_b64, "scope_id": WS_A}),
        ("DELETE", f"/api/v1/packs/{uid}", None),
        ("POST", f"/api/v1/workspaces/{WS_A}/packs/sdlc/activate", {}),
        ("DELETE", f"/api/v1/workspaces/{WS_A}/packs/sdlc/deactivate", None),
        ("PUT", f"/api/v1/workspaces/{WS_A}/packs/reorder", {"ordered_pack_slugs": ["sdlc"]}),
        ("PUT", f"/api/v1/workspaces/{WS_A}/packs/sdlc/slots", slot_body),
        (
            "POST",
            "/api/v1/packs/composer",
            {"slug": "o", "name": "O", "scope_type": "WORKSPACE", "scope_id": WS_A},
        ),
        ("PATCH", f"/api/v1/packs/composer/{draft_b}", {"name": "Blocked"}),
        ("PUT", f"/api/v1/packs/composer/{draft_b}/members", {"members": []}),
        ("POST", f"/api/v1/packs/composer/{draft_b}/publish", {}),
        ("POST", f"/api/v1/packs/composer/{draft_b}/export", {"auto_include_dependencies": True}),
        ("DELETE", f"/api/v1/agents-and-skills/agents/{uid}?unlink_from_draft_packs=true", None),
        ("DELETE", f"/api/v1/agents-and-skills/skills/{uid}?unlink_from_draft_packs=true", None),
        ("DELETE", f"/api/v1/workflows/v2/{uid}?unlink_from_draft_packs=true", None),
        (
            "DELETE",
            f"/api/v1/packs/composer/dna-mechanisms/{uid}?unlink_from_draft_packs=true",
            None,
        ),  # noqa: E501
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for method, path, body in cross_calls:
            r_cross = await client.request(method, path, headers=marc_hdr, json=body)
            assert r_cross.status_code == 403, f"cross {method} {path}: {r_cross.text}"
            assert r_cross.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"
        for method, path, body in obs_calls:
            for tag, hdrs in (("jwt", claire_hdr), ("header", obs_hdr)):
                r_obs = await client.request(method, path, headers=hdrs, json=body)
                assert r_obs.status_code == 403, f"obs {tag} {method} {path}: {r_obs.text}"
                assert r_obs.headers["content-type"].startswith("application/problem+json")
                assert r_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"
