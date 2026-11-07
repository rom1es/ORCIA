"""ORCIA System Pack Builder (`packages/orcia-pack-builder`, `AD-20`, `Story 11.4` & `Story 11.5`).

Pre-installed system business pack registered via `orcia.packs` `entry_points`.
Provides the 4 specialized Pack Builder agents (`@Architecte-Métier-Pack`,
`@Ingénieur-Prompt-et-Workflow`, `@Certificateur-Sécurité-et-Sandbox`,
`@Rédacteur-Documentation-Orcia`) and the 5 governed processes (`create-business-pack`,
`evolve-business-pack`, `certify-pack-tool`, `export-from-workspace-to-pack`,
`generate-and-attach-help`) without polluting `orcia_kernel` or `orcia_core`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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


@dataclass(frozen=True, slots=True)
class GovernedPackBuilderProcessSpec:
    """Descriptor for one of the governed processes of `orcia-pack-builder`."""

    process_number: int
    slug: str
    uri: str
    title_fr: str
    title_en: str
    lead_agent_handle: str
    requires_human_anchor: bool


ORCIA_DOCUMENTATION_GENERATOR_PROCESS = GovernedPackBuilderProcessSpec(
    process_number=6,
    slug="generate-orcia-documentation",
    uri="orcia://pack-builder/workflows/generate-orcia-documentation",
    title_fr=(
        "Processus 6 — Générer et Synchroniser la Documentation Complète d'ORCIA "
        "(Guides Écrans, FAQ Architecture & Catalogue)"
    ),
    title_en=(
        "Process 6 — Generate and Synchronize Full ORCIA Documentation "
        "(Screen Guides, Architecture FAQ & Catalog)"
    ),
    lead_agent_handle="@Rédacteur-Documentation-Orcia",
    requires_human_anchor=False,
)


PACK_BUILDER_PROCESSES: tuple[GovernedPackBuilderProcessSpec, ...] = (
    GovernedPackBuilderProcessSpec(
        process_number=1,
        slug="create-business-pack",
        uri="orcia://pack-builder/workflows/create-business-pack",
        title_fr=(
            "Processus 1 — Créer un Pack Métier (Ancrage Violet + Chaîne ADN + Starlark < 2 ms)"
        ),
        title_en="Process 1 — Create Business Pack (Violet Anchor + DNA Chain + Starlark < 2 ms)",
        lead_agent_handle="@Architecte-Métier-Pack",
        requires_human_anchor=True,
    ),
    GovernedPackBuilderProcessSpec(
        process_number=2,
        slug="evolve-business-pack",
        uri="orcia://pack-builder/workflows/evolve-business-pack",
        title_fr="Processus 2 — Évolution & Simulation d'Impact What-If (@vX.Y.Z)",
        title_en="Process 2 — Evolution & What-If Impact Simulation (@vX.Y.Z)",
        lead_agent_handle="@Ingénieur-Prompt-et-Workflow",
        requires_human_anchor=False,
    ),
    GovernedPackBuilderProcessSpec(
        process_number=3,
        slug="certify-pack-tool",
        uri="orcia://pack-builder/workflows/certify-pack-tool",
        title_fr=(
            "Processus 3 — Certification Règles Starlark (Palier 1b < 2 ms) & "
            "Outils Sandbox (Palier 2)"
        ),
        title_en=(
            "Process 3 — Starlark Rules (Tier 1b < 2 ms) & Sandbox Tools (Tier 2) Certification"
        ),
        lead_agent_handle="@Certificateur-Sécurité-et-Sandbox",
        requires_human_anchor=False,
    ),
    GovernedPackBuilderProcessSpec(
        process_number=4,
        slug="export-from-workspace-to-pack",
        uri="orcia://pack-builder/workflows/export-from-workspace-to-pack",
        title_fr="Processus 4 — Promotion & Nettoyage d'une Brique d'Espace vers un Pack Partagé",
        title_en="Process 4 — Workspace Asset Scrubbing & Promotion to Shared Pack",
        lead_agent_handle="@Ingénieur-Prompt-et-Workflow",
        requires_human_anchor=False,
    ),
    GovernedPackBuilderProcessSpec(
        process_number=5,
        slug="generate-and-attach-help",
        uri="orcia://pack-builder/workflows/generate-and-attach-help",
        title_fr=(
            "Processus 5 — Génération Bilingue HelpArticle, Gate validate_help_article (< 5 s) "
            "& Rattachement (< 100 ms)"
        ),
        title_en=(
            "Process 5 — Bilingual HelpArticle Generation, validate_help_article Gate (< 5 s) "
            "& Hot Attach (< 100 ms)"
        ),
        lead_agent_handle="@Rédacteur-Documentation-Orcia",
        requires_human_anchor=False,
    ),
    ORCIA_DOCUMENTATION_GENERATOR_PROCESS,
)

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
