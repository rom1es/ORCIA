import type {
  AssistantActiveStreamLabels,
  AssistantCitationPillsAndArtifactCardLabels,
  AssistantFoldersAndCollaborativeThreadViewLabels,
  AssistantGovernanceModalAndStudioLabels,
  AssistantResponseFooterLabels,
  AssistantSpeedSelectorAndStreamViewLabels,
  UiAssistantAutocompleteOption,
  UiAssistantOrciaDocumentOption,
} from "../index";

export const TEST_ASSISTANT_RESPONSE_FOOTER_LABELS: AssistantResponseFooterLabels = {
  likeLabel: "Bonne réponse",
  dislikeLabel: "Réponse à améliorer",
  copyLabel: "Copier",
  copiedLabel: "Copié",
  regenerateLabel: "Régénérer",
  saveDraftLabel: "Enregistrer en brouillon",
  draftSavedLabel: "Brouillon enregistré",
  continueProcessLabel: "Poursuivre dans un Processus",
  detailsLabel: "Voir les détails de la réponse",
  consultedSourcesHeading: "Sources consultées :",
  actionsToolbarAriaLabel: "Actions sur la réponse",
  deepenFallbackLabel: "Approfondir",
  feedbackThanksText: "Merci pour votre retour !",
  modelPrefix: "Modèle :",
  effortPrefix: "Niveau de réflexion :",
  defaultModelLabel: "Polyvalent",
  defaultEffortLabel: "Standard",
};

export const TEST_ASSISTANT_STREAM_LABELS: AssistantActiveStreamLabels = {
  stoppedByUserText: "Génération interrompue par l'utilisateur",
  reconnectFallbackCta: "Se reconnecter →",
  searchingAndDraftingText: "Recherche et rédaction en cours",
  thinkingDotsAriaLabel: "Réflexion en cours",
  responseFooter: TEST_ASSISTANT_RESPONSE_FOOTER_LABELS,
};

export const TEST_ASSISTANT_SPEED_DEFAULTS: Pick<
  AssistantSpeedSelectorAndStreamViewLabels,
  | "defaultWelcomeTitle"
  | "stopGenerationAriaLabel"
  | "sendTitle"
  | "stopTitle"
  | "followLiveResponseCta"
  | "plusMenuAriaLabel"
  | "durationMsUnit"
  | "defaultGreetingPrompt"
  | "activeFolderPrefix"
  | "activeNoteAppliedText"
  | "detachActiveFolderAriaLabel"
  | "defaultModelOptions"
  | "stream"
  | "responseFooter"
  | "modelPopover"
  | "plusMenu"
