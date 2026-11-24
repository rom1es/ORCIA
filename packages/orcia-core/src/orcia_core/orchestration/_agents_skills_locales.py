"""Bilingual locale bundles for Agents, Skills & AI Models connection messages (`Story 27.7`)."""

from __future__ import annotations

from dataclasses import dataclass

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale


@dataclass(frozen=True, slots=True)
class AgentsSkillsCopy:
    """Localized outcome and validation labels for Agents, Skills & AI Models."""

    default_output_format: str
    no_additional_params: str
    no_attached_skill: str
    no_external_skill_used: str
    copy_suffix: str
    posture_evaluator: str
    posture_producer: str
    validated_synthesis_tpl: str
    skill_success_tpl: str
    skill_objective_tpl: str
    skill_input_tpl: str
    skill_params_tpl: str
    skill_method_tpl: str
    skill_result_tpl: str
    agent_header_tpl: str
    agent_posture_tpl: str
    agent_engine_tpl: str
    agent_prompt_tpl: str
    agent_skills_tpl: str
    agent_synthesis_tpl: str
    agent_system_tpl: str
    agent_user_tpl: str
    agent_trace_tpl: str


AGENTS_SKILLS_LOCALES: dict[SupportedLocale, AgentsSkillsCopy] = {
    "fr": AgentsSkillsCopy(
        default_output_format="Synthèse structurée",
        no_additional_params="aucun paramètre additionnel",
        no_attached_skill="aucune compétence rattachée",
        no_external_skill_used="Aucune compétence externe mobilisée.",
        copy_suffix="(Copie)",
        posture_evaluator="Évaluateur / Contradicteur (Gate)",
        posture_producer="Producteur / Assistant métier",
        validated_synthesis_tpl="Synthèse validée pour « {clean_input} ».",
        skill_success_tpl="✅ Compétence « {name} » ({handle}) exécutée avec succès.",
        skill_objective_tpl="• Objectif appliqué : {objective}",
        skill_input_tpl="• Entrée analysée : {clean_input}",
        skill_params_tpl="• Paramètres pris en compte : {params_summary}",
        skill_method_tpl="• Méthode exécutée : {instructions}",
        skill_result_tpl="• Résultat ({expected_output_format}) :\n{res}",
        agent_header_tpl="🤖 Réponse de {name} ({handle}) — Mission : {role_mission}",
        agent_posture_tpl=(
            "• Posture : {posture_lbl} | Binôme humain : {human_partner_role} "
            "| Contrat : {output_contract_format}"
        ),
        agent_engine_tpl=(
            "• Moteur cognitif : {llm_model_tier} "
            "(effort={thinking_level}, temp={temperature}, max_tokens={max_tokens})"
        ),
        agent_prompt_tpl="• Demande traitée : « {clean_prompt} »",
        agent_skills_tpl="• Compétences mobilisées ({count}) : {skills_names}",
        agent_synthesis_tpl=(
            "• Synthèse : Selon mes instructions (« {instructions} »), "
            "voici la proposition structurée avec citations [S1] pour « {clean_prompt} ». "
            "({llm_text})"
        ),
        agent_system_tpl=(
            "Agent: {name} ({handle}) | Rôle: {role_mission} | "
            "Posture: {posture} | Instructions: {instructions}"
        ),
        agent_user_tpl="Demande: {clean_prompt}\nCompétences: {skills_block}",
        agent_trace_tpl=(
            "{name} ({handle}) -> {expected_output_format} produit pour « {clean_prompt} »"
        ),
    ),
    "en": AgentsSkillsCopy(
        default_output_format="Structured synthesis",
        no_additional_params="no additional parameters",
        no_attached_skill="no attached skills",
        no_external_skill_used="No external skill invoked.",
        copy_suffix="(Copy)",
        posture_evaluator="Evaluator / Challenger (Gate)",
        posture_producer="Producer / Business Assistant",
        validated_synthesis_tpl="Validated synthesis for '{clean_input}'.",
        skill_success_tpl="✅ Skill '{name}' ({handle}) executed successfully.",
        skill_objective_tpl="• Applied objective: {objective}",
        skill_input_tpl="• Analyzed input: {clean_input}",
        skill_params_tpl="• Applied parameters: {params_summary}",
        skill_method_tpl="• Executed method: {instructions}",
        skill_result_tpl="• Result ({expected_output_format}):\n{res}",
        agent_header_tpl="🤖 Response from {name} ({handle}) — Mission: {role_mission}",
        agent_posture_tpl=(
            "• Posture: {posture_lbl} | Human partner: {human_partner_role} "
            "| Contract: {output_contract_format}"
        ),
        agent_engine_tpl=(
            "• Cognitive engine: {llm_model_tier} "
            "(effort={thinking_level}, temp={temperature}, max_tokens={max_tokens})"
        ),
        agent_prompt_tpl="• Handled request: '{clean_prompt}'",
        agent_skills_tpl="• Invoked skills ({count}): {skills_names}",
        agent_synthesis_tpl=(
            "• Synthesis: Per my instructions ('{instructions}'), "
            "here is the structured proposal with [S1] citations for '{clean_prompt}'. "
            "({llm_text})"
        ),
        agent_system_tpl=(
            "Agent: {name} ({handle}) | Role: {role_mission} | "
            "Posture: {posture} | Instructions: {instructions}"
        ),
        agent_user_tpl="Request: {clean_prompt}\nSkills: {skills_block}",
        agent_trace_tpl=(
            "{name} ({handle}) -> {expected_output_format} produced for '{clean_prompt}'"
        ),
    ),
}

AI_MODEL_CONNECTION_MSG_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "fallback_ok": "Connexion établie via le modèle de secours ({fb_model}) en {ms} ms.",
        "chat_ok": (
            "✅ Connexion réussie au modèle « {model_name} » ({p_label}) sur {endpoint_uri} — "
            "Réponse reçue en {latency_ms} ms."
        ),
        "embed_ok": (
            "✅ Connexion réussie au modèle d'embedding « {model_name} » "
            "(dimension 1024 validée) — Réponse en {latency_ms} ms."
        ),
    },
    "en": {
        "fallback_ok": "Connection established via fallback model ({fb_model}) in {ms} ms.",
        "chat_ok": (
            "✅ Successfully connected to model '{model_name}' ({p_label}) at {endpoint_uri} — "
            "Response received in {latency_ms} ms."
        ),
        "embed_ok": (
            "✅ Successfully connected to embedding model '{model_name}' "
            "(1024-dim validated) — Response in {latency_ms} ms."
        ),
    },
}


def get_agents_skills_copy(locale: SupportedLocale = DEFAULT_LOCALE) -> AgentsSkillsCopy:
    """Return localized Agents/Skills execution messages."""
    return AGENTS_SKILLS_LOCALES.get(locale, AGENTS_SKILLS_LOCALES[DEFAULT_LOCALE])


__all__ = [
    "AGENTS_SKILLS_LOCALES",
    "AI_MODEL_CONNECTION_MSG_LOCALES",
    "AgentsSkillsCopy",
    "get_agents_skills_copy",
]
