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
    modalTitle: "⚙ Réglages de l'assistant",
    tab1UserTitle: "👤 Mes préférences",
    tab2WorkspaceTitle: "📦 Réglages de l'Espace",
    tab3AssemblyTitle: "👁️ Assemblage complet (Lecture seule)",
    toneLabel: "Ton & concision",
    formatLabel: "Format de réponse favori",
    defaultHatLabel: "Rôle par défaut",
    personalInstructionsLabel: "Instructions personnelles permanentes",
    saveUserPrefsCta: "Enregistrer mes préférences",
    workspaceInstructionsLabel: "Instructions métier de l'Espace",
    workspaceReadOnlyBadge:
      "👁️ Lecture seule — Seul un responsable d'équipe ou administrateur peut modifier les réglages de l'Espace",
    mcpExposeToggleLabel:
      "🔌 Exposer l'Assistant de l'Espace en MCP (/api/v1/mcp — outil assistant.ask)",
    mcpFrozenByUpperBadge:
      "🔒 Gelé par l'Équipe / le Socle",
    copyMcpConfigCta: "📋 Copier la config MCP",
    saveWorkspaceSettingsCta: "Enregistrer pour l'Espace",
    openStudioModeBCta: "☍ Personnaliser dans le Studio",
    studioHeaderTitle: "☍ Studio Graphique de l'Assistant",
    studioPrePromptLabel: "Pré-prompt IA de surcharge",
    studioHarnessImmutableBadge:
      "🔒 Bornes de sécurité AssistantHarness inaltérables",
    studioTestDryRunCta: "▷ Tester",
    studioSaveOverrideCta: "Enregistrer pour cet Espace / cette Équipe",
    studioResetDefaultCta: "↺ Réinitialiser à la configuration par défaut",
  },
  assistantSpeedStream: {
    headerTitle: "Sélecteur Conversationnel à 3 Vitesses",
    speed1PillLabel: "⚡ Vitesse 1 — Rapide",
    speed2PillLabel: "@Agent / /Skill — Vitesse 2 (Outils gouvernés)",
    speed3DeepAuditPillLabel: "🧠 Approfondi — Vitesse 3 (Multi-facettes)",
    cacheHitBadge: "⚡ Contexte assemblé prêt",
    cacheMissBadge: "🔄 Assemblage du contexte",
    nodesDeterministicLabel: "Préparation déterministe :",
    ttftBadgePrefix: "Réponse :",
    inputPlaceholder: "Posez une question, invoquez @agent ou /skill, ou activez 🧠 Approfondi...",
    sendPromptCta: "Envoyer à Mon Assistant",
  },
  assistantCitations: {
    freshnessFreshBadge: "✅ À jour (FRESH)",
    freshnessStaleBadge: "⚠️ [STALE_WARNING]",
    restrictedSourcePillSuffix: "🔒 Source restreinte",
    requestAccessCta: "Demander l'accès",
    unverifiedCitationBadge: "[Citation non vérifiée]",
    artifactCardTitlePrefix: "📄 Brouillon d'Artefact Structuré",
    copyArtifactCta: "📋 Copier",
    exportArtifactCta: "⬇ Exporter .md",
    saveDraftCta: "💾 Enregistrer le brouillon",
    continueInProcessCta: "☍ Poursuivre dans un Processus gouverné →",
    v5LockNoticeText:
      "🔒 Verrou de gouvernance : Aucune publication directe dans le SI sans franchir la Gate d'un Processus.",
  },
  assistantFolders: {
    tab1ActiveDiscussionTitle: "💬 Discussion active",
    tab2FoldersTitlePrefix: "📁 Dossiers",
    tab3HistorySearchTitle: "🕘 Historique & Recherche",
    activeFolderPillPrefix: "📁 Dossier actif :",
    pinnedNotesButtonLabel: "📌 Notes du dossier",
    launchProcessFromFolderCta: "☍ Lancer un Processus à partir de ce dossier →",
    shareButtonLabel: "👥 Partager / Visibilité",
    visibilityPrivateLabel: "🔒 Privé (Moi uniquement)",
    visibilitySharedSelectedLabel: "👥 Partagé (Membres sélectionnés)",
    visibilityWorkspaceOpenLabel: "📦 Ouvert à l'Espace",
    restrictedSourcesWarningText:
      "⚠️ Ce dossier cite des sources restreintes : chaque lecteur verra uniquement les extraits autorisés par son jeton Passthrough (READ_SOURCE).",
    searchPlaceholder: "Rechercher dans les discussions, dossiers et brouillons...",
  },
};

