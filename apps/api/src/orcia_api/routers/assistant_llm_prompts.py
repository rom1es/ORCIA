"""Prompt Assembly & Tool Schema Helpers (`AD-15`, `Story 26.1`)."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from orcia_api.routers._assistant_prompt_sanitization import (
    ALLOWED_CLIENT_HISTORY_ROLES,
    sanitize_prompt_layer_markers,
)
from orcia_api.routers._assistant_prompt_sanitization import (
    detect_adaptive_thinking_steps_for_question as detect_adaptive_thinking_steps_for_question,
)
from orcia_api.routers._assistant_prompt_sanitization import (
    resolve_request_locale as resolve_request_locale,
)
from orcia_core.orchestration.assistant_harness import (
    CONSTITUTIONAL_LAYER_1_TEXT,
    resolve_profile_adaptation,
)
from orcia_core.orchestration.errors import ImmutableHarnessBoundaryError


def _format_user_governance_and_folder_block(
    *,
    response_tone: str | None = None,
    response_format: str | None = None,
    personal_instructions: str | None = None,
    workspace_instructions: str | None = None,
    folder_pinned_notes: str | None = None,
    locale: str = "fr",
) -> str:
    """Build sanitized prompt sections for Layer 4 Workspace, Layer 5 User prefs & Folder Notes."""
    sections: list[str] = []
    is_en = locale.startswith("en")
    safe_ws = sanitize_prompt_layer_markers(workspace_instructions)
    if safe_ws:
        sections.append(f"[LAYER_4_WORKSPACE_INSTRUCTIONS]\n{safe_ws}")
    tone_map = {
        "SYNTHETIC": "Concise & Direct" if is_en else "Synthétique & Direct (Aller à l'essentiel)",
        "BALANCED": "Balanced & Structured" if is_en else "Équilibré & Structuré",
        "DETAILED_CODE": "Detailed & Illustrated" if is_en else "Détaillé & Illustré",
    }
    fmt_map = {
        "BULLETS_SUMMARY": "Key points (Bullet list)" if is_en else "Points clés (Liste à puces)",
        "STRUCTURED_SECTIONS": "Structured sections" if is_en else "Sections structurées",
        "STEP_BY_STEP": "Step-by-step guide" if is_en else "Guide étape par étape",
    }
    user_lines: list[str] = []
    if response_tone and response_tone.upper() in tone_map:
        tone_lbl = "Expected tone" if is_en else "Ton attendu"
        user_lines.append(f"- {tone_lbl} : {tone_map[response_tone.upper()]}")
    if response_format and response_format.upper() in fmt_map:
        fmt_lbl = "Expected format" if is_en else "Format attendu"
        user_lines.append(f"- {fmt_lbl} : {fmt_map[response_format.upper()]}")
    safe_personal = sanitize_prompt_layer_markers(personal_instructions)
    if safe_personal:
        instr_lbl = "Personal instructions" if is_en else "Instructions personnelles"
        user_lines.append(f"- {instr_lbl} : {safe_personal}")
    if user_lines:
        sections.append("[LAYER_5_USER_PREFERENCES]\n" + "\n".join(user_lines))
    safe_notes = sanitize_prompt_layer_markers(folder_pinned_notes)
    if safe_notes:
        sections.append(f"[LAYER_5_ACTIVE_FOLDER_PINNED_NOTES]\n{safe_notes}")
    return ("\n\n" + "\n\n".join(sections)) if sections else ""


def build_assistant_system_instructions(
    *,
    hat: str,
    speed_mode: str,
    requested_tier: str | None = None,
    thinking_effort: str | None = None,
    system_instructions_override: str | None = None,
    allow_system_override: bool = False,
    assembled_5_layers_prompt: str | None = None,
    ontology_concepts_summary: str | None = None,
    response_tone: str | None = None,
    response_format: str | None = None,
    personal_instructions: str | None = None,
    workspace_instructions: str | None = None,
    folder_pinned_notes: str | None = None,
    locale: str = "fr",
) -> str:
    """Assemble immutable Layer 1 + 5-layer `AssistantHarness` + Ontology + Folder Notes prompt."""
    if system_instructions_override and system_instructions_override.strip():
        if not allow_system_override:
            raise ImmutableHarnessBoundaryError(
                detail_override="Layer 1 constitutional harness cannot be overridden."
            )
        return system_instructions_override.strip()

    profile_spec = resolve_profile_adaptation(hat)
    effort = (thinking_effort or "").strip().lower() or (
        "deep"
        if speed_mode == "SPEED_3_DEEP_AUDIT"
        else "balanced"
        if speed_mode == "SPEED_2_AGENT_TOOLS"
        else "fast"
    )
    tier_key = (requested_tier or "medium").strip().lower()

    if locale.startswith("en"):
        tier_guidance = {
            "simple": "Fast Tier: prioritize conciseness, clarity, and immediate actionability.",
            "medium": "Versatile Tier: balance pedagogical clarity, examples, and structure.",
            "complex": "Advanced Reasoning Tier: address domain nuances and trade-offs.",
        }.get(tier_key, "Versatile Tier: balance pedagogical clarity and structure.")
        effort_guidance = (
            "High Thinking Effort (Multi-perspective deep analysis): structure your response in "
            "3 sections: 1) Executive Summary, 2) Risks, compliance & watchpoints, "
            "3) Technical feasibility & recommended action plan."
            if effort == "deep"
            else "Standard Thinking Effort (Balanced — Sources & Skills): organize key points "
            "using workspace context and relevant skills."
            if effort == "balanced"
            else "Fast Thinking Effort: provide a direct, concise, and actionable answer."
        )
    else:
        tier_guidance = {
            "simple": "Palier Rapide : privilégie l'essentiel, la concision et l'immédiateté.",
            "medium": "Palier Polyvalent : équilibre clarté pédagogique, exemples et structure.",
            "complex": "Palier Raisonnement avancé : traite nuances métiers et arbitrages.",
        }.get(tier_key, "Palier Polyvalent : équilibre clarté pédagogique et structure.")
        effort_guidance = (
            "Niveau de réflexion Élevé (Analyse approfondie multi-points de vue) : "
            "structure impérativement ta réponse en 3 volets : "
            "1) Synthèse exécutive, 2) Risques, conformité & points de vigilance, "
            "3) Faisabilité technique & plan d'action recommandé."
            if effort == "deep"
            else "Niveau de réflexion Standard (Équilibré — Sources & Compétences) : "
            "organise ta réponse avec des points clés structurés en mobilisant le contexte "
            "de l'espace de travail et les compétences mentionnées."
            if effort == "balanced"
            else "Niveau de réflexion Bas (Standard — Rapide et efficace) : "
            "réponds de manière directe, synthétique et immédiatement actionnable, sans détour."
        )

    layers_block = (
        assembled_5_layers_prompt.strip()
        if assembled_5_layers_prompt and assembled_5_layers_prompt.strip()
        else (
            f"{CONSTITUTIONAL_LAYER_1_TEXT}\n\n"
            f"[HUMAN_PROFILE_ADAPTATION_LAYER_3]\n"
            f"Registre : {profile_spec.register_label}\n"
            f"Indicateurs prioritaires : {', '.join(profile_spec.highlighted_indicators)}"
        )
    )
    ontology_block = (
        f"\n[ONTOLOGY_L1_L4_CONTEXT]\n{sanitize_prompt_layer_markers(ontology_concepts_summary)}"
        if ontology_concepts_summary and ontology_concepts_summary.strip()
        else ""
    )
    custom_block = _format_user_governance_and_folder_block(
        response_tone=response_tone,
        response_format=response_format,
        personal_instructions=personal_instructions,
        workspace_instructions=workspace_instructions,
        folder_pinned_notes=folder_pinned_notes,
        locale=locale,
    )
    return (
        f"{layers_block}{ontology_block}{custom_block}\n\n"
        f"[ADAPTATION_RUNTIME_METADATA]\n"
        f"- Active Hat (Casquette): {hat} | Speed Mode: {speed_mode}\n"
        f"- {tier_guidance}\n"
        f"- {effort_guidance}\n"
        "- Format your answer in clean Markdown (headings, bullet points, fenced code blocks with "
        "language tags when showing code).\n"
        "- CRITICAL LANGUAGE RULE: Respond in the exact same language as the "
        "user's message (unless the user explicitly asks to translate or answer in another "
        "language). Do NOT translate technical identifiers or user-supplied terms arbitrarily."
    )


def resolve_5_layers_and_ontology_from_request(
    request: Request,
    *,
    workspace_id: str,
    user_id: str,
    hat: str,
) -> tuple[str | None, str | None]:
    """Read assembled 5-layer prompt and active L1-L4 Ontology concepts from domain services."""
    assembled_text: str | None = None
    ontology_summary: str | None = None
    try:
        from orcia_api.dependencies import get_assistant_three_speed_router_service

        router_svc = get_assistant_three_speed_router_service(request)
        cached = router_svc.get_or_assemble_cached_prompt(
            workspace_id=workspace_id, user_id=user_id, hat=hat
        )
        assembled_text = cached.assembled_prompt_text
    except Exception as exc:
        from orcia_core.observability.logging import get_logger

        get_logger("orcia.assistant.llm").warning(
            "assistant_5_layer_prompt_resolution_fallback", error_type=type(exc).__name__
        )
    try:
        from orcia_api.dependencies import get_ontology_and_rag_services

        ont_svc, _, _ = get_ontology_and_rag_services(request)
        concepts = getattr(ont_svc, "concepts", ())
        lines = [
            f"- [{c.level}] {c.canonical_term}: {c.definition_text}"
            for c in list(concepts)[:8]
            if getattr(c, "snapshot_branch_status", "ACTIVE") == "ACTIVE"
        ]
        if lines:
            ontology_summary = "\n".join(lines)
    except Exception as exc:
        from orcia_core.observability.logging import get_logger

        get_logger("orcia.assistant.llm").warning(
            "assistant_ontology_l1_l4_resolution_fallback", error_type=type(exc).__name__
        )
    return assembled_text, ontology_summary


def build_workspace_tools_schema(request: Request | None, speed_mode: str) -> list[dict[str, Any]]:
    """Build OpenAI/Anthropic JSON Schema `tools` list for `SPEED_2_AGENT_TOOLS` / `SPEED_3`."""
    if speed_mode not in ("SPEED_2_AGENT_TOOLS", "SPEED_3_DEEP_AUDIT"):
        return []
    tools: list[dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "query_workspace_knowledge_and_glossary",
                "description": "Search workspace documents, L1-L4 ontology concepts, and sources.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Search query"}},
                    "required": ["query"],
                },
            },
        }
    ]
    if request is not None and hasattr(request, "app"):
        ag_svc = getattr(request.app.state, "agents_and_skills_service", None)
        if ag_svc is not None:
            for sk in list(getattr(ag_svc, "skills", ()))[:10]:
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": f"skill_{sk.slug.replace('-', '_')}",
                            "description": f"{sk.name}: {sk.objective}",
                            "parameters": {
                                "type": "object",
                                "properties": {"input_text": {"type": "string"}},
                                "required": ["input_text"],
                            },
                        },
                    }
                )
    return tools


def build_multi_turn_messages(
    *,
    system_msg: str,
    user_prompt: str,
    conversation_history: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build sanitized `[system, *history, user]` restricting roles to `user|assistant`."""
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_msg}]
    for item in conversation_history or ():
        if isinstance(item, dict):
            role = str(item.get("role") or "user").strip().lower()
            content = sanitize_prompt_layer_markers(str(item.get("content") or ""))
            if role in ALLOWED_CLIENT_HISTORY_ROLES and content:
                msg: dict[str, Any] = {"role": role, "content": content}
                if item.get("name"):
                    msg["name"] = str(item["name"])
                messages.append(msg)
    messages.append({"role": "user", "content": sanitize_prompt_layer_markers(user_prompt)})
    return messages
