"""Bilingual locale bundles for Control Center & Notifications/Claims (`Story 27.7`)."""

from __future__ import annotations

from dataclasses import dataclass

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale


@dataclass(frozen=True, slots=True)
class GuidanceStepLocale:
    step_number: int
    title: str
    description: str
    action_command: str


GUIDANCE_DRAWER_STEPS_LOCALES: dict[SupportedLocale, tuple[GuidanceStepLocale, ...]] = {
    "fr": (
        GuidanceStepLocale(
            1,
            "1. Qualifier la phase du Produit / Workspace",
            "Sélectionner RUN, BUILD ou MIGRATION dans l'onglet Gouvernance.",
            "set-lifecycle-phase",
        ),
        GuidanceStepLocale(
            2,
            "2. Rattacher les sources dédiées et partagées",
            "Connecter les dépôts documentaires, bases et référentiels avec un TTL de fraîcheur.",
            "init-datasource",
        ),
        GuidanceStepLocale(
            3,
            "3. Configurer l'identité d'exécution (Passthrough vs Compte de Service)",
            "Choisir passthrough (défaut sécurisé) ou service_account pour l'indexation.",
            "configure-execution-identity",
        ),
        GuidanceStepLocale(
            4,
            "4. Vérifier l'alignement dans le Graphe Tripartite",
            "Inspecter les alertes [STALE_WARNING] et lancer une synchronisation RAG hybride.",
            "sync-tripartite-graph",
        ),
        GuidanceStepLocale(
            5,
            "5. Activer les Workflows et Surcharges 4 niveaux",
            "Valider les Gates de gouvernance et lancer un premier Run supervisé.",
            "launch-supervised-run",
        ),
    ),
    "en": (
        GuidanceStepLocale(
            1,
            "1. Qualify the Product / Workspace lifecycle phase",
            "Select RUN, BUILD or MIGRATION in the Governance tab.",
            "set-lifecycle-phase",
        ),
        GuidanceStepLocale(
            2,
            "2. Attach dedicated and shared datasources",
            "Connect document repositories, databases and registries with a freshness TTL.",
            "init-datasource",
        ),
        GuidanceStepLocale(
            3,
            "3. Configure execution identity (Passthrough vs Service Account)",
            "Choose passthrough (secure default) or service_account for indexing.",
            "configure-execution-identity",
        ),
        GuidanceStepLocale(
            4,
            "4. Verify alignment in the Tripartite Graph",
            "Inspect [STALE_WARNING] alerts and trigger a hybrid RAG synchronization.",
            "sync-tripartite-graph",
        ),
        GuidanceStepLocale(
            5,
            "5. Enable Workflows and 4-level Overrides",
            "Validate Governance Gates and launch a first supervised Run.",
            "launch-supervised-run",
        ),
    ),
}

