import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import {
  AssistantGovernanceModalAndStudio,
  type AssistantGovernanceModalAndStudioLabels,
  AssistantSpeedSelectorAndStreamView,
  type AssistantSpeedSelectorAndStreamViewLabels,
} from "../index";

const GOV_LABELS: AssistantGovernanceModalAndStudioLabels = {
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
};

describe("Epic 10 — Mon Assistant All-in-One (Story 10.1)", () => {
  it("Story 10.1 — renders Mode A (3 tabs: USER, WORKSPACE with MCP Funnel Rule, and 5-Layer Full Assembly) and switches to Mode B Studio with locked 🔒 AssistantHarness bounds and 1-click Reset", () => {
    const onSaveUserPreferences = vi.fn();
    const onSaveWorkspaceSettings = vi.fn();
    const onCopyMcpConfig = vi.fn();
    const onSaveStudioOverride = vi.fn();
    const onResetStudioOverride = vi.fn();

    render(
      <AssistantGovernanceModalAndStudio
        workspaceId="ws-claims-alpha"
        canEditWorkspaceLayer={true}
        canOpenStudioModeB={true}
        mcpFrozenByUpperLayer={false}
        assembledLayers={[
          {
            layerNumber: 1,
            layerCode: "1_CONSTITUTION",
            label: "1. 🔒 Constitution",
            immutable: true,
            originBadge: "SOCLE",
            content: "[CONSTITUTIONAL_IMMUTABLE_LAYER_1]",
            sha256: "a".repeat(64),
          },
          {
            layerNumber: 2,
            layerCode: "2_PACK_METIER",
            label: "2. Pack Métier",
            immutable: true,
            originBadge: "PACK",
            content: "[PACK_METIER]",
            sha256: "b".repeat(64),
          },
          {
            layerNumber: 3,
            layerCode: "3_EQUIPE",
            label: "3. Équipe",
            immutable: false,
            originBadge: "EQUIPE",
            content: "[EQUIPE]",
            sha256: "c".repeat(64),
          },
          {
            layerNumber: 4,
            layerCode: "4_ESPACE",
            label: "4. Espace",
            immutable: false,
            originBadge: "ESPACE",
            content: "[ESPACE]",
            sha256: "d".repeat(64),
          },
          {
            layerNumber: 5,
            layerCode: "5_UTILISATEUR",
            label: "5. Utilisateur",
            immutable: false,
            originBadge: "UTILISATEUR",
            content: "[UTILISATEUR]",
            sha256: "e".repeat(64),
          },
        ]}
        studioNodes={[
          {
            nodeId: "ENTRY_BOUNDARY_HARNESS",
            title: "🔒 Borne d'Entrée — AssistantHarness",
            nodeOrder: 0,
            isHarnessBoundary: true,
            lockedBy: "HARNESS",
            enabled: true,
            subLayersCount: 2,
          },
          {
            nodeId: "3_PARALLEL_FAN_OUT",
            title: "3. Fan-Out Parallèle",
            nodeOrder: 3,
            isHarnessBoundary: false,
            lockedBy: null,
            enabled: true,
            subLayersCount: 4,
          },
          {
            nodeId: "EXIT_BOUNDARY_HARNESS",
            title: "🔒 Borne de Sortie — AssistantHarness",
            nodeOrder: 6,
            isHarnessBoundary: true,
            lockedBy: "HARNESS",
            enabled: true,
            subLayersCount: 2,
          },
        ]}
        labels={GOV_LABELS}
        onSaveUserPreferences={onSaveUserPreferences}
        onSaveWorkspaceSettings={onSaveWorkspaceSettings}
        onCopyMcpConfig={onCopyMcpConfig}
        onSaveStudioOverride={onSaveStudioOverride}
        onResetStudioOverride={onResetStudioOverride}
      />,
    );

    // Tab 1: Save user preferences
    fireEvent.change(screen.getByTestId("assistant-user-tone-select"), {
      target: { value: "SYNTHETIC" },
    });
    fireEvent.click(screen.getByTestId("assistant-save-user-prefs-btn"));
    expect(onSaveUserPreferences).toHaveBeenCalledWith(
      expect.objectContaining({ responseTone: "SYNTHETIC" }),
    );

    // Tab 2: Workspace settings + MCP copy config
    fireEvent.click(screen.getByTestId("assistant-gov-tab-WORKSPACE_SETTINGS"));
    fireEvent.click(screen.getByTestId("assistant-copy-mcp-config-btn"));
    expect(onCopyMcpConfig).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByTestId("assistant-save-workspace-settings-btn"));
    expect(onSaveWorkspaceSettings).toHaveBeenCalledTimes(1);

    // Tab 3: Full 5-layer assembly
    fireEvent.click(screen.getByTestId("assistant-gov-tab-FULL_ASSEMBLY"));
    expect(screen.getByTestId("assembled-layer-1").textContent).toContain(
      "1. 🔒 Constitution",
    );
    expect(screen.getByTestId("assembled-layer-5").textContent).toContain(
      "5. Utilisateur",
    );

    // Switch to Mode B Studio
    fireEvent.click(screen.getByTestId("assistant-open-studio-mode-b-btn"));
    expect(screen.getByTestId("assistant-governance-mode-b-studio")).toBeDefined();

    // Entry/Exit 🔒 AssistantHarness boundaries are locked and have no edit button
    expect(
      screen.getByTestId("studio-node-locked-ENTRY_BOUNDARY_HARNESS").textContent, // pragma: allowlist secret
    ).toContain("HARNESS");
    expect(
      screen.getByTestId("studio-node-locked-EXIT_BOUNDARY_HARNESS").textContent, // pragma: allowlist secret
    ).toContain("HARNESS");

    // Add sub-agent to Node 3, run Dry-Run (▷ Tester), Save, and 1-click Reset
    fireEvent.click(
      screen.getByTestId("studio-node-add-subagent-3_PARALLEL_FAN_OUT"), // pragma: allowlist secret
    );
    fireEvent.click(screen.getByTestId("studio-test-dryrun-btn"));
    expect(screen.getByTestId("studio-dry-run-banner").textContent).toContain(
      "Dry-Run OK",
    );

    fireEvent.click(screen.getByTestId("studio-save-override-btn"));
    expect(onSaveStudioOverride).toHaveBeenCalledWith(
      expect.objectContaining({
        scopeLevel: "WORKSPACE",
      }),
    );

    fireEvent.click(screen.getByTestId("studio-reset-default-btn"));
    expect(onResetStudioOverride).toHaveBeenCalledWith("WORKSPACE");
    expect(screen.getByTestId("studio-reset-restored-banner")).toBeDefined();
  });

  it("Story 10.2 — renders 3-Speed Conversational Selector (⚡ Rapide, @Agent / /Skill, 🧠 Approfondi), Redis cache badge, and real-time step progress", () => {
    const onSendTurn = vi.fn();
    const speedLabels: AssistantSpeedSelectorAndStreamViewLabels = {
      headerTitle: "Routage Conversationnel à 3 Vitesses & Cache Redis 5 Couches",
      speed1PillLabel: "⚡ Vitesse 1 — Rapide (TTFT < 1,2 s)",
      speed2PillLabel: "🛠️ Vitesse 2 — @Agent / /Skill (TTFT < 2,5 s)",
      speed3DeepAuditPillLabel: "🧠 Approfondi (Audit multi-facettes AD-10)",
      cacheHitBadge: "⚡ Cache Redis HIT",
      cacheMissBadge: "🔄 Cache Redis MISS",
      nodesDeterministicLabel: "Nœuds 1–4 déterministes",
      ttftBadgePrefix: "TTFT",
      inputPlaceholder: "Posez votre question, mentionnez @Agent ou /Skill...",
      sendPromptCta: "Envoyer",
    };

    render(
      <AssistantSpeedSelectorAndStreamView
        workspaceId="ws-claims-alpha"
        userId="u-claire-01"
        hat="PM"
        cacheHit={true}
        cacheLookupMs={1.2}
        nodes1To4DeterministicMs={15.7}
        ttftMs={395.7}
        stepProgress={[
          {
            stepCode: "CONNECTOR_INTERROGATION",
            label: "🔍 Interrogation de Jira...",
            durationMs: 520,
            status: "COMPLETED",
            connectorOrLens: "@jira-triage",
          },
        ]}
        streamedText="Réponse vérifiée [S1]"
        labels={speedLabels}
        onSendTurn={onSendTurn}
      />,
    );

    expect(screen.getByTestId("assistant-prompt-cache-badge").textContent).toContain(
      "assistant:prompt:ws-claims-alpha:u-claire-01:PM",
    );
    expect(screen.getByTestId("assistant-step-progress-list").textContent).toContain(
      "🔍 Interrogation de Jira...",
    );

    // Typing @jira-triage switches to SPEED_2_AGENT_TOOLS automatically
    fireEvent.change(screen.getByTestId("assistant-three-speed-input"), {
      target: { value: "Vérifie @jira-triage sur le backlog" },
    });
    fireEvent.click(screen.getByTestId("assistant-three-speed-send-btn"));
    expect(onSendTurn).toHaveBeenCalledWith({
      userPrompt: "Vérifie @jira-triage sur le backlog",
      requestedSpeed: "SPEED_2_AGENT_TOOLS",
      deepAuditPillActive: false,
    });

    // Clicking 🧠 Approfondi toggles SPEED_3_DEEP_AUDIT
    fireEvent.click(screen.getByTestId("assistant-deep-audit-pill-toggle"));
    fireEvent.click(screen.getByTestId("assistant-three-speed-send-btn"));
    expect(onSendTurn).toHaveBeenLastCalledWith({
      userPrompt: "Vérifie @jira-triage sur le backlog",
      requestedSpeed: "SPEED_3_DEEP_AUDIT",
      deepAuditPillActive: true,
    });
  });
});
