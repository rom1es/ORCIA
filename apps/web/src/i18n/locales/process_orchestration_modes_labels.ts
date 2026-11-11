export interface ProcessOrchestrationModesCopy {
  readonly selectorSectionTitle: string;
  readonly selectorSectionHint: string;
  readonly goalDrivenTitle: string;
  readonly goalDrivenSubtitle: string;
  readonly goalDrivenBadge: string;
  readonly milestoneDrivenTitle: string;
  readonly milestoneDrivenSubtitle: string;
  readonly milestoneDrivenBadge: string;
  readonly goalBlock2Title: string;
  readonly goalBlock2Subtitle: string;
  readonly goalObjectiveLabel: string;
  readonly goalObjectivePlaceholder: string;
  readonly goalDelegateAgentsLabel: string;
  readonly goalDelegateAgentsHint: string;
  readonly goalNoDelegateAgentsNotice: string;
  readonly milestoneBlock2Title: string;
  readonly milestoneBlock2Subtitle: string;
  readonly modeSwitchedToGoalBanner: string;
  readonly modeSwitchedToMilestoneBanner: string;
  readonly goalSummaryPrefix: string;
  readonly milestoneSummarySuffix: string;
}

export interface ProcessOrchestrationModesDictionarySection {
  readonly processOrchestrationModes: ProcessOrchestrationModesCopy;
}

export const PROCESS_ORCHESTRATION_MODES_FR_LABELS: ProcessOrchestrationModesDictionarySection = {
  processOrchestrationModes: {
    selectorSectionTitle: "Mode de conduite du processus",
    selectorSectionHint:
      "Choisissez comment vos agents mènent ce processus. Vos brouillons sont conservés dans les deux modes.",
    goalDrivenTitle: "Processus piloté par l'objectif (adaptatif)",
    goalDrivenSubtitle:
      "Vous fixez le résultat attendu et les agents mobilisables ; l'enchaînement des recherches s'adapte aux éléments découverts.",
    goalDrivenBadge: "Piloté par l'objectif",
    milestoneDrivenTitle: "Processus piloté par les jalons (étapes garanties)",
    milestoneDrivenSubtitle:
      "Vous fixez l'ordre précis des étapes, les validations humaines attendues et les boucles de reprise sur toute la durée du dossier.",
    milestoneDrivenBadge: "Piloté par les jalons",
    goalBlock2Title: "2. Objectif attendu & Agents mobilisables",
    goalBlock2Subtitle:
      "Décrivez le résultat métier attendu et sélectionnez les agents spécialisés que le pilote peut mobiliser en renfort.",
    goalObjectiveLabel: "Résultat métier attendu",
    goalObjectivePlaceholder:
      "Décrivez le livrable attendu, le périmètre d'investigation et les critères de réussite...",
    goalDelegateAgentsLabel: "Agents spécialisés mobilisables (1 niveau de renfort)",
    goalDelegateAgentsHint:
      "Activez ou retirez les agents que le responsable du processus peut solliciter pour approfondir un point précis.",
    goalNoDelegateAgentsNotice:
      "Aucun agent de renfort sélectionné : le responsable du processus mène seul l'investigation.",
    milestoneBlock2Title: "2. Déroulement des étapes du processus",
    milestoneBlock2Subtitle:
      "Activez ou ignorez chaque étape selon les besoins de votre projet.",
    modeSwitchedToGoalBanner:
      "Mode basculé sur « Processus piloté par l'objectif (adaptatif) » dans votre copie de travail.",
    modeSwitchedToMilestoneBanner:
      "Mode basculé sur « Processus piloté par les jalons (étapes garanties) » dans votre copie de travail.",
    goalSummaryPrefix: "Investigation adaptative",
    milestoneSummarySuffix: "étape(s) guidée(s)",
  },
};

export const PROCESS_ORCHESTRATION_MODES_EN_LABELS: ProcessOrchestrationModesDictionarySection = {
  processOrchestrationModes: {
    selectorSectionTitle: "Process guidance mode",
    selectorSectionHint:
      "Choose how your agents conduct this process. Your working inputs are preserved across both modes.",
    goalDrivenTitle: "Goal-driven process (adaptive)",
    goalDrivenSubtitle:
      "You define the expected outcome and mobilizable agents; the research sequence adapts as findings emerge.",
    goalDrivenBadge: "Goal-driven",
    milestoneDrivenTitle: "Milestone-driven process (guaranteed steps)",
    milestoneDrivenSubtitle:
      "You define the exact step order, required human reviews, and revision loops across the full dossier lifecycle.",
    milestoneDrivenBadge: "Milestone-driven",
    goalBlock2Title: "2. Expected Outcome & Mobilizable Agents",
    goalBlock2Subtitle:
      "Describe the expected business outcome and select specialist agents that may be mobilized as support.",
    goalObjectiveLabel: "Expected business outcome",
    goalObjectivePlaceholder:
      "Describe the expected deliverable, investigation scope, and acceptance expectations...",
    goalDelegateAgentsLabel: "Mobilizable specialist agents (1-level support)",
    goalDelegateAgentsHint:
      "Enable or remove specialist agents that the lead agent can call upon for targeted investigation.",
    goalNoDelegateAgentsNotice:
      "No support agent selected: the lead agent conducts the investigation directly.",
    milestoneBlock2Title: "2. Process Step Sequence",
    milestoneBlock2Subtitle:
      "Enable or skip each step according to your project needs.",
    modeSwitchedToGoalBanner:
      'Mode switched to "Goal-driven process (adaptive)" in your working draft.',
    modeSwitchedToMilestoneBanner:
      'Mode switched to "Milestone-driven process (guaranteed steps)" in your working draft.',
    goalSummaryPrefix: "Adaptive investigation",
    milestoneSummarySuffix: "guided step(s)",
  },
};
