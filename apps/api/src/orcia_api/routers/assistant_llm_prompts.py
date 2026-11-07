"""Prompt Assembly, Multilingual Thinking Steps & Tool Schema Helpers (`AD-15`, `AD-19`).

Implements:
- `resolve_request_locale` & `detect_adaptive_thinking_steps_for_question` (`fr`, `en`, `es`).
- `build_assistant_system_instructions` & `_resolve_5_layers_and_ontology_from_request`:
  integrates the 5-layer `AssistantHarness` prompt (`AssistantThreeSpeedRouterService`) and
  `OntologyGovernanceService` (`L1–L4`) with `resolve_profile_adaptation(hat)` (zero hardcoded
  `hat` dictionary in the API router).
- `build_workspace_tools_schema` & `build_multi_turn_messages`: multi-turn `conversation_history`
  and governed JSON Schema `tools` for `SPEED_2_AGENT_TOOLS` and `SPEED_3_DEEP_AUDIT`.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import Request

from orcia_core.orchestration.assistant_harness import (
    CONSTITUTIONAL_LAYER_1_TEXT,
    resolve_profile_adaptation,
)

_STEP_TEMPLATES_BY_LOCALE: dict[str, dict[str, tuple[tuple[str, str], ...]]] = {
    "fr": {
        "code": (
            ("Spécification et cas limites", "Cadrage des entrées/sorties et cas particuliers."),
            ("Conception de l'implémentation", "Structuration du code et choix techniques."),
            ("Vérification et exemple d'usage", "Contrôle de validité et cas de test."),
        ),
        "doc": (
            ("Extraction des points clés", "Repérage des idées principales et de la structure."),
            ("Croisement avec le contexte de l'espace", "Mise en regard avec le glossaire métier."),
            ("Structuration pédagogique", "Organisation claire de l'explication."),
        ),
        "decision": (
            ("Critères d'évaluation", "Définition des axes de comparaison pertinents."),
            ("Analyse des options et points de vigilance", "Pesée des avantages et limites."),
            ("Recommandation argumentée", "Synthèse décisionnelle."),
        ),
        "default": (
            ("Cadrage de la demande", "Identification des objectifs et du périmètre."),
            ("Analyse approfondie et sources", "Exploration détaillée des éléments de réponse."),
            ("Consolidation de la réponse", "Mise en forme structurée et synthétique."),
        ),
    },
    "en": {
        "code": (
            ("Specification & edge cases", "Framing inputs, outputs, and boundary conditions."),
            ("Implementation design", "Structuring clean code and technical choices."),
            ("Verification & usage example", "Validating correctness and test cases."),
        ),
        "doc": (
            ("Key points extraction", "Identifying core ideas and document structure."),
            ("Workspace context cross-check", "Aligning with domain glossary and rules."),
            ("Clear synthesis", "Organizing a pedagogical and structured explanation."),
        ),
        "decision": (
            ("Evaluation criteria", "Defining relevant comparison axes."),
            ("Trade-off & risk analysis", "Weighing pros, cons, and watchpoints."),
            ("Grounded recommendation", "Formulating an actionable decision synthesis."),
        ),
        "default": (
            ("Request framing", "Identifying objectives and scope of the question."),
            ("In-depth source analysis", "Exploring relevant context and evidence."),
            ("Response consolidation", "Structuring a clear and concise answer."),
        ),
    },
    "es": {
        "code": (
            ("Especificación y casos límite", "Definición de entradas, salidas y bordes."),
            ("Diseño de la implementación", "Estructuración del código y decisiones técnicas."),
            ("Verificación y ejemplo de uso", "Control de validez y casos de prueba."),
        ),
        "doc": (
            ("Extracción de puntos clave", "Identificación de ideas principales y estructura."),
            ("Cruce con el contexto del espacio", "Alineación con el glosario de negocio."),
            ("Síntesis estructurada", "Organización clara de la explicación."),
        ),
        "decision": (
            ("Criterios de evaluación", "Definición de ejes de comparación."),
            ("Análisis de opciones y riesgos", "Evaluación de ventajas y límites."),
            ("Recomendación fundamentada", "Síntesis para la toma de decisiones."),
        ),
        "default": (
            ("Encuadre de la solicitud", "Identificación de objetivos y alcance."),
            ("Análisis profundo y fuentes", "Exploración detallada de elementos."),
            ("Consolidación de la respuesta", "Formato estructurado y sintético."),
        ),
    },
}

_CODE_INTENT_RE = re.compile(
    r"\b(code|fonction|function|python|sql|bug|script|algorithme|algorithm|api|test|react|"
    r"typescript|class|implement|implémenter|refactor|código|función)\b",
    re.IGNORECASE,
)
_DOC_INTENT_RE = re.compile(
    r"\b(explique|explain|résume|summarize|summary|document|contrat|contract|texte|text|"
    r"synthèse|rapport|report|dossier|explica|resumen)\b",
    re.IGNORECASE,
)
_DECISION_INTENT_RE = re.compile(
    r"\b(choisir|choose|comparer|compare|option|avantage|advantage|risque|risk|pourquoi|why|"
    r"quel|which|arbitrage|trade-off|tradeoff|versus|vs|elegir|comparar)\b",
    re.IGNORECASE,
)


def resolve_request_locale(request: Request | None, explicit_locale: str | None = None) -> str:
    """Resolve UI locale (`fr`, `en`, `es`) from explicit parameter or HTTP `Accept-Language`."""
    raw = (explicit_locale or "").strip().lower()
    if not raw and request is not None:
        raw = str(request.headers.get("accept-language") or "").strip().lower()
    if raw.startswith("en") or ",en" in raw:
        return "en"
    if raw.startswith("es") or ",es" in raw:
        return "es"
    return "fr"


def detect_adaptive_thinking_steps_for_question(
    user_prompt: str,
    *,
    locale: str = "fr",
) -> tuple[tuple[str, str], ...]:
    """Return 3 adaptive thinking step `(title, intermediate_summary)` pairs in `locale`."""
    lang = (
        locale
        if locale in _STEP_TEMPLATES_BY_LOCALE
        else ("en" if locale.startswith("en") else "fr")
    )
    templates = _STEP_TEMPLATES_BY_LOCALE[lang]
    if _CODE_INTENT_RE.search(user_prompt):
        return templates["code"]
    if _DOC_INTENT_RE.search(user_prompt):
        return templates["doc"]
    if _DECISION_INTENT_RE.search(user_prompt):
        return templates["decision"]
    return templates["default"]


def build_assistant_system_instructions(
    *,
    hat: str,
    speed_mode: str,
    requested_tier: str | None = None,
    thinking_effort: str | None = None,
    system_instructions_override: str | None = None,
    assembled_5_layers_prompt: str | None = None,
    ontology_concepts_summary: str | None = None,
    locale: str = "fr",
) -> str:
    """Assemble the 5-layer `AssistantHarness` + Ontology `L1–L4` system prompt (`AD-15`)."""
    if system_instructions_override and system_instructions_override.strip():
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
        f"\n[ONTOLOGY_L1_L4_CONTEXT]\n{ontology_concepts_summary.strip()}"
        if ontology_concepts_summary and ontology_concepts_summary.strip()
        else ""
    )
    return (
        f"{layers_block}{ontology_block}\n\n"
        f"[COGNITIVE_ROUTING_DIRECTIVES]\n"
        f"Profil adaptatif : {profile_spec.register_label}. "
        f"{tier_guidance} {effort_guidance}\n"
        "Ne mentionne jamais d'identifiant technique interne dans ta réponse. "
        "Respond in the exact same language as the user's message "
        "(unless the user explicitly asks for another language)."
    )


def resolve_5_layers_and_ontology_from_request(
    request: Request | None,
    *,
    workspace_id: str,
    user_id: str,
    hat: str,
) -> tuple[str | None, str | None]:
    """Fetch cached 5-layer prompt (`AssistantThreeSpeedRouterService`) and Ontology `L1–L4`."""
    if request is None or not hasattr(request, "app"):
        return None, None
    assembled_text: str | None = None
    ontology_summary: str | None = None
    try:
        router_svc = getattr(request.app.state, "assistant_three_speed_router_service", None)
        if router_svc is None:
            from orcia_api.dependencies import get_assistant_three_speed_router_service

            router_svc = get_assistant_three_speed_router_service(request)
        cached = router_svc.get_or_assemble_cached_prompt(
            workspace_id=workspace_id,
            user_id=user_id,
            hat=hat,
        )
        assembled_text = cached.assembled_prompt_text
    except Exception as exc:
        from orcia_core.observability.logging import get_logger

        get_logger("orcia.assistant.llm").warning(
            "assistant_5_layer_prompt_resolution_fallback", error_type=type(exc).__name__
        )
        assembled_text = None

    try:
        from orcia_api.dependencies import get_ontology_and_rag_services

        ont_svc, _, _ = get_ontology_and_rag_services(request)
        concepts = getattr(ont_svc, "concepts", ())
        if concepts:
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
        ontology_summary = None
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
                "description": (
                    "Search workspace documents, L1-L4 ontology concepts, and Jira/Git sources."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                    },
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
    """Build `[system, *conversation_history, user]` message array."""
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_msg}]
    for item in conversation_history or ():
        if isinstance(item, dict):
            role = str(item.get("role") or "user").strip().lower()
            content = str(item.get("content") or "").strip()
            if role in ("user", "assistant", "tool") and content:
                msg: dict[str, Any] = {"role": role, "content": content}
                if item.get("name"):
                    msg["name"] = str(item["name"])
                if item.get("tool_call_id"):
                    msg["tool_call_id"] = str(item["tool_call_id"])
                messages.append(msg)
    messages.append({"role": "user", "content": user_prompt.strip()})
    return messages
