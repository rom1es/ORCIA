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
  workspaceTopology: {
    panelTitle: "Arbre d'Équipes (OrgUnit), Workspaces Multi-Sources & 5 Permissions Dissociées",
    panelSubtitle:
      "Authentification Hybride Bi-Mode (OIDC + Locale Argon2id/TOTP), Roll-up ascendant et isolation inter-Workspaces.",
    personaSelectorLabel: "Simuler la persona RBAC active",
    personas: {
      karim: "Karim — PLATFORM_ADMIN (Entreprise)",
      claire: "Claire — BU_DIRECTOR (Roll-up Observateur)",
      marc: "Marc — TEAM_LEAD (Sous-Équipe Checkout)",
      nadia: "Nadia — CONTRIBUTOR (Développeuse)",
      partenaire: "Partenaire Externe (Invité Workspace 1)",
    },
    finopsRollupPrefix: "Roll-up FinOps consolidé",
    confidentialExcludedNotice:
      "Les Workspaces marqués CONFIDENTIAL_RESTRICTED bloquent tout Roll-up ascendant sur le contenu métier.",
    datasourcesCountPrefix: "Sources fédérées rattachées",
    catalogPermissionsTitle: "5 Permissions Dissociées du Catalogue & Protection Boîte Noire",
    sourceMaskedBadgeLabel: "🔒 Source masquée (READ_SOURCE=False)",
    sourceOpenBadgeLabel: "📖 Source accessible (READ_SOURCE=True)",
    inspectSourceButtonLabel: "Inspecter la source",
    sourceDeniedErrorBanner: "HTTP 403 ERR_READ_SOURCE_DENIED — Permission READ_SOURCE requise",
    sourceAllowedBannerPrefix: "HTTP 200 OK — Source autorisée",
    mutationGuardButtonLabel: "Tester ScopeAccessGuard (Mutation)",
    mutationAllowedBanner: "HTTP 200 OK — Mutation autorisée (Contributeur)",
    mutationDeniedObserverBanner:
      "HTTP 403 ERR_OBSERVER_MODE_READ_ONLY — Mutation rejetée en mode Observateur",
  },
  catalogExplorer: {
    panelTitle: "Catalogue Fédéré Multi-Sources, Cache CAS SHA-256 & Surcharges à 4 Niveaux",
    panelSubtitle:
      "Résolution à la volée (< 50 ms sur cache chaud cas/<sha256>), cycle de publication gouverné et Adaptateur BMAD.",
    filterAllSchemesLabel: "Tous les schémas",
    maskedSourceBadgeLabel: "🔒 Source masquée",
    openSourceBadgeLabel: "📖 Source ouverte",
    resolveCasButtonLabel: "Résoudre CAS (< 50 ms)",
    casResolvedBannerPrefix: "HTTP 200 OK — Objet immuable résolu",
    promoteScopeButtonLabel: "Promouvoir la portée",
    promotedBannerPrefix: "HTTP 200 OK — Portée promue",
    promoteDeniedObserverBanner:
      "HTTP 403 ERR_OBSERVER_MODE_READ_ONLY — Promotion refusée en mode Observateur",
    overrideSectionTitle: "Fusion Déclarative à 4 Niveaux (Base -> Team -> Workspace -> User)",
    overrideSectionSubtitle:
      "Hiérarchie pure non mutante avec génération déterministe du manifeste cryptographique run-lock.json.",
    overrideLayers: {
      base: "1. Base (db://workflow)",
      teamParent: "2a. Équipe Parente (Architecture)",
      teamSub: "2b. Sous-Équipe (Checkout)",
      workspace: "3. Workspace (3 git + 2 jira + 2 confluence)",
      user: "4. Utilisateur (Marc Tech Lead)",
    },
    runLockTitle: "Manifeste run-lock.json (Sources épinglées SHA-256)",
    bmadAdapterTitle: "Adaptateur BMAD sans perte (SKILL.md + customize.toml + steps/*.md)",
    bmadImportButtonLabel: "Importer un Pack BMAD",
    bmadImportedBanner:
      "HTTP 200 OK — Pack BMAD converti en WorkflowDefinitionEntity (source_format=BMAD_PACK) et épinglé dans cas/<sha256>",
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
