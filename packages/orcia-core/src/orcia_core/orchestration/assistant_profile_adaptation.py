"""Profile Adaptation & Constitutional Prompt Layer Sanitizers (`Story 3.3`, `Story 26.2`)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from orcia_core.orchestration._assistant_profile_locales import PROFILE_LABELS_LOCALES
from orcia_core.orchestration.assistant_prompt_locales import (
    CONSTITUTIONAL_LAYER_1_TEXT_EN,
    CONSTITUTIONAL_LAYER_1_TEXT_FR,
)

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

CONSTITUTIONAL_LAYER_1_TEXT: str = CONSTITUTIONAL_LAYER_1_TEXT_FR

_LAYER_OR_CONSTITUTIONAL_TAG_RE = re.compile(
    r"\[((?:LAYER|CONSTITUTIONAL|ONTOLOGY|HUMAN_PROFILE|ADAPTATION)(?:[_\s]+[^\]]*)?)\]",
    re.IGNORECASE,
)


def sanitize_layer_marker_tags(text: str | None) -> str:
    """Escape `[LAYER_*]` and `[CONSTITUTIONAL_*]` marker tags in untrusted text."""
    if not text:
        return ""
    return _LAYER_OR_CONSTITUTIONAL_TAG_RE.sub(r"(escaped:\1)", text.strip())


@dataclass(frozen=True, slots=True)
class ProfileAdaptationSpec:
    """Semantic adaptation descriptor for a `HumanProfileArchetype` (`FR-1`, `UX-DR12`)."""

    archetype: str
    register_label: str
    vocabulary_tier: Literal[
        "N1_N2_EXECUTIVE",
        "N2_PRODUCT_RULES",
        "N3_TECHNICAL_LINEAGE",
        "N3_SECOPS_GATES",
    ]
    highlighted_indicators: tuple[str, ...]
    response_prefix_fr: str
    register_label_en: str = ""
    highlighted_indicators_en: tuple[str, ...] = ()
    response_prefix_en: str = ""


_VocabTier = Literal[
    "N1_N2_EXECUTIVE",
    "N2_PRODUCT_RULES",
    "N3_TECHNICAL_LINEAGE",
    "N3_SECOPS_GATES",
]

_VOCAB_TIERS: dict[str, _VocabTier] = {
    "EXECUTIVE": "N1_N2_EXECUTIVE",
    "PM": "N2_PRODUCT_RULES",
    "ARCHITECT": "N3_TECHNICAL_LINEAGE",
    "TECH_LEAD": "N3_TECHNICAL_LINEAGE",
    "DEVELOPER": "N3_TECHNICAL_LINEAGE",
    "SECOPS": "N3_SECOPS_GATES",
}

PROFILE_ADAPTATION_MAP: dict[str, ProfileAdaptationSpec] = {
    arch: ProfileAdaptationSpec(
        archetype=arch,
        register_label=str(PROFILE_LABELS_LOCALES["fr"][arch]["register"]),
        vocabulary_tier=_VOCAB_TIERS[arch],
        highlighted_indicators=tuple(
            str(x)
            for x in PROFILE_LABELS_LOCALES["fr"][arch]["indicators"]  # type: ignore[attr-defined]
        ),
        response_prefix_fr=str(PROFILE_LABELS_LOCALES["fr"][arch]["prefix"]),
        register_label_en=str(PROFILE_LABELS_LOCALES["en"][arch]["register"]),
        highlighted_indicators_en=tuple(
            str(x)
            for x in PROFILE_LABELS_LOCALES["en"][arch]["indicators"]  # type: ignore[attr-defined]
        ),
        response_prefix_en=str(PROFILE_LABELS_LOCALES["en"][arch]["prefix"]),
    )
    for arch in ("EXECUTIVE", "PM", "ARCHITECT", "TECH_LEAD", "DEVELOPER", "SECOPS")
}


def resolve_profile_adaptation(archetype: str) -> ProfileAdaptationSpec:
    """Resolve `ProfileAdaptationSpec` for a user's `human_profile_archetype` (`UX-DR12`)."""
    norm = (archetype or "").strip().upper()
    return PROFILE_ADAPTATION_MAP.get(norm, PROFILE_ADAPTATION_MAP["ARCHITECT"])


def resolve_profile_copy_for_locale(
    spec: ProfileAdaptationSpec, *, locale: str = "fr"
) -> tuple[str, tuple[str, ...], str]:
    """Return `(register_label, highlighted_indicators, response_prefix)` in `locale`."""
    if (locale or "fr").strip().lower().startswith("en"):
        return (
            spec.register_label_en or spec.register_label,
            spec.highlighted_indicators_en or spec.highlighted_indicators,
            spec.response_prefix_en or spec.response_prefix_fr,
        )
    return spec.register_label, spec.highlighted_indicators, spec.response_prefix_fr


__all__ = [
    "CONSTITUTIONAL_LAYER_1_TEXT",
    "CONSTITUTIONAL_LAYER_1_TEXT_EN",
    "CONSTITUTIONAL_LAYER_1_TEXT_FR",
    "PROFILE_ADAPTATION_MAP",
    "AssistantIntentKind",
    "AssistantLayerId",
    "ProfileAdaptationSpec",
    "resolve_profile_adaptation",
    "resolve_profile_copy_for_locale",
    "sanitize_layer_marker_tags",
]
