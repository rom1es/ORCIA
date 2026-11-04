import type {
  BiModeLoginLabels,
  CollapsibleAppRailLabels,
  CommandPaletteModalLabels,
  MobileCompanionLabels,
  ScopedPromptBoxLabels,
  SprintContextWidgetLabels,
  TopHeaderBarLabels,
  WorkspaceControlCenterLabels,
} from "@orcia/ui";

export interface InboxAndCockpitDictionarySection {
  readonly controlCenter: WorkspaceControlCenterLabels;
  readonly commandPalette: CommandPaletteModalLabels;
  readonly mobileCompanion: MobileCompanionLabels;
  readonly biModeLogin: BiModeLoginLabels;
  readonly collapsibleRail: CollapsibleAppRailLabels;
  readonly topHeader: TopHeaderBarLabels;
  readonly sprintWidget: SprintContextWidgetLabels;
  readonly scopedPrompt: ScopedPromptBoxLabels;
}

export const INBOX_AND_COCKPIT_FR_LABELS: InboxAndCockpitDictionarySection = {
  controlCenter: {
    title: "Pilotage des Espaces de Travail et des Équipes",
    scopeSelectorLabel: "Périmètre",
    scopeGlobal: "🌐 Plateforme Globale",
    scopeBu: "🏢 Direction / Pôle",
    scopeTeam: "👥 Équipe",
    scopeWorkspace: "🗂️ Espace de travail",
    tab1Runs: "▶️ 1. Exécutions & Livrables",
    tab2Datasources: "🔌 2. Sources Dédiées & Partagées",
    tab3Workflows: "🤖 3. Processus, Agents & Personnalisation",
    tab4Governance: "👥 4. Équipes, Membres & Droits d'Accès",
    contributorRunsHeader: "Actions Requises de Votre Part",
    observerRunsHeader: "En Suivi — Consultation Seule",
    attachDatasourceButton: "Connecter une nouvelle source",
    launchRunButton: "Lancer un processus",
    observerBannerDefault:
      "👁️ Mode Consultation Seule — Vous suivez cette exécution sans pouvoir la modifier",
    guidanceDrawer: {
      drawerTitle: "Guide de Mise en Route en 5 Étapes",
      toggleExpand: "Afficher les 5 étapes",
      toggleCollapse: "Replier le guide",
      commandPrefix: "Étape",
    },
    lifecycleCard: {
      phaseTitle: "Phase du cycle de vie du projet",
      runBadge: "🟢 EXPLOITATION",
      buildBadge: "🏗️ CONSTRUCTION",
      migrationBadge: "🔄 ÉVOLUTION",
      suggestedWorkflowsTitle: "Processus recommandés pour cette phase",
      readOnlyHint: "Modification désactivée en mode Consultation Seule.",
    },
  },
  commandPalette: {
    modalTitle: "Recherche Rapide & Navigation",
    searchPlaceholder: "Rechercher une exécution, un espace, un terme métier ou un raccourci...",
    closeButton: "Fermer",
    emptyResults: "Aucun résultat ne correspond à votre recherche.",
    contributorBadge: "⚡ Action Requise",
    observerBadge: "👁️ Consultation",
  },
  mobileCompanion: {
    companionTitle: "Vue Mobile Simplifiée",
    tabInbox: "🔔 À traiter",
    tabArbitration: "💬 Arbitrage / Chat",
    tabBriefing: "📄 Synthèse",
    desktopOnlyBanner: "Fonctionnalité disponible sur ordinateur",
    blockedYamlEditorLabel: "Conception avancée de processus",
    blockedHeavyCoEditingLabel: "Édition approfondie de documents longs",
    blockedAdminModuleLabel: "Administration de l'organisation",
    badgeHumanAnchor: "✍️ Rédaction requise",
    badgeAiArbitration: "⚖️ Arbitrage",
    badgeGate: "🛡️ Validation",
    badgeStaleWarning: "🚨 Source à vérifier",
    approveSectionCta: "Valider la section",
    liveRegionDefault: "Mise à jour en direct active",
  },
  biModeLogin: {
    title: "Connexion à ORCIA",
    subtitle:
      "Connectez-vous avec le compte unique de votre organisation ou avec votre compte local",
    primarySsoCta: "Connexion avec le compte de l'organisation (SSO)",
    localAccordionToggle: "Connexion avec un compte local / Administrateur",
    emailLabel: "Adresse e-mail professionnelle",
    passwordLabel: "Mot de passe", // pragma: allowlist secret
    totpLabel: "Code de vérification à 6 chiffres",
    submitLocalCta: "Se connecter",
    errorBannerTitle: "Impossible de vous connecter",
  },
  collapsibleRail: {
    railAriaLabel: "Menu latéral de navigation",
    expandRailCta: "Déplier",
    collapseRailCta: "Réduire",
    activePackPrefix: "Métier actif",
    actionRequiredBadgeLabel: "actions en attente",
    outboxHealthyLabel: "synchronisation active",
  },
  topHeader: {
    workspacePackSelectorLabel: "Espace / Métier",
    sprintSelectorLabel: "Période / Lot actif",
    dbosPg18HealthLabel: "Service d'exécution",
    outboxHealthLabel: "Synchronisation",
  },
  sprintWidget: {
    widgetTitle: "Objectifs de la Période en Cours",
    sprintGoalLabel: "Objectif principal",
    velocityLabel: "Avancement",
    openRisksLabel: "Points d'attention",
    auditRisksCta: "Analyser les points d'attention avec Mon Assistant",
    auditCompletedMessage: "Analyse des points d'attention lancée dans le Cockpit",
  },
  scopedPrompt: {
    boxTitle: "Poser une Question sur cet Espace",
    promptPlaceholder: "Posez une question ou demandez une synthèse sur l'espace sélectionné...",
    ragScopeLabel: "Sources documentaires consultées",
    cognitiveTierLabel: "Niveau d'analyse",
    tier1Label: "Rapide & Concis",
    tier2Label: "Standard Équilibré",
    tier3Label: "Analyse Approfondie",
    submitCta: "Demander à Mon Assistant",
  },
};

