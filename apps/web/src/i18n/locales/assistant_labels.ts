import type {
  AssistantApprovalRequiredCardLabels,
  AssistantCitationPillsAndArtifactCardLabels,
  AssistantFoldersAndCollaborativeThreadViewLabels,
  AssistantGovernanceModalAndStudioLabels,
  AssistantSpeedSelectorAndStreamViewLabels,
  AssistantToolCallTraceLabels,
} from "@orcia/ui";

export interface AssistantDictionarySection {
  readonly assistantGovernance: AssistantGovernanceModalAndStudioLabels;
  readonly assistantSpeedStream: AssistantSpeedSelectorAndStreamViewLabels;
  readonly assistantCitations: AssistantCitationPillsAndArtifactCardLabels;
  readonly assistantFolders: AssistantFoldersAndCollaborativeThreadViewLabels;
  readonly assistantFoldersSync: {
    readonly workspaceRequired: string;
    readonly loadFailed: (detail: string) => string;
    readonly saveFailed: (detail: string) => string;
  };
  readonly assistantNoEmbeddingModel: {
    readonly bannerTitle: string;
    readonly bannerDescription: string;
    readonly configureCta: string;
  };
  readonly assistantNoChatModel: {
    readonly bannerTitle: string;
    readonly bannerDescription: string;
    readonly configureCta: string;
  };
  readonly assistantRagNotice: {
    readonly noEmbeddingTitle: string;
    readonly noEmbeddingDescription: string;
    readonly configureEmbeddingCta: string;
    readonly reindexingTitle: string;
    readonly reindexingDescription: string;
    readonly reindexFailedTitle: string;
    readonly reindexFailedDescription: string;
    readonly relaunchReindexCta: string;
    readonly checkEmbeddingCta: string;
  };
  readonly assistantStreamErrors: {
    readonly sessionExpiredMessage: string;
    readonly reconnectCta: string;
    readonly aiUnavailableMessage: (detail?: string) => string;
  };
  readonly assistantToolTrace: AssistantToolCallTraceLabels;
  readonly assistantApprovalCard: AssistantApprovalRequiredCardLabels;
}