> = {
  defaultWelcomeTitle: "Par quoi voulez-vous commencer ?",
  stopGenerationAriaLabel: "Arrêter la réflexion de Mon Assistant",
  sendTitle: "Envoyer",
  stopTitle: "Arrêter",
  followLiveResponseCta: "Suivre la réponse en direct",
  plusMenuAriaLabel: "Actions rapides et dossiers",
  durationMsUnit: "ms",
  defaultGreetingPrompt:
    "Bonjour, peux-tu te présenter brièvement et confirmer que tu es opérationnel ?",
  activeFolderPrefix: "Dossier actif :",
  activeNoteAppliedText: "Note active prise en compte par l'Assistant",
  detachActiveFolderAriaLabel: "Détacher le dossier actif",
  defaultModelOptions: [
    { tier: "simple", title: "Rapide", subtitle: "Réponses les plus rapides" },
    { tier: "medium", title: "Polyvalent", subtitle: "Aide polyvalente au quotidien" },
    { tier: "complex", title: "Raisonnement avancé", subtitle: "Tâches complexes & analyse critique" },
  ],
  stream: {
    stoppedByUserText: TEST_ASSISTANT_STREAM_LABELS.stoppedByUserText,
    reconnectFallbackCta: TEST_ASSISTANT_STREAM_LABELS.reconnectFallbackCta,
    searchingAndDraftingText: TEST_ASSISTANT_STREAM_LABELS.searchingAndDraftingText,
    thinkingDotsAriaLabel: TEST_ASSISTANT_STREAM_LABELS.thinkingDotsAriaLabel,
  },
  responseFooter: TEST_ASSISTANT_RESPONSE_FOOTER_LABELS,
  modelPopover: {
    aiModelHeading: "Modèle IA",
    selectedAriaLabel: "Sélectionné",
    thinkingLevelTriggerLabel: "Niveau de réflexion",
    thinkingModeHeading: "Mode de réflexion",
    effortOptions: [
      {
        effort: "fast",
        speed: "SPEED_1_FAST",
        title: "Standard",
        subtitle: "Réponse directe avec vos sources & compétences",
        hiddenLegacyFast: true,
      },
      {
        effort: "balanced",
        speed: "SPEED_2_AGENT_TOOLS",
        title: "Standard",
        subtitle: "Réponse directe avec vos sources & compétences",
      },
      {
        effort: "deep",
        speed: "SPEED_3_DEEP_AUDIT",
        title: "Approfondi",
        subtitle: "Réflexion décomposée en étapes selon la question",
      },
    ],
  },
  plusMenu: {
    removeFilePrefix: "Retirer",
    selectAgentHeading: "Sélectionner un agent (@) — Entrée ou clic pour valider",
    selectSkillHeading: "Sélectionner une compétence (/) — Entrée ou clic pour valider",
    plusInsertAgentLabel: "@ Mentionner un agent",
    plusInsertSkillLabel: "/ Utiliser une compétence",
    plusUploadLocalFileLabel: "Ajouter un fichier depuis mon ordinateur",
    plusAttachOrciaDocLabel: "Ajouter un document disponible dans ORCIA",
    plusOpenFoldersLabel: "Gérer les dossiers thématiques",
  },
};

export const TEST_ASSISTANT_GOV_EXTRAS: Pick<
  AssistantGovernanceModalAndStudioLabels,
  | "savedBadgeLabel"
  | "infoBannerText"
  | "toneOptions"
  | "formatLabels"
  | "hatOptions"
  | "telemetryHeading"
  | "telemetrySubtitle"
  | "telemetryEmptyIntro"
  | "telemetryLikeLabel"
  | "telemetryDislikeLabel"
  | "telemetryUnratedLabel"
  | "telemetryHideContextCta"
  | "telemetryInspectContextCta"
  | "telemetryModelPrefix"
  | "telemetryThinkingPrefix"
  | "telemetryHistoryPrefix"
  | "telemetryMessagesUnit"
  | "telemetryFolderPrefix"
  | "telemetrySystemPromptHeading"
  | "telemetryDefaultContextFallback"
  | "studioWorkspaceScopeLabel"
  | "studioTeamScopeLabel"
  | "studioLayersPrefix"
  | "studioAddSubAgentCta"
  | "studioResetRestoredBanner"
> = {
  savedBadgeLabel: "Enregistré",
  infoBannerText: "Ces réglages personnalisent directement le rôle métier, le ton et le format.",
  toneOptions: [
    { value: "SYNTHETIC", label: "Synthétique & Direct (Aller à l'essentiel)" },
    { value: "BALANCED", label: "Équilibré & Structuré (Recommandé)" },
    { value: "DETAILED_CODE", label: "Détaillé & Illustré (Avec exemples complets)" },
  ],
  formatLabels: {
    bulletsSummary: "Points clés (Liste à puces)",
    structuredSections: "Sections structurées avec titres",
    stepByStep: "Guide étape par étape",
  },
  hatOptions: [
    { value: "PM", label: "Chef de Projet / Product Manager" },
    { value: "TECH_LEAD", label: "Référent Technique / Architecte" },
    { value: "DEV", label: "Développeur / Ingénieur" },
    { value: "ANALYST", label: "Analyste Métier" },
    { value: "QA_COMPLIANCE", label: "Responsable Qualité & Conformité" },
    { value: "PLATFORM_ADMIN", label: "Administrateur de la Plateforme" },
    { value: "CONTRIBUTOR", label: "Contributeur d'Équipe" },
  ],
  telemetryHeading: "Journal des Prompts, Contextes & Retours Utilisateurs",
  telemetrySubtitle: "Analyse et amélioration continue des consignes",
  telemetryEmptyIntro: "Aucune question enregistrée pour le moment.",
  telemetryLikeLabel: "Bonne réponse",
  telemetryDislikeLabel: "Réponse à améliorer",
  telemetryUnratedLabel: "Non évalué",
  telemetryHideContextCta: "Masquer le contexte",
  telemetryInspectContextCta: "Inspecter le contexte envoyé au LLM",
  telemetryModelPrefix: "Modèle :",
  telemetryThinkingPrefix: "Réflexion :",
  telemetryHistoryPrefix: "Historique injecté :",
  telemetryMessagesUnit: "message(s)",
  telemetryFolderPrefix: "Dossier :",
  telemetrySystemPromptHeading: "System Prompt & Contexte exact transmis au LLM :",
  telemetryDefaultContextFallback: "Contexte 5 couches standard",
  studioWorkspaceScopeLabel: "WORKSPACE",
  studioTeamScopeLabel: "TEAM",
  studioLayersPrefix: "COUCHES",
  studioAddSubAgentCta: "+ Sous-agent / Couche",
  studioResetRestoredBanner: "Configuration standard restaurée",
};

