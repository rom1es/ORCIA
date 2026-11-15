"""Async LLM Endpoint Resolver for `Mon Assistant` (`Story 17.5`, `AD-21`)."""

from __future__ import annotations

import os
import time
from typing import Any

from fastapi import Request

from orcia_api.dependencies import get_or_create_shared_db_engine
from orcia_api.routers.assistant_llm_providers import (
    ResolvedLiveLlmEndpoint,
    is_safe_llm_endpoint_url,
    logger,
)


def extract_tier_endpoint_from_dict(item: dict[str, Any]) -> ResolvedLiveLlmEndpoint | None:
    """Extract and validate endpoint from legacy snapshot dictionary."""
    model_name = str(item.get("primaryModel") or item.get("model") or "").strip()
    endpoint_uri = str(item.get("endpointUrl") or item.get("endpoint_uri") or "").strip()
    if not model_name or not is_safe_llm_endpoint_url(endpoint_uri):
        return None
    provider = str(item.get("modelFamily") or item.get("provider") or "OpenAI").strip()
    auth_mode = str(item.get("authMode") or "api_key").strip()
    tier_key = str(item.get("tier") or item.get("tierKey") or "medium").strip().lower()
    raw_key = item.get("apiKey")
    api_key = str(raw_key).strip() if isinstance(raw_key, str) and raw_key.strip() else None
    return ResolvedLiveLlmEndpoint(
        provider=provider,
        model_name=model_name,
        endpoint_uri=endpoint_uri.rstrip("/"),
        auth_mode=auth_mode,
        tier=tier_key or "medium",
        api_key=api_key,
    )


def select_endpoint_from_tiers(
    llm_tiers: list[Any],
    requested_tier: str | None = None,
) -> ResolvedLiveLlmEndpoint | None:
    """Select appropriate tier endpoint from a list of dict configurations."""
    target = (requested_tier or "").strip().lower()
    valid_endpoints = [
        resolved
        for item in llm_tiers
        if isinstance(item, dict)
        and (resolved := extract_tier_endpoint_from_dict(item)) is not None
    ]
    if not valid_endpoints:
        return None
    if target and target != "auto":
        for ep in valid_endpoints:
            if ep.tier == target:
                return ep
    return valid_endpoints[0]


async def resolve_configured_llm_endpoint(
    request: Request,
    *,
    requested_tier: str | None = None,
) -> ResolvedLiveLlmEndpoint | None:
    """Resolve active LLM endpoint asynchronously from PG18 table or Day-0 snapshot."""
    if (
        os.environ.get("ORCIA_USE_CASSETTE_LLM", "").strip().lower() in ("1", "true", "yes")
        and os.environ.get("ORCIA_FORCE_LIVE_LLM_IN_TESTS") != "1"
    ):
        return None

    snap = getattr(request.app.state, "platform_setup_snapshot", None)
    if snap is not None and getattr(snap, "llm_tiers", None):
        chosen = select_endpoint_from_tiers(list(snap.llm_tiers), requested_tier)
        if chosen is not None:
            return chosen

    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1":
        t0 = time.perf_counter()
        try:
            import orcia_core.bootstrap as bstrap
            import orcia_core.orchestration._internal.sql_ai_model_mappings as bm

            engine = get_or_create_shared_db_engine(request)
            auth = getattr(request.app.state, "auth_service", None)
            tier = requested_tier or "medium"
            if auth is not None and getattr(auth, "vault_cipher", None) is not None:
                async with engine.begin() as conn:
                    await bm.ensure_ai_model_mappings_schema_on_postgres18(conn)
                    m = await bm.resolve_decrypted_ai_model_for_tier_pg18(
                        conn,
                        cipher=auth.vault_cipher,
                        scope_id="0195f000-0000-7000-8000-000000000301",
                        inference_tier=tier,
                    )
                    if m is not None:
                        rec, key = m
                        return ResolvedLiveLlmEndpoint(
                            provider=rec.provider_slug,
                            model_name=rec.model_name,
                            endpoint_uri=rec.endpoint_uri,
                            auth_mode=rec.auth_mode,
                            tier=rec.inference_tier,
                            api_key=key,
                        )
            db_snap = await bstrap.load_platform_setup_state_from_postgres18(
                engine, orcia_env="local"
            )
            if db_snap is not None:
                request.app.state.platform_setup_snapshot = db_snap
                return select_endpoint_from_tiers(list(db_snap.llm_tiers), requested_tier)
        except Exception as exc:
            logger.warning(
                "llm_endpoint_pg_resolution_failed",
                elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                error_type=type(exc).__name__,
            )
    return None


__all__ = [
    "extract_tier_endpoint_from_dict",
    "resolve_configured_llm_endpoint",
    "select_endpoint_from_tiers",
]
