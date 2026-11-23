"""Branch-coverage tests for `llm_endpoint_resolver` and `_ai_models_helpers`."""

from __future__ import annotations

import dataclasses
import os
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from starlette.requests import Request

import orcia_core.orchestration._internal.sql_ai_model_mappings as sql_mappings
from orcia_api.routers import _ai_models_helpers as helpers
from orcia_api.schemas.settings_and_studio import SecretInputPayload
from orcia_core.orchestration.ai_models_records import AiModelMappingRecord
from orcia_core.orchestration.llm_endpoint_resolver import (
    extract_tier_endpoint_from_dict,
    resolve_configured_llm_endpoint_from_sources,
    select_endpoint_from_tiers,
)
from orcia_core.permissions.errors import ObserverModeReadOnlyError, ScopeAccessDeniedError


class _FakeBeginCtx:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_args: Any) -> None:
        return None


class _FakeEngine:
    def begin(self) -> _FakeBeginCtx:
        return _FakeBeginCtx()


def _make_record(**overrides: Any) -> AiModelMappingRecord:
    base = AiModelMappingRecord(
        id="map-1",
        scope_level="GLOBAL",
        scope_id="00000000-0000-7000-8000-000000000000",
        display_name="Gemini Interactions",
        inference_tier="medium",
        effort="balanced",
        provider_slug="google",
        model_family="Google Gemini",
        model_name="antigravity-preview-05-2026",
        fallback_model_name="gemini-2.5-flash",
        endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
        auth_mode="api_key",
        protocol_mode="gemini_native",
        usage="chat",
        supports_tools=True,
    )
    return dataclasses.replace(base, **overrides)


def _make_request(
    headers: list[tuple[bytes, bytes]] | None = None, *, app_state: Any | None = None
) -> Request:
    app = SimpleNamespace(state=app_state or SimpleNamespace())
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/settings/ai-models/test",
            "headers": headers or [],
            "app": app,
        }
    )


def test_extract_and_select_tier_endpoints() -> None:
    assert (
        extract_tier_endpoint_from_dict(
            {"usage": "embedding", "primaryModel": "e", "endpointUrl": "https://api.openai.com/v1"}
        )
        is None
    )
    assert (
        extract_tier_endpoint_from_dict(
            {"primaryModel": "", "endpointUrl": "https://api.openai.com/v1"}
        )
        is None
    )
    ep = extract_tier_endpoint_from_dict(
        {
            "primaryModel": "m1",
            "fallback_model_name": "m2",
            "endpoint_uri": "https://api.openai.com/v1",
            "maxTokensBudget": "invalid",
            "supports_tools": True,
        }
    )
    assert (
        ep is not None
        and ep.fallback_model_name == "m2"
        and ep.max_tokens_budget == 8192
        and ep.supports_tools is True
    )
    assert select_endpoint_from_tiers([], "medium") is None
    assert (
        select_endpoint_from_tiers(
            [{"primaryModel": "m1", "endpointUrl": "https://api.openai.com/v1", "tier": "simple"}],
            "complex",
        )
        is not None
    )
    assert (
        select_endpoint_from_tiers(
            [{"primaryModel": "m1", "endpointUrl": "https://api.openai.com/v1", "tier": "complex"}],
            "complex",
        )
        is not None
    )


