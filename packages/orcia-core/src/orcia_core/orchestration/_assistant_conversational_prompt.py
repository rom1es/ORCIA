"""Clean Conversational Prompt Assembly & Conditional Evidence Guard (`Story 30.2`).

Strictly decoupled from Tab 3 UI Governance Preview cards (`build_five_layers_preview_items`).
Zero raw internal bracket markers (`[CONSTITUTIONAL_*]`, `[LAYER_*]`, `[ACTIVE_DOMAIN_PACK:*]`).
"""

from __future__ import annotations

from orcia_core.orchestration._assistant_conversational_locales import get_conversational_locale
from orcia_core.orchestration.assistant_profile_adaptation import (
    resolve_profile_adaptation,
    resolve_profile_copy_for_locale,
    sanitize_layer_marker_tags,
)
from orcia_core.orchestration.assistant_prompt_locales import get_prompt_locale_bundle


def build_conversational_base_context(
    *,
    workspace_id: str,
    workspace_label: str,
    hat: str = "ARCHITECT",
    pack_key: str | None = None,
    team_instructions: str | None = None,
    locale: str = "fr",
) -> str:
    """Assemble clean conversational core principles, pack/team context & role profile."""
    _ = workspace_id
    bundle = get_prompt_locale_bundle(locale)
    cloc = get_conversational_locale(locale)
    profile_spec = resolve_profile_adaptation(hat)
    reg_label, indicators, _ = resolve_profile_copy_for_locale(profile_spec, locale=locale)

    sections: list[str] = [bundle.constitutional_layer_1]

    context_lines: list[str] = []
    clean_pack = sanitize_layer_marker_tags(pack_key)
    if clean_pack:
        context_lines.append(cloc.active_pack_tpl.format(pack_key=clean_pack))
    if workspace_label:
        context_lines.append(cloc.workspace_tpl.format(workspace=workspace_label))
    safe_team = sanitize_layer_marker_tags(team_instructions)
    if safe_team:
        context_lines.append(f"{bundle.team_instructions_label}: {safe_team}")
    if context_lines:
        sections.append(f"{cloc.context_heading}:\n" + "\n".join(context_lines))

    sections.append(
        f"{cloc.profile_heading}:\n"
        f"{bundle.register_label}: {reg_label}\n"
        f"{bundle.indicators_label}: {', '.join(indicators)}"
    )
    return "\n\n".join(sections)


def format_conversational_governance_sections(
    *,
    response_tone: str | None = None,
    response_format: str | None = None,
    personal_instructions: str | None = None,
    workspace_instructions: str | None = None,
    folder_pinned_notes: str | None = None,
    locale: str = "fr",
) -> str:
    """Format single-injection Workspace instructions, User preferences & Folder notes."""
    bundle = get_prompt_locale_bundle(locale)
    cloc = get_conversational_locale(locale)
    sections: list[str] = []
    safe_ws = sanitize_layer_marker_tags(workspace_instructions)
    if safe_ws:
        sections.append(f"{cloc.workspace_instructions_heading}:\n{safe_ws}")

    user_lines: list[str] = []
    if response_tone and response_tone.upper() in bundle.tone_map:
        user_lines.append(f"- {bundle.tone_label}: {bundle.tone_map[response_tone.upper()]}")
    if response_format and response_format.upper() in bundle.format_map:
        user_lines.append(f"- {bundle.format_label}: {bundle.format_map[response_format.upper()]}")
    safe_personal = sanitize_layer_marker_tags(personal_instructions)
    if safe_personal:
        user_lines.append(f"- {bundle.personal_instructions_label}: {safe_personal}")
    if user_lines:
        sections.append(f"{cloc.user_preferences_heading}:\n" + "\n".join(user_lines))

    safe_notes = sanitize_layer_marker_tags(folder_pinned_notes)
    if safe_notes:
        sections.append(f"{cloc.folder_notes_heading}:\n{safe_notes}")

    return ("\n\n" + "\n\n".join(sections)) if sections else ""


def format_conversational_system_instructions(
    *,
    hat: str,
    speed_mode: str,
    requested_tier: str | None,
    thinking_effort: str | None,
    assembled_5_layers_prompt: str | None,
    ontology_concepts_summary: str | None,
    federated_evidence_summary: str | None,
    custom_block: str,
    locale: str,
    human_hat: str,
    human_speed: str,
    has_evidence: bool | None = None,
    pack_key: str | None = None,
    workspace_label: str = "",
) -> str:
    """Assemble clean conversational system instructions with conditional citation guard."""
    bundle = get_prompt_locale_bundle(locale)
    cloc = get_conversational_locale(locale)
    effort = (thinking_effort or "").strip().lower() or (
        "deep"
        if speed_mode == "SPEED_3_DEEP_AUDIT"
        else "balanced"
        if speed_mode == "SPEED_2_AGENT_TOOLS"
        else "fast"
    )
    tier_key = (requested_tier or "medium").strip().lower()
    tier_guidance = bundle.tier_map.get(tier_key, bundle.tier_default)
    effort_guidance = (
        bundle.effort_deep
        if effort == "deep"
        else bundle.effort_balanced
        if effort == "balanced"
        else bundle.effort_fast
    )
    layers_block = (
        assembled_5_layers_prompt.strip()
        if assembled_5_layers_prompt and assembled_5_layers_prompt.strip()
        else build_conversational_base_context(
            workspace_id="",
            workspace_label=workspace_label,
            hat=hat,
            pack_key=pack_key,
            locale=locale,
        )
    )
    ontology_block = (
        f"\n\n{cloc.ontology_heading}:\n{sanitize_layer_marker_tags(ontology_concepts_summary)}"
        if ontology_concepts_summary and ontology_concepts_summary.strip()
        else ""
    )
    has_ev_text = bool(federated_evidence_summary and federated_evidence_summary.strip())
    effective_has_evidence = has_ev_text if has_evidence is None else bool(has_evidence)
    evidence_block = (
        f"\n\n{federated_evidence_summary.strip()}"
        if effective_has_evidence and has_ev_text and federated_evidence_summary
        else ""
    )
    evidence_rule = (
        cloc.evidence_citation_rule if effective_has_evidence else cloc.empty_evidence_guard
    )
    return (
        f"{layers_block}{ontology_block}{evidence_block}{custom_block}\n\n"
        f"{cloc.runtime_heading}:\n"
        f"{bundle.active_hat_tpl.format(hat=human_hat, speed_mode=human_speed)}\n"
        f"- {tier_guidance}\n"
        f"- {effort_guidance}\n"
        f"{evidence_rule}\n"
        f"{bundle.markdown_rule}\n"
        f"{bundle.language_rule}"
    )
