"""Shared data types for `AssistantHarness` and `AssistantPromptBuilder` (`AD-15`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from orcia_core.orchestration.assistant_profile_adaptation import ProfileAdaptationSpec

AssistantLayerId = Literal[
    "1_CONSTITUTIONAL_IMMUTABLE",
    "2_ONTOLOGY_AND_AXIOMS_L1_L4",
    "3_HUMAN_PROFILE_ADAPTATION",
    "4_FEDERATED_CONTEXT_FANOUT",
    "5_CONVERSATIONAL_INTENT_AND_COMPOSER",
]

AssistantIntentKind = Literal[
    "QA_COACHING",
    "WORKFLOW_COMPOSE",
    "WORKFLOW_MODIFY",
    "WORKFLOW_LAUNCH",
    "HUMAN_ANCHOR_WRITE_REFUSAL",
]


@dataclass(frozen=True, slots=True)
class PromptLayerBlock:
    """Single layer inside the 5-layer `AssistantPromptBuilder` (`AD-15`)."""

    layer_id: AssistantLayerId
    layer_order: int
    immutable: bool
    content_sha256: str
    content: str


@dataclass(frozen=True, slots=True)
class AssembledAssistantPrompt:
    """Full 5-layer prompt assembled by `AssistantPromptBuilder` (`AD-15`, `AR-4`)."""

    layers: tuple[PromptLayerBlock, ...]
    system_prompt: str
    user_prompt: str
    constitutional_sha256: str
    profile_adaptation: ProfileAdaptationSpec
    cited_uris: tuple[str, ...]
    stale_warnings: tuple[str, ...]
