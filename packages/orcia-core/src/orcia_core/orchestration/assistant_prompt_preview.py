"""5-Layer Assistant Governance Preview Builder (`AD-15`, `H-25`, `H-31`, `Story 26.2`)."""

from __future__ import annotations

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


def resolve_default_hat(
    *,
    explicit_hat: str | None = None,
    user: UserIdentity | None = None,
    fallback: str = "ARCHITECT",
) -> str:
    """Resolve active hat from explicit override or `user.human_profile_archetype`."""
    if explicit_hat and explicit_hat.strip():
        return explicit_hat.strip().upper()
    if user is not None and user.human_profile_archetype and user.human_profile_archetype.strip():
        return user.human_profile_archetype.strip().upper()
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
    """Build sanitized Layer 4 Workspace, Layer 5 User prefs & Folder Notes blocks."""
    bundle = get_prompt_locale_bundle(locale)
    sections: list[str] = []
    safe_ws = sanitize_layer_marker_tags(workspace_instructions)
    if safe_ws:
        sections.append(f"[LAYER_4_WORKSPACE_INSTRUCTIONS]\n{safe_ws}")
    user_lines: list[str] = []
    if response_tone and response_tone.upper() in bundle.tone_map:
        user_lines.append(f"- {bundle.tone_label}: {bundle.tone_map[response_tone.upper()]}")
    if response_format and response_format.upper() in bundle.format_map:
        user_lines.append(f"- {bundle.format_label}: {bundle.format_map[response_format.upper()]}")
    safe_personal = sanitize_layer_marker_tags(personal_instructions)
    if safe_personal:
        user_lines.append(f"- {bundle.personal_instructions_label}: {safe_personal}")
    if user_lines:
        sections.append("[LAYER_5_USER_PREFERENCES]\n" + "\n".join(user_lines))
    safe_notes = sanitize_layer_marker_tags(folder_pinned_notes)
    if safe_notes:
        sections.append(f"[LAYER_5_ACTIVE_FOLDER_PINNED_NOTES]\n{safe_notes}")
    return ("\n\n" + "\n\n".join(sections)) if sections else ""


def build_five_layers_preview_items(
    *,
    workspace_id: str,
    user_id: str,
    pack_key: str | None,
    user_prefs: UserLayerPreferences,
    ws_settings: WorkspaceLayerSettings,
    team_instr: str,
    locale: str = "fr",
) -> tuple[AssembledLayerPreviewItem, ...]:
    """Assemble the 5-layer preview tuple with sanitized mutable layers and `locale`."""
    bundle = get_prompt_locale_bundle(locale)
    profile_spec = resolve_profile_adaptation(user_prefs.default_hat)
    reg_label, _, _ = resolve_profile_copy_for_locale(profile_spec, locale=locale)
    resolved_pack = (pack_key or "").strip() or "core"
    l1_content = bundle.constitutional_layer_1
    l2_content = f"[ACTIVE_DOMAIN_PACK: {resolved_pack}]\n{bundle.pack_layer_summary}"
    l3_content = (
        f"[TEAM_AND_HAT: {profile_spec.archetype}]\n"
        f"{bundle.register_label}: {reg_label}\n"
        f"{bundle.team_instructions_label}: {sanitize_layer_marker_tags(team_instr)}"
    )
    l4_content = (
        f"[WORKSPACE: {workspace_id}]\n"
        f"{bundle.workspace_instructions_label}: "
        f"{sanitize_layer_marker_tags(ws_settings.workspace_instructions)}\n"
        f"{bundle.default_sources_label}: {', '.join(ws_settings.default_checked_sources)}\n"
        f"{bundle.recommended_agents_label}: {', '.join(ws_settings.recommended_agents)}"
    )
    l5_content = (
        f"[USER: {user_id}]\n"
        f"{bundle.tone_label}: {user_prefs.response_tone} | "
        f"{bundle.format_label}: {user_prefs.favorite_format}\n"
        f"{bundle.personal_instructions_label}: "
        f"{sanitize_layer_marker_tags(user_prefs.personal_instructions)}"
    )
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
