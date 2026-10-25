import type { TranslationDictionary } from "../types";

export const frDictionary: TranslationDictionary = {
  locale: "fr",
  shell: {
    brandTitle: "ORCIA",
    brandSubtitle: "Cockpit Obsidienne & Studio Jour",
    sidebarNavigationAriaLabel: "Navigation Globale à 7 Modules",
    sidebarToggleExpandLabel: "Déplier le menu latéral ([)",
    sidebarToggleCollapseLabel: "Replier le menu latéral ([)",
    scopeSwitcherButtonLabel: "Sélecteur de périmètre (⌘W)",
    scopeSwitcherDialogTitle: "Sélecteur de Périmètre Hiérarchique (⌘W)",
    scopeSwitcherCloseLabel: "Fermer",
    scopeLevels: {
      GLOBAL: "Plateforme Globale",
      BU: "BU / Tribu",
      TEAM: "Équipe",
      WORKSPACE: "Workspace Solution",
    },
    accessModes: {
      CONTRIBUTOR_ACTION_REQUIRED: "Contributeur (Action requise)",
      READ_ONLY_OBSERVER: "Consultation seule (Observateur)",
    },
    modules: {
      cockpit: "Cockpit & Chat",
      inbox: "Boîte & Mes Runs",
      catalog: "Catalogue Fédéré",
      ontology: "Ontologie & KB",
      gates: "Gates & Habilitations",
      finops: "FinOps & Audit",
      admin: "Administration & Pilotage des Workspaces",
    },
    staleWarningBadgeLabel: "! [STALE_WARNING]",
    humanProfilePrefixLabel: "Profil Humain",
    conciergeDockTitle: "Agent Concierge & Permission Broker",
    conciergeDockSubtitle: "Exécution Passthrough gouvernée",
    conciergeDockToggleExpandLabel: "Déplier le Dock Concierge (])",
    conciergeDockToggleCollapseLabel: "Replier le Dock Concierge (])",
    conciergePermissionBrokerReadyLabel: "Permission Broker actif",
    conciergeInputPlaceholder: "Poser une question au Concierge ou diagnostiquer un accès 403...",
    conciergeSendLabel: "Envoyer au Concierge",
    localeSwitchLabel: "Langue",
    mobileTabs: {
      inbox: "🔔 Inbox",
      chat: "💬 Arbitrage/Chat",
      briefing: "📄 Briefing",
    },
  },
  humanAnchor: {
    badgeTitle: "✍️ ANCRAGE HUMAIN OBLIGATOIRE (human_authored_required: true)",
    authorLabel: "Auteur humain",
    placeholderText: "Saisissez vos hypothèses structurantes (rédaction humaine obligatoire)...",
    submitLabel: "Signer l'ancrage humain",
    defaultSectionTitle: "Intentions & Contraintes Architecturales",
    defaultAuthorName: "Architecte / Tech Lead",
    defaultValue: "Isolation hexagonale stricte et contrat OpenAPI 3.1 sans dérive (0-diff).",
  },
  modulePages: {
    cockpit: {
      subtitle: "Espace de co-conception Human-Led, Agent-Accelerated",
      description:
        "Pilotez vos Workflows durables, rédigez les Ancres Humaines Obligatoires et arbitrez les matrices de décision.",
      uriBadgeExample: "orcia://system/workflows/concierge-agent",
    },
    inbox: {
      subtitle: "Boîte de Notifications Unifiée & Verrouillage Temps Réel (< 500ms)",
      description:
        "Consultez vos Workflow Runs actifs en mode Contributeur ou Observateur et prenez en charge les étapes en attente.",
      uriBadgeExample: "orcia://runs/active/inbox",
    },
    catalog: {
      subtitle: "Catalogue Fédéré Multi-Sources & Cache CAS SHA-256",
      description:
        "Explorez les ressources fédérées (git://, jira://, confluence://, db://, nexus://) et les surcharges à 4 niveaux.",
      uriBadgeExample: "git://orcia-core/skills/bmad-pack@sha256:8f4e2b",
    },
    ontology: {
      subtitle: "Ontologie Dynamique à 4 Niveaux & Base de Connaissances RAG",
      description:
        "Gouvernez les concepts (Entreprise, Domaine, Équipe/Workspace, Run Éphémère) et résolvez les alertes [STALE_WARNING].",
      uriBadgeExample: "confluence://ARCHI/ontology-v1@v12",
    },
    gates: {
      subtitle: "Gates Déterministes, Agentiques Cross-Model & Permission Broker",
      description:
        "Auditez les évaluations en DAG de lentilles orthogonales et débloquez les refus 401/403 via Jira.",
      uriBadgeExample: "jira://IAM/PERM-403",
    },
    finops: {
      subtitle: "Journal d'Audit Immuable & Coupe-Circuit Budgétaire FinOps",
      description:
        "Suivez la consommation de tokens par modèle/étape et vérifiez la lignée cryptographique run-lock.json.",
      uriBadgeExample: "db://orcia/audit_ledger",
    },
    admin: {
      subtitle: "Centre de Pilotage Unifié des Workspaces & Unités Organisationnelles",
      description:
        "Administrez l'arbre d'équipes (OrgUnit), les Workspaces Solutions multi-sources et les workflows d'amorçage Jour 0.",
      uriBadgeExample: "orcia://system/bootstrap/init-workspace",
    },
  },
};
