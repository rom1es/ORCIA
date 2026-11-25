"""Localized `fr`/`en` prompt dictionaries for `AssistantPromptBuilder` (`AD-15`, `H-31`)."""

from __future__ import annotations

from dataclasses import dataclass

CONSTITUTIONAL_LAYER_1_TEXT_FR: str = (
    "[CONSTITUTIONAL_IMMUTABLE_LAYER_1]\n"
    "1. [NO_HUMAN_ANCHOR_WRITE]: Interdiction absolue de rédiger, pré-remplir ou modifier toute "
    "section marquée `human_authored_required: true` (Human-Led Anchor Card). En cas de demande "
    "de rédaction à la place de l'humain, refuser poliment et engager un questionnement "
    "socratique.\n"
    "2. [NO_GATE_SELF_APPROVAL]: Interdiction absolue d'approuver ou de contourner une Gate "
    "Déterministe, Agentique ou Humaine.\n"
    "3. [EXPLICIT_PROVENANCE_URI]: Toute affirmation factuelle doit citer son URI canonique "
    "`orcia://` et son condensat `sha256:`."
)

CONSTITUTIONAL_LAYER_1_TEXT_EN: str = (
    "[CONSTITUTIONAL_IMMUTABLE_LAYER_1]\n"
    "1. [NO_HUMAN_ANCHOR_WRITE]: Strict prohibition against drafting, pre-filling, or modifying "
    "any section marked `human_authored_required: true` (Human-Led Anchor Card). When asked to "
    "write on the human's behalf, politely refuse and initiate Socratic questioning.\n"
    "2. [NO_GATE_SELF_APPROVAL]: Strict prohibition against approving or bypassing a "
    "Deterministic, Agentic, or Human Gate.\n"
    "3. [EXPLICIT_PROVENANCE_URI]: Every factual claim must cite its canonical `orcia://` URI "
    "and `sha256:` digest."
)


@dataclass(frozen=True, slots=True)
class PromptLocaleBundle:
    """Complete locale-specific strings for all 5 prompt layers and runtime adaptation."""

    constitutional_layer_1: str
    no_ontology_concepts: str
    base_axiom: str
    ontology_header: str
    concepts_header: str
    axioms_header: str
    archetype_label: str
    register_label: str
    indicators_label: str
    prefix_label: str
    team_instructions_label: str
    empty_fanout_tpl: str
    no_blueprint: str
    blueprint_tpl: str
    workspace_label: str
    intent_label: str
    user_message_label: str
    active_hat_tpl: str
    tone_label: str
    format_label: str
    personal_instructions_label: str
    tone_map: dict[str, str]
    format_map: dict[str, str]
    tier_map: dict[str, str]
    tier_default: str
    effort_deep: str
    effort_balanced: str
    effort_fast: str
    markdown_rule: str
    language_rule: str
    pack_layer_summary: str
    default_sources_label: str
    recommended_agents_label: str
    workspace_instructions_label: str
    layer_labels: tuple[str, str, str, str, str]
    global_scope_label: str
    active_workspace_fallback_label: str
    active_user_fallback_label: str
    speed_mode_labels: dict[str, str]
    hat_labels: dict[str, str]


