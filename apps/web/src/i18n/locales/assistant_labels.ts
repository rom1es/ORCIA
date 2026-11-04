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
    inputPlaceholder: "Posez votre question, mentionnez un @agent ou activez 🧠 Analyse approfondie...",
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
    inputPlaceholder: "Ask a question, mention an @agent, or toggle 🧠 In-depth analysis...",
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
};
