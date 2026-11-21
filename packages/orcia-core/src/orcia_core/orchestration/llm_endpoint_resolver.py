"""Core LLM Endpoint Resolver from PG18, Platform Snapshot, or Hub (`AD-21`, `Story 26.2`)."""

from __future__ import annotations

import os
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from orcia_core.observability.logging import get_logger
from orcia_core.permissions.ssrf_guard import is_safe_llm_endpoint_url
from orcia_core.ports.llm_streaming_port import LlmEndpointConfig

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

logger = get_logger("orcia.assistant.llm")


def extract_tier_endpoint_from_dict(item: dict[str, Any]) -> LlmEndpointConfig | None:
    """Extract and SSRF-validate an endpoint from a snapshot tier dictionary."""
    if str(item.get("usage") or "chat").strip().lower() == "embedding":
        return None
    model_name = str(item.get("primaryModel") or item.get("model") or "").strip()
    endpoint_uri = str(item.get("endpointUrl") or item.get("endpoint_uri") or "").strip()
    if not model_name or not is_safe_llm_endpoint_url(endpoint_uri):
        return None
    provider = str(item.get("modelFamily") or item.get("provider") or "OpenAI").strip()
    auth_mode = str(item.get("authMode") or "api_key").strip()
    tier_key = str(item.get("tier") or item.get("tierKey") or "medium").strip().lower()
    raw_key = item.get("apiKey")
    api_key = str(raw_key).strip() if isinstance(raw_key, str) and raw_key.strip() else None
    protocol_mode = str(item.get("protocolMode") or item.get("protocol_mode") or "").strip()
    return LlmEndpointConfig(
        provider=provider,
        model_name=model_name,
        endpoint_uri=endpoint_uri.rstrip("/"),
        auth_mode=auth_mode,
        tier=tier_key or "medium",
        api_key=api_key,
        protocol_mode=protocol_mode,
    )


def select_endpoint_from_tiers(
    llm_tiers: list[Any],
    requested_tier: str | None = None,
) -> LlmEndpointConfig | None:
    """Select the requested tier endpoint (or first valid chat endpoint) from tier configs."""
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


async def resolve_configured_llm_endpoint_from_sources(
    *,
    engine: AsyncEngine | None,
    vault_cipher: Any | None,
    snapshot: Any | None,
    hub_svc: Any | None,
    resolved_scope_id: str,
    requested_tier: str | None = None,
    orcia_env: str = "local",
    use_cassette: bool = False,
    snapshot_loader: Callable[[AsyncEngine, str], Awaitable[Any | None]] | None = None,
) -> tuple[LlmEndpointConfig | None, Any | None]:
    """Resolve active chat LLM endpoint from PG18, Day-0 snapshot, or Hub service.

    Returns `(endpoint, refreshed_snapshot)`.
    """
    if use_cassette:
        return None, None

    if engine is not None:
        t0 = time.perf_counter()
        try:
            import orcia_core.orchestration._internal.sql_ai_model_mappings as bm

            tier = requested_tier or "medium"
            if vault_cipher is not None:
                async with engine.begin() as conn:
                    await bm.ensure_ai_model_mappings_schema_on_postgres18(conn)
                    m = await bm.resolve_decrypted_ai_model_for_tier_pg18(
                        conn,
                        cipher=vault_cipher,
                        scope_id=resolved_scope_id,
                        inference_tier=tier,
                    )
                    if m is not None:
                        rec, key = m
                        if not is_safe_llm_endpoint_url(rec.endpoint_uri):
                            logger.warning(
                                "llm_endpoint_blocked_by_ssrf_policy",
                                endpoint=rec.endpoint_uri,
                                scope_id=resolved_scope_id,
                            )
                            return None, None
                        return (
                            LlmEndpointConfig(
                                provider=rec.provider_slug,
                                model_name=rec.model_name,
                                endpoint_uri=rec.endpoint_uri,
                                auth_mode=rec.auth_mode,
                                tier=rec.inference_tier,
                                api_key=key,
                                protocol_mode=getattr(rec, "protocol_mode", ""),
                            ),
                            None,
                        )
            if snapshot is not None and getattr(snapshot, "llm_tiers", None):
                chosen = select_endpoint_from_tiers(list(snapshot.llm_tiers), requested_tier)
                if chosen is not None:
                    return chosen, None
            resolved_env = orcia_env or os.environ.get("ORCIA_ENV", "").strip() or "local"
            if snapshot_loader is not None:
                db_snap = await snapshot_loader(engine, resolved_env)
                if db_snap is not None:
                    return (
                        select_endpoint_from_tiers(list(db_snap.llm_tiers), requested_tier),
                        db_snap,
                    )
        except Exception as exc:
            logger.warning(
                "llm_endpoint_pg_resolution_failed",
                elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                error_type=type(exc).__name__,
            )
        return None, None

    if snapshot is not None and getattr(snapshot, "llm_tiers", None):
        chosen = select_endpoint_from_tiers(list(snapshot.llm_tiers), requested_tier)
        if chosen is not None:
            return chosen, None
    if hub_svc is not None:
        active_chat = hub_svc.list_mappings(is_active=True, usage="chat")
        target = (requested_tier or "medium").strip().lower()
        chosen_rec = next(
            (m for m in active_chat if m.inference_tier == target and not m.draining),
            next((m for m in active_chat if not m.draining), None),
        )
        if chosen_rec is not None and is_safe_llm_endpoint_url(chosen_rec.endpoint_uri):
            return (
                LlmEndpointConfig(
                    provider=chosen_rec.provider_slug,
                    model_name=chosen_rec.model_name,
                    endpoint_uri=chosen_rec.endpoint_uri,
                    auth_mode=chosen_rec.auth_mode,
                    tier=chosen_rec.inference_tier,
                    api_key=None,
                    protocol_mode=getattr(chosen_rec, "protocol_mode", ""),
                ),
                None,
            )
    return None, None