@pytest.mark.asyncio
async def test_resolve_configured_llm_endpoint_all_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    assert await resolve_configured_llm_endpoint_from_sources(
        engine=None,
        vault_cipher=None,
        snapshot=None,
        hub_svc=None,
        resolved_scope_id="s1",
        use_cassette=True,
    ) == (None, None)

    rec = _make_record()

    async def _fake_pg18_ok(*_a: Any, **_k: Any) -> tuple[AiModelMappingRecord, str]:
        return rec, "resolved-token"

    monkeypatch.setattr(sql_mappings, "resolve_decrypted_ai_model_for_tier_pg18", _fake_pg18_ok)
    ep_pg, _ = await resolve_configured_llm_endpoint_from_sources(
        engine=_FakeEngine(),
        vault_cipher=object(),
        snapshot=None,
        hub_svc=None,
        resolved_scope_id="s1",  # type: ignore[arg-type]
    )
    assert (
        ep_pg is not None
        and ep_pg.fallback_model_name == "gemini-2.5-flash"
        and ep_pg.api_key == "resolved-token"  # pragma: allowlist secret
    )

    async def _fake_pg18_ssrf(*_a: Any, **_k: Any) -> tuple[AiModelMappingRecord, str]:
        return _make_record(endpoint_uri="http://169.254.169.254/v1"), "resolved-token"

    async def _fake_pg18_err(*_a: Any, **_k: Any) -> None:
        raise RuntimeError("db err")

    for fn in (_fake_pg18_ssrf, _fake_pg18_err):
        monkeypatch.setattr(sql_mappings, "resolve_decrypted_ai_model_for_tier_pg18", fn)
        assert await resolve_configured_llm_endpoint_from_sources(
            engine=_FakeEngine(),  # type: ignore[arg-type]
            vault_cipher=object(),
            snapshot=None,
            hub_svc=None,
            resolved_scope_id="s1",
        ) == (None, None)

    snap_obj = SimpleNamespace(
        llm_tiers=[
            {
                "primaryModel": "snap-m",
                "secondaryModel": "snap-fb",
                "endpointUrl": "https://api.openai.com/v1",
            }
        ]
    )

    async def _snap_loader(_eng: Any, _env: str) -> Any:
        return snap_obj

    ep_snap, ret_snap = await resolve_configured_llm_endpoint_from_sources(
        engine=_FakeEngine(),
        vault_cipher=None,
        snapshot=None,
        hub_svc=None,
        resolved_scope_id="s1",
        snapshot_loader=_snap_loader,  # type: ignore[arg-type]
    )
    assert ep_snap is not None and ep_snap.fallback_model_name == "snap-fb" and ret_snap is snap_obj

    ep_snap2, _ = await resolve_configured_llm_endpoint_from_sources(
        engine=None,
        vault_cipher=None,
        snapshot=snap_obj,
        hub_svc=None,
        resolved_scope_id="s1",
    )
    assert ep_snap2 is not None and ep_snap2.model_name == "snap-m"

    fake_hub = SimpleNamespace(list_mappings=lambda **_k: [rec])
    ep_hub, _ = await resolve_configured_llm_endpoint_from_sources(
        engine=None,
        vault_cipher=None,
        snapshot=None,
        hub_svc=fake_hub,
        resolved_scope_id="s1",
    )
    assert ep_hub is not None and ep_hub.fallback_model_name == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_ai_models_helpers_routes_and_key_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    assert helpers.to_secret_input_spec(None) is None
    spec = helpers.to_secret_input_spec(SecretInputPayload(action="set", plaintext_value="abc"))
    assert spec is not None and spec.action == "set"

    monkeypatch.setattr(
        helpers,
        "resolve_request_user",
        lambda _r, persona_key=None: SimpleNamespace(platform_role="OBSERVER", roles=[]),
    )
    with pytest.raises(ObserverModeReadOnlyError):
        helpers.require_ai_models_platform_admin(_make_request())

    monkeypatch.setattr(
        helpers,
        "resolve_request_user",
        lambda _r, persona_key=None: SimpleNamespace(platform_role="MEMBER", roles=[]),
    )
    with pytest.raises(ScopeAccessDeniedError):
        helpers.require_ai_models_platform_admin(_make_request())

    monkeypatch.setenv("ORCIA_TEST_ENV_API_KEY", "env-secret-123")
    rec_env = _make_record(
        auth_mode="env_var", env_var_name="ORCIA_TEST_ENV_API_KEY", supports_tools_override=False
    )

    def _mock_handler(req: httpx.Request) -> httpx.Response:
        return (
            httpx.Response(404, text="retired")
            if "antigravity" in req.content.decode("utf-8")
            else httpx.Response(200, json={"candidates": []})
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler)) as client:
        req_fr = _make_request(
            [(b"accept-language", b"fr-FR")], app_state=SimpleNamespace(http_client=client)
        )
        status, resp_fr = await helpers.execute_model_connection_test(rec_env, None, req_fr)
        assert (
            status == "OPERATIONAL"
            and "gemini-2.5-flash" in resp_fr.message
            and resp_fr.supports_tools is False
        )

        req_en = _make_request(
            [(b"accept-language", b"en-US")], app_state=SimpleNamespace(http_client=client)
        )
        _, resp_en = await helpers.execute_model_connection_test(rec_env, None, req_en)
        assert "fallback model (gemini-2.5-flash)" in resp_en.message

    rec_enc = _make_record(encrypted_api_key="iv1:cipher1")
    fake_auth = SimpleNamespace(vault_cipher=SimpleNamespace(decrypt=lambda *_a, **_k: "plain-k"))
    fake_hub = SimpleNamespace(
        get_mapping=lambda *_a, **_k: rec_env, resolve_decrypted_api_key=lambda *_a, **_k: None
    )

    pg_req = _make_request(app_state=SimpleNamespace(db_engine=_FakeEngine()))
    for rec_item, expected_key in ((rec_enc, "plain-k"), (rec_env, "env-secret-123")):
        monkeypatch.setattr(
            helpers, "get_ai_model_mapping_pg18", lambda *_a, _r=rec_item, **_k: _async_return(_r)
        )
        got_rec, got_key = await helpers.resolve_mapping_decrypted_key(
            pg_req,
            "map-1",
            fake_auth,
            fake_hub,  # type: ignore[arg-type]
        )
        assert got_rec.id == "map-1" and got_key == expected_key

    _, got_env_hub = await helpers.resolve_mapping_decrypted_key(
        _make_request(), "map-1", fake_auth, fake_hub
    )  # type: ignore[arg-type]
    assert got_env_hub == "env-secret-123"
    os.environ.pop("ORCIA_TEST_ENV_API_KEY", None)


async def _async_return(val: Any) -> Any:
    return val
