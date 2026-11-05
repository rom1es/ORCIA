"""Live LLM invocation bridge for `Mon Assistant` (`/api/v1/assistant/three-speed/*`).

Resolves the active LLM tier configured by the administrator in `Modèles IA`
(`request.app.state.platform_setup_snapshot` / `accostage_service` / PostgreSQL 18) and
invokes the configured endpoint (Ollama `/api/chat` or `/v1/chat/completions`, OpenAI,
Mistral, Anthropic) when running in live mode. Falls back deterministically in CI/TestClient
when no live LLM endpoint is reachable or when `ORCIA_USE_CASSETTE_LLM=1`.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import Request


@dataclass(frozen=True, slots=True)
class ResolvedLiveLlmEndpoint:
    """Active LLM endpoint configuration resolved for `Mon Assistant`."""

    provider: str
    model_name: str
    endpoint_uri: str
    auth_mode: str
    api_key: str | None = None


@dataclass(frozen=True, slots=True)
class LiveLlmTurnOutcome:
    """Result of invoking the configured LLM endpoint for an Assistant turn."""

    response_text: str
    step_label: str
    latency_ms: float


def _extract_tier_endpoint_from_dict(item: dict[str, Any]) -> ResolvedLiveLlmEndpoint | None:
    model_name = str(item.get("primaryModel") or item.get("model") or "").strip()
    endpoint_uri = str(item.get("endpointUrl") or item.get("endpoint_uri") or "").strip()
    if not model_name or not endpoint_uri:
        return None
    if not (endpoint_uri.startswith("http://") or endpoint_uri.startswith("https://")):
        return None
    if ".local/" in endpoint_uri:
        return None
    provider = str(item.get("modelFamily") or item.get("provider") or "OpenAI").strip()
    auth_mode = str(item.get("authMode") or "api_key").strip()
    raw_key = item.get("apiKey")
    api_key = str(raw_key).strip() if isinstance(raw_key, str) and raw_key.strip() else None
    return ResolvedLiveLlmEndpoint(
        provider=provider,
        model_name=model_name,
        endpoint_uri=endpoint_uri.rstrip("/"),
        auth_mode=auth_mode,
        api_key=api_key,
    )


def resolve_configured_llm_endpoint(request: Request) -> ResolvedLiveLlmEndpoint | None:
    """Resolve the active configured LLM endpoint from app state or PostgreSQL 18."""
    use_cassette = os.environ.get("ORCIA_USE_CASSETTE_LLM", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if use_cassette:
        return None

    # 1. Check in-memory snapshot on app.state
    snap = getattr(request.app.state, "platform_setup_snapshot", None)
    if snap is not None and getattr(snap, "llm_tiers", None):
        for item in snap.llm_tiers:
            if isinstance(item, dict):
                resolved = _extract_tier_endpoint_from_dict(item)
                if resolved is not None:
                    return resolved

    # 2. Lazy load from PostgreSQL 18 if snapshot was not yet hydrated in this worker
    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1":
        try:
            import asyncio
            import concurrent.futures

            from sqlalchemy.ext.asyncio import create_async_engine

            import orcia_core.bootstrap as bm
            from orcia_core.config import resolve_database_url

            async def _load_snap() -> bm.PlatformSetupSnapshotRecord | None:
                engine = create_async_engine(resolve_database_url(), connect_args={"timeout": 1.0})
                try:
                    return await bm.load_platform_setup_state_from_postgres18(
                        engine, orcia_env="local"
                    )
                finally:
                    await engine.dispose()

            try:
                asyncio.get_running_loop()
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    db_snap = pool.submit(lambda: asyncio.run(_load_snap())).result(timeout=2.0)
            except RuntimeError:
                db_snap = asyncio.run(_load_snap())

            if db_snap is not None:
                request.app.state.platform_setup_snapshot = db_snap
                for item in db_snap.llm_tiers:
                    if isinstance(item, dict):
                        resolved = _extract_tier_endpoint_from_dict(item)
                        if resolved is not None:
                            return resolved
        except Exception:
            pass

    return None


def _build_ollama_root_url(endpoint_uri: str) -> str:
    """Normalize `http://localhost:11434/api` or `/v1` to base root `http://localhost:11434`."""
    clean = endpoint_uri.rstrip("/")
    for suffix in ("/api/chat", "/api/generate", "/api", "/v1/chat/completions", "/v1"):
        if clean.endswith(suffix):
            return clean[: -len(suffix)].rstrip("/")
    return clean


def _is_ollama_endpoint(ep: ResolvedLiveLlmEndpoint) -> bool:
    uri_lower = ep.endpoint_uri.lower()
    prov_lower = ep.provider.lower()
    return (
        "ollama" in prov_lower
        or ":11434" in uri_lower
        or uri_lower.endswith("/api")
        or uri_lower.endswith("/api/chat")
    )


def invoke_configured_llm_for_assistant_turn(
    request: Request,
    *,
    user_prompt: str,
    hat: str,
    speed_mode: str,
    system_instructions_override: str | None = None,
) -> LiveLlmTurnOutcome | None:
    """Call the configured LLM endpoint and return its response text and latency."""
    # Skip live network call when running inside FastAPI TestClient (`http://testserver`)
    client_host = getattr(getattr(request, "client", None), "host", "") or ""
    if client_host == "testclient" and os.environ.get("ORCIA_FORCE_LIVE_LLM_IN_TESTS") != "1":
        return None

    ep = resolve_configured_llm_endpoint(request)
    if ep is None:
        return None

    system_msg = (
        system_instructions_override.strip()
        if system_instructions_override and system_instructions_override.strip()
        else (
            f"Tu es Mon Assistant ORCIA (rôle actif : {hat}). "
            "Réponds en français de manière claire, structurée, précise et "
            "directement utile à l'utilisateur."
        )
    )
    t0 = time.perf_counter()

    try:
        if _is_ollama_endpoint(ep):
            root_url = _build_ollama_root_url(ep.endpoint_uri)
            chat_url = f"{root_url}/api/chat"
            payload: dict[str, Any] = {
                "model": ep.model_name,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt.strip()},
                ],
                "stream": False,
                "think": False,
            }
            with httpx.Client(timeout=45.0) as client:
                resp = client.post(chat_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            msg_obj = data.get("message") if isinstance(data, dict) else {}
            content = ""
            if isinstance(msg_obj, dict):
                content = str(msg_obj.get("content") or "").strip()
                if not content and msg_obj.get("thinking"):
                    content = str(msg_obj.get("thinking")).strip()
            if not content:
                return None
            return LiveLlmTurnOutcome(
                response_text=content,
                step_label=f"💬 Modèle IA {ep.model_name} ({ep.provider}) — réponse générée",
                latency_ms=elapsed_ms,
            )

        # OpenAI-compatible (`/v1/chat/completions`)
        base = ep.endpoint_uri.rstrip("/")
        completions_url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if ep.api_key:
            headers["Authorization"] = f"Bearer {ep.api_key}"
        openai_payload: dict[str, Any] = {
            "model": ep.model_name,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt.strip()},
            ],
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(completions_url, json=openai_payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        choices = data.get("choices") if isinstance(data, dict) else None
        if isinstance(choices, list) and choices:
            first_msg = choices[0].get("message", {})
            content = str(first_msg.get("content") or first_msg.get("reasoning") or "").strip()
            if content:
                return LiveLlmTurnOutcome(
                    response_text=content,
                    step_label=f"💬 Modèle IA {ep.model_name} ({ep.provider}) — réponse générée",
                    latency_ms=elapsed_ms,
                )
    except Exception:
        return None

    return None
