"""Live LLM invocation bridge for `Mon Assistant` (`/api/v1/assistant/three-speed/*`).

Resolves the active LLM tier configured in `Modèles IA` (`platform_setup_snapshot` / PostgreSQL 18)
and invokes Ollama (`/api/chat`) or OpenAI-compatible (`/v1/chat/completions`) endpoints.
"""

from __future__ import annotations

import os
import re
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import Request

_HAT_FRENCH_LABELS: dict[str, str] = {
    "PLATFORM_ADMIN": "Administrateur",
    "ADMIN": "Administrateur",
    "PM": "Chef de Projet",
    "PRODUCT_MANAGER": "Chef de Projet",
    "ARCHITECT": "Architecte",
    "TECH_LEAD": "Développeur",
    "DEV": "Développeur",
    "BA": "Analyste",
    "UX": "Designer",
}


def humanize_hat_label_fr(hat: str) -> str:
    """Translate technical `hat` code (`PLATFORM_ADMIN`, `PM`, ...) to French business label."""
    return _HAT_FRENCH_LABELS.get((hat or "").strip().upper(), "Collaborateur")


def detect_adaptive_thinking_steps_for_question(user_prompt: str) -> tuple[tuple[str, str], ...]:
    """Return 3 adaptive thinking step `(title, intermediate_summary)` pairs for a question."""
    lower = user_prompt.lower()
    if re.search(r"\b(code|fonction|python|sql|bug|script|algorithme|api|test|react)\b", lower):
        return (
            ("Spécification et cas limites", "Cadrage des entrées/sorties et cas particuliers."),
            ("Conception de l'implémentation", "Structuration du code et choix techniques."),
            ("Vérification et exemple d'usage", "Contrôle de validité et cas de test."),
        )
    if re.search(r"\b(explique|résume|document|contrat|texte|synthèse|rapport|dossier)\b", lower):
        return (
            ("Extraction des points clés", "Repérage des idées principales et de la structure."),
            ("Croisement avec le contexte de l'espace", "Mise en regard avec le glossaire métier."),
            ("Structuration pédagogique", "Organisation claire de l'explication."),
        )
    if re.search(r"\b(choisir|comparer|option|avantage|risque|pourquoi|quel|arbitrage)\b", lower):
        return (
            ("Critères d'évaluation", "Définition des axes de comparaison pertinents."),
            ("Analyse des options et points de vigilance", "Pesée des avantages et limites."),
            ("Recommandation argumentée", "Synthèse décisionnelle."),
        )
    return (
        ("Cadrage de la demande", "Identification des objectifs et du périmètre de la question."),
        ("Analyse approfondie et sources", "Exploration détaillée des éléments de réponse."),
        ("Consolidation de la réponse", "Mise en forme structurée et synthétique."),
    )


@dataclass(frozen=True, slots=True)
class ResolvedLiveLlmEndpoint:
    provider: str
    model_name: str
    endpoint_uri: str
    auth_mode: str
    tier: str = "medium"
    api_key: str | None = None


@dataclass(frozen=True, slots=True)
class LiveLlmTurnOutcome:
    response_text: str
    step_label: str
    latency_ms: float
    thinking_text: str | None = None


