import type {
  AssistantCitationPillsAndArtifactCardLabels,
  AssistantFoldersAndCollaborativeThreadViewLabels,
  AssistantGovernanceModalAndStudioLabels,
  AssistantSpeedSelectorAndStreamViewLabels,
} from "@orcia/ui";

export interface Epic10DictionarySection {
  readonly assistantGovernance: AssistantGovernanceModalAndStudioLabels;
  readonly assistantSpeedStream: AssistantSpeedSelectorAndStreamViewLabels;
  readonly assistantCitations: AssistantCitationPillsAndArtifactCardLabels;
  readonly assistantFolders: AssistantFoldersAndCollaborativeThreadViewLabels;
}

export const EPIC10_FR_LABELS: Epic10DictionarySection = {
  assistantGovernance: {
    modalTitle: "⚙ Réglages de l'assistant (Mode A — 3 onglets)",
    tab1UserTitle: "👤 Mes préférences (Couche 5 — USER)",
    tab2WorkspaceTitle: "📦 Réglages de l'Espace (Couche 4 — WORKSPACE)",
    tab3AssemblyTitle: "👁️ Assemblage complet (Lecture seule)",
    toneLabel: "Ton & concision",
    formatLabel: "Format de réponse favori",
    defaultHatLabel: "Casquette métier par défaut",
    personalInstructionsLabel: "Instructions personnelles permanentes (Couche 5)",
    saveUserPrefsCta: "Enregistrer mes préférences",
    workspaceInstructionsLabel: "Instructions métier de l'Espace",
    workspaceReadOnlyBadge:
      "👁️ Lecture seule — Seul un TEAM_LEAD ou PLATFORM_ADMIN peut modifier les réglages de l'Espace",
    mcpExposeToggleLabel:
      "🔌 Exposer l'Assistant de l'Espace en MCP (/api/v1/mcp — outil assistant.ask)",
    mcpFrozenByUpperBadge:
      "🔒 Gelé par l'Équipe / le Socle (Règle de l'Entonnoir Principe G)",
    copyMcpConfigCta: "📋 Copier la config MCP",
    saveWorkspaceSettingsCta: "Enregistrer pour l'Espace",
    openStudioModeBCta: "☍ Personnaliser dans le Studio",
    studioHeaderTitle:
      "☍ Studio Graphique de l'Assistant (Mode B — @xyflow/react)",
    studioPrePromptLabel: "Pré-prompt IA de surcharge",
    studioHarnessImmutableBadge:
      "🔒 Bornes AssistantHarness inaltérables (Couche 1 AD-15)",
    studioTestDryRunCta: "▷ Tester",
    studioSaveOverrideCta: "Enregistrer pour cet Espace / cette Équipe",
    studioResetDefaultCta: "↺ Réinitialiser à la configuration par défaut",
  },
  assistantSpeedStream: {
    headerTitle: "Sélecteur Conversationnel à 3 Vitesses & Cache Redis 5 Couches (TTL 300s, < 5 ms)",
    speed1PillLabel: "⚡ Vitesse 1 — Rapide (< 80 ms déterministe, TTFT < 1.2s)",
    speed2PillLabel: "@Agent / /Skill — Vitesse 2 (Outils gouvernés < 2.5s)",
    speed3DeepAuditPillLabel: "🧠 Approfondi — Vitesse 3 (Multi-facettes AD-10)",
    cacheHitBadge: "⚡ Cache 5 Couches HIT",
    cacheMissBadge: "🔄 Assemblage 5 Couches",
    nodesDeterministicLabel: "Nœuds 1..4 déterministes :",
    ttftBadgePrefix: "TTFT :",
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
      "🔒 Verrou V5 (AD-15) : Aucune publication directe dans le SI sans franchir la Gate d'un Processus.",
  },
  assistantFolders: {
    tab1ActiveDiscussionTitle: "💬 Discussion active",
    tab2FoldersTitlePrefix: "📁 Dossiers",
    tab3HistorySearchTitle: "🕘 Historique & Recherche",
    activeFolderPillPrefix: "📁 Dossier actif :",
    pinnedNotesButtonLabel: "📌 Notes du dossier (Couche 5)",
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

export const EPIC10_EN_LABELS: Epic10DictionarySection = {
  assistantGovernance: {
    modalTitle: "⚙ Assistant Settings (Mode A — 3 tabs)",
    tab1UserTitle: "👤 My preferences (Layer 5 — USER)",
    tab2WorkspaceTitle: "📦 Space settings (Layer 4 — WORKSPACE)",
    tab3AssemblyTitle: "👁️ Full assembly (Read-only)",
    toneLabel: "Tone & conciseness",
    formatLabel: "Preferred response format",
    defaultHatLabel: "Default Business Hat",
    personalInstructionsLabel: "Permanent personal instructions (Layer 5)",
    saveUserPrefsCta: "Save my preferences",
    workspaceInstructionsLabel: "Space business instructions",
    workspaceReadOnlyBadge:
      "👁️ Read-only — Only a TEAM_LEAD or PLATFORM_ADMIN can edit Space settings",
    mcpExposeToggleLabel:
      "🔌 Expose Space Assistant via MCP (/api/v1/mcp — tool assistant.ask)",
    mcpFrozenByUpperBadge:
      "🔒 Frozen by Team / Platform (Funnel Rule Principle G)",
    copyMcpConfigCta: "📋 Copy MCP config",
    saveWorkspaceSettingsCta: "Save for Space",
    openStudioModeBCta: "☍ Customize in Studio",
    studioHeaderTitle: "☍ Assistant Visual Studio (Mode B — @xyflow/react)",
    studioPrePromptLabel: "Override AI pre-prompt",
    studioHarnessImmutableBadge:
      "🔒 Immutable AssistantHarness bounds (Layer 1 AD-15)",
    studioTestDryRunCta: "▷ Test",
    studioSaveOverrideCta: "Save for this Space / Team",
    studioResetDefaultCta: "↺ Reset to default configuration",
  },
  assistantSpeedStream: {
    headerTitle: "3-Speed Conversational Selector & 5-Layer Redis Cache (TTL 300s, < 5 ms)",
    speed1PillLabel: "⚡ Speed 1 — Fast (< 80 ms deterministic, TTFT < 1.2s)",
    speed2PillLabel: "@Agent / /Skill — Speed 2 (Governed tools < 2.5s)",
    speed3DeepAuditPillLabel: "🧠 Deep Audit — Speed 3 (Multi-facet AD-10)",
    cacheHitBadge: "⚡ 5-Layer Cache HIT",
    cacheMissBadge: "🔄 5-Layer Assembly",
    nodesDeterministicLabel: "Deterministic Nodes 1..4:",
    ttftBadgePrefix: "TTFT:",
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
      "🔒 Lock V5 (AD-15): No direct SI publication without passing through a Process Gate.",
  },
  assistantFolders: {
    tab1ActiveDiscussionTitle: "💬 Active discussion",
    tab2FoldersTitlePrefix: "📁 Folders",
    tab3HistorySearchTitle: "🕘 History & Search",
    activeFolderPillPrefix: "📁 Active folder:",
    pinnedNotesButtonLabel: "📌 Folder notes (Layer 5)",
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
