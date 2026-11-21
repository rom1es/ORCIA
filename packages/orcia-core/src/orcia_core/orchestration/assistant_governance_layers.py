"""5-Layer Prompt Preview Builder (`Story 10.1`, `Story 26.1`)."""

from __future__ import annotations

from orcia_core.orchestration.assistant_governance_models import (
    AssembledLayerPreviewItem,
    UserLayerPreferences,
    WorkspaceLayerSettings,
    _compute_sha256_hex,
)
from orcia_core.orchestration.assistant_harness import (
    CONSTITUTIONAL_LAYER_1_TEXT,
    resolve_profile_adaptation,
    sanitize_layer_marker_tags,
)


def build_five_layers_preview_items(
    *,
    workspace_id: str,
    user_id: str,
    pack_key: str,
    user_prefs: UserLayerPreferences,
    ws_settings: WorkspaceLayerSettings,
    team_instr: str,
) -> tuple[AssembledLayerPreviewItem, ...]:
    """Assemble the 5-layer preview tuple with sanitized mutable layers."""
    profile_spec = resolve_profile_adaptation(user_prefs.default_hat)
    l1_content = CONSTITUTIONAL_LAYER_1_TEXT
    l2_content = (
        f"[PACK_METIER_ACTIVE: {pack_key}]\n"
        "Conventions de domaine et axiomes N1–N3 chargés depuis le Pack Métier actif."
    )
    l3_content = (
        f"[EQUIPE_ET_CASQUETTE: {profile_spec.archetype}]\n"
        f"Registre: {profile_spec.register_label}\n"
        f"Instructions Équipe: {sanitize_layer_marker_tags(team_instr)}"
    )
    l4_content = (
        f"[ESPACE: {workspace_id}]\n"
        f"Instructions Espace: {sanitize_layer_marker_tags(ws_settings.workspace_instructions)}\n"
        f"Sources par défaut: {', '.join(ws_settings.default_checked_sources)}\n"
        f"Agents recommandés: {', '.join(ws_settings.recommended_agents)}"
    )
    l5_content = (
        f"[UTILISATEUR: {user_id}]\n"
        f"Ton: {user_prefs.response_tone} | Format: {user_prefs.favorite_format}\n"
        f"Instructions personnelles: {sanitize_layer_marker_tags(user_prefs.personal_instructions)}"
    )
    return (
        AssembledLayerPreviewItem(
            layer_number=1,
            layer_code="1_CONSTITUTION",
            label="1. 🔒 Constitution (AssistantHarness Socle)",
            immutable=True,
            origin_badge="SOCLE",
            content=l1_content,
            sha256=_compute_sha256_hex(l1_content),
        ),
        AssembledLayerPreviewItem(
            layer_number=2,
            layer_code="2_PACK_METIER",
            label="2. Pack Métier & Ontologie",
            immutable=True,
            origin_badge="PACK",
            content=l2_content,
            sha256=_compute_sha256_hex(l2_content),
        ),
        AssembledLayerPreviewItem(
            layer_number=3,
            layer_code="3_EQUIPE",
            label="3. Équipe & Casquette",
            immutable=False,
            origin_badge="EQUIPE",
            content=l3_content,
            sha256=_compute_sha256_hex(l3_content),
        ),
        AssembledLayerPreviewItem(
            layer_number=4,
            layer_code="4_ESPACE",
            label="4. Espace & Glossaire",
            immutable=False,
            origin_badge="ESPACE",
            content=l4_content,
            sha256=_compute_sha256_hex(l4_content),
        ),
        AssembledLayerPreviewItem(
            layer_number=5,
            layer_code="5_UTILISATEUR",
            label="5. Utilisateur (Préférences & Continuité Dossier)",
            immutable=False,
            origin_badge="UTILISATEUR",
            content=l5_content,
            sha256=_compute_sha256_hex(l5_content),
        ),
    )
