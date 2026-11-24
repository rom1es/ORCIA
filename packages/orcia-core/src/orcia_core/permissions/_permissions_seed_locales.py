"""Bilingual seed strings for permissions org units, workspaces & broker (`Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale

ORG_UNIT_SEED_NAMES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "orcia-enterprise": "Entreprise ORCIA Group",
        "bu-digital-payments": "BU Digital & Paiements",
        "team-architecture-parent": "Équipe Parente Architecture & Plateforme",
        "subteam-checkout-squad": "Sous-Équipe Checkout & Core Solutions",
        "team-partner-external": "Équipe Partenaire Intégration",
    },
    "en": {
        "orcia-enterprise": "ORCIA Group Enterprise",
        "bu-digital-payments": "Digital & Payments BU",
        "team-architecture-parent": "Architecture & Platform Parent Team",
        "subteam-checkout-squad": "Checkout & Core Solutions Sub-Team",
        "team-partner-external": "External Integration Partner Team",
    },
}

WORKSPACE_SEED_NAMES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "ws-solution-paiement": "Workspace 1 : Solution Paiement",
        "ws-solution-fidelite": "Workspace 2 : Solution Fidélité",
        "ws-projet-confidentiel": "Workspace 3 : Projet Confidentiel M&A",
    },
    "en": {
        "ws-solution-paiement": "Workspace 1: Payment Solution",
        "ws-solution-fidelite": "Workspace 2: Loyalty Solution",
        "ws-projet-confidentiel": "Workspace 3: Confidential M&A Project",
    },
}

BROKER_POLICY_APPROVERS: dict[SupportedLocale, dict[str, str]] = {
    "fr": {"confluence_pay": "Architecture Paiement & Conformité PCI"},
    "en": {"confluence_pay": "Payment Architecture & PCI Compliance"},
}

BROKER_POLICY_PROCEDURES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "pol-git-payments-checkout": (
            "### Procédure d'habilitation Dépôts Git Paiement\n"
            "1. Ouvrir le ticket Jira IAM pré-rempli.\n"
            "2. Faire valider `ROLE_GIT_PAYMENTS_MAINTAINER` par `SecOps & Core Payments IAM`.\n"
            "3. Cliquer sur **Rejouer l'étape** dans le Dock Permission Broker."
        ),
        "pol-git-archi-security-blackbox": (
            "### Procédure d'habilitation Agents Architecture & SecOps\n"
            "Validation par le comité Architecture & Security Board (SLA 8h)."
        ),
        "pol-confluence-pay-spaces": (
            "### Accès Espace Confluence Architecture PCI\n"
            "Octroi du groupe `CONFLUENCE_PAY_ADR_READER` sous 2h ouvrées."
        ),
        "pol-jira-secops-projects": (
            "### Habilitation Transitions Jira SecOps\n"
            "Requiert le rôle `JIRA_SECOPS_TRANSITION_ACTOR` validé par CSIRT."
        ),
        "pol-git-default-fallback": (
            "### Procédure d'habilitation Dépôt Git\n"
            "1. Ouvrir la demande d'accès IAM pré-remplie auprès de `SecOps & Platform IAM`.\n"
            "2. Faire valider le rôle `ROLE_GIT_REPOSITORY_READER` pour la source demandée.\n"
            "3. Cliquer sur **Relancer l'étape** une fois l'accès confirmé."
        ),
        "pol-jira-default-fallback": (
            "### Procédure d'habilitation Projet Jira\n"
            "1. Ouvrir la demande d'accès IAM pré-remplie auprès de `SecOps & PMO IAM`.\n"
            "2. Faire valider `ROLE_JIRA_PROJECT_CONTRIBUTOR` puis relancer l'étape."
        ),
        "pol-confluence-default-fallback": (
            "### Procédure d'habilitation Espace Confluence\n"
            "1. Ouvrir la demande d'accès IAM pré-remplie.\n"
            "2. Faire valider `ROLE_CONFLUENCE_SPACE_READER` puis relancer l'étape."
        ),
        "pol-mcp-default-fallback": (
            "### Procédure d'habilitation Outil MCP\n"
            "1. Faire valider `ROLE_MCP_TOOL_EXECUTOR` par `Platform Engineering & SecOps`.\n"
            "2. Relancer l'étape."
        ),
    },
    "en": {
        "pol-git-payments-checkout": (
            "### Payment Git Repositories Enablement Procedure\n"
            "1. Open the pre-filled IAM Jira ticket.\n"
            "2. Request `ROLE_GIT_PAYMENTS_MAINTAINER` approval from "
            "`SecOps & Core Payments IAM`.\n"
            "3. Click **Replay Step** in the Permission Broker Dock."
        ),
        "pol-git-archi-security-blackbox": (
            "### Architecture & SecOps Agents Enablement Procedure\n"
            "Approved by the Architecture & Security Board (8h SLA)."
        ),
        "pol-confluence-pay-spaces": (
            "### PCI Architecture Confluence Space Access\n"
            "`CONFLUENCE_PAY_ADR_READER` group granted within 2 business hours."
        ),
        "pol-jira-secops-projects": (
            "### SecOps Jira Transitions Enablement\n"
            "Requires `JIRA_SECOPS_TRANSITION_ACTOR` role approved by CSIRT."
        ),
        "pol-git-default-fallback": (
            "### Git Repository Enablement Procedure\n"
            "1. Open the pre-filled IAM access request with `SecOps & Platform IAM`.\n"
            "2. Request `ROLE_GIT_REPOSITORY_READER` approval for the target source.\n"
            "3. Click **Replay Step** once access is confirmed."
        ),
        "pol-jira-default-fallback": (
            "### Jira Project Enablement Procedure\n"
            "1. Open the pre-filled IAM access request with `SecOps & PMO IAM`.\n"
            "2. Request `ROLE_JIRA_PROJECT_CONTRIBUTOR` approval, then replay step."
        ),
        "pol-confluence-default-fallback": (
            "### Confluence Space Enablement Procedure\n"
            "1. Open the pre-filled IAM access request.\n"
            "2. Request `ROLE_CONFLUENCE_SPACE_READER` approval, then replay step."
        ),
        "pol-mcp-default-fallback": (
            "### MCP Tool Enablement Procedure\n"
            "1. Request `ROLE_MCP_TOOL_EXECUTOR` approval from `Platform Engineering & SecOps`.\n"
            "2. Replay step."
        ),
    },
}

__all__ = [
    "BROKER_POLICY_APPROVERS",
    "BROKER_POLICY_PROCEDURES",
    "ORG_UNIT_SEED_NAMES",
    "WORKSPACE_SEED_NAMES",
]
