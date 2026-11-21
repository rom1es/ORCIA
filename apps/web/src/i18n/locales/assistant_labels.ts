import type {
  AssistantCitationPillsAndArtifactCardLabels,
  AssistantFoldersAndCollaborativeThreadViewLabels,
  AssistantGovernanceModalAndStudioLabels,
  AssistantSpeedSelectorAndStreamViewLabels,
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
    openStudioModeBCta: "☍ Personnaliser le parcours de réponse",
    studioHeaderTitle: "☍ Personnalisation Avancée de Mon Assistant",
    studioPrePromptLabel: "Consignes complémentaires",
    studioHarnessImmutableBadge:
      "🔒 Les règles de sécurité et de confidentialité de l'organisation restent toujours actives",
    studioTestDryRunCta: "▷ Tester",
    studioSaveOverrideCta: "Enregistrer pour cet Espace / cette Équipe",
    studioResetDefaultCta: "↺ Rétablir les réglages par défaut",
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
};

export const ASSISTANT_EN_LABELS: AssistantDictionarySection = {
  assistantGovernance: {
    modalTitle: "⚙ My Assistant Settings",
    tab1UserTitle: "👤 My preferences",
    tab2WorkspaceTitle: "📦 Space settings",
    tab3AssemblyTitle: "👁️ Active instructions (Read-only)",
    toneLabel: "Tone & conciseness",
    formatLabel: "Preferred response format",
    defaultHatLabel: "Default Role",
    personalInstructionsLabel: "My permanent personal instructions",
    saveUserPrefsCta: "Save my preferences",
    workspaceInstructionsLabel: "Shared business instructions for this Space",
    workspaceReadOnlyBadge:
      "👁️ Read-only — Only a team lead or administrator can edit Space instructions",
    mcpExposeToggleLabel:
      "🔌 Allow access to this Space's Assistant from an external code editor",
    mcpFrozenByUpperBadge:
      "🔒 Set by Team or Organization",
    copyMcpConfigCta: "📋 Copy editor configuration",
    saveWorkspaceSettingsCta: "Save for Space",
    openStudioModeBCta: "☍ Customize response flow",
    studioHeaderTitle: "☍ Advanced Assistant Customization",
    studioPrePromptLabel: "Additional instructions",
    studioHarnessImmutableBadge:
      "🔒 Organization security and privacy safeguards always remain active",
    studioTestDryRunCta: "▷ Test",
    studioSaveOverrideCta: "Save for this Space / Team",
    studioResetDefaultCta: "↺ Restore default settings",
  },
  assistantSpeedStream: {
    headerTitle: "Assistant Response Mode",
    speed1PillLabel: "⚡ Fast response",
    speed2PillLabel: "🛠️ With an agent or skill (@Agent / /Skill)",
    speed3DeepAuditPillLabel: "🧠 In-depth analysis (multiple perspectives)",
    cacheHitBadge: "⚡ Workspace context ready",
    cacheMissBadge: "🔄 Preparing context",
    nodesDeterministicLabel: "Searching your sources:",
    ttftBadgePrefix: "Response time:",
    inputPlaceholder:
      "Type @ for agents, / for skills, or ask your question...",
    sendPromptCta: "Send to My Assistant",
  },
  assistantCitations: {
    freshnessFreshBadge: "✅ Source up to date",
    freshnessStaleBadge: "⚠️ Source needs review",
    restrictedSourcePillSuffix: "🔒 Restricted access",
    requestAccessCta: "Request access",
    unverifiedCitationBadge: "Reference to confirm",
    artifactCardTitlePrefix: "📄 Document Draft",
    copyArtifactCta: "📋 Copy",
    exportArtifactCta: "⬇ Download (.md)",
    saveDraftCta: "💾 Save draft",
    continueInProcessCta: "☍ Continue in a reviewed Process →",
    v5LockNoticeText:
      "🔒 To ensure quality, publishing to shared tools always goes through a review step.",
  },
  assistantFoldersSync: {
    workspaceRequired: "⚠️ Create or select a Workspace first to save your folders.",
    loadFailed: (detail: string) => `⚠️ Unable to load your folders (${detail}).`,
    saveFailed: (detail: string) => `⚠️ The folder could not be saved (${detail}).`,
  },
  assistantFolders: {
    tab1ActiveDiscussionTitle: "💬 Active discussion",
    tab2FoldersTitlePrefix: "📁 Folders",
    tab3HistorySearchTitle: "🕘 History & Search",
    activeFolderPillPrefix: "📁 Active folder:",
    pinnedNotesButtonLabel: "📌 Pinned notes",
    launchProcessFromFolderCta: "☍ Start a Process from this folder →",
    shareButtonLabel: "👥 Share / Visibility",
    visibilityPrivateLabel: "🔒 Private (Only me)",
    visibilitySharedSelectedLabel: "👥 Shared (Selected members)",
    visibilityWorkspaceOpenLabel: "📦 Visible to entire Space",
    restrictedSourcesWarningText:
      "⚠️ This folder cites protected sources: each reader will only see excerpts their account is authorized to view.",
    searchPlaceholder: "Search across your discussions, folders, and drafts...",
  },
  assistantNoEmbeddingModel: {
    bannerTitle: "Direct dialogue active · Document search inactive",
    bannerDescription:
      "Direct dialogue and glossary are active. Document semantic search requires an active indexing model.",
    configureCta: "Configure in AI Models →",
  },
  assistantNoChatModel: {
    bannerTitle: "Chat AI model required",
    bannerDescription:
      "No active chat AI model is configured on the platform. Configure at least one chat model to use My Assistant.",
    configureCta: "Configure an AI model →",
  },
  assistantRagNotice: {
    noEmbeddingTitle: "Direct dialogue & glossary active · Document search inactive",
    noEmbeddingDescription:
      "No semantic indexing model is configured. You can chat normally with My Assistant; searching workspace documents requires an embedding model.",
    configureEmbeddingCta: "Configure in Administration › AI Models →",
    reindexingTitle: "Direct dialogue & glossary active · Document reindexing in progress",
    reindexingDescription:
      "The document corpus is undergoing semantic reindexing. Direct chat remains active; document search will resume automatically once finished.",
    reindexFailedTitle: "Direct dialogue active · Document reindexing interrupted",
    reindexFailedDescription:
      "Semantic reindexing of the document corpus failed. Direct dialogue with My Assistant remains available.",
    relaunchReindexCta: "Relaunch reindexing",
    checkEmbeddingCta: "Check embedding model →",
  },
  assistantStreamErrors: {
    sessionExpiredMessage:
      "Your session has expired or needs to be renewed to continue the conversation.",
    reconnectCta: "Log in again →",
    aiUnavailableMessage: (detail?: string) =>
      detail
        ? `⚠️ Could not get a response from My Assistant (${detail}). Please check that your configured AI model is running.`
        : "⚠️ The AI service is temporarily unavailable. Please check that your configured AI model is running.",
  },
};
