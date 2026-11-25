"""5-Layer Assistant Governance Preview Builder (`AD-15`, `H-25`, `H-31`, `Story 26.2`)."""

from __future__ import annotations

import re

from orcia_core.orchestration._assistant_conversational_locales import get_conversational_locale
from orcia_core.orchestration._assistant_conversational_prompt import (
    format_conversational_governance_sections,
    format_conversational_system_instructions,
)
from orcia_core.orchestration.assistant_governance_models import (
    AssembledLayerPreviewItem,
    UserLayerPreferences,
    WorkspaceLayerSettings,
    _compute_sha256_hex,
)
from orcia_core.orchestration.assistant_profile_adaptation import (
    resolve_profile_adaptation,
    resolve_profile_copy_for_locale,
    sanitize_layer_marker_tags,
)
from orcia_core.orchestration.assistant_prompt_locales import get_prompt_locale_bundle
from orcia_core.permissions.models import UserIdentity

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def is_raw_uuid_string(value: str | None) -> bool:
    """Return True if `value` is a raw UUID string."""
    return bool(value and _UUID_RE.match(value.strip()))


def resolve_human_workspace_label(
    workspace_id: str,
    workspace_display_name: str | None = None,
    *,
    locale: str = "fr",
) -> str:
    """Resolve a human-readable workspace label without leaking raw UUIDv7s or `scope-global`."""
    bundle = get_prompt_locale_bundle(locale)
    clean_name = sanitize_layer_marker_tags(workspace_display_name)
    if clean_name and not is_raw_uuid_string(clean_name):
        return clean_name
    raw_id = (workspace_id or "").strip()
    if raw_id.lower() in ("scope-global", "global"):
        return bundle.global_scope_label
    if not raw_id or is_raw_uuid_string(raw_id):
        return bundle.active_workspace_fallback_label
    return raw_id


def resolve_human_user_label(
    user_id: str,
    user_display_name: str | None = None,
    *,
    locale: str = "fr",
) -> str:
    """Resolve a human-readable user label without leaking raw UUIDv7s."""
    bundle = get_prompt_locale_bundle(locale)
    clean_name = sanitize_layer_marker_tags(user_display_name)
    if clean_name and not is_raw_uuid_string(clean_name):
        return clean_name
    raw_id = (user_id or "").strip()
    if not raw_id or is_raw_uuid_string(raw_id):
        return bundle.active_user_fallback_label
    return raw_id


def resolve_human_speed_label(speed_mode: str, *, locale: str = "fr") -> str:
    """Map internal speed enum (`SPEED_*`) to a localized human-readable label."""
    bundle = get_prompt_locale_bundle(locale)
    norm = (speed_mode or "").strip().upper()
    return bundle.speed_mode_labels.get(norm, bundle.speed_mode_labels["SPEED_1_FAST"])


def resolve_human_hat_label(hat: str, *, locale: str = "fr") -> str:
    """Map role/archetype code to a localized human-readable label."""
    bundle = get_prompt_locale_bundle(locale)
    norm = (hat or "").strip().upper() or "ARCHITECT"
    return bundle.hat_labels.get(norm, norm.replace("_", " ").title())


def resolve_default_hat(
    *,
    explicit_hat: str | None = None,
    user: UserIdentity | None = None,
    fallback: str = "ARCHITECT",
) -> str:
    """Resolve active hat from explicit override, `human_profile_archetype`, or `platform_role`."""
    if explicit_hat and explicit_hat.strip():
        return explicit_hat.strip().upper()
    if user is not None and user.human_profile_archetype and user.human_profile_archetype.strip():
        return user.human_profile_archetype.strip().upper()
    if user is not None and user.platform_role and user.platform_role.strip():
        return user.platform_role.strip().upper()
    return fallback.strip().upper() or "ARCHITECT"


def format_governance_and_folder_sections(
    *,
    response_tone: str | None = None,
    response_format: str | None = None,
    personal_instructions: str | None = None,
    workspace_instructions: str | None = None,
    folder_pinned_notes: str | None = None,
    locale: str = "fr",
) -> str:
    """Build sanitized Workspace, User preferences & Folder Notes blocks."""
    return format_conversational_governance_sections(
        response_tone=response_tone,
        response_format=response_format,
        personal_instructions=personal_instructions,
        workspace_instructions=workspace_instructions,
        folder_pinned_notes=folder_pinned_notes,
        locale=locale,
    )


