import type { AssistantGovernanceModalAndStudioLabels } from "@orcia/ui";

export interface Epic10DictionarySection {
  readonly assistantGovernance: AssistantGovernanceModalAndStudioLabels;
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
};
