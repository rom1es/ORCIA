import type {
  FourZoneDirectionCShellLabels,
  ProgressiveDay0AccostageLabels,
  StreamlinedCockpitLabels,
} from "@orcia/ui";

export interface Epic9DictionarySection {
  readonly fourZoneShell: FourZoneDirectionCShellLabels;
  readonly streamlinedCockpit: StreamlinedCockpitLabels;
  readonly progressiveAccostage: ProgressiveDay0AccostageLabels;
}

export const EPIC9_FR_LABELS: Epic9DictionarySection = {
  fourZoneShell: {
    workspacePrefix: "Espace",
    searchTriggerPlaceholder: "Rechercher dans cet Espace ou partout (⌘K)...",
    contextualHelpButtonLabel: "? Aide",
    notificationsButtonLabel: "🔔 Notifications",
    notificationsDrawerTitle: "Centre de Notifications (420px)",
    notificationsEmptyText: "Aucune notification non lue.",
    sidebarAriaLabel: "Navigation principale à 8 entrées sans numéro",
    railCollapseLabel: "Replier le rail ([)",
    railExpandLabel: "Déplier le rail ([)",
    packSelectorLabel: "Pack Métier actif",
    helpColumnTitle: "❓ Aide Contextuelle (340px)",
    helpColumnExpectedTitle: "Ce qui est attendu ici",
    helpColumnExpectedBody:
      "Pilotez vos décisions prioritaires ou interrogez Mon Assistant.",
    menuEntries: {
      cockpit: "Cockpit",
      assistant: "Mon Assistant",
      processes: "Mes Processus",
      agents: "Mes Agents",
      spaces: "Mes Espaces",
      finops: "FinOps",
      configuration: "Configuration",
      help: "Aide",
    },
  },
  streamlinedCockpit: {
    zeroDecisionsBanner: "✅ Aucune décision en attente",
    quickAssistantTitle: "Accès rapide à Mon Assistant",
    quickAssistantPlaceholder: "Posez une question ou préparez un dossier...",
    quickAssistantCta: "Ouvrir Mon Assistant →",
    orientationAssistantTitle: "💬 Mon Assistant",
    orientationAssistantDesc:
      "Interrogez vos sources avec citations [S1] en < 1,2 s.",
    orientationProcessesTitle: "☍ Mes Processus",
    orientationProcessesDesc:
      "Lancez le workflow pilote sdlc/ticket-to-tech-spec.",
    orientationSpacesTitle: "📦 Mes Espaces",
    orientationSpacesDesc:
      "Gérez vos sources, livrables et glossaire métier.",
    kpiAnchorsLabel: "Ancrages Humains",
    kpiArbitrationsLabel: "Arbitrages Tie-Break",
    kpiReviewsLabel: "Revues 4 blocs",
    kpiAlertsLabel: "Alertes",
    filterAllLabel: "Toutes les décisions",
    filterShortLabel: "Décisions courtes (Tie-Break)",
    filterHeavyLabel: "Atelier de revue Fokus",
    tieBreakInlineBadge: "⚖️ Arbitrage rapide sur place",
    tieBreakResolvedPrefix: "Arbitrage tranché :",
    heavyActionBadge: "🔒 Revue Fokus requise",
    openFocusReviewCta: "Ouvrir l'atelier de revue →",
    focusWorkshopBreadcrumbPrefix: "Mes Processus › Exécutions & Décisions ›",
    focusWorkshopCloseCta: "← Retour au Cockpit",
    redisLockAcquiredPrefix: "🔒 Verrou Redis acquis :",
  },
  progressiveAccostage: {
    bannerTitle: "Parcours d'Accostage Progressif Jour 0",
    welcomeWizardTitle: "Assistant de Bienvenue (/welcome-setup)",
    step1AdminTitle: "Étape 1 : Premier Administrateur (LOCK TABLE users)",
    step2LlmTitle: "Étape 2 : Modèles IA Progressifs (1 Modèle → ≥ 2 Familles)",
    step3SpaceTitle: "Étape 3 : Jalons d'Accostage 1/6",
    bootstrapTokenLabel: "Jeton d'amorçage ORCIA_BOOTSTRAP_TOKEN",
    bootstrapTokenPlaceholder: "Saisissez ORCIA_BOOTSTRAP_TOKEN...",
    bootstrapTokenDeniedBanner:
      "HTTP 403 ERR_INVALID_BOOTSTRAP_TOKEN — Jeton d'amorçage invalide",
    createFirstAdminCta: "Créer le compte PLATFORM_ADMIN",
    addFirstModelCta: "+ Configurer 1er modèle (Ollama / OpenAI)",
    addSecondModelFamilyCta: "+ Ajouter 2e famille orthogonale (Claude)",
    singleFamilyAmberWarning:
      "⚠️ 1 seule famille de modèles configurée — Ajoutez une 2e famille dans Configuration › Modèles IA pour activer les Gates Agentiques AD-10",
    dualFamilyAd10UnlockedBadge:
      "✅ ≥ 2 familles orthogonales actives — Gates Agentiques AD-10 débloquées",
    assistantTrialReadyBadge:
      "🚀 Mode Essai Rapide actif : Mon Assistant & Cockpit débloqués",
  },
};