CONTROL_CENTER_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "ws_1_name": "Workspace 1 — Paiements & Checkout Web",
        "ws_2_name": "Workspace 2 — Core Banking & Ledger",
        "ws_3_name": "Workspace 3 — Audit Confidentiel SecOps (Restreint)",
        "run_1_title": "Run #701 — Arbitrage Topologie Paiements v2",
        "run_1_summary": "Synthèse d'architecture prête pour arbitrage humain.",
        "run_2_title": "Run #702 — Audit Bascule Core Ledger",
        "run_2_summary": "Rapport de conformité Core Ledger généré.",
        "run_3_title": "Run #703 — Investigation SecOps Restreinte",
        "run_3_summary": "Payload métier confidentiel SecOps.",
        "masked_summary": "[CONFIDENTIAL_RESTRICTED — Payload Métier Masqué]",
        "observer_banner": (
            "👁️ Mode Consultation Seule — Vous suivez ce périmètre en tant qu'Observateur"
        ),
        "override_title": "Arbitrage Topologie & Gates Adaptatives",
        "override_base": "v1.0.0 (Socle Plateforme)",
        "override_team": "seuil_gate_agentique=0.85",
        "override_user_tpl": "mode_execution={user_mode}",
        "nav_cockpit": "Aller au Cockpit & Flux de Travail",
        "nav_cockpit_sub": "Navigation rapide",
        "nav_inbox": "Aller à la Boîte & Mes Runs",
        "nav_inbox_sub": "Notifications & Claims",
        "nav_workspaces": "Aller au Centre de Pilotage des Workspaces",
        "nav_workspaces_sub": "Supervision 4 onglets",
        "nav_catalog": "Aller au Catalogue Fédéré",
        "nav_catalog_sub": "Agents, Skills & Workflows",
        "nav_ontology": "Aller à l'Ontologie & Graphe",
        "nav_ontology_sub": "Concepts SKOS & What-If",
        "nav_governance": "Aller aux Gates & Permissions",
        "nav_governance_sub": "Courtier d'Accès",
        "nav_audit": "Aller à l'Audit & FinOps",
        "nav_audit_sub": "Registre immuable",
        "nav_admin": "Aller à l'Administration",
        "nav_admin_sub": "Topologie & Sécurité",
        "ws_subtitle_tpl": "Cycle {phase} • {visibility}",
    },
    "en": {
        "ws_1_name": "Workspace 1 — Payments & Web Checkout",
        "ws_2_name": "Workspace 2 — Core Banking & Ledger",
        "ws_3_name": "Workspace 3 — Confidential SecOps Audit (Restricted)",
        "run_1_title": "Run #701 — Payments Topology Arbitration v2",
        "run_1_summary": "Architecture synthesis ready for human arbitration.",
        "run_2_title": "Run #702 — Core Ledger Cutover Audit",
        "run_2_summary": "Core Ledger compliance report generated.",
        "run_3_title": "Run #703 — Restricted SecOps Investigation",
        "run_3_summary": "Confidential SecOps business payload.",
        "masked_summary": "[CONFIDENTIAL_RESTRICTED — Business Payload Masked]",
        "observer_banner": "👁️ Read-Only Mode — You are following this scope as an Observer",
        "override_title": "Topology Arbitration & Adaptive Gates",
        "override_base": "v1.0.0 (Platform Baseline)",
        "override_team": "agentic_gate_threshold=0.85",
        "override_user_tpl": "execution_mode={user_mode}",
        "nav_cockpit": "Go to Cockpit & Workflows",
        "nav_cockpit_sub": "Quick navigation",
        "nav_inbox": "Go to Inbox & My Runs",
        "nav_inbox_sub": "Notifications & Claims",
        "nav_workspaces": "Go to Workspaces Control Center",
        "nav_workspaces_sub": "4-tab supervision",
        "nav_catalog": "Go to Federated Catalog",
        "nav_catalog_sub": "Agents, Skills & Workflows",
        "nav_ontology": "Go to Ontology & Graph",
        "nav_ontology_sub": "SKOS concepts & What-If",
        "nav_governance": "Go to Gates & Permissions",
        "nav_governance_sub": "Access Broker",
        "nav_audit": "Go to Audit & FinOps",
        "nav_audit_sub": "Append-only ledger",
        "nav_admin": "Go to Administration",
        "nav_admin_sub": "Topology & Security",
        "ws_subtitle_tpl": "Phase {phase} • {visibility}",
    },
}

NOTIFICATION_CLAIM_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "arb_title": "⚖️ Arbitrage IA requis — Choix de topologie d'isolation",
        "arb_summary": (
            "Deux options d'architecture présentent un score équivalent ; "
            "décision d'équipe requise."
        ),
        "gate_title": "🛡️ Gate Humaine Adaptative — Revue du Briefing 4 blocs",
        "gate_summary": "Validation par découpage attendue sur le livrable de sécurité.",
        "claim_inbox": "Prise en charge directe — Relecture en boîte de réception",
        "claim_prefix": "Prise en charge directe — {readable}",
        "lock_acquired_cockpit": "Verrou de présence acquis depuis le Cockpit.",
        "notif_ws_name": "Espace Notifications Équipe",
    },
    "en": {
        "arb_title": "⚖️ AI Arbitration Required — Isolation Topology Choice",
        "arb_summary": "Two architecture options have an equivalent score; team decision required.",
        "gate_title": "🛡️ Adaptive Human Gate — 4-Block Briefing Review",
        "gate_summary": "Sectioned validation expected on the security deliverable.",
        "claim_inbox": "Direct claim — Inbox review",
        "claim_prefix": "Direct claim — {readable}",
        "lock_acquired_cockpit": "Presence lock acquired from Cockpit.",
        "notif_ws_name": "Team Notifications Space",
    },
}


def get_cc_copy(locale: SupportedLocale = DEFAULT_LOCALE) -> dict[str, str]:
    return CONTROL_CENTER_LOCALES.get(locale, CONTROL_CENTER_LOCALES[DEFAULT_LOCALE])


def get_notif_copy(locale: SupportedLocale = DEFAULT_LOCALE) -> dict[str, str]:
    return NOTIFICATION_CLAIM_LOCALES.get(locale, NOTIFICATION_CLAIM_LOCALES[DEFAULT_LOCALE])


__all__ = [
    "CONTROL_CENTER_LOCALES",
    "GUIDANCE_DRAWER_STEPS_LOCALES",
    "GuidanceStepLocale",
    "NOTIFICATION_CLAIM_LOCALES",
    "get_cc_copy",
    "get_notif_copy",
]