export const ASSISTANT_EN_LABELS: AssistantDictionarySection = {
  assistantGovernance: {
    modalTitle: "⚙ Assistant Settings",
    tab1UserTitle: "👤 My preferences",
    tab2WorkspaceTitle: "📦 Space settings",
    tab3AssemblyTitle: "👁️ Full assembly (Read-only)",
    toneLabel: "Tone & conciseness",
    formatLabel: "Preferred response format",
    defaultHatLabel: "Default Role",
    personalInstructionsLabel: "Permanent personal instructions",
    saveUserPrefsCta: "Save my preferences",
    workspaceInstructionsLabel: "Space business instructions",
    workspaceReadOnlyBadge:
      "👁️ Read-only — Only a team lead or administrator can edit Space settings",
    mcpExposeToggleLabel:
      "🔌 Expose Space Assistant via MCP (/api/v1/mcp — tool assistant.ask)",
    mcpFrozenByUpperBadge:
      "🔒 Frozen by Team / Platform",
    copyMcpConfigCta: "📋 Copy MCP config",
    saveWorkspaceSettingsCta: "Save for Space",
    openStudioModeBCta: "☍ Customize in Studio",
    studioHeaderTitle: "☍ Assistant Visual Studio",
    studioPrePromptLabel: "Override AI pre-prompt",
    studioHarnessImmutableBadge:
      "🔒 Immutable AssistantHarness security bounds",
    studioTestDryRunCta: "▷ Test",
    studioSaveOverrideCta: "Save for this Space / Team",
    studioResetDefaultCta: "↺ Reset to default configuration",
  },
  assistantSpeedStream: {
    headerTitle: "3-Speed Conversational Selector",
    speed1PillLabel: "⚡ Speed 1 — Fast",
    speed2PillLabel: "@Agent / /Skill — Speed 2 (Governed tools)",
    speed3DeepAuditPillLabel: "🧠 Deep Audit — Speed 3 (Multi-facet)",
    cacheHitBadge: "⚡ Assembled context ready",
    cacheMissBadge: "🔄 Context assembly",
    nodesDeterministicLabel: "Deterministic preparation:",
    ttftBadgePrefix: "Response:",
    inputPlaceholder: "Ask a question, invoke @agent or /skill, or toggle 🧠 Deep Audit...",
    sendPromptCta: "Send to My Assistant",
  },
  assistantCitations: {
    freshnessFreshBadge: "✅ Up to date (FRESH)",
    freshnessStaleBadge: "⚠️ [STALE_WARNING]",
    restrictedSourcePillSuffix: "🔒 Restricted source",
    requestAccessCta: "Request access",
    unverifiedCitationBadge: "[Unverified citation]",
    artifactCardTitlePrefix: "📄 Structured Artifact Draft",
    copyArtifactCta: "📋 Copy",
    exportArtifactCta: "⬇ Export .md",
    saveDraftCta: "💾 Save draft",
    continueInProcessCta: "☍ Continue in a governed Process →",
    v5LockNoticeText:
      "🔒 Governance lock: No direct SI publication without passing through a Process Gate.",
  },
  assistantFolders: {
    tab1ActiveDiscussionTitle: "💬 Active discussion",
    tab2FoldersTitlePrefix: "📁 Folders",
    tab3HistorySearchTitle: "🕘 History & Search",
    activeFolderPillPrefix: "📁 Active folder:",
    pinnedNotesButtonLabel: "📌 Folder notes",
    launchProcessFromFolderCta: "☍ Launch a Process from this folder →",
    shareButtonLabel: "👥 Share / Visibility",
    visibilityPrivateLabel: "🔒 Private (Only me)",
    visibilitySharedSelectedLabel: "👥 Shared (Selected members)",
    visibilityWorkspaceOpenLabel: "📦 Open to Space",
    restrictedSourcesWarningText:
      "⚠️ This folder cites restricted sources: each reader will only see excerpts allowed by their Passthrough token (READ_SOURCE).",
    searchPlaceholder: "Search across threads, folders, and artifact drafts...",
  },
};
