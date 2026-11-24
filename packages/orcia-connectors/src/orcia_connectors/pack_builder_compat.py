"""ORCIA System Pack Builder (`packages/orcia-pack-builder`, `AD-20`, `Story 11.4` & `Story 11.5`).

Pre-installed system business pack registered via `orcia.packs` `entry_points`.
Provides the 4 specialized Pack Builder agents and the 6 governed processes without
polluting `orcia_kernel` or `orcia_core`.
"""

from __future__ import annotations

from typing import Any

from orcia_connectors._pack_builder_locales import (
    ORCIA_DOCUMENTATION_GENERATOR_PROCESS,
    PACK_BUILDER_PROCESSES,
    GovernedPackBuilderProcessSpec,
)
from orcia_core.orchestration.help_generator_and_validator import (
    GeneratedAndAttachedHelpResult,
    HelpArticleDeterministicValidator,
    HelpArticleValidationError,
    HelpArticleValidationReport,
    HelpGenerationAndHotAttachmentService,
    HelpTriggerRegime,
    OrciaDocumentationWorkflowReport,
    OrciaDocumentationWorkflowStepResult,
    run_generate_orcia_documentation_workflow,
)
from orcia_core.orchestration.pack_builder_processes import (
    PACK_BUILDER_AGENTS,
    CreatedBusinessPackResult,
    DnaChainPackSeedSpec,
    PackBuilderAgentSpec,
    PackBuilderSystemService,
    PackBuilderValidationError,
    PackCertificationTier,
    PackEvolutionWhatIfReport,
    PackToolCertificationReport,
    PromotableAssetKind,
    WhatIfWorkspaceImpactItem,
    WorkspaceToPackPromotionResult,
)

__version__: str = "0.1.0"
PACK_BUILDER_URI: str = "orcia://packs/orcia-pack-builder"
PACK_BUILDER_ALL_PROCESSES: tuple[GovernedPackBuilderProcessSpec, ...] = PACK_BUILDER_PROCESSES


def get_pack_builder_manifest() -> dict[str, Any]:
    """Entry-point (`orcia.packs:pack_builder`) returning the declarative manifest."""
    return {
        "pack_id": PACK_BUILDER_URI,
        "pack_slug": "pack-builder",
        "version": __version__,
        "human_anchor_required": True,
        "agents": [
            {
                "slug": a.slug,
                "handle": a.handle,
                "role_fr": a.role_fr,
                "role_en": a.role_en,
            }
            for a in PACK_BUILDER_AGENTS
        ],
        "processes": [
            {
                "process_number": p.process_number,
                "slug": p.slug,
                "uri": p.uri,
                "title_fr": p.title_fr,
                "title_en": p.title_en,
                "lead_agent_handle": p.lead_agent_handle,
                "requires_human_anchor": p.requires_human_anchor,
            }
            for p in PACK_BUILDER_PROCESSES
        ],
    }


__all__ = [
    "CreatedBusinessPackResult",
    "DnaChainPackSeedSpec",
    "GeneratedAndAttachedHelpResult",
    "GovernedPackBuilderProcessSpec",
    "HelpArticleDeterministicValidator",
    "HelpArticleValidationError",
    "HelpArticleValidationReport",
    "HelpGenerationAndHotAttachmentService",
    "HelpTriggerRegime",
    "ORCIA_DOCUMENTATION_GENERATOR_PROCESS",
    "OrciaDocumentationWorkflowReport",
    "OrciaDocumentationWorkflowStepResult",
    "PACK_BUILDER_AGENTS",
    "PACK_BUILDER_ALL_PROCESSES",
    "PACK_BUILDER_PROCESSES",
    "PACK_BUILDER_URI",
    "PackBuilderAgentSpec",
    "PackBuilderSystemService",
    "PackBuilderValidationError",
    "PackCertificationTier",
    "PackEvolutionWhatIfReport",
    "PackToolCertificationReport",
    "PromotableAssetKind",
    "WhatIfWorkspaceImpactItem",
    "WorkspaceToPackPromotionResult",
    "__version__",
    "get_pack_builder_manifest",
    "run_generate_orcia_documentation_workflow",
]
