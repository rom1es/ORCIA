"""Unit tests for Story 19.5: AI Models usage attribute, uniqueness, and API routing."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from tests.unit.fakes import default_in_memory_reindex_manager

from orcia_api.errors.registry import resolve_domain_error_mapping
from orcia_api.routers.ai_models_hub import router as ai_models_router
from orcia_core.orchestration.ai_models_governance import AiModelsHubService
from orcia_core.permissions import build_default_auth_and_org_service
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.rag.errors import EmbeddingProviderUnsupportedError
from orcia_kernel.errors import OrciaDomainError


def test_ai_models_hub_service_usage_and_uniqueness() -> None:
    """Verify AiModelsHubService handles usage='embedding' and enforces single global active."""
    cipher = PassthroughVaultCipher(master_key=b"1" * 32)
    service = AiModelsHubService(vault_cipher=cipher)

    # 1. Create chat model
    chat_m = service.create_mapping(
        scope_level="WORKSPACE",
        scope_id="0195f000-0000-7000-8000-000000000301",
        display_name="Chat Model",
        inference_tier="medium",
        provider_slug="mistral",
        model_family="Mistral",
        model_name="mistral-large-latest",
        endpoint_uri="https://api.mistral.ai",
        usage="chat",
    )
    assert chat_m.usage == "chat"
    assert chat_m.is_active is True

    # 2. Refuse Anthropic for embedding
    with pytest.raises(EmbeddingProviderUnsupportedError):
        service.create_mapping(
            scope_level="GLOBAL",
            scope_id="0195f000-0000-7000-8000-000000000301",
            display_name="Anthropic Embedding Attempt",
            inference_tier="auto",
            provider_slug="anthropic",
            model_family="Anthropic",
            model_name="claude-3-5-sonnet",
            endpoint_uri="https://api.anthropic.com/v1",
            protocol_mode="anthropic_messages",
            usage="embedding",
        )

    # 3. Create first global embedding model
    embed_1 = service.create_mapping(
        scope_level="GLOBAL",
        scope_id="0195f000-0000-7000-8000-000000000301",
        display_name="Global Embedding 1",
        inference_tier="auto",
        provider_slug="openai",
        model_family="OpenAI",
        model_name="text-embedding-3-large",
        endpoint_uri="https://api.openai.com/v1",
        protocol_mode="openai_compatible",
        usage="embedding",
    )
    assert embed_1.usage == "embedding"
    assert embed_1.is_active is True
    assert service.get_active_embedding_mapping() == embed_1

    # 4. Create second global embedding model -> automatically deactivates embed_1
    embed_2 = service.create_mapping(
        scope_level="GLOBAL",
        scope_id="0195f000-0000-7000-8000-000000000301",
        display_name="Global Embedding 2",
        inference_tier="auto",
        provider_slug="google",
        model_family="Google",
        model_name="text-embedding-004",
        endpoint_uri="https://generativelanguage.googleapis.com",
        protocol_mode="gemini_native",
        usage="embedding",
    )
    assert embed_2.is_active is True
    updated_embed_1 = service.get_mapping(embed_1.id)
    assert updated_embed_1.is_active is False
    assert service.get_active_embedding_mapping() == embed_2

    # 5. Filter list_mappings by usage
    chat_list = service.list_mappings(usage="chat")
    assert len(chat_list) == 1
    assert chat_list[0].id == chat_m.id

    embedding_list = service.list_mappings(usage="embedding")
    assert len(embedding_list) == 2


@pytest.mark.asyncio
async def test_fastapi_ai_models_hub_usage_endpoints() -> None:
    """Verify HTTP API contracts for usage and error mapping via ASGITransport."""
    cipher = PassthroughVaultCipher(master_key=b"2" * 32)
    hub_svc = AiModelsHubService(vault_cipher=cipher)
    auth_svc = build_default_auth_and_org_service()

    app = FastAPI()

    @app.exception_handler(OrciaDomainError)
    async def orcia_domain_error_handler(request: httpx.Request, exc: OrciaDomainError):
        mapping = resolve_domain_error_mapping(exc)
        return JSONResponse(
            status_code=mapping.http_status,
            content={
                "type": mapping.type_uri,
                "title": exc.localize().title,
                "status": mapping.http_status,
                "detail": str(exc),
                "error_code": exc.error_code,
            },
        )

    app.include_router(ai_models_router)
    app.state.ai_models_hub_service = hub_svc
    app.state.auth_service = auth_svc
    app.state.reindex_manager = default_in_memory_reindex_manager

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create embedding model via API
        payload = {
            "scope_level": "GLOBAL",
            "scope_id": "0195f000-0000-7000-8000-000000000301",
            "display_name": "OpenAI Embedding Model",
            "inference_tier": "auto",
            "effort": "default",
            "provider_slug": "openai",
            "model_family": "OpenAI",
            "model_name": "text-embedding-3-small",
            "endpoint_uri": "https://api.openai.com/v1",
            "protocol_mode": "openai_compatible",
            "usage": "embedding",
        }
        res = await client.post(
            "/api/v1/settings/ai-models/mappings",
            headers={"X-Orcia-Persona": "karim"},
            json=payload,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["usage"] == "embedding"
        created_id = data["id"]

        # List with usage query param
        list_res = await client.get("/api/v1/settings/ai-models/mappings?usage=embedding")
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total_count"] == 1
        assert list_data["items"][0]["id"] == created_id

        # Attempt to create Anthropic embedding model -> 422 ERR_EMBEDDING_PROVIDER_UNSUPPORTED
        bad_payload = {
            "scope_level": "GLOBAL",
            "scope_id": "0195f000-0000-7000-8000-000000000301",
            "display_name": "Claude Embedding Attempt",
            "inference_tier": "auto",
            "effort": "default",
            "provider_slug": "anthropic",
            "model_family": "Anthropic",
            "model_name": "claude-3-5-sonnet",
            "endpoint_uri": "https://api.anthropic.com/v1",
            "protocol_mode": "anthropic_messages",
            "usage": "embedding",
        }
        bad_res = await client.post(
            "/api/v1/settings/ai-models/mappings",
            headers={"X-Orcia-Persona": "karim"},
            json=bad_payload,
        )
        assert bad_res.status_code == 422
        assert bad_res.json()["error_code"] == "ERR_EMBEDDING_PROVIDER_UNSUPPORTED"
