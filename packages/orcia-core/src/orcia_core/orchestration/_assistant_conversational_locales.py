"""Localized `fr`/`en` strings for clean conversational Assistant prompts (`Story 30.2`)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConversationalPromptLocale:
    """Natural-language headings and conditional citation rules for live LLM turns."""

    profile_heading: str
    context_heading: str
    intent_heading: str
    ontology_heading: str
    workspace_instructions_heading: str
    user_preferences_heading: str
    folder_notes_heading: str
    runtime_heading: str
    active_pack_tpl: str
    team_hat_tpl: str
    workspace_tpl: str
    user_tpl: str
    evidence_table_heading: str
    evidence_citation_rule: str
    empty_evidence_guard: str


CONVERSATIONAL_LOCALES: dict[str, ConversationalPromptLocale] = {
    "fr": ConversationalPromptLocale(
        profile_heading="Profil utilisateur",
        context_heading="Contexte de travail",
        intent_heading="Demande utilisateur",
        ontology_heading="Contexte métier et glossaire actif",
        workspace_instructions_heading="Instructions de l'espace",
        user_preferences_heading="Préférences utilisateur",
        folder_notes_heading="Notes épinglées du dossier actif",
        runtime_heading="Adaptation de la réponse",
        active_pack_tpl="Pack métier actif : {pack_key}",
        team_hat_tpl="Équipe & rôle : {hat}",
        workspace_tpl="Espace : {workspace}",
        user_tpl="Utilisateur : {user}",
        evidence_table_heading="Sources documentaires et glossaire récupérés :",
        evidence_citation_rule=(
            "- Preuves disponibles : appuie tes affirmations factuelles issues des sources "
            "récupérées ci-dessus sur leurs repères exacts ([S#], [G#], [O#]) sans jamais "
            "inventer de citation absente."
        ),
        empty_evidence_guard=(
            "- Aucune source documentaire ni règle du glossaire de l'espace n'a correspondu "
            "à ce tour. Réponds naturellement à partir de tes connaissances générales ou du fil "
            "de conversation, et n'invente en aucun cas de citations [S#]/[G#]/[O#], d'URI "
            "orcia:// ni d'empreintes sha256:."
        ),
    ),
    "en": ConversationalPromptLocale(
        profile_heading="User profile",
        context_heading="Workspace context",
        intent_heading="User request",
        ontology_heading="Domain context and active glossary",
        workspace_instructions_heading="Workspace instructions",
        user_preferences_heading="User preferences",
        folder_notes_heading="Active folder pinned notes",
        runtime_heading="Response adaptation",
        active_pack_tpl="Active domain pack: {pack_key}",
        team_hat_tpl="Team & role: {hat}",
        workspace_tpl="Workspace: {workspace}",
        user_tpl="User: {user}",
        evidence_table_heading="Retrieved workspace sources & glossary:",
        evidence_citation_rule=(
            "- Grounded citations: anchor factual claims drawn from the retrieved sources above "
            "using their exact tags ([S#], [G#], [O#]) without ever inventing missing tags."
        ),
        empty_evidence_guard=(
            "- No workspace documents or glossary rules matched this turn. Reply naturally "
            "using general reasoning or conversation context, and strictly do NOT invent or "
            "output [S#]/[G#]/[O#] citations, orcia:// URIs, or sha256: digests."
        ),
    ),
}


def get_conversational_locale(locale: str = "fr") -> ConversationalPromptLocale:
    """Return localized `ConversationalPromptLocale` (`en` or `fr`)."""
    norm = (locale or "fr").strip().lower()
    return CONVERSATIONAL_LOCALES["en"] if norm.startswith("en") else CONVERSATIONAL_LOCALES["fr"]
