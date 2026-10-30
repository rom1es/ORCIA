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

export interface Epic5DictionarySection {
  readonly controlCenter: WorkspaceControlCenterLabels;
  readonly commandPalette: CommandPaletteModalLabels;
  readonly mobileCompanion: MobileCompanionLabels;
  readonly biModeLogin: BiModeLoginLabels;
  readonly collapsibleRail: CollapsibleAppRailLabels;
  readonly topHeader: TopHeaderBarLabels;
  readonly sprintWidget: SprintContextWidgetLabels;
  readonly scopedPrompt: ScopedPromptBoxLabels;
}

export const EPIC5_FR_LABELS: Epic5DictionarySection = {
  controlCenter: {
    title: "Centre de Pilotage Unifié Multi-Niveaux des Workspaces (4 Onglets Fractals)",
    scopeSelectorLabel: "Périmètre",
    scopeGlobal: "🌐 Plateforme Globale",
    scopeBu: "🏢 BU / Tribu",
    scopeTeam: "👥 Équipe",
    scopeWorkspace: "🗂️ Workspace Solution",
    tab1Runs: "▶️ 1. Instances de Workflow Runs & Artefacts",
    tab2Datasources: "🔌 2. Sources Dédiées & Partagées",
    tab3Workflows: "🤖 3. Workflows, Agents & Surcharges 4 niveaux",
    tab4Governance: "👥 4. Équipes, Membres & Gouvernance",
    contributorRunsHeader: "Actions Requises (CONTRIBUTOR_ACTION_REQUIRED)",
    observerRunsHeader: "En Suivi — Consultation Seule (READ_ONLY_OBSERVER)",
    attachDatasourceButton: "Rattacher une source (init-datasource)",
    launchRunButton: "Lancer un Run supervisé",
    observerBannerDefault:
      "👁️ Mode Consultation Seule — Vous suivez ce Workflow Run en tant qu'Observateur",
    guidanceDrawer: {
      drawerTitle: "Guide Méthodologique d'Intégration en 5 Étapes",
      toggleExpand: "Afficher les 5 étapes",
      toggleCollapse: "Replier le guide",
      commandPrefix: "Action",
    },
    lifecycleCard: {
      phaseTitle: "Phase du cycle de vie produit",
      runBadge: "🟢 RUN",
      buildBadge: "🏗️ BUILD",
      migrationBadge: "🔄 MIGRATION",
      suggestedWorkflowsTitle: "Workflows recommandés pour cette phase",
      readOnlyHint: "Modification verrouillée en mode Consultation Seule (HTTP 403).",
    },
  },
  commandPalette: {
    modalTitle: "Palette de Commandes Universelle & Bascule Multi-Runs (< 1 s)",
    searchPlaceholder: "Rechercher un Run, Workspace, concept SKOS ou raccourci (g c, g w)...",
    closeButton: "Fermer",
    emptyResults: "Aucun résultat pour cette recherche.",
    contributorBadge: "⚡ Action Requise",
    observerBadge: "👁️ Observateur",
  },
  mobileCompanion: {
    companionTitle: "Interface Mobile Companion Restreinte (3 Onglets — UX-DR16)",
    tabInbox: "🔔 Inbox",
    tabArbitration: "💬 Arbitrage/Chat",
    tabBriefing: "📄 Briefing",
    desktopOnlyBanner: "Fonctionnalité réservée au poste Desktop",
    blockedYamlEditorLabel: "Édition YAML Workflow-as-Code",
    blockedHeavyCoEditingLabel: "Co-édition lourde multi-pages",
    blockedAdminModuleLabel: "Module 7. Administration",
    badgeHumanAnchor: "✍️ Ancrage Humain",
    badgeAiArbitration: "⚖️ Arbitrage IA",
    badgeGate: "🛡️ Gate",
    badgeStaleWarning: "🚨 Obsolète",
    approveSectionCta: "Valider la section",
    liveRegionDefault: "Flux temps réel actif (SSE < 500 ms)",
  },
  biModeLogin: {
    title: "Connexion à la Plateforme ORCIA",
    subtitle:
      "Authentification Hybride Bi-Mode : SSO d'Entreprise OIDC PKCE ou Compte Local Argon2id + TOTP 2FA",
    primarySsoCta: "SSO d'Entreprise (OIDC PKCE)",
    localAccordionToggle: "Connexion locale / Administrateur de secours (Argon2id + TOTP)",
    emailLabel: "Adresse e-mail professionnelle",
    passwordLabel: "Mot de passe local (Argon2id)", // pragma: allowlist secret
    totpLabel: "Code TOTP 2FA (6 chiffres)",
    submitLocalCta: "Se connecter en mode local",
    errorBannerTitle: "Erreur d'authentification (RFC 9457)",
  },
  collapsibleRail: {
    railAriaLabel: "Barre latérale repliable Direction C",
    expandRailCta: "Étendre (240px)",
    collapseRailCta: "Mode Rail (72px)",
    activePackPrefix: "Pack actif",
    actionRequiredBadgeLabel: "actions requises",
    outboxHealthyLabel: "relais nominal",
  },
  topHeader: {
    workspacePackSelectorLabel: "Workspace / Pack",
    sprintSelectorLabel: "Sprint / Lot actif",
    dbosPg18HealthLabel: "DBOS / PG18",
    outboxHealthLabel: "Outbox",
  },
  sprintWidget: {
    widgetTitle: "Contexte du Sprint / Lot Actif",
    sprintGoalLabel: "Objectif du Sprint",
    velocityLabel: "Avancement",
    openRisksLabel: "Risques ouverts",
    auditRisksCta: "Auditer les risques du sprint / lot avec l'IA",
    auditCompletedMessage: "Audit IA des risques du sprint lancé dans le Cockpit",
  },
  scopedPrompt: {
    boxTitle: "Requête Scopée à l'Agent Assistant (Anti-Empty-State)",
    promptPlaceholder: "Posez une question ou lancez un diagnostic sur le périmètre sélectionné...",
    ragScopeLabel: "Périmètre de sources RAG autorisées (Permission Broker)",
    cognitiveTierLabel: "Tier cognitif",
    tier1Label: "Tier 1 — Rapide & Économique",
    tier2Label: "Tier 2 — Standard Équilibré",
    tier3Label: "Tier 3 — Raisonnement Profond",
    submitCta: "Interroger l'Agent Assistant",
  },
};