export const EPIC9_EN_LABELS: Epic9DictionarySection = {
  fourZoneShell: {
    workspacePrefix: "Space",
    searchTriggerPlaceholder: "Search in this Space or everywhere (⌘K)...",
    contextualHelpButtonLabel: "? Help",
    notificationsButtonLabel: "🔔 Notifications",
    notificationsDrawerTitle: "Notification Center (420px)",
    notificationsEmptyText: "No unread notifications.",
    sidebarAriaLabel: "Main 8-Entry Unnumbered Navigation",
    railCollapseLabel: "Collapse rail ([)",
    railExpandLabel: "Expand rail ([)",
    packSelectorLabel: "Active Business Pack",
    helpColumnTitle: "❓ Contextual Help (340px)",
    helpColumnExpectedTitle: "What is expected here",
    helpColumnExpectedBody:
      "Drive your priority decisions or query My Assistant.",
    menuEntries: {
      cockpit: "Cockpit",
      assistant: "My Assistant",
      processes: "My Processes",
      agents: "My Agents",
      spaces: "My Spaces",
      finops: "FinOps",
      configuration: "Configuration",
      help: "Help",
    },
  },
  streamlinedCockpit: {
    zeroDecisionsBanner: "✅ No pending decisions",
    quickAssistantTitle: "Quick access to My Assistant",
    quickAssistantPlaceholder: "Ask a question or prepare a briefing...",
    quickAssistantCta: "Open My Assistant →",
    orientationAssistantTitle: "💬 My Assistant",
    orientationAssistantDesc:
      "Query your sources with [S1] citations in < 1.2 s.",
    orientationProcessesTitle: "☍ My Processes",
    orientationProcessesDesc:
      "Launch the pilot workflow sdlc/ticket-to-tech-spec.",
    orientationSpacesTitle: "📦 My Spaces",
    orientationSpacesDesc:
      "Manage your sources, deliverables, and business glossary.",
    kpiAnchorsLabel: "Human Anchors",
    kpiArbitrationsLabel: "Tie-Break Arbitrations",
    kpiReviewsLabel: "4-Block Reviews",
    kpiAlertsLabel: "Alerts",
    filterAllLabel: "All decisions",
    filterShortLabel: "Short decisions (Tie-Break)",
    filterHeavyLabel: "Focus Review Workshop",
    tieBreakInlineBadge: "⚖️ Inline quick arbitration",
    tieBreakResolvedPrefix: "Arbitration resolved:",
    heavyActionBadge: "🔒 Focus Review required",
    openFocusReviewCta: "Open Review Workshop →",
    focusWorkshopBreadcrumbPrefix: "My Processes › Executions & Decisions ›",
    focusWorkshopCloseCta: "← Back to Cockpit",
    redisLockAcquiredPrefix: "🔒 Redis lock acquired:",
  },
  progressiveAccostage: {
    bannerTitle: "Progressive Day-0 Accostage Journey",
    welcomeWizardTitle: "Welcome Setup Wizard (/welcome-setup)",
    step1AdminTitle: "Step 1: First Administrator (LOCK TABLE users)",
    step2LlmTitle: "Step 2: Progressive AI Models (1 Model → ≥ 2 Families)",
    step3SpaceTitle: "Step 3: 1/6 Accostage Milestones",
    bootstrapTokenLabel: "ORCIA_BOOTSTRAP_TOKEN bootstrap token",
    bootstrapTokenPlaceholder: "Enter ORCIA_BOOTSTRAP_TOKEN...",
    bootstrapTokenDeniedBanner:
      "HTTP 403 ERR_INVALID_BOOTSTRAP_TOKEN — Invalid bootstrap token",
    createFirstAdminCta: "Create PLATFORM_ADMIN account",
    addFirstModelCta: "+ Configure 1st model (Ollama / OpenAI)",
    addSecondModelFamilyCta: "+ Add 2nd orthogonal family (Claude)",
    singleFamilyAmberWarning:
      "⚠️ Only 1 model family configured — Add a 2nd family in Configuration › AI Models to enable AD-10 Agentic Gates",
    dualFamilyAd10UnlockedBadge:
      "✅ ≥ 2 orthogonal families active — AD-10 Agentic Gates unlocked",
    assistantTrialReadyBadge:
      "🚀 Quick Trial Mode active: My Assistant & Cockpit unlocked",
  },
};
