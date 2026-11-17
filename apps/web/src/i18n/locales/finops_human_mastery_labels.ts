/**
 * Localized labels for Executive Cognitive Impact & Human Mastery (`Story 6.3`, `Direction C`).
 *
 * Strict anti-jargon enforcement:
 * - ZERO forbidden words: Rubber-Stamping, Pattern Drift, Human-Led Think, < 15 s, DBOS, etc.
 * - Pure clear business terminology in French and English.
 */

import type { HumanMasteryLabels } from "@orcia/ui";

export const HUMAN_MASTERY_FR_LABELS: HumanMasteryLabels = {
  tabTitle: "Maîtrise humaine et qualité",
  tabSubtitle:
    "Surveillez la posture active des experts, prévenez les validations expéditives et garantissez la réversibilité d'architecture.",
  infoButtonAriaLabel: "Comprendre les indicateurs de maîtrise humaine et réversibilité",
  framingGauge: {
    title: "Part de cadrage humain actif",
    targetLabel: "cible ≥ 40 %",
    statusHealthy: "Équilibré",
    statusAlert: "Déséquilibre",
    subtitle: "Temps investi en cadrage et arbitrages rapporté au temps de revue",
  },
  quickPassGauge: {
    title: "Validations expéditives",
    thresholdLabel: "seuil < 5 %",
    statusHealthy: "Conforme",
    statusAlert: "Alerte de vigilance",
    subtitle: "Part des approbations réalisées avec un temps de relecture trop court",
  },
  architectureGauge: {
    title: "Conformité d'architecture & Réversibilité",
    targetLabel: "cible 0 %",
    statusHealthy: "Aligné",
    statusAlert: "Écart non couvert",
    subtitle: "Écarts constatés par rapport aux décisions verrouillées sans dérogation",
  },
  recommendationsSectionTitle: "Recommandations d'ajustement des validations",
  recommendationsEmptyText:
    "Aucun ajustement recommandé sur cette période. Les rythmes de revue et niveaux de cadrage sont optimaux.",
  workflowsTable: {
    title: "Indicateurs par processus",
    workflowCol: "Processus",
    criticalityCol: "Criticité",
    reviewsCol: "Validations humaines",
    quickPassCol: "Validations expéditives",
    medianDurationCol: "Durée médiane",
    deviationsCol: "Écarts d'architecture",
    statusCol: "Statut",
    statusNormal: "Normal",
    statusAlert: "Attention",
    criticalityLabels: {
      HIGH_CRITICAL: "Critique élevée",
      CRITICAL: "Critique",
      STANDARD: "Standard",
      LOW: "Faible",
    },
  },
  appliedBadge: "Ajustement appliqué ✓",
};

export const HUMAN_MASTERY_EN_LABELS: HumanMasteryLabels = {
  tabTitle: "Human Mastery and Quality",
  tabSubtitle:
    "Monitor active expert engagement, prevent quick-pass approvals, and ensure architecture reversibility.",
  infoButtonAriaLabel: "Learn about human mastery indicators and reversibility",
  framingGauge: {
    title: "Active human framing share",
    targetLabel: "target ≥ 40%",
    statusHealthy: "Balanced",
    statusAlert: "Imbalance",
    subtitle: "Time invested in framing and arbitration relative to review time",
  },
  quickPassGauge: {
    title: "Quick-pass approvals",
    thresholdLabel: "threshold < 5%",
    statusHealthy: "Compliant",
    statusAlert: "Attention required",
    subtitle: "Share of approvals made with an excessively short reading duration",
  },
  architectureGauge: {
    title: "Architecture compliance & reversibility",
    targetLabel: "target 0%",
    statusHealthy: "Aligned",
    statusAlert: "Uncovered deviation",
    subtitle: "Deviations from locked decisions without approved exception",
  },
  recommendationsSectionTitle: "Validation policy adjustment recommendations",
  recommendationsEmptyText:
    "No policy adjustments recommended for this period. Review pace and framing levels are optimal.",
  workflowsTable: {
    title: "Metrics by process",
    workflowCol: "Process",
    criticalityCol: "Criticality",
    reviewsCol: "Human reviews",
    quickPassCol: "Quick-pass rate",
    medianDurationCol: "Median duration",
    deviationsCol: "Deviations",
    statusCol: "Status",
    statusNormal: "Normal",
    statusAlert: "Warning",
    criticalityLabels: {
      HIGH_CRITICAL: "High criticality",
      CRITICAL: "Critical",
      STANDARD: "Standard",
      LOW: "Low",
    },
  },
  appliedBadge: "Adjustment applied ✓",
};
