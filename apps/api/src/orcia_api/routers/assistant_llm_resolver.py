"""Thin Async LLM Endpoint Resolver Facade (`Story 17.5`, `Story 26.2`, `AD-21`)."""

from __future__ import annotations

import os
from typing import Any

from fastapi import Request

from orcia_api.dependencies._llm_streaming_providers import is_cassette_llm_enabled
from orcia_core.orchestration.llm_endpoint_resolver import (
    extract_tier_endpoint_from_dict as extract_tier_endpoint_from_dict,
)
from orcia_core.orchestration.llm_endpoint_resolver import (
    resolve_configured_llm_endpoint_from_sources,
)
from orcia_core.orchestration.llm_endpoint_resolver import (
    select_endpoint_from_tiers as select_endpoint_from_tiers,
)
from orcia_core.ports.llm_streaming_port import LlmEndpointConfig


async def resolve_configured_llm_endpoint(
    request: Request,
    *,
    requested_tier: str | None = None,
    workspace_id: str | None = None,
) -> LlmEndpointConfig | None:
    """Resolve active LLM endpoint via `orcia_core.orchestration.llm_endpoint_resolver`."""
    if is_cassette_llm_enabled():
        return None

    from orcia_api.dependencies._assistant_guards import resolve_assistant_workspace_uuid
    from orcia_api.dependencies._core_providers import get_configured_db_engine
    from orcia_core.bootstrap import load_platform_setup_state_from_postgres18

    engine = get_configured_db_engine(request)
    auth = getattr(request.app.state, "auth_service", None)
    snap = getattr(request.app.state, "platform_setup_snapshot", None)
    hub_svc = getattr(request.app.state, "ai_models_hub_service", None)
    accostage_svc = getattr(request.app.state, "accostage_service", None)
    resolved_env = (
        getattr(accostage_svc, "orcia_env", None)
        or os.environ.get("ORCIA_ENV", "").strip()
        or "local"
    )
    resolved_scope_id = (
        await resolve_assistant_workspace_uuid(request, workspace_id)
        if engine is not None
        else "00000000-0000-7000-8000-000000000000"
    )
    ep, refreshed_snap = await resolve_configured_llm_endpoint_from_sources(
        engine=engine,
        vault_cipher=getattr(auth, "vault_cipher", None),
        snapshot=snap,
        hub_svc=hub_svc,
        resolved_scope_id=resolved_scope_id,
        requested_tier=requested_tier,
        orcia_env=resolved_env,
        use_cassette=False,
        snapshot_loader=lambda eng, env: load_platform_setup_state_from_postgres18(
            eng, orcia_env=env
        ),
    )
    if refreshed_snap is not None:
        request.app.state.platform_setup_snapshot = refreshed_snap
    return ep


async def ensure_active_chat_model_if_live(
    request: Request,
    *,
    requested_tier: str | None = None,
    workspace_id: str | None = None,
) -> LlmEndpointConfig | None:
    """Assert an active `chat` model exists when calling live LLM (outside cassette mode)."""
    if is_cassette_llm_enabled():
        return None
    ep = await resolve_configured_llm_endpoint(
        request, requested_tier=requested_tier, workspace_id=workspace_id
    )
    if ep is None:
        from orcia_core.orchestration.errors import TierModelNotConfiguredError

        raise TierModelNotConfiguredError(
            inference_tier=requested_tier or "medium",
            detail_override=(
                "Aucun modèle IA de dialogue (chat) actif n'est configuré. "
                "Veuillez configurer un modèle chat dans /settings/ai-models."
            ),
            instance=str(request.url.path),
        )
    return ep


def _unused_placeholder(_val: Any = None) -> None:
    return None


__all__ = [
    "ensure_active_chat_model_if_live",
    "extract_tier_endpoint_from_dict",
    "resolve_configured_llm_endpoint",
    "select_endpoint_from_tiers",
]
