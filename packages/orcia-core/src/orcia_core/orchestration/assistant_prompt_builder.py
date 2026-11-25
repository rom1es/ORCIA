"""Unified Localized `AssistantPromptBuilder` (`AD-15`, `H-25`, `H-31`, `Story 26.2`)."""

from __future__ import annotations

import hashlib
from typing import Any

from orcia_core.orchestration.assistant_governance_models import (
    AssembledLayerPreviewItem,
    UserLayerPreferences,
    WorkspaceLayerSettings,
)
from orcia_core.orchestration.assistant_harness_types import (
    AssembledAssistantPrompt,
    AssistantIntentKind,
    PromptLayerBlock,
)
from orcia_core.orchestration.assistant_profile_adaptation import (
    resolve_profile_adaptation,
    resolve_profile_copy_for_locale,
    sanitize_layer_marker_tags,
)
from orcia_core.orchestration.assistant_prompt_locales import get_prompt_locale_bundle
from orcia_core.orchestration.assistant_prompt_preview import (
    build_five_layers_preview_items,
    format_governance_and_folder_sections,
    format_system_instructions_text,
    resolve_human_workspace_label,
)
from orcia_core.orchestration.assistant_prompt_preview import (
    resolve_default_hat as resolve_default_hat,
)
from orcia_core.orchestration.errors import ImmutableHarnessBoundaryError
from orcia_kernel.context_ports import (
    AssistantWorkflowBlueprint,
    ContextSliceRecord,
    VectorSearchHitRecord,
)