def build_five_layers_preview_items(
    *,
    workspace_id: str,
    user_id: str,
    pack_key: str | None,
    user_prefs: UserLayerPreferences,
    ws_settings: WorkspaceLayerSettings,
    team_instr: str,
    locale: str = "fr",
    workspace_display_name: str | None = None,
    user_display_name: str | None = None,
) -> tuple[AssembledLayerPreviewItem, ...]:
    """Assemble Tab 3 UI 5-layer preview tuple with sanitized mutable layers and `locale`."""
    bundle = get_prompt_locale_bundle(locale)
    cloc = get_conversational_locale(locale)
    effective_hat = (user_prefs.default_hat or "").strip().upper() or "ARCHITECT"
    profile_spec = resolve_profile_adaptation(effective_hat)
    reg_label, _, _ = resolve_profile_copy_for_locale(profile_spec, locale=locale)
    human_hat = resolve_human_hat_label(effective_hat, locale=locale)
    workspace_label = resolve_human_workspace_label(
        workspace_id, workspace_display_name, locale=locale
    )
    user_label = resolve_human_user_label(user_id, user_display_name, locale=locale)
    resolved_pack = (pack_key or "").strip() or "core"
    l1_content = bundle.constitutional_layer_1
    l2_content = (
        f"{cloc.active_pack_tpl.format(pack_key=resolved_pack)}\n{bundle.pack_layer_summary}"
    )
    l3_content = (
        f"{cloc.team_hat_tpl.format(hat=human_hat)}\n"
        f"{bundle.register_label}: {reg_label}\n"
        f"{bundle.team_instructions_label}: {sanitize_layer_marker_tags(team_instr)}"
    )
    l4_lines = [
        cloc.workspace_tpl.format(workspace=workspace_label),
        (
            f"{bundle.workspace_instructions_label}: "
            f"{sanitize_layer_marker_tags(ws_settings.workspace_instructions)}"
        ),
    ]
    if ws_settings.default_checked_sources:
        l4_lines.append(
            f"{bundle.default_sources_label}: {', '.join(ws_settings.default_checked_sources)}"
        )
    if ws_settings.recommended_agents:
        l4_lines.append(
            f"{bundle.recommended_agents_label}: {', '.join(ws_settings.recommended_agents)}"
        )
    l4_content = "\n".join(l4_lines)
    tone_txt = bundle.tone_map.get(user_prefs.response_tone, user_prefs.response_tone)
    fmt_txt = bundle.format_map.get(user_prefs.favorite_format, user_prefs.favorite_format)
    l5_lines = [
        cloc.user_tpl.format(user=user_label),
        f"{bundle.tone_label}: {tone_txt} | {bundle.format_label}: {fmt_txt}",
    ]
    safe_personal = sanitize_layer_marker_tags(user_prefs.personal_instructions)
    if safe_personal:
        l5_lines.append(f"{bundle.personal_instructions_label}: {safe_personal}")
    l5_content = "\n".join(l5_lines)
    lbls = bundle.layer_labels
    return (
        AssembledLayerPreviewItem(
            layer_number=1,
            layer_code="1_CONSTITUTION",
            label=lbls[0],
            immutable=True,
            origin_badge="SOCLE",
            content=l1_content,
            sha256=_compute_sha256_hex(l1_content),
        ),
        AssembledLayerPreviewItem(
            layer_number=2,
            layer_code="2_PACK_METIER",
            label=lbls[1],
            immutable=True,
            origin_badge="PACK",
            content=l2_content,
            sha256=_compute_sha256_hex(l2_content),
        ),
        AssembledLayerPreviewItem(
            layer_number=3,
            layer_code="3_EQUIPE",
            label=lbls[2],
            immutable=False,
            origin_badge="EQUIPE",
            content=l3_content,
            sha256=_compute_sha256_hex(l3_content),
        ),
        AssembledLayerPreviewItem(
            layer_number=4,
            layer_code="4_ESPACE",
            label=lbls[3],
            immutable=False,
            origin_badge="ESPACE",
            content=l4_content,
            sha256=_compute_sha256_hex(l4_content),
        ),
        AssembledLayerPreviewItem(
            layer_number=5,
            layer_code="5_UTILISATEUR",
            label=lbls[4],
            immutable=False,
            origin_badge="UTILISATEUR",
            content=l5_content,
            sha256=_compute_sha256_hex(l5_content),
        ),
    )


def format_system_instructions_text(
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
    has_evidence: bool | None = None,
    pack_key: str | None = None,
) -> str:
    """Assemble conversational system instructions with conditional provenance rules."""
    return format_conversational_system_instructions(
        hat=hat,
        speed_mode=speed_mode,
        requested_tier=requested_tier,
        thinking_effort=thinking_effort,
        assembled_5_layers_prompt=assembled_5_layers_prompt,
        ontology_concepts_summary=ontology_concepts_summary,
        federated_evidence_summary=federated_evidence_summary,
        custom_block=custom_block,
        locale=locale,
        human_hat=resolve_human_hat_label(hat, locale=locale),
        human_speed=resolve_human_speed_label(speed_mode, locale=locale),
        has_evidence=has_evidence,
        pack_key=pack_key,
    )
