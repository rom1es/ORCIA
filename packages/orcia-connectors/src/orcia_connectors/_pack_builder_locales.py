"""Bilingual (`fr`/`en`) descriptors for Pack Builder processes (`AD-20`, `Story 27.8`)."""

from __future__ import annotations

from dataclasses import dataclass


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

__all__ = [
    "GovernedPackBuilderProcessSpec",
    "ORCIA_DOCUMENTATION_GENERATOR_PROCESS",
    "PACK_BUILDER_PROCESSES",
]
