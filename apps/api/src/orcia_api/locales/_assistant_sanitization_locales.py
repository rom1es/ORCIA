"""Localized adaptive thinking step templates and intent regexes (`Story 26.1`, `Story 27.7`)."""

from __future__ import annotations

import re
from types import MappingProxyType
from typing import Final

STEP_TEMPLATES_BY_LOCALE: Final[
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
                    (
                        "Cruce con el contexto del espacio",
                        "Alineación con el glosario de negocio.",
                    ),
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

CODE_INTENT_RE = re.compile(
    r"\b(code|fonction|function|python|sql|bug|script|algorithme|algorithm|api|test|react|"
    r"typescript|class|implement|implémenter|refactor|código|función)\b",
    re.IGNORECASE,
)
DOC_INTENT_RE = re.compile(
    r"\b(explique|explain|résume|summarize|summary|document|contrat|contract|texte|text|"
    r"synthèse|rapport|report|dossier|explica|resumen)\b",
    re.IGNORECASE,
)
DECISION_INTENT_RE = re.compile(
    r"\b(choisir|choose|comparer|compare|option|avantage|advantage|risque|risk|pourquoi|why|"
    r"quel|which|arbitrage|trade-off|tradeoff|versus|vs|elegir|comparar)\b",
    re.IGNORECASE,
)