export const INBOX_AND_COCKPIT_EN_LABELS: InboxAndCockpitDictionarySection = {
  controlCenter: {
    title: "Workspace and Team Management",
    scopeSelectorLabel: "Scope",
    scopeGlobal: "🌐 Global Platform",
    scopeBu: "🏢 Division / Department",
    scopeTeam: "👥 Team",
    scopeWorkspace: "🗂️ Workspace",
    tab1Runs: "▶️ 1. Executions & Deliverables",
    tab2Datasources: "🔌 2. Dedicated & Shared Sources",
    tab3Workflows: "🤖 3. Processes, Agents & Customization",
    tab4Governance: "👥 4. Teams, Members & Access Rights",
    contributorRunsHeader: "Actions Required from You",
    observerRunsHeader: "Following — Read-Only",
    attachDatasourceButton: "Connect a new source",
    launchRunButton: "Start a process",
    observerBannerDefault:
      "👁️ Read-Only Mode — You are following this execution without edit permissions",
    guidanceDrawer: {
      drawerTitle: "5-Step Getting Started Guide",
      toggleExpand: "Show 5 steps",
      toggleCollapse: "Hide guide",
      commandPrefix: "Step",
    },
    lifecycleCard: {
      phaseTitle: "Project lifecycle phase",
      runBadge: "🟢 OPERATIONS",
      buildBadge: "🏗️ BUILD",
      migrationBadge: "🔄 EVOLUTION",
      suggestedWorkflowsTitle: "Recommended processes for this phase",
      readOnlyHint: "Editing disabled in Read-Only mode.",
    },
  },
  commandPalette: {
    modalTitle: "Quick Search & Navigation",
    searchPlaceholder: "Search an execution, workspace, business term, or shortcut...",
    closeButton: "Close",
    emptyResults: "No matching entries found.",
    contributorBadge: "⚡ Action Required",
    observerBadge: "👁️ Read-Only",
  },
  mobileCompanion: {
    companionTitle: "Simplified Mobile View",
    tabInbox: "🔔 To Do",
    tabArbitration: "💬 Decisions / Chat",
    tabBriefing: "📄 Summary",
    desktopOnlyBanner: "Feature available on desktop computer",
    blockedYamlEditorLabel: "Advanced process design",
    blockedHeavyCoEditingLabel: "In-depth editing of long documents",
    blockedAdminModuleLabel: "Organization administration",
    badgeHumanAnchor: "✍️ Authoring required",
    badgeAiArbitration: "⚖️ Decision",
    badgeGate: "🛡️ Review",
    badgeStaleWarning: "🚨 Source to verify",
    approveSectionCta: "Approve section",
    liveRegionDefault: "Live updates active",
  },
  biModeLogin: {
    title: "Sign in to ORCIA",
    subtitle:
      "Sign in with your organization's single sign-on or your local account",
    primarySsoCta: "Sign in with organization account (SSO)",
    localAccordionToggle: "Sign in with a local / Administrator account",
    emailLabel: "Work email address",
    passwordLabel: "Password", // pragma: allowlist secret
    totpLabel: "6-digit verification code",
    submitLocalCta: "Sign in",
    errorBannerTitle: "Unable to sign in",
  },
  collapsibleRail: {
    railAriaLabel: "Sidebar navigation menu",
    expandRailCta: "Expand",
    collapseRailCta: "Collapse",
    activePackPrefix: "Active domain",
    actionRequiredBadgeLabel: "pending actions",
    outboxHealthyLabel: "sync active",
  },
  topHeader: {
    workspacePackSelectorLabel: "Workspace / Domain",
    sprintSelectorLabel: "Active Period / Batch",
    dbosPg18HealthLabel: "Execution service",
    outboxHealthLabel: "Synchronization",
  },
  sprintWidget: {
    widgetTitle: "Current Period Goals",
    sprintGoalLabel: "Primary goal",
    velocityLabel: "Progress",
    openRisksLabel: "Attention points",
    auditRisksCta: "Analyze attention points with My Assistant",
    auditCompletedMessage: "Attention points analysis started in Cockpit",
  },
  scopedPrompt: {
    boxTitle: "Ask a Question about this Workspace",
    promptPlaceholder: "Ask a question or request a summary for the selected workspace...",
    ragScopeLabel: "Consulted document sources",
    cognitiveTierLabel: "Analysis depth",
    tier1Label: "Fast & Concise",
    tier2Label: "Balanced Standard",
    tier3Label: "In-Depth Analysis",
    submitCta: "Ask My Assistant",
  },
};
