"""5-Layer Prompt Harness (`AssistantHarness`) delegating to `AssistantPromptBuilder` (`AD-15`)."""

from __future__ import annotations

from typing import Any

from orcia_core.orchestration.assistant_harness_types import (
    AssembledAssistantPrompt,
    AssistantIntentKind,
    AssistantLayerId,
    PromptLayerBlock,
)
from orcia_core.orchestration.assistant_profile_adaptation import (
    CONSTITUTIONAL_LAYER_1_TEXT,
    PROFILE_ADAPTATION_MAP,
    ProfileAdaptationSpec,
    resolve_profile_adaptation,
    sanitize_layer_marker_tags,
)
from orcia_core.orchestration.assistant_prompt_builder import AssistantPromptBuilder
from orcia_kernel.context_ports import (
    AssistantWorkflowBlueprint,
    ContextSliceRecord,
    VectorSearchHitRecord,
)


class AssistantHarness:
    """Compatibility facade delegating 5-layer assembly to `AssistantPromptBuilder` (`AD-15`)."""

    def __init__(self, builder: AssistantPromptBuilder | None = None) -> None:
        self._builder = builder or AssistantPromptBuilder()

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
    ) -> AssembledAssistantPrompt:
        """Assemble all 5 layers and compute cryptographic provenance hashes."""
        return self._builder.assemble_prompt(
            user_prompt=user_prompt,
            human_profile_archetype=human_profile_archetype,
            workspace_id=workspace_id,
            intent=intent,
            ontology_concepts=ontology_concepts,
            ontology_axioms=ontology_axioms,
            context_slices=context_slices,
            vector_hits=vector_hits,
            workflow_blueprint=workflow_blueprint,
            locale=locale,
        )


__all__ = [
    "AssembledAssistantPrompt",
    "AssistantHarness",
    "AssistantIntentKind",
    "AssistantLayerId",
    "CONSTITUTIONAL_LAYER_1_TEXT",
    "PROFILE_ADAPTATION_MAP",
    "ProfileAdaptationSpec",
    "PromptLayerBlock",
    "resolve_profile_adaptation",
    "sanitize_layer_marker_tags",
]