export const ASSISTANT_FR_LABELS: AssistantDictionarySection = {
  assistantGovernance: {
    modalTitle: "⚙ Réglages de Mon Assistant",
    tab1UserTitle: "👤 Mes préférences",
    tab2WorkspaceTitle: "📦 Réglages de l'Espace",
    tab3AssemblyTitle: "👁️ Consignes actives (Lecture seule)",
    toneLabel: "Ton & niveau de synthèse",
    formatLabel: "Format de réponse préféré",
    defaultHatLabel: "Rôle par défaut",
    personalInstructionsLabel: "Mes consignes personnelles permanentes",
    saveUserPrefsCta: "Enregistrer mes préférences",
    workspaceInstructionsLabel: "Consignes métier communes à l'Espace",
    workspaceReadOnlyBadge:
      "👁️ Lecture seule — Seul un responsable d'équipe ou un administrateur peut modifier les consignes de l'Espace",
    mcpExposeToggleLabel:
      "🔌 Permettre l'accès à l'Assistant de cet Espace depuis un éditeur de code externe",
    mcpFrozenByUpperBadge:
      "🔒 Défini par l'Équipe ou l'Organisation",
    copyMcpConfigCta: "📋 Copier la configuration éditeur",
    saveWorkspaceSettingsCta: "Enregistrer pour l'Espace",
  },
  assistantSpeedStream: {
    headerTitle: "Mode de Réponse de Mon Assistant",
    speed1PillLabel: "⚡ Réponse rapide",
    speed2PillLabel: "🛠️ Avec un agent ou une compétence (@Agent / /Compétence)",
    speed3DeepAuditPillLabel: "🧠 Analyse approfondie (plusieurs points de vue)",
    cacheHitBadge: "⚡ Contexte de l'espace prêt",
    cacheMissBadge: "🔄 Préparation du contexte",
    nodesDeterministicLabel: "Recherche dans vos sources :",
    ttftBadgePrefix: "Temps de réponse :",
    inputPlaceholder:
      "Tapez @ pour les agents, / pour les compétences ou posez votre question...",
    sendPromptCta: "Envoyer à Mon Assistant",
    toolsUnsupportedNotice:
      "Le modèle IA actif ne prend pas en charge les outils de l'espace : le mode dialogue rapide reste disponible.",
    toolsUnsupportedBadge: "Dialogue direct",
    deepenCta: "Approfondir",
    deepenLowEvidenceCta: "Approfondir avec les outils de l'espace",
  },
  assistantCitations: {
    freshnessFreshBadge: "✅ Source à jour",
    freshnessStaleBadge: "⚠️ Source à vérifier",
    restrictedSourcePillSuffix: "🔒 Accès restreint",
    requestAccessCta: "Demander l'accès",
    unverifiedCitationBadge: "Référence à confirmer",
    artifactCardTitlePrefix: "📄 Brouillon de Document",
    copyArtifactCta: "📋 Copier",
    exportArtifactCta: "⬇ Télécharger (.md)",
    saveDraftCta: "💾 Enregistrer le brouillon",
    continueInProcessCta: "☍ Poursuivre dans un Processus avec validation →",
    v5LockNoticeText:
      "🔒 Pour garantir la qualité, toute publication vers vos outils partagés passe par une étape de validation.",
  },
  assistantFoldersSync: {
    workspaceRequired: "⚠️ Créez ou sélectionnez d'abord un Espace de travail pour enregistrer vos dossiers.",
    loadFailed: (detail: string) => `⚠️ Impossible de charger vos dossiers (${detail}).`,
    saveFailed: (detail: string) => `⚠️ Le dossier n'a pas pu être enregistré (${detail}).`,
  },
  assistantFolders: {
    tab1ActiveDiscussionTitle: "💬 Discussion en cours",
    tab2FoldersTitlePrefix: "📁 Dossiers",
    tab3HistorySearchTitle: "🕘 Historique & Recherche",
    activeFolderPillPrefix: "📁 Dossier actif :",
    pinnedNotesButtonLabel: "📌 Notes épinglées",
    launchProcessFromFolderCta: "☍ Démarrer un Processus à partir de ce dossier →",
    shareButtonLabel: "👥 Partager / Visibilité",
    visibilityPrivateLabel: "🔒 Privé (Moi uniquement)",
    visibilitySharedSelectedLabel: "👥 Partagé (Membres choisis)",
    visibilityWorkspaceOpenLabel: "📦 Visible par tout l'Espace",
    restrictedSourcesWarningText:
      "⚠️ Ce dossier cite des sources protégées : chaque lecteur ne verra que les extraits auxquels son compte a accès.",
    searchPlaceholder: "Rechercher dans vos discussions, dossiers et brouillons...",
  },
  assistantNoEmbeddingModel: {
    bannerTitle: "Dialogue direct actif · Recherche documentaire inactive",
    bannerDescription:
      "Le dialogue direct et le glossaire sont actifs. La recherche documentaire nécessite un modèle d'indexation sémantique.",
    configureCta: "Configurer dans Modèles IA →",
  },
  assistantNoChatModel: {
    bannerTitle: "Modèle de dialogue IA requis",
    bannerDescription:
      "Aucun modèle de dialogue (chat) actif n'est configuré sur la plateforme. Configurez au moins un modèle chat pour utiliser Mon Assistant.",
    configureCta: "Configurer un modèle IA →",
  },
  assistantRagNotice: {
    noEmbeddingTitle: "Dialogue direct & glossaire actifs · Recherche documentaire inactive",
    noEmbeddingDescription:
      "Aucun modèle d'indexation sémantique n'est configuré. Vous pouvez échanger normalement avec Mon Assistant ; la recherche dans les documents nécessite un modèle d'embedding.",
    configureEmbeddingCta: "Configurer dans Administration › Modèles IA →",
    reindexingTitle: "Dialogue direct & glossaire actifs · Réindexation documentaire en cours",
    reindexingDescription:
      "Le corpus documentaire est en cours de réindexation sémantique. Le dialogue direct reste actif ; la recherche documentaire reprendra automatiquement à la fin.",
    reindexFailedTitle: "Dialogue direct actif · Réindexation documentaire interrompue",
    reindexFailedDescription:
      "La réindexation sémantique du corpus documentaire a échoué. Le dialogue direct avec Mon Assistant reste disponible.",
    relaunchReindexCta: "Relancer la réindexation",
    checkEmbeddingCta: "Vérifier le modèle d'embedding →",
  },
  assistantStreamErrors: {
    sessionExpiredMessage:
      "Votre session a expiré ou doit être renouvelée pour continuer la conversation.",
    reconnectCta: "Se reconnecter →",
    aiUnavailableMessage: (detail?: string) =>
      detail
        ? `⚠️ Impossible d'obtenir une réponse de Mon Assistant (${detail}). Vérifiez que le modèle IA configuré est bien démarré.`
        : "⚠️ Le service d'IA est temporairement indisponible. Vérifiez que le modèle IA configuré est bien démarré.",
  },
  assistantToolTrace: {
    heading: "Outils de l'espace sollicités",
    runningLabel: "En cours",
    executedLabel: "Terminé",
    deniedLabel: "Refusé",
    errorLabel: "Erreur",
    approvalRequiredLabel: "Validation requise",
    inspectLinesLabel: "Inspecter les lignes",
    durationSuffix: "ms",
  },
  assistantApprovalCard: {
    heading: "Validation humaine requise avant application",
    targetLabel: "Cible",
    workflowLabel: "Processus",
    humanAnchorLabel: "Votre justification de validation (requise)",
    humanAnchorPlaceholder: "Indiquez la raison de votre approbation...",
    humanAnchorRequiredError: "Veuillez saisir une brève justification avant d'approuver cette action.",
    approveCta: "Approuver et poursuivre",
    rejectCta: "Refuser",
    approvedStatusLabel: "Approuvé — poursuivi dans le processus",
    rejectedStatusLabel: "Refusé",
    openProcessCta: "Ouvrir le processus →",
  },
};

export { ASSISTANT_EN_LABELS } from "./assistant_labels_en";
