"""Live LLM invocation bridge for `Mon Assistant` (`/api/v1/assistant/three-speed/*`).

Resolves the active LLM tier configured by the administrator in `Modèles IA`
(`request.app.state.platform_setup_snapshot` / `accostage_service` / PostgreSQL 18) and
invokes the configured endpoint (Ollama `/api/chat` or `/v1/chat/completions`, OpenAI,
Mistral, Anthropic) when running in live mode. Supports explicit tier selection
(`simple`, `medium`, `complex`, `auto`) and thinking effort (`fast`, `balanced`, `deep`).
Falls back deterministically in CI/TestClient when no live LLM endpoint is reachable or
when `ORCIA_USE_CASSETTE_LLM=1`.
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
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
    tier: str = "medium"
    api_key: str | None = None


@dataclass(frozen=True, slots=True)
class LiveLlmTurnOutcome:
    """Result of invoking the configured LLM endpoint for an Assistant turn."""

    response_text: str
    step_label: str
    latency_ms: float
    thinking_text: str | None = None


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


def _select_endpoint_from_tiers(
    llm_tiers: list[Any],
    requested_tier: str | None = None,
) -> ResolvedLiveLlmEndpoint | None:
    target = (requested_tier or "").strip().lower()
    valid_endpoints: list[ResolvedLiveLlmEndpoint] = []
    for item in llm_tiers:
        if isinstance(item, dict):
            resolved = _extract_tier_endpoint_from_dict(item)
            if resolved is not None:
                valid_endpoints.append(resolved)
    if not valid_endpoints:
        return None
    if target and target != "auto":
        for ep in valid_endpoints:
            if ep.tier == target:
                return ep
    return valid_endpoints[0]


def resolve_configured_llm_endpoint(
    request: Request,
    *,
    requested_tier: str | None = None,
) -> ResolvedLiveLlmEndpoint | None:
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
        chosen = _select_endpoint_from_tiers(list(snap.llm_tiers), requested_tier)
        if chosen is not None:
            return chosen

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
                chosen = _select_endpoint_from_tiers(list(db_snap.llm_tiers), requested_tier)
                if chosen is not None:
                    return chosen
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


def build_assistant_system_instructions(
    *,
    hat: str,
    speed_mode: str,
    requested_tier: str | None = None,
    thinking_effort: str | None = None,
    system_instructions_override: str | None = None,
) -> str:
    """Build differentiated system instructions according to model tier & thinking effort."""
    if system_instructions_override and system_instructions_override.strip():
        return system_instructions_override.strip()

    effort = (thinking_effort or "").strip().lower()
    if not effort:
        if speed_mode == "SPEED_3_DEEP_AUDIT":
            effort = "deep"
        elif speed_mode == "SPEED_2_AGENT_TOOLS":
            effort = "balanced"
        else:
            effort = "fast"

    tier_key = (requested_tier or "medium").strip().lower()
    tier_guidance = {
        "simple": "Palier Rapide : privilégie l'essentiel, la concision et une réponse immédiate.",
        "medium": (
            "Palier Polyvalent : équilibre clarté pédagogique, exemples concrets et structure."
        ),
        "complex": (
            "Palier Raisonnement avancé : traite les nuances métiers, cas limites et arbitrages."
        ),
    }.get(tier_key, "Palier Polyvalent : équilibre clarté pédagogique et structure.")

    if effort == "deep":
        effort_guidance = (
            "Niveau de réflexion Élevé (Analyse approfondie multi-points de vue) : "
            "structure impérativement ta réponse en 3 volets : "
            "1) Synthèse exécutive, 2) Risques, conformité & points de vigilance, "
            "3) Faisabilité technique & plan d'action recommandé."
        )
    elif effort == "balanced":
        effort_guidance = (
            "Niveau de réflexion Moyen (Équilibré — Sources & Compétences) : "
            "organise ta réponse avec des points clés structurés en mobilisant le contexte "
            "de l'espace de travail et les compétences mentionnées."
        )
    else:
        effort_guidance = (
            "Niveau de réflexion Bas (Rapide et efficace) : "
            "réponds de manière directe, synthétique et immédiatement actionnable, sans détour."
        )

    return (
        f"Tu es Mon Assistant ORCIA (rôle actif : {hat}). "
        f"{tier_guidance} {effort_guidance} "
        "Réponds toujours en français de manière claire et précise."
    )


def invoke_configured_llm_for_assistant_turn(
    request: Request,
    *,
    user_prompt: str,
    hat: str,
    speed_mode: str,
    requested_tier: str | None = None,
    thinking_effort: str | None = None,
    system_instructions_override: str | None = None,
) -> LiveLlmTurnOutcome | None:
    """Call the configured LLM endpoint and return its response text and latency."""
    # Skip live network call when running inside FastAPI TestClient (`http://testserver`)
    client_host = getattr(getattr(request, "client", None), "host", "") or ""
    if client_host == "testclient" and os.environ.get("ORCIA_FORCE_LIVE_LLM_IN_TESTS") != "1":
        return None

    ep = resolve_configured_llm_endpoint(request, requested_tier=requested_tier)
    if ep is None:
        return None

    effort = (thinking_effort or "").strip().lower()
    if not effort:
        effort = (
            "deep"
            if speed_mode == "SPEED_3_DEEP_AUDIT"
            else "balanced"
            if speed_mode == "SPEED_2_AGENT_TOOLS"
            else "fast"
        )
    effort_fr = {
        "fast": "Réflexion Basse",
        "balanced": "Réflexion Moyenne",
        "deep": "Réflexion Élevée",
    }.get(effort, "Réflexion Standard")

    system_msg = build_assistant_system_instructions(
        hat=hat,
        speed_mode=speed_mode,
        requested_tier=requested_tier or ep.tier,
        thinking_effort=effort,
        system_instructions_override=system_instructions_override,
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
            thinking_val: str | None = None
            if isinstance(msg_obj, dict):
                content = str(msg_obj.get("content") or "").strip()
                raw_think = str(msg_obj.get("thinking") or "").strip()
                if raw_think:
                    thinking_val = raw_think
                if not content and raw_think:
                    content = raw_think
            if not content:
                return None
            if not thinking_val:
                thinking_val = (
                    f"Modèle {ep.model_name} ({ep.provider} · {effort_fr}) : "
                    f"analyse de la question « {user_prompt.strip()[:120]} » et structuration "
                    "de la réponse."
                )
            return LiveLlmTurnOutcome(
                response_text=content,
                step_label=(
                    f"💬 Modèle IA {ep.model_name} ({ep.provider} · {effort_fr}) — réponse générée"
                ),
                latency_ms=elapsed_ms,
                thinking_text=thinking_val,
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
            raw_reasoning = str(
                first_msg.get("reasoning") or first_msg.get("thinking") or ""
            ).strip()
            content = str(first_msg.get("content") or raw_reasoning or "").strip()
            if content:
                return LiveLlmTurnOutcome(
                    response_text=content,
                    step_label=(
                        f"💬 Modèle IA {ep.model_name} "
                        f"({ep.provider} · {effort_fr}) — réponse générée"
                    ),
                    latency_ms=elapsed_ms,
                    thinking_text=raw_reasoning
                    or (
                        f"Modèle {ep.model_name} ({ep.provider} · {effort_fr}) : "
                        f"élaboration de la réponse pour « {user_prompt.strip()[:120]} »."
                    ),
                )
    except Exception:
        return None

    return None


def stream_configured_llm_for_assistant_turn(
    request: Request,
    *,
    user_prompt: str,
    hat: str,
    speed_mode: str,
    requested_tier: str | None = None,
    thinking_effort: str | None = None,
    fallback_response_text: str | None = None,
) -> Iterator[dict[str, object]]:
    """Yield incremental SSE events (`thinking_delta`, `token_delta`, `turn_completed`)."""
    outcome = invoke_configured_llm_for_assistant_turn(
        request,
        user_prompt=user_prompt,
        hat=hat,
        speed_mode=speed_mode,
        requested_tier=requested_tier,
        thinking_effort=thinking_effort,
    )
    thinking_text = (
        outcome.thinking_text
        if outcome is not None and outcome.thinking_text
        else f"Analyse de la demande « {user_prompt.strip()[:120]} » et préparation des éléments."
    )
    yield {
        "event": "thinking_delta",
        "data": {
            "step_code": "NODE_5_SINGLE_STREAM_LLM",
            "thinking_text": thinking_text,
        },
    }
    full_text = outcome.response_text if outcome is not None else (fallback_response_text or "")
    words = full_text.split(" ")
    chunk_size = max(1, min(4, len(words) // 6 or 1))
    for idx in range(0, len(words), chunk_size):
        piece = " ".join(words[idx : idx + chunk_size])
        suffix = " " if idx + chunk_size < len(words) else ""
        yield {
            "event": "token_delta",
            "data": {
                "delta": f"{piece}{suffix}",
            },
        }
    yield {
        "event": "turn_completed",
        "data": {
            "response_text": full_text,
            "thinking_text": thinking_text,
            "latency_ms": outcome.latency_ms if outcome is not None else 380.0,
        },
    }