export const TEST_ASSISTANT_AGENT_OPTIONS: readonly UiAssistantAutocompleteOption[] = [
  { slug: "analyste-metier", label: "Analyste Métier", description: "Analyse des besoins", kind: "agent" },
  { slug: "architecte-solution", label: "Architecte Solution", description: "Conception technique", kind: "agent" },
];

export const TEST_ASSISTANT_SKILL_OPTIONS: readonly UiAssistantAutocompleteOption[] = [
  { slug: "synthese-executive", label: "Synthèse Exécutive", description: "Résumé structuré", kind: "skill" },
  { slug: "analyse-risques", label: "Analyse des Risques", description: "Identification des risques", kind: "skill" },
];

export const TEST_ASSISTANT_ORCIA_DOCUMENTS: readonly UiAssistantOrciaDocumentOption[] = [
  { id: "orcia-doc-1", title: "Référentiel Métier & Règles de l'Espace", uri: "https://docs.orcia.local/espaces/referentiel-metier" },
  { id: "orcia-doc-2", title: "Guide d'Architecture & Bonnes Pratiques", uri: "https://docs.orcia.local/espaces/guide-architecture" },
];

export const TEST_ASSISTANT_CITATIONS_EXTRAS: Pick<
  AssistantCitationPillsAndArtifactCardLabels,
  "linesLabel" | "draftBadgeLabel"
> = {
  linesLabel: "Lignes",
  draftBadgeLabel: "@draft",
};

export const TEST_ASSISTANT_FOLDER_EXTRAS: Pick<
  AssistantFoldersAndCollaborativeThreadViewLabels,
  | "clearActiveFolderCta"
  | "noActiveFolderHint"
  | "permanentNotesTitleTemplate"
  | "notesSavedBadgeLabel"
  | "notesTextareaPlaceholder"
  | "notesEnrichHint"
  | "saveNotesCta"
  | "newFolderTitlePlaceholder"
  | "defaultNewFolderTitlePrefix"
  | "newFolderCta"
  | "activeAccountPrefix"
  | "collaborativeSendCta"
> = {
  clearActiveFolderCta: "Désélectionner",
  noActiveFolderHint: "Aucun dossier actif sélectionné.",
  permanentNotesTitleTemplate: "Notes permanentes du dossier « {title} » (injectées dans chaque question)",
  notesSavedBadgeLabel: "Notes enregistrées et actives",
  notesTextareaPlaceholder: "Ex. : Toujours répondre avec des exemples structurés...",
  notesEnrichHint: "Les notes enregistrées enrichissent automatiquement vos questions.",
  saveNotesCta: "Enregistrer les notes",
  newFolderTitlePlaceholder: "Titre du nouveau dossier thématique...",
  defaultNewFolderTitlePrefix: "Dossier thématique #",
  newFolderCta: "+ Nouveau dossier",
  activeAccountPrefix: "Compte actif :",
  collaborativeSendCta: "Envoyer",
};
