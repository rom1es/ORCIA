"""Unit tests for Story 31.2 `/api/v1/packs` import/delete/export endpoints (`<= 300 L`)."""

from __future__ import annotations

import base64
from typing import Any

from fastapi.testclient import TestClient
from tests.unit.packs.test_story_31_2_packs_router_and_materializer import _make_sample_zip

from orcia_api.main import create_app
from orcia_core.packs import PackBundleKind, PackImportOutcome, PackScopeType


def test_packs_import_and_delete_router_observer_and_multipart() -> None:
    """Verify `/api/v1/packs/import` (JSON + multipart) and `DELETE /api/v1/packs/{id}`."""
    app = create_app()
    client = TestClient(app)
    _AUTH_WS = "0192c4e0-0000-7000-8000-000000000201"
    zip_bytes = _make_sample_zip()
    b64 = base64.b64encode(zip_bytes).decode("ascii")

    obs_resp = client.post(
        "/api/v1/packs/import",
        json={"zip_base64": b64},
        headers={"x-orcia-access-mode": "READ_ONLY_OBSERVER"},
    )
    assert obs_resp.status_code == 403
    assert obs_resp.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    obs_del = client.delete(
        "/api/v1/packs/0195f000-0000-7000-8000-000000000901",
        headers={"x-orcia-access-mode": "READ_ONLY_OBSERVER"},
    )
    assert obs_del.status_code == 403
    assert obs_del.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    class _StubImportSvc:
        async def get_bundle(self, bid: str) -> dict[str, object]:
            return {
                "id": bid,
                "slug": "demo-pack",
                "bundle_kind": PackBundleKind.IMPORTED.value,
                "scope_type": PackScopeType.WORKSPACE.value,
                "scope_id": _AUTH_WS,
            }

        async def import_zip_bytes(self, raw: bytes, **_kwargs: Any) -> PackImportOutcome:
            assert raw == zip_bytes
            return PackImportOutcome(
                bundle_id="0195f000-0000-7000-8000-000000000901",
                pack_id="orcia-pack-demo-pack",
                slug="demo-pack",
                name="demo-pack",
                version="1.0.0",
                bundle_kind=PackBundleKind.IMPORTED.value,
                scope_type=PackScopeType.WORKSPACE.value,
                scope_id=_AUTH_WS,
                status="PUBLISHED",
                archive_sha256="a" * 64,
                cas_object_key="packs/demo-pack/1.0.0/aaa.zip",
                idempotent_noop=False,
                counts={"agents": 1, "skills": 1},
            )

        async def delete_bundle(self, bid: str, **_kwargs: Any) -> dict[str, str]:
            return {"bundle_id": bid, "slug": "demo-pack", "version": "1.0.0"}

    app.state.pack_import_service = _StubImportSvc()
    mp_resp = client.post(
        "/api/v1/packs/import",
        files={"file": ("demo-pack.zip", zip_bytes, "application/zip")},
        data={"scope_type": "WORKSPACE", "scope_id": _AUTH_WS},
    )
    assert mp_resp.status_code == 200
    assert mp_resp.json()["slug"] == "demo-pack"
    assert mp_resp.json()["counts"]["agents"] == 1

    json_resp = client.post(
        "/api/v1/packs/import",
        json={"zip_base64": b64, "scope_type": "WORKSPACE", "scope_id": _AUTH_WS},
    )
    assert json_resp.status_code == 200

    del_resp = client.delete("/api/v1/packs/0195f000-0000-7000-8000-000000000901")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True