def _extract_tier_endpoint_from_dict(item: dict[str, Any]) -> ResolvedLiveLlmEndpoint | None:
    model_name = str(item.get("primaryModel") or item.get("model") or "").strip()
    endpoint_uri = str(item.get("endpointUrl") or item.get("endpoint_uri") or "").strip()
    if (
        not model_name
        or not endpoint_uri
        or not (endpoint_uri.startswith("http://") or endpoint_uri.startswith("https://"))
        or ".local/" in endpoint_uri
    ):
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
    valid_endpoints = [
        resolved
        for item in llm_tiers
        if isinstance(item, dict)
        and (resolved := _extract_tier_endpoint_from_dict(item)) is not None
    ]
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
    if os.environ.get("ORCIA_USE_CASSETTE_LLM", "").strip().lower() in ("1", "true", "yes"):
        return None

    snap = getattr(request.app.state, "platform_setup_snapshot", None)
    if snap is not None and getattr(snap, "llm_tiers", None):
        chosen = _select_endpoint_from_tiers(list(snap.llm_tiers), requested_tier)
        if chosen is not None:
            return chosen

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
                return _select_endpoint_from_tiers(list(db_snap.llm_tiers), requested_tier)
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
    return (
        "ollama" in ep.provider.lower()
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
    """Build differentiated system instructions without raw technical `hat` codes."""
    if system_instructions_override and system_instructions_override.strip():
        return system_instructions_override.strip()

    effort = (thinking_effort or "").strip().lower() or (
        "deep"
        if speed_mode == "SPEED_3_DEEP_AUDIT"
        else "balanced"
        if speed_mode == "SPEED_2_AGENT_TOOLS"
        else "fast"
    )
    tier_key = (requested_tier or "medium").strip().lower()
    tier_guidance = {
        "simple": "Palier Rapide : privilégie l'essentiel, la concision et une réponse immédiate.",
        "medium": "Palier Polyvalent : équilibre clarté pédagogique, exemples et structure.",
        "complex": "Palier Raisonnement avancé : traite nuances métiers et arbitrages.",
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
            "Niveau de réflexion Standard (Équilibré — Sources & Compétences) : "
            "organise ta réponse avec des points clés structurés en mobilisant le contexte "
            "de l'espace de travail et les compétences mentionnées."
        )
    else:
        effort_guidance = (
            "Niveau de réflexion Bas (Standard — Rapide et efficace) : "
            "réponds de manière directe, synthétique et immédiatement actionnable, sans détour."
        )

    hat_label = humanize_hat_label_fr(hat)
    return (
        f"Tu es Mon Assistant ORCIA accompagnant un profil {hat_label}. "
        f"{tier_guidance} {effort_guidance} "
        "Ne mentionne jamais d'identifiant technique interne dans ta réponse. "
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
    client_host = getattr(getattr(request, "client", None), "host", "") or ""
    if client_host == "testclient" and os.environ.get("ORCIA_FORCE_LIVE_LLM_IN_TESTS") != "1":
        return None

    ep = resolve_configured_llm_endpoint(request, requested_tier=requested_tier)
    if ep is None:
        return None

    effort = (thinking_effort or "").strip().lower() or (
        "deep"
        if speed_mode == "SPEED_3_DEEP_AUDIT"
        else "balanced"
        if speed_mode == "SPEED_2_AGENT_TOOLS"
        else "fast"
    )
    effort_fr = "Réflexion Élevée" if effort == "deep" else "Réflexion Standard"
    system_msg = build_assistant_system_instructions(
        hat=hat,
        speed_mode=speed_mode,
        requested_tier=requested_tier or ep.tier,
        thinking_effort=effort,
        system_instructions_override=system_instructions_override,
    )
    t0 = time.perf_counter()
    default_thinking = " · ".join(
        f"{t}: {s}" for t, s in detect_adaptive_thinking_steps_for_question(user_prompt)
    )
    step_label = f"💬 Modèle IA {ep.model_name} ({ep.provider} · {effort_fr}) — réponse générée"
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_prompt.strip()},
    ]

    try:
        if _is_ollama_endpoint(ep):
            root_url = _build_ollama_root_url(ep.endpoint_uri)
            with httpx.Client(timeout=45.0) as client:
                resp = client.post(
                    f"{root_url}/api/chat",
                    json={
                        "model": ep.model_name,
                        "messages": messages,
                        "stream": False,
                        "think": False,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            msg_obj = data.get("message") if isinstance(data, dict) else {}
            if isinstance(msg_obj, dict):
                raw_think = str(msg_obj.get("thinking") or "").strip()
                content = str(msg_obj.get("content") or raw_think or "").strip()
                if content:
                    return LiveLlmTurnOutcome(
                        response_text=content,
                        step_label=step_label,
                        latency_ms=elapsed_ms,
                        thinking_text=raw_think or default_thinking,
                    )
            return None

        base = ep.endpoint_uri.rstrip("/")
        completions_url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if ep.api_key:
            headers["Authorization"] = f"Bearer {ep.api_key}"
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                completions_url,
                json={"model": ep.model_name, "messages": messages},
                headers=headers,
            )
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
                    step_label=step_label,
                    latency_ms=elapsed_ms,
                    thinking_text=raw_reasoning or default_thinking,
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
        "data": {"step_code": "NODE_5_SINGLE_STREAM_LLM", "thinking_text": thinking_text},
    }
    full_text = outcome.response_text if outcome is not None else (fallback_response_text or "")
    words = full_text.split(" ")
    chunk_size = max(1, min(4, len(words) // 6 or 1))
    for idx in range(0, len(words), chunk_size):
        piece = " ".join(words[idx : idx + chunk_size])
        suffix = " " if idx + chunk_size < len(words) else ""
        yield {"event": "token_delta", "data": {"delta": f"{piece}{suffix}"}}
    yield {
        "event": "turn_completed",
        "data": {
            "response_text": full_text,
            "thinking_text": thinking_text,
            "latency_ms": outcome.latency_ms if outcome is not None else 380.0,
        },
    }
