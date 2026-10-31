import type {
  FourZoneDirectionCShellLabels,
  StreamlinedCockpitLabels,
} from "@orcia/ui";

export interface Epic9DictionarySection {
  readonly fourZoneShell: FourZoneDirectionCShellLabels;
  readonly streamlinedCockpit: StreamlinedCockpitLabels;
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
};