PROMPT_LOCALES: dict[str, PromptLocaleBundle] = {
    "fr": PromptLocaleBundle(
        constitutional_layer_1=CONSTITUTIONAL_LAYER_1_TEXT_FR,
        no_ontology_concepts="- Aucun concept ontologique spécifique actif.",
        base_axiom="- Axiome de base : Intégrité des références `orcia://`.",
        ontology_header="[ONTOLOGY_AND_AXIOMS_LAYER_2]",
        concepts_header="Concepts Ontologiques Actifs :",
        axioms_header="Axiomes Formels :",
        archetype_label="Archetype",
        register_label="Registre",
        indicators_label="Indicateurs prioritaires",
        prefix_label="Préfixe attendu",
        team_instructions_label="Instructions Équipe",
        empty_fanout_tpl="- Périmètre Workspace `{workspace_id}` (aucune tranche externe).",
        no_blueprint="Aucun blueprint de workflow requis.",
        blueprint_tpl="Blueprint Workflow: {workflow_uri} ({title})",
        workspace_label="Workspace",
        intent_label="Intention classifiée",
        user_message_label="Message utilisateur",
        active_hat_tpl="- Casquette active : {hat} | Mode de vitesse : {speed_mode}",
        tone_label="Ton attendu",
        format_label="Format attendu",
        personal_instructions_label="Instructions personnelles",
        tone_map={
            "SYNTHETIC": "Synthétique & Direct (Aller à l'essentiel)",
            "BALANCED": "Équilibré & Structuré",
            "DETAILED_CODE": "Détaillé & Illustré",
        },
        format_map={
            "BULLETS_SUMMARY": "Points clés (Liste à puces)",
            "STRUCTURED_SECTIONS": "Sections structurées",
            "STEP_BY_STEP": "Guide étape par étape",
        },
        tier_map={
            "simple": "Palier Rapide : privilégie l'essentiel, la concision et l'immédiateté.",
            "medium": "Palier Polyvalent : équilibre clarté pédagogique, exemples et structure.",
            "complex": "Palier Raisonnement avancé : traite nuances métiers et arbitrages.",
        },
        tier_default="Palier Polyvalent : équilibre clarté pédagogique et structure.",
        effort_deep=(
            "Niveau de réflexion Élevé (Analyse approfondie multi-points de vue) : "
            "structure impérativement ta réponse en 3 volets : "
            "1) Synthèse exécutive, 2) Risques, conformité & points de vigilance, "
            "3) Faisabilité technique & plan d'action recommandé."
        ),
        effort_balanced=(
            "Niveau de réflexion Standard (Équilibré — Sources & Compétences) : "
            "organise ta réponse avec des points clés structurés en mobilisant le contexte "
            "de l'espace de travail et les compétences mentionnées."
        ),
        effort_fast=(
            "Niveau de réflexion Bas (Standard — Rapide et efficace) : "
            "réponds de manière directe, synthétique et immédiatement actionnable, sans détour."
        ),
        markdown_rule=(
            "- Formate ta réponse en Markdown propre (titres, listes à puces, blocs de code "
            "clôturés avec balise de langage)."
        ),
        language_rule=(
            "- RÈGLE DE LANGUE IMPÉRATIVE : L'interface est en français. Réponds en français "
            "et rédige en français tous les fichiers, artefacts, titres et commentaires générés "
            "par défaut (sauf si l'utilisateur écrit explicitement dans une autre langue ou "
            "demande une traduction). Ne traduis pas arbitrairement les identifiants techniques "
            "ni les termes exacts fournis par l'utilisateur."
        ),
        pack_layer_summary="Conventions de domaine et axiomes N1–N3 chargés depuis le Pack actif.",
        default_sources_label="Sources par défaut",
        recommended_agents_label="Agents recommandés",
        workspace_instructions_label="Instructions Espace",
        layer_labels=(
            "1. 🔒 Constitution (AssistantHarness Socle)",
            "2. Pack Métier & Ontologie",
            "3. Équipe & Casquette",
            "4. Espace & Glossaire",
            "5. Utilisateur (Préférences & Continuité Dossier)",
        ),
        global_scope_label="Tous mes espaces",
        active_workspace_fallback_label="Espace actif",
        active_user_fallback_label="Utilisateur actif",
        speed_mode_labels={
            "SPEED_1_FAST": "Réponse rapide",
            "SPEED_2_AGENT_TOOLS": "Standard (sources et outils de l'espace)",
            "SPEED_3_DEEP_AUDIT": "Analyse approfondie",
        },
        hat_labels={
            "EXECUTIVE": "Direction",
            "PM": "Chef de Projet",
            "ARCHITECT": "Architecte",
            "TECH_LEAD": "Référent Technique",
            "TEAM_LEAD": "Responsable d'équipe",
            "DEVELOPER": "Développeur",
            "SECOPS": "SecOps",
            "CONTRIBUTOR": "Contributeur",
            "PLATFORM_ADMIN": "Administrateur",
        },
    ),
    "en": PromptLocaleBundle(
        constitutional_layer_1=CONSTITUTIONAL_LAYER_1_TEXT_EN,
        no_ontology_concepts="- No specific active ontology concept.",
        base_axiom="- Base axiom: Integrity of `orcia://` references.",
        ontology_header="[ONTOLOGY_AND_AXIOMS_LAYER_2]",
        concepts_header="Active Ontology Concepts:",
        axioms_header="Formal Axioms:",
        archetype_label="Archetype",
        register_label="Register",
        indicators_label="Priority indicators",
        prefix_label="Expected prefix",
        team_instructions_label="Team instructions",
        empty_fanout_tpl="- Workspace scope `{workspace_id}` (no external context slices).",
        no_blueprint="No workflow blueprint required.",
        blueprint_tpl="Workflow Blueprint: {workflow_uri} ({title})",
        workspace_label="Workspace",
        intent_label="Classified intent",
        user_message_label="User message",
        active_hat_tpl="- Active Hat: {hat} | Speed Mode: {speed_mode}",
        tone_label="Expected tone",
        format_label="Expected format",
        personal_instructions_label="Personal instructions",
        tone_map={
            "SYNTHETIC": "Concise & Direct",
            "BALANCED": "Balanced & Structured",
            "DETAILED_CODE": "Detailed & Illustrated",
        },
        format_map={
            "BULLETS_SUMMARY": "Key points (Bullet list)",
            "STRUCTURED_SECTIONS": "Structured sections",
            "STEP_BY_STEP": "Step-by-step guide",
        },
        tier_map={
            "simple": "Fast Tier: prioritize conciseness, clarity, and immediate actionability.",
            "medium": "Versatile Tier: balance pedagogical clarity, examples, and structure.",
            "complex": "Advanced Reasoning Tier: address domain nuances and trade-offs.",
        },
        tier_default="Versatile Tier: balance pedagogical clarity and structure.",
        effort_deep=(
            "High Thinking Effort (Multi-perspective deep analysis): structure your response in "
            "3 sections: 1) Executive Summary, 2) Risks, compliance & watchpoints, "
            "3) Technical feasibility & recommended action plan."
        ),
        effort_balanced=(
            "Standard Thinking Effort (Balanced — Sources & Skills): organize key points "
            "using workspace context and relevant skills."
        ),
        effort_fast="Fast Thinking Effort: provide a direct, concise, and actionable answer.",
        markdown_rule=(
            "- Format your answer in clean Markdown (headings, bullet points, fenced code blocks "
            "with language tags when showing code)."
        ),
        language_rule=(
            "- CRITICAL LANGUAGE RULE: Respond in the exact same language as the user's message "
            "when they explicitly write in or request another language, and default to English for "
            "responses and generated files/artifacts when the UI locale is English. "
            "Do NOT translate technical identifiers or user-supplied terms arbitrarily."
        ),
        pack_layer_summary=(
            "Domain conventions and N1-N3 axioms loaded from the active domain pack."
        ),
        default_sources_label="Default sources",
        recommended_agents_label="Recommended agents",
        workspace_instructions_label="Workspace instructions",
        layer_labels=(
            "1. 🔒 Constitution (AssistantHarness Core)",
            "2. Domain Pack & Ontology",
            "3. Team & Hat",
            "4. Workspace & Glossary",
            "5. User (Preferences & Folder Continuity)",
        ),
        global_scope_label="All my spaces",
        active_workspace_fallback_label="Active space",
        active_user_fallback_label="Active user",
        speed_mode_labels={
            "SPEED_1_FAST": "Fast response",
            "SPEED_2_AGENT_TOOLS": "Standard (workspace sources and tools)",
            "SPEED_3_DEEP_AUDIT": "In-depth analysis",
        },
        hat_labels={
            "EXECUTIVE": "Executive",
            "PM": "Product Manager",
            "ARCHITECT": "Architect",
            "TECH_LEAD": "Technical Lead",
            "TEAM_LEAD": "Team Lead",
            "DEVELOPER": "Developer",
            "SECOPS": "SecOps",
            "CONTRIBUTOR": "Contributor",
            "PLATFORM_ADMIN": "Platform Administrator",
        },
    ),
}


def get_prompt_locale_bundle(locale: str = "fr") -> PromptLocaleBundle:
    """Return the localized `PromptLocaleBundle` (`en` or `fr`)."""
    norm = (locale or "fr").strip().lower()
    return PROMPT_LOCALES["en"] if norm.startswith("en") else PROMPT_LOCALES["fr"]
