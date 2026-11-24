"""Bilingual locale bundles for Pack Builder, Studio & Workspace Rebase (`Story 27.7`)."""

from __future__ import annotations

from dataclasses import dataclass

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale


@dataclass(frozen=True, slots=True)
class PackBuilderAgentMeta:
    slug: str
    handle_fr: str
    handle_en: str
    role_fr: str
    role_en: str


PACK_BUILDER_AGENTS_META: tuple[PackBuilderAgentMeta, ...] = (
    PackBuilderAgentMeta(
        slug="architecte-metier-pack",
        handle_fr="@Architecte-Métier-Pack",
        handle_en="@Pack-Domain-Architect",
        role_fr=(
            "Structuration de la chaîne causale ADN (DIRECTIVE ➔ NORME ➔ MÉCANISME), "
            "du glossaire socle et des profils humains"
        ),
        role_en=(
            "Causal DNA chain (DIRECTIVE ➔ NORM ➔ MECHANISM), core glossary & human "
            "profiles structuring"
        ),
    ),
    PackBuilderAgentMeta(
        slug="ingenieur-prompt-et-workflow",
        handle_fr="@Ingénieur-Prompt-et-Workflow",
        handle_en="@Prompt-And-Workflow-Engineer",
        role_fr="Conception des agents spécialisés, des graphes DAG DBOS et des Gates d'arbitrage",
        role_en="Specialized agents, DBOS DAG workflows & arbitration Gates design",
    ),
    PackBuilderAgentMeta(
        slug="certificateur-securite-et-sandbox",
        handle_fr="@Certificateur-Sécurité-et-Sandbox",
        handle_en="@Security-And-Sandbox-Certifier",
        role_fr=(
            "Compilation et certification des règles Starlark Palier 1b (< 2 ms) et "
            "audit des outils lourds en Sandbox Palier 2"
        ),
        role_en=(
            "Tier 1b Starlark rule certification (< 2 ms) & Tier 2 Container Sandbox "
            "security auditing"
        ),
    ),
    PackBuilderAgentMeta(
        slug="redacteur-documentation-orcia",
        handle_fr="@Rédacteur-Documentation-Orcia",
        handle_en="@Orcia-Documentation-Writer",
        role_fr=(
            "Rédaction bilingue (fr/en) des fiches HelpArticle et validation "
            "déterministe validate_help_article (< 5 s)"
        ),
        role_en=(
            "Bilingual (fr/en) HelpArticle authoring & deterministic "
            "validate_help_article (< 5 s) validation"
        ),
    ),
)

PACK_BUILDER_DIAG_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "tier1b": "Palier 1b Starlark ({ms:.3f} ms) — PASS={pass_ok}, FAIL={fail_ok}",
        "tier2": "Palier 2 Sandbox OCI rootless (--network=none, {ms:.3f} ms) — digest={digest}",
    },
    "en": {
        "tier1b": "Tier 1b Starlark ({ms:.3f} ms) — PASS={pass_ok}, FAIL={fail_ok}",
        "tier2": "Tier 2 Rootless OCI Sandbox (--network=none, {ms:.3f} ms) — digest={digest}",
    },
}

STUDIO_SEED_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "pre_prompt": (
            "Respecter l'ontologie N1..N3, citer chaque source et ne jamais inventer de faits."
        ),
        "wf_title": "Conception & Validation Technique",
        "p1_label": "Périmètre Fonctionnel",
        "p2_label": "Niveau de Criticité",
        "sec1": "## 1. Intention & Cadrage",
        "sec2": "## 2. Analyse d'Impact",
        "sec3": "## 3. Décisions Retenues",
        "node1_title": "Cadrage & Intention Métier",
        "node2_title": "Analyse Architecture & Sécurité",
        "layer1_title": "Collecte Chunks KB & Contrat",
        "layer2_title": "Vérification Axiomes Ontologie N1..N3",
        "layer3_title": "Synthèse Livrable & Pré-Gate",
        "pack_sdlc_name": "Pack Ingénierie Logicielle (SDLC)",
        "pack_legacy_name": "Pack Finance Legacy (Désinstallé)",
        "dry_run_content": "{sec}\nContenu d'essai pour {validated}.",
    },
    "en": {
        "pre_prompt": ("Follow the L1..L3 ontology, cite every source, and never fabricate facts."),
        "wf_title": "Design & Technical Validation",
        "p1_label": "Functional Scope",
        "p2_label": "Criticality Level",
        "sec1": "## 1. Intent & Framing",
        "sec2": "## 2. Impact Analysis",
        "sec3": "## 3. Retained Decisions",
        "node1_title": "Business Intent & Framing",
        "node2_title": "Architecture & Security Analysis",
        "layer1_title": "KB Chunks & Contract Collection",
        "layer2_title": "Ontology Axioms L1..L3 Verification",
        "layer3_title": "Deliverable Synthesis & Pre-Gate",
        "pack_sdlc_name": "Software Engineering Pack (SDLC)",
        "pack_legacy_name": "Legacy Finance Pack (Uninstalled)",
        "dry_run_content": "{sec}\nDry-run content for {validated}.",
    },
}

REBASE_SPEC_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "heading": "# Spécification Technique — {ticket_key}\n\n",
        "sec1": "## 1. Contexte & Périmètre\n{ticket_summary}\n\n",
        "sec2": "## 2. Contrats d'Interface & Impacts\nValidation via Gate adaptative.\n",
    },
    "en": {
        "heading": "# Technical Specification — {ticket_key}\n\n",
        "sec1": "## 1. Context & Scope\n{ticket_summary}\n\n",
        "sec2": "## 2. Interface Contracts & Impacts\nAdaptive Gate validation.\n",
    },
}


def get_studio_seed_copy(locale: SupportedLocale = DEFAULT_LOCALE) -> dict[str, str]:
    return STUDIO_SEED_LOCALES.get(locale, STUDIO_SEED_LOCALES[DEFAULT_LOCALE])


__all__ = [
    "PACK_BUILDER_AGENTS_META",
    "PACK_BUILDER_DIAG_LOCALES",
    "REBASE_SPEC_LOCALES",
    "STUDIO_SEED_LOCALES",
    "get_studio_seed_copy",
]