export const EPIC5_EN_LABELS: Epic5DictionarySection = {
  controlCenter: {
    title: "Multi-Level Unified Workspace Control Center (4 Fractal Tabs)",
    scopeSelectorLabel: "Scope",
    scopeGlobal: "🌐 Global Platform",
    scopeBu: "🏢 BU / Tribe",
    scopeTeam: "👥 Team",
    scopeWorkspace: "🗂️ Solution Workspace",
    tab1Runs: "▶️ 1. Workflow Run Instances & Artifacts",
    tab2Datasources: "🔌 2. Dedicated & Shared Datasources",
    tab3Workflows: "🤖 3. Workflows, Agents & 4-Layer Overrides",
    tab4Governance: "👥 4. Teams, Members & Governance",
    contributorRunsHeader: "Actions Required (CONTRIBUTOR_ACTION_REQUIRED)",
    observerRunsHeader: "Following — Read-Only (READ_ONLY_OBSERVER)",
    attachDatasourceButton: "Attach datasource (init-datasource)",
    launchRunButton: "Launch supervised Run",
    observerBannerDefault:
      "👁️ Read-Only Mode — You are following this Workflow Run as an Observer",
    guidanceDrawer: {
      drawerTitle: "5-Step Methodological Integration Guide",
      toggleExpand: "Show 5 steps",
      toggleCollapse: "Collapse guide",
      commandPrefix: "Action",
    },
    lifecycleCard: {
      phaseTitle: "Product lifecycle phase",
      runBadge: "🟢 RUN",
      buildBadge: "🏗️ BUILD",
      migrationBadge: "🔄 MIGRATION",
      suggestedWorkflowsTitle: "Suggested workflows for this phase",
      readOnlyHint: "Mutation locked in Read-Only Observer mode (HTTP 403).",
    },
  },
  commandPalette: {
    modalTitle: "Universal Command Palette & Multi-Run Switcher (< 1 s)",
    searchPlaceholder: "Search Run, Workspace, SKOS concept, or shortcut (g c, g w)...",
    closeButton: "Close",
    emptyResults: "No matching entries found.",
    contributorBadge: "⚡ Action Required",
    observerBadge: "👁️ Observer",
  },
  mobileCompanion: {
    companionTitle: "Restricted Mobile Companion Interface (3 Tabs — UX-DR16)",
    tabInbox: "🔔 Inbox",
    tabArbitration: "💬 Arbitration/Chat",
    tabBriefing: "📄 Briefing",
    desktopOnlyBanner: "Fonctionnalité réservée au poste Desktop",
    blockedYamlEditorLabel: "Workflow-as-Code YAML Editor",
    blockedHeavyCoEditingLabel: "Multi-page heavy co-editing",
    blockedAdminModuleLabel: "Module 7. Administration",
    badgeHumanAnchor: "✍️ Ancrage Humain",
    badgeAiArbitration: "⚖️ Arbitrage IA",
    badgeGate: "🛡️ Gate",
    badgeStaleWarning: "🚨 Obsolète",
    approveSectionCta: "Approve section",
    liveRegionDefault: "Real-time stream active (SSE < 500 ms)",
  },
  biModeLogin: {
    title: "Sign in to ORCIA Platform",
    subtitle:
      "Hybrid Bi-Mode Authentication: Enterprise OIDC PKCE SSO or Local Argon2id + TOTP 2FA",
    primarySsoCta: "Enterprise SSO (OIDC PKCE)",
    localAccordionToggle: "Local login / Emergency administrator (Argon2id + TOTP)",
    emailLabel: "Work email address",
    passwordLabel: "Local password (Argon2id)", // pragma: allowlist secret
    totpLabel: "TOTP 2FA code (6 digits)",
    submitLocalCta: "Sign in locally",
    errorBannerTitle: "Authentication Error (RFC 9457)",
  },
  collapsibleRail: {
    railAriaLabel: "Direction C collapsible sidebar rail",
    expandRailCta: "Expand (240px)",
    collapseRailCta: "Rail Mode (72px)",
    activePackPrefix: "Active pack",
    actionRequiredBadgeLabel: "actions required",
    outboxHealthyLabel: "nominal relay",
  },
  topHeader: {
    workspacePackSelectorLabel: "Workspace / Pack",
    sprintSelectorLabel: "Active Sprint / PI",
    dbosPg18HealthLabel: "DBOS / PG18",
    outboxHealthLabel: "Outbox",
  },
  sprintWidget: {
    widgetTitle: "Active Sprint / PI Context",
    sprintGoalLabel: "Sprint Goal",
    velocityLabel: "Progress",
    openRisksLabel: "Open risks",
    auditRisksCta: "Auditer les risques du sprint / lot avec l'IA",
    auditCompletedMessage: "AI sprint risk audit launched in Cockpit",
  },
  scopedPrompt: {
    boxTitle: "Scoped Assistant Prompt Box (Anti-Empty-State)",
    promptPlaceholder: "Ask a question or launch a diagnostic on the selected scope...",
    ragScopeLabel: "Authorized RAG datasource scope (Permission Broker)",
    cognitiveTierLabel: "Cognitive tier",
    tier1Label: "Tier 1 — Fast & Economical",
    tier2Label: "Tier 2 — Balanced Standard",
    tier3Label: "Tier 3 — Deep Reasoning",
    submitCta: "Query Assistant Agent",
  },
};
