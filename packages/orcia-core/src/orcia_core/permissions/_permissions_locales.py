"""Bilingual locale bundles for permissions, MCP tokens, broker, and org units (`Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale

DEFAULT_SERVICE_CATALOG_TITLES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "blackbox": "Agent d'Audit SecOps Boîte Noire (Équipe Parente)",
        "checkout": "Skill Validation Checkout (Source Ouverte Équipe)",
    },
    "en": {
        "blackbox": "Black-Box SecOps Audit Agent (Parent Team)",
        "checkout": "Checkout Validation Skill (Team Open Source)",
    },
}

DEFAULT_SERVICE_PERSONA_NAMES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "karim": "Karim (Ingénieur Plateforme)",
        "claire": "Claire (Directrice BU / Équipe Parente)",
        "marc": "Marc (Chef d'Équipe / Tech Lead)",
        "nadia": "Nadia (Développeuse Senior)",
        "partenaire": "Partenaire Externe (Invité Workspace 1)",
    },
    "en": {
        "karim": "Karim (Platform Engineer)",
        "claire": "Claire (BU Director / Parent Team)",
        "marc": "Marc (Team Lead / Tech Lead)",
        "nadia": "Nadia (Senior Developer)",
        "partenaire": "External Partner (Workspace 1 Guest)",
    },
}

MCP_TOKEN_DEFAULT_LABEL_LOCALES: dict[SupportedLocale, str] = {
    "fr": "Clé personnelle d'éditeur",
    "en": "Personal IDE Key",
}

BROKER_WORKSPACE_SOURCE_LABEL_LOCALES: dict[SupportedLocale, str] = {
    "fr": "**Source d'espace associée** : `{alias}` (`{uri}`)",
    "en": "**Associated space source**: `{alias}` (`{uri}`)",
}

ACCESS_REQUEST_SUMMARY_LOCALES: dict[SupportedLocale, str] = {
    "fr": "[ORCIA Permission Broker] {required_role} sur {target_uri}",
    "en": "[ORCIA Permission Broker] {required_role} on {target_uri}",
}

ACCESS_REQUEST_DESC_LOCALES: dict[SupportedLocale, str] = {
    "fr": (
        "Demande d'accès ({execution_identity}) pour l'étape {step_key} "
        "par {requester_email} — Approbateur: {approver_team}"
    ),
    "en": (
        "Access request ({execution_identity}) for step {step_key} "
        "by {requester_email} — Approver: {approver_team}"
    ),
}

DAY0_ADMIN_NAME_LOCALES: dict[SupportedLocale, str] = {
    "fr": "Administrateur Plateforme (Jour 0)",
    "en": "Platform Administrator (Day 0)",
}

ORG_UNIT_DELETION_NOUNS: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "unit_singular": "sous-unité enfant",
        "unit_plural": "sous-unités enfants",
        "ws_singular": "espace de travail rattaché",
        "ws_plural": "espaces de travail rattachés",
        "conjunction": " et ",
    },
    "en": {
        "unit_singular": "child sub-unit",
        "unit_plural": "child sub-units",
        "ws_singular": "attached workspace",
        "ws_plural": "attached workspaces",
        "conjunction": " and ",
    },
}


def format_org_unit_deletion_details(
    *,
    child_units_count: int,
    attached_workspaces_count: int,
    locale: SupportedLocale = DEFAULT_LOCALE,
) -> str:
    """Format localized non-empty counts for org unit deletion errors."""
    nouns = ORG_UNIT_DELETION_NOUNS.get(locale, ORG_UNIT_DELETION_NOUNS[DEFAULT_LOCALE])
    parts: list[str] = []
    if child_units_count > 0:
        unit_lbl = nouns["unit_plural"] if child_units_count > 1 else nouns["unit_singular"]
        parts.append(f"{child_units_count} {unit_lbl}")
    if attached_workspaces_count > 0:
        ws_lbl = nouns["ws_plural"] if attached_workspaces_count > 1 else nouns["ws_singular"]
        parts.append(f"{attached_workspaces_count} {ws_lbl}")
    return nouns["conjunction"].join(parts)


__all__ = [
    "ACCESS_REQUEST_DESC_LOCALES",
    "ACCESS_REQUEST_SUMMARY_LOCALES",
    "BROKER_WORKSPACE_SOURCE_LABEL_LOCALES",
    "DAY0_ADMIN_NAME_LOCALES",
    "DEFAULT_SERVICE_CATALOG_TITLES",
    "DEFAULT_SERVICE_PERSONA_NAMES",
    "MCP_TOKEN_DEFAULT_LABEL_LOCALES",
    "ORG_UNIT_DELETION_NOUNS",
    "format_org_unit_deletion_details",
]
