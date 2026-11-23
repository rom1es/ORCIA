"""Prompt Layer Marker Sanitization, History Roles & Adaptive Steps (`Story 26.1`)."""

from __future__ import annotations

import re
from types import MappingProxyType
from typing import Final

from fastapi import Request

ALLOWED_CLIENT_HISTORY_ROLES: frozenset[str] = frozenset({"user", "assistant"})

_LAYER_OR_CONSTITUTIONAL_TAG_RE = re.compile(
    r"\[((?:"
    r"LAYER|CONSTITUTIONAL|ONTOLOGY|HUMAN_PROFILE|ADAPTATION|"
    r"FEDERATED_CONTEXT_FANOUT|CONVERSATIONAL_INTENT|"
    r"SERVER_EVIDENCE_TABLE|TABLE_PREUVES_SERVEUR|"
    r"NO_HUMAN_ANCHOR_WRITE|NO_GATE_SELF_APPROVAL|"
    r"EXPLICIT_PROVENANCE_URI|STALE_WARNING"
    r")(?:[_\s:=-]+[^\]]*)?)\]",
    re.IGNORECASE,
)

_STEP_TEMPLATES_BY_LOCALE: Final[
    MappingProxyType[str, MappingProxyType[str, tuple[tuple[str, str], ...]]]
] = MappingProxyType(
    {
        "fr": MappingProxyType(
            {
                "code": (
                    (
                        "Spécification et cas limites",
                        "Cadrage des entrées/sorties et cas particuliers.",
                    ),
                    (
                        "Conception de l'implémentation",
                        "Structuration du code et choix techniques.",
                    ),
                    ("Vérification et exemple d'usage", "Contrôle de validité et cas de test."),
                ),
                "doc": (
                    (
                        "Extraction des points clés",
                        "Repérage des idées principales et de la structure.",
                    ),
                    (
                        "Croisement avec le contexte de l'espace",
                        "Mise en regard avec le glossaire métier.",
                    ),
                    ("Structuration pédagogique", "Organisation claire de l'explication."),
                ),
                "decision": (
                    ("Critères d'évaluation", "Définition des axes de comparaison pertinents."),
                    (
                        "Analyse des options et points de vigilance",
                        "Pesée des avantages et limites.",
                    ),
                    ("Recommandation argumentée", "Synthèse décisionnelle."),
                ),
                "default": (
                    ("Cadrage de la demande", "Identification des objectifs et du périmètre."),
                    (
                        "Analyse approfondie et sources",
                        "Exploration détaillée des éléments de réponse.",
                    ),
                    ("Consolidation de la réponse", "Mise en forme structurée et synthétique."),
                ),
            }
        ),
        "en": MappingProxyType(
            {
                "code": (
                    (
                        "Specification & edge cases",
                        "Framing inputs, outputs, and boundary conditions.",
                    ),
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
            }
        ),
        "es": MappingProxyType(
            {
                "code": (
                    ("Especificación y casos límite", "Definición de entradas, salidas y bordes."),
                    (
                        "Diseño de la implementación",
                        "Estructuración del código y decisiones técnicas.",
                    ),
                    ("Verificación y ejemplo de uso", "Control de validez y casos de prueba."),
                ),
                "doc": (
                    (
                        "Extracción de puntos clave",
                        "Identificación de ideas principales y estructura.",
                    ),
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
            }
        ),
    }
)

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


def sanitize_prompt_layer_markers(text: str | None) -> str:
    """Escape `[LAYER_*]` and `[CONSTITUTIONAL_*]` delimiter tags in untrusted text."""
    if not text:
        return ""
    return _LAYER_OR_CONSTITUTIONAL_TAG_RE.sub(r"(escaped:\1)", text.strip())


def resolve_request_locale(request: Request | None, explicit_locale: str | None = None) -> str:
    """Resolve UI locale (`fr`, `en`, `es`) from explicit parameter or HTTP `Accept-Language`."""
    raw = (explicit_locale or "").strip().lower()
    if not raw and request is not None:
        raw = str(request.headers.get("accept-language") or "").strip().lower()
    primary = raw.split(",")[0].split(";")[0].strip()
    if primary.startswith("en"):
        return "en"
    if primary.startswith("es"):
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