def _sha256_str(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


class AssistantPromptBuilder:
    """Single source of truth for 5-layer prompt assembly, system instructions, and previews."""

    def assemble_prompt(
        self,
        *,
        user_prompt: str,
        human_profile_archetype: str,
        workspace_id: str,
        intent: AssistantIntentKind,
        ontology_concepts: tuple[dict[str, Any], ...] = (),
        ontology_axioms: tuple[dict[str, Any], ...] = (),
        context_slices: tuple[ContextSliceRecord, ...] = (),
        vector_hits: tuple[VectorSearchHitRecord, ...] = (),
        workflow_blueprint: AssistantWorkflowBlueprint | None = None,
        locale: str = "fr",
        workspace_display_name: str | None = None,
    ) -> AssembledAssistantPrompt:
        """Assemble all 5 layers with immutable Layer 1 and clean `fr`/`en` localization."""
        bundle = get_prompt_locale_bundle(locale)
        workspace_label = resolve_human_workspace_label(
            workspace_id, workspace_display_name, locale=locale
        )
        layer_1 = PromptLayerBlock(
            layer_id="1_CONSTITUTIONAL_IMMUTABLE",
            layer_order=1,
            immutable=True,
            content_sha256=_sha256_str(bundle.constitutional_layer_1),
            content=bundle.constitutional_layer_1,
        )

        concept_lines = [
            f"- Concept [{c.get('level', 'L3')}] {c.get('canonical_term', c.get('key', ''))}: "
            f"{c.get('definition', '')}"
            for c in ontology_concepts
        ] or [bundle.no_ontology_concepts]
        axiom_lines = [
            f"- Axiom [IMMUTABLE={a.get('immutable', True)}] {a.get('axiom_key', '')}: "
            f"{a.get('formal_rule', '')}"
            for a in ontology_axioms
        ] or [bundle.base_axiom]
        layer_2_text = (
            f"{bundle.ontology_header}\n"
            f"{bundle.concepts_header}\n"
            + "\n".join(concept_lines)
            + f"\n{bundle.axioms_header}\n"
            + "\n".join(axiom_lines)
        )
        layer_2 = PromptLayerBlock(
            layer_id="2_ONTOLOGY_AND_AXIOMS_L1_L4",
            layer_order=2,
            immutable=True,
            content_sha256=_sha256_str(layer_2_text),
            content=layer_2_text,
        )

        profile_spec = resolve_profile_adaptation(human_profile_archetype)
        reg_label, indicators, prefix = resolve_profile_copy_for_locale(profile_spec, locale=locale)
        layer_3_text = (
            f"[HUMAN_PROFILE_ADAPTATION_LAYER_3]\n"
            f"{bundle.archetype_label}: {profile_spec.archetype}\n"
            f"{bundle.register_label}: {reg_label}\n"
            f"{bundle.indicators_label}: {', '.join(indicators)}\n"
            f"{bundle.prefix_label}: {prefix}"
        )
        layer_3 = PromptLayerBlock(
            layer_id="3_HUMAN_PROFILE_ADAPTATION",
            layer_order=3,
            immutable=False,
            content_sha256=_sha256_str(layer_3_text),
            content=layer_3_text,
        )

        cited_uris: list[str] = []
        stale_warnings: list[str] = []
        fanout_lines: list[str] = []
        for s in context_slices:
            cited_uris.append(s.source_uri)
            if s.is_stale and s.stale_warning_marker:
                stale_warnings.append(f"{s.source_uri}: {s.stale_warning_marker}")
            fanout_lines.append(
                f"- [{s.source_kind}] {s.source_uri} ({s.content_sha256[:19]}): "
                f"{sanitize_layer_marker_tags(s.text_excerpt)}"
            )
        for h in vector_hits:
            if h.source_uri not in cited_uris:
                cited_uris.append(h.source_uri)
            if h.is_stale and h.stale_warning_marker:
                stale_warnings.append(f"{h.source_uri}: {h.stale_warning_marker}")
            fanout_lines.append(
                f"- [VECTOR_RRF={h.rrf_score:.4f}] {h.source_uri} ({h.chunk_key}): "
                f"{sanitize_layer_marker_tags(h.injected_content[:180])}"
            )
        if not fanout_lines:
            fanout_lines.append(bundle.empty_fanout_tpl.format(workspace_id=workspace_label))

        layer_4_text = "[FEDERATED_CONTEXT_FANOUT_LAYER_4]\n" + "\n".join(fanout_lines)
        layer_4 = PromptLayerBlock(
            layer_id="4_FEDERATED_CONTEXT_FANOUT",
            layer_order=4,
            immutable=False,
            content_sha256=_sha256_str(layer_4_text),
            content=layer_4_text,
        )

        composer_note = (
            bundle.blueprint_tpl.format(
                workflow_uri=workflow_blueprint.workflow_uri, title=workflow_blueprint.title
            )
            if workflow_blueprint is not None
            else bundle.no_blueprint
        )
        layer_5_text = (
            f"[CONVERSATIONAL_INTENT_AND_COMPOSER_LAYER_5]\n"
            f"{bundle.workspace_label}: {workspace_label}\n"
            f"{bundle.intent_label}: {intent}\n"
            f"{composer_note}\n"
            f"{bundle.user_message_label}: {sanitize_layer_marker_tags(user_prompt)}"
        )
        layer_5 = PromptLayerBlock(
            layer_id="5_CONVERSATIONAL_INTENT_AND_COMPOSER",
            layer_order=5,
            immutable=False,
            content_sha256=_sha256_str(layer_5_text),
            content=layer_5_text,
        )

        layers = (layer_1, layer_2, layer_3, layer_4, layer_5)
        system_prompt = "\n\n".join(block.content for block in layers[:4])
        return AssembledAssistantPrompt(
            layers=layers,
            system_prompt=system_prompt,
            user_prompt=layer_5_text,
            constitutional_sha256=layer_1.content_sha256,
            profile_adaptation=profile_spec,
            cited_uris=tuple(cited_uris),
            stale_warnings=tuple(stale_warnings),
        )

    def format_governance_and_folder_block(
        self,
        *,
        response_tone: str | None = None,
        response_format: str | None = None,
        personal_instructions: str | None = None,
        workspace_instructions: str | None = None,
        folder_pinned_notes: str | None = None,
        locale: str = "fr",
    ) -> str:
        """Build sanitized Layer 4 Workspace, Layer 5 User prefs & Folder Notes blocks."""
        return format_governance_and_folder_sections(
            response_tone=response_tone,
            response_format=response_format,
            personal_instructions=personal_instructions,
            workspace_instructions=workspace_instructions,
            folder_pinned_notes=folder_pinned_notes,
            locale=locale,
        )

    def build_system_instructions(
        self,
        *,
        hat: str,
        speed_mode: str,
        requested_tier: str | None = None,
        thinking_effort: str | None = None,
        system_instructions_override: str | None = None,
        allow_system_override: bool = False,
        assembled_5_layers_prompt: str | None = None,
        ontology_concepts_summary: str | None = None,
        federated_evidence_summary: str | None = None,
        response_tone: str | None = None,
        response_format: str | None = None,
        personal_instructions: str | None = None,
        workspace_instructions: str | None = None,
        folder_pinned_notes: str | None = None,
        locale: str = "fr",
    ) -> str:
        """Build complete 5-layer + ontology + evidence + preferences system prompt (`AD-15`)."""
        if system_instructions_override and system_instructions_override.strip():
            if not allow_system_override:
                raise ImmutableHarnessBoundaryError(
                    detail_override="Layer 1 constitutional harness cannot be overridden."
                )
            return system_instructions_override.strip()

        custom_block = self.format_governance_and_folder_block(
            response_tone=response_tone,
            response_format=response_format,
            personal_instructions=personal_instructions,
            workspace_instructions=workspace_instructions,
            folder_pinned_notes=folder_pinned_notes,
            locale=locale,
        )
        return format_system_instructions_text(
            hat=hat,
            speed_mode=speed_mode,
            requested_tier=requested_tier,
            thinking_effort=thinking_effort,
            assembled_5_layers_prompt=assembled_5_layers_prompt,
            ontology_concepts_summary=ontology_concepts_summary,
            federated_evidence_summary=federated_evidence_summary,
            custom_block=custom_block,
            locale=locale,
        )

    def build_five_layers_preview(
        self,
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
        """Assemble the 5-layer preview tuple with sanitized mutable layers and `locale`."""
        return build_five_layers_preview_items(
            workspace_id=workspace_id,
            user_id=user_id,
            pack_key=pack_key,
            user_prefs=user_prefs,
            ws_settings=ws_settings,
            team_instr=team_instr,
            locale=locale,
            workspace_display_name=workspace_display_name,
            user_display_name=user_display_name,
        )
