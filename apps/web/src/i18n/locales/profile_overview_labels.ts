import type { UserProfileOverviewLabels } from "@orcia/ui";
import {
  ROLE_DISPLAY_LABELS_EN,
  ROLE_DISPLAY_LABELS_FR,
} from "./role_display_labels";

export const PROFILE_OVERVIEW_FR_LABELS: UserProfileOverviewLabels = {
  editButtonLabel: "Modifier",
  ledBuBadgePrefix: "BU :",
  ontologyBuBadgePrefix: "Référent Glossaire :",
  ledTeamBadgePrefix: "Équipe dirigée :",
  memberTeamBadgePrefix: "Équipe :",
  totalTokensLabel: "Total des tokens",
  totalTokensHint: "Mon Assistant & processus",
  peakDailyTokensLabel: "Pic de tokens",
  peakDailyTokensHint: "maximum sur 1 jour",
  longestStreakLabel: "Série la plus longue",
  currentStreakLabel: "Série en cours",
  daysUnitSingular: "jour",
  daysUnitPlural: "jours",
  popularSectionTitle: "Agents, Processus & Outils populaires",
  popularSectionSubtitle: "Vos ressources les plus sollicitées récemment.",
  usageCountSingular: "utilisation",
  usageCountPlural: "utilisations",
  itemTypeLabels: {
    AGENT: "Agent",
    PROCESS: "Processus",
    SKILL: "Compétence",
    TOOL: "Outil",
  },
  emptyPopularTitle: "Aucune utilisation enregistrée pour le moment",
  emptyPopularDescription:
    "Lancez un processus ou sollicitez un agent pour voir apparaître vos favoris.",
  emptyKpisMessage:
    "Aucune activité enregistrée pour le moment. Vos indicateurs d'usage apparaîtront ici dès vos premiers échanges avec Mon Assistant.",
  exploreAgentsCta: "Explorer Mes Agents →",
  loadingLabel: "Chargement du profil...",
  retryLabel: "Réessayer",
  roleDisplayLabels: ROLE_DISPLAY_LABELS_FR,
};

export const PROFILE_OVERVIEW_EN_LABELS: UserProfileOverviewLabels = {
  editButtonLabel: "Edit",
  ledBuBadgePrefix: "BU Lead:",
  ontologyBuBadgePrefix: "Glossary Lead:",
  ledTeamBadgePrefix: "Team Lead:",
  memberTeamBadgePrefix: "Team:",
  totalTokensLabel: "Total tokens",
  totalTokensHint: "My Assistant & processes",
  peakDailyTokensLabel: "Peak daily tokens",
  peakDailyTokensHint: "single-day maximum",
  longestStreakLabel: "Longest streak",
  currentStreakLabel: "Current streak",
  daysUnitSingular: "day",
  daysUnitPlural: "days",
  popularSectionTitle: "Popular Agents, Processes & Tools",
  popularSectionSubtitle: "Your most frequently used workspace resources.",
  usageCountSingular: "use",
  usageCountPlural: "uses",
  itemTypeLabels: {
    AGENT: "Agent",
    PROCESS: "Process",
    SKILL: "Skill",
    TOOL: "Tool",
  },
  emptyPopularTitle: "No usage recorded yet",
  emptyPopularDescription:
    "Run a process or invoke an agent to see your most-used items here.",
  emptyKpisMessage:
    "No assistant activity or token usage recorded yet. Your metrics will appear here after your first exchanges.",
  exploreAgentsCta: "Explore My Agents →",
  loadingLabel: "Loading profile...",
  retryLabel: "Retry",
  roleDisplayLabels: ROLE_DISPLAY_LABELS_EN,
};
