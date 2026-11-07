import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import {
  AssistantCitationPillsAndArtifactCard,
  type AssistantCitationPillsAndArtifactCardLabels,
  AssistantFoldersAndCollaborativeThreadView,
  type AssistantFoldersAndCollaborativeThreadViewLabels,
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

    // Clicking Send on an empty input populates a default test prompt and triggers onSendTurn immediately
    fireEvent.click(screen.getByTestId("assistant-three-speed-send-btn"));
    expect(onSendTurn).toHaveBeenCalledWith(
      expect.objectContaining({
        requestedSpeed: "SPEED_1_FAST",
        deepAuditPillActive: false,
      }),
    );

    // Typing @jira-triage switches to SPEED_2_AGENT_TOOLS automatically
    fireEvent.change(screen.getByTestId("assistant-three-speed-input"), {
      target: { value: "Vérifie @jira-triage sur le backlog" },
    });
    fireEvent.keyDown(screen.getByTestId("assistant-three-speed-input"), {
      key: "Enter",
    });
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

  it("Story 10.2b — toggles Play (▶) and Stop (■) button, displays collapsible AssistantThinkingSubWindow with live second counter and intermediate outputs, auto-collapses when response streams, and preserves partial output on Stop", () => {
    vi.useFakeTimers();
    try {
      const onSendTurn = vi.fn();
      const onStopGeneration = vi.fn();
      const speedLabels: AssistantSpeedSelectorAndStreamViewLabels = {
        headerTitle: "Routage Conversationnel à 3 Vitesses",
        speed1PillLabel: "⚡ Rapide",
        speed2PillLabel: "🛠️ Outils",
        speed3DeepAuditPillLabel: "🧠 Approfondi",
        cacheHitBadge: "HIT",
        cacheMissBadge: "MISS",
        nodesDeterministicLabel: "Nœuds 1–4",
        ttftBadgePrefix: "TTFT",
        inputPlaceholder: "Posez votre question...",
        sendPromptCta: "Envoyer",
      };

      const { rerender } = render(
        <AssistantSpeedSelectorAndStreamView
          workspaceId="ws-claims-alpha"
          userId="u-claire-01"
          hat="PM"
          isGenerating={false}
          stepProgress={[]}
          streamedText=""
          labels={speedLabels}
          onSendTurn={onSendTurn}
          onStopGeneration={onStopGeneration}
        />,
      );

      // 1. When idle (!isGenerating), send button displays triangle play icon (▶)
      expect(screen.getByTestId("assistant-send-play-icon").textContent).toBe("▶");
      expect(screen.queryByTestId("assistant-stop-square-icon")).toBeNull();

      // 2. When generating starts (isGenerating=true), button is NOT disabled and shows filled square (■)
      rerender(
        <AssistantSpeedSelectorAndStreamView
          workspaceId="ws-claims-alpha"
          userId="u-claire-01"
          hat="PM"
          isGenerating={true}
          stepProgress={[
            {
              stepCode: "NODES_1_TO_4_DETERMINISTIC",
              label: "Analyse de la question & cadrage",
              durationMs: 18,
              status: "COMPLETED",
              intermediateOutput: "Demande cadrée : synthèse des risques.",
            },
            {
              stepCode: "NODE_5_SINGLE_STREAM_LLM",
              label: "Réflexion intermédiaire du modèle",
              durationMs: 1200,
              status: "RUNNING",
              intermediateOutput: "Vérification des règles de gestion...",
            },
          ]}
          streamedText=""
          labels={speedLabels}
          onSendTurn={onSendTurn}
          onStopGeneration={onStopGeneration}
        />,
      );

      const actionBtn = screen.getByTestId("assistant-three-speed-send-btn") as HTMLButtonElement;
      expect(actionBtn.disabled).toBe(false);
      expect(screen.getByTestId("assistant-stop-square-icon").textContent).toBe("■");

      // Thinking sub-window is open by default while thinking (data-expanded="true")
      const subWindow = screen.getByTestId("assistant-thinking-subwindow");
      expect(subWindow.getAttribute("data-expanded")).toBe("true");
      expect(
        screen.getByTestId("assistant-step-intermediate-output-NODES_1_TO_4_DETERMINISTIC")
          .textContent,
      ).toContain("Demande cadrée : synthèse des risques.");
      expect(
        screen.getByTestId("assistant-step-intermediate-output-NODE_5_SINGLE_STREAM_LLM")
          .textContent,
      ).toContain("Vérification des règles de gestion...");

      // 3. Live timer increments every second while isGenerating === true
      expect(screen.getByTestId("assistant-thinking-subwindow-header-label").textContent).toContain(
        "0s",
      );
      vi.advanceTimersByTime(2000);
      rerender(
        <AssistantSpeedSelectorAndStreamView
          workspaceId="ws-claims-alpha"
          userId="u-claire-01"
          hat="PM"
          isGenerating={true}
          stepProgress={[
            {
              stepCode: "NODES_1_TO_4_DETERMINISTIC",
              label: "Analyse de la question & cadrage",
              durationMs: 18,
              status: "COMPLETED",
              intermediateOutput: "Demande cadrée : synthèse des risques.",
            },
            {
              stepCode: "NODE_5_SINGLE_STREAM_LLM",
              label: "Réflexion intermédiaire du modèle",
              durationMs: 2000,
              status: "RUNNING",
              intermediateOutput: "Vérification des règles de gestion...",
            },
          ]}
          streamedText=""
          labels={speedLabels}
          onSendTurn={onSendTurn}
          onStopGeneration={onStopGeneration}
        />,
      );
      expect(
        screen.getByTestId("assistant-step-live-timer-NODE_5_SINGLE_STREAM_LLM").textContent,
      ).toContain("s");

      // 4. When streamedText starts arriving in the main box, sub-window auto-collapses (data-expanded="false")
      rerender(
        <AssistantSpeedSelectorAndStreamView
          workspaceId="ws-claims-alpha"
          userId="u-claire-01"
          hat="PM"
          isGenerating={true}
          stepProgress={[
            {
              stepCode: "NODES_1_TO_4_DETERMINISTIC",
              label: "Analyse de la question & cadrage",
              durationMs: 18,
              status: "COMPLETED",
              intermediateOutput: "Demande cadrée : synthèse des risques.",
            },
            {
              stepCode: "NODE_5_SINGLE_STREAM_LLM",
              label: "Réflexion intermédiaire du modèle",
              durationMs: 2400,
              status: "COMPLETED",
              intermediateOutput: "Vérification terminée.",
            },
          ]}
          streamedText="Voici le début de la réponse générée progressivement..."
          labels={speedLabels}
          onSendTurn={onSendTurn}
          onStopGeneration={onStopGeneration}
        />,
      );
      expect(screen.getByTestId("assistant-thinking-subwindow").getAttribute("data-expanded")).toBe(
        "false",
      );
      expect(screen.getByTestId("assistant-streamed-response-box").textContent).toContain(
        "Voici le début de la réponse générée progressivement...",
      );

      // Clicking the sub-window toggle re-expands it so the user can inspect intermediate outputs
      fireEvent.click(screen.getByTestId("assistant-thinking-subwindow-toggle"));
      expect(screen.getByTestId("assistant-thinking-subwindow").getAttribute("data-expanded")).toBe(
        "true",
      );

      // 5. Clicking the Stop square button (■) calls onStopGeneration, preserves text, and shows stopped badge
      fireEvent.click(screen.getByTestId("assistant-three-speed-send-btn"));
      expect(onStopGeneration).toHaveBeenCalledTimes(1);

      rerender(
        <AssistantSpeedSelectorAndStreamView
          workspaceId="ws-claims-alpha"
          userId="u-claire-01"
          hat="PM"
          isGenerating={false}
          generationStopped={true}
          stepProgress={[
            {
              stepCode: "NODES_1_TO_4_DETERMINISTIC",
              label: "Analyse de la question & cadrage",
              durationMs: 18,
              status: "COMPLETED",
              intermediateOutput: "Demande cadrée : synthèse des risques.",
            },
          ]}
          streamedText="Voici le début de la réponse générée progressivement..."
          labels={speedLabels}
          onSendTurn={onSendTurn}
          onStopGeneration={onStopGeneration}
        />,
      );

      expect(screen.getByTestId("assistant-send-play-icon").textContent).toBe("▶");
      expect(screen.getByTestId("assistant-generation-stopped-badge").textContent).toContain(
        "⏹ Génération interrompue par l'utilisateur",
      );
      expect(screen.getByTestId("assistant-streamed-response-box").textContent).toContain(
        "Voici le début de la réponse générée progressivement...",
      );
    } finally {
      vi.useRealTimers();
    }
  });

  it("Story 10.3 — renders deterministic [S1]/[G1]/[O1] pills, filters restricted sources for shared readers without leaking snippets, highlights phantom citations, and enforces Verrou V5 on artifact cards", () => {
    const onInspectSource = vi.fn();
    const onRequestRestrictedAccess = vi.fn();
    const onSaveDraft = vi.fn();
    const onContinueInProcess = vi.fn();
    const citationLabels: AssistantCitationPillsAndArtifactCardLabels = {
      freshnessFreshBadge: "✅ À jour",
      freshnessStaleBadge: "⚠️ [STALE_WARNING]",
      restrictedSourcePillSuffix: "🔒 Source restreinte",
      requestAccessCta: "Demander l'accès",
      unverifiedCitationBadge: "⚠️ [Citation non vérifiée] neutralisée",
      artifactCardTitlePrefix: "📄 Carte d'Artefact Structuré",
      copyArtifactCta: "📋 Copier",
      exportArtifactCta: "⬇️ Exporter",
      saveDraftCta: "💾 Enregistrer le brouillon (@draft)",
      continueInProcessCta: "☍ Poursuivre dans un Processus →",
      v5LockNoticeText:
        "🔒 Verrou V5 (AD-15) : Aucune écriture directe vers Git/Confluence/Jira ni publication @v1 hors Gate humaine.",
    };

    render(
      <AssistantCitationPillsAndArtifactCard
        sanitizedResponseText="Conformément à l'ADR [S1] et à l'invariant [G1], bien que [Citation non vérifiée] ait été filtrée."
        strippedPhantomTags={["S99"]}
        sources={[
          {
            tag: "S1",
            index: 1,
            uri: "confluence://claims/ADR-012",
            title: "ADR-012 — Tarification Sinistres",
            authorityTier: "REFERENCE",
            freshness: "FRESH",
            snippet: "Le plafond d'indemnisation automatique est fixé à 5 000 €.",
            lineStart: 12,
            lineEnd: 28,
            restrictedAccess: false,
            displayPill: "[S1 · ADR-012 — Tarification Sinistres]",
          },
          {
            tag: "S2",
            index: 2,
            uri: "confluence://reinsurance/audit-2026",
            title: "Audit Confidentiel Réassurance",
            authorityTier: "ACTIVE",
            freshness: "FRESH",
            snippet: null,
            lineStart: 1,
            lineEnd: 15,
            restrictedAccess: true,
            displayPill: "[S2 · 🔒 Source restreinte — Demander l'accès]",
          },
        ]}
        glossaryItems={[
          {
            tag: "G1",
            label: "Plafond Sinistre Automatique",
            ontologyLevel: "N1_DIRECTIVE",
            definition: "Tout paiement > 5 000 € exige une Gate humaine.",
          },
        ]}
        toolOutputs={[
          {
            tag: "O1",
            toolName: "@jira-triage",
            connectorUri: "jira://CLAIMS-402",
            summary: "Ticket critique en attente d'arbitrage",
          },
        ]}
        footerSummaryLine="📚 2 sources (1 REFERENCE, 1 restreinte) · 1 terme N1 · 1 outil"
        artifactTitle="Spécification Technique — Routeur Sinistres"
        artifactContent={"# Spécification Technique\n- Plafond : 5 000 € [S1]"}
        labels={citationLabels}
        onInspectSource={onInspectSource}
        onRequestRestrictedAccess={onRequestRestrictedAccess}
        onSaveDraft={onSaveDraft}
        onContinueInProcess={onContinueInProcess}
      />,
    );

    expect(
      screen.getByTestId("assistant-phantom-citations-alert").textContent,
    ).toContain("S99");

    // Clicking accessible [S1] opens side inspector panel with snippet
    fireEvent.click(screen.getByTestId("citation-pill-S1"));
    expect(onInspectSource).toHaveBeenCalledWith(
      expect.objectContaining({ tag: "S1", authorityTier: "REFERENCE" }),
    );
    expect(
      screen.getByTestId("citation-side-inspector-panel").textContent,
    ).toContain("5 000 €");

    // Restricted [S2] never leaks snippet and triggers onRequestRestrictedAccess
    expect(
      screen.getByTestId("citation-pill-restricted-S2").textContent,
    ).toContain("🔒 Source restreinte");
    fireEvent.click(screen.getByTestId("citation-request-access-btn-S2"));
    expect(onRequestRestrictedAccess).toHaveBeenCalledWith(
      "confluence://reinsurance/audit-2026",
    );

    // Structured Artifact Card actions + Verrou V5 bridge
    fireEvent.click(screen.getByTestId("artifact-card-continue-process-btn"));
    expect(onContinueInProcess).toHaveBeenCalledWith(
      "Spécification Technique — Routeur Sinistres",
      "# Spécification Technique\n- Plafond : 5 000 € [S1]",
      ["S1", "S2"],
    );
  });

  it("Story 10.4 — renders 3-tab Mon Assistant header (💬 Discussion active, 📁 Dossiers, 🕘 Historique), Layer 5 folder notes continuity, 1-click Process Bridge, 3-level sharing with restricted sources warning, and Redis turn lock banner", () => {
    const onSelectFolder = vi.fn();
    const onUpdatePinnedNotes = vi.fn();
    const onLaunchProcessFromFolder = vi.fn();
    const onChangeVisibility = vi.fn();
    const onSendCollaborativeMessage = vi.fn();

    const folderLabels: AssistantFoldersAndCollaborativeThreadViewLabels = {
      tab1ActiveDiscussionTitle: "💬 Discussion active",
      tab2FoldersTitlePrefix: "📁 Dossiers",
      tab3HistorySearchTitle: "🕘 Historique & Recherche",
      activeFolderPillPrefix: "📁 Dossier",
      pinnedNotesButtonLabel: "📌 Notes du dossier",
      launchProcessFromFolderCta: "☍ Lancer un Processus à partir de ce dossier →",
      shareButtonLabel: "👥 Partager",
      visibilityPrivateLabel: "🔒 Privé",
      visibilitySharedSelectedLabel: "👥 Partagé avec des collègues choisis",
      visibilityWorkspaceOpenLabel: "📦 Ouvert à tout l'Espace",
      restrictedSourcesWarningText:
        "⚠️ Ce dossier cite des sources restreintes : leurs extraits seront masqués (🔒 Source restreinte) pour les collègues non habilités.",
      searchPlaceholder: "Rechercher dans les discussions, dossiers et artefacts...",
    };

    render(
      <AssistantFoldersAndCollaborativeThreadView
        workspaceId="ws-claims-alpha"
        activeFolderId="folder-checkout-01"
        folders={[
          {
            folderId: "folder-checkout-01",
            title: "Refonte Tunnel Checkout",
            pinnedNotesMarkdown: "Décision #1 : conserver le PSP Stripe en secours.",
            consolidatedSummary: "Synthèse de 3 discussions sur le parcours paiement.",
            visibilityMode: "SHARED_SELECTED",
            hasRestrictedSources: true,
            assembledLayer5PromptBlock:
              "[LAYER_5_FOLDER_CONTINUITY folder=Refonte Tunnel Checkout] 📌 Notes : PSP Stripe",
          },
        ]}
        historyHits={[
          {
            itemId: "hit-thread-01",
            itemKind: "THREAD",
            title: "Arbitrage PSP Checkout",
            snippet: "Comparaison des latences 3DS2",
          },
        ]}
        activeTurnLockBanner="✍️ Yanis interroge l'assistant..."
        currentAuthorPassthroughIdentity="passthrough:oidc:u-yanis-01:yanis@orcia.io"
        labels={folderLabels}
        onSelectFolder={onSelectFolder}
        onUpdatePinnedNotes={onUpdatePinnedNotes}
        onLaunchProcessFromFolder={onLaunchProcessFromFolder}
        onChangeVisibility={onChangeVisibility}
        onSendCollaborativeMessage={onSendCollaborativeMessage}
      />,
    );

    // Redis turn lock banner & personal Passthrough identity
    expect(
      screen.getByTestId("assistant-redis-turn-lock-banner").textContent,
    ).toContain("✍️ Yanis interroge l'assistant...");
    expect(
      screen.getByTestId("assistant-author-passthrough-badge").textContent,
    ).toContain("passthrough:oidc:u-yanis-01:yanis@orcia.io");

    // Open 📌 Notes du dossier (Layer 5 Continuity) and update notes
    fireEvent.click(screen.getByTestId("assistant-folder-notes-toggle-btn"));
    expect(
      screen.getByTestId("assistant-layer5-injected-preview").textContent,
    ).toContain("LAYER_5_FOLDER_CONTINUITY");
    fireEvent.click(screen.getByTestId("assistant-save-pinned-notes-btn"));
    expect(onUpdatePinnedNotes).toHaveBeenCalledWith(
      "folder-checkout-01",
      "Décision #1 : conserver le PSP Stripe en secours.",
    );

    // Open 👥 Partager modal, check preventive restricted sources warning & change visibility
    fireEvent.click(screen.getByTestId("assistant-folder-share-modal-btn"));
    expect(
      screen.getByTestId("assistant-share-restricted-sources-warning").textContent,
    ).toContain("🔒 Source restreinte");
    fireEvent.click(screen.getByTestId("folder-visibility-btn-WORKSPACE_OPEN"));
    expect(onChangeVisibility).toHaveBeenCalledWith(
      "folder-checkout-01",
      "WORKSPACE_OPEN",
    );

    // 1-click Process Bridge (`☍ Lancer un Processus à partir de ce dossier →`)
    fireEvent.click(
      screen.getByTestId("assistant-launch-process-from-folder-btn"),
    );
    expect(onLaunchProcessFromFolder).toHaveBeenCalledWith(
      "folder-checkout-01",
      "orcia://pack-sdlc/workflows/ticket-to-tech-spec",
    );

    // Switch to Tab 2 (`📁 Dossiers (1)`) and Tab 3 (`🕘 Historique & Recherche`)
    fireEvent.click(screen.getByTestId("assistant-main-tab-FOLDERS"));
    fireEvent.click(
      screen.getByTestId("assistant-select-folder-btn-folder-checkout-01"),
    );
    expect(onSelectFolder).toHaveBeenCalledWith("folder-checkout-01");

    fireEvent.click(screen.getByTestId("assistant-main-tab-HISTORY_SEARCH"));
    expect(
      screen.getByTestId("assistant-history-hit-hit-thread-01").textContent,
    ).toContain("Arbitrage PSP Checkout");
  });

  it("Story 10.2c — renders FormattedMarkdownContent (headings, fenced code blocks with python language header & Copy button, bold/inline code, lists), clears input on send, strips internal jargon in AssistantThinkingSubWindow, and shows a single clean duration in seconds", () => {
    const onSendTurn = vi.fn();
    const speedLabels: AssistantSpeedSelectorAndStreamViewLabels = {
      headerTitle: "Routage Conversationnel",
      speed1PillLabel: "⚡ Rapide",
      speed2PillLabel: "🛠️ Outils",
      speed3DeepAuditPillLabel: "🧠 Approfondi",
      cacheHitBadge: "HIT",
      cacheMissBadge: "MISS",
      nodesDeterministicLabel: "Préparation",
      ttftBadgePrefix: "TTFT",
      inputPlaceholder: "Posez votre question...",
      sendPromptCta: "Envoyer",
    };

    const markdownResponse =
      "Voici deux façons de coder la fonction factorielle en Python. ### 1. Méthode Itérative ```python def factorielle_iterative(n): if n < 0: return \"Erreur\" resultat = 1 return resultat ``` ### 2. Résumé * **Complexité** : `O(n)` optimale * *Recommandation* : privilégier la boucle.";

    render(
      <AssistantSpeedSelectorAndStreamView
        workspaceId="ws-1"
        userId="admin@orcia.io"
        hat="PLATFORM_ADMIN"
        hideTechnicalCacheHeader={true}
        hideLegacySpeedPills={true}
        isGenerating={false}
        stepProgress={[
          {
            stepCode: "NODES_1_TO_4_DETERMINISTIC",
            label:
              "⚡ Nœuds 1–4 déterministes (Intention, RBAC, RAG SQL/pgvector & Cache 5 couches)",
            durationMs: 14.51,
            status: "COMPLETED",
            intermediateOutput:
              "Demande analysée pour l'espace « ws-1 » (rôle : PLATFORM_ADMIN) : « code la fonction factorielle en python ».",
          },
          {
            stepCode: "NODE_5_SINGLE_STREAM_LLM",
            label: "💬 Modèle IA gemma4:12b — réponse générée",
            durationMs: 33786.39,
            status: "COMPLETED",
            intermediateOutput: "Structuration de la réponse avec exemples Python.",
          },
        ]}
        streamedText={markdownResponse}
        labels={speedLabels}
        onSendTurn={onSendTurn}
      />,
    );

    // 1. Markdown headings, code block, bold, and lists are converted into structured HTML elements
    const responseBox = screen.getByTestId("assistant-streamed-response-box");
    const headings = responseBox.querySelectorAll("h3");
    expect(headings.length).toBe(2);
    expect(headings[0]?.textContent).toContain("1. Méthode Itérative");
    expect(headings[1]?.textContent).toContain("2. Résumé");

    const codeBlock = screen.getByTestId("markdown-code-block");
    expect(codeBlock.querySelector("pre code")?.textContent).toContain(
      "def factorielle_iterative(n):",
    );
    expect(codeBlock.textContent).toContain("python");
    expect(responseBox.querySelectorAll("strong").length).toBeGreaterThanOrEqual(1);
    expect(responseBox.querySelectorAll("ul li").length).toBe(2);

    // 2. Legacy speed pills row is hidden via sr-only when hideLegacySpeedPills=true
    expect(
      screen.getByTestId("assistant-legacy-speed-pills-row").className,
    ).toContain("sr-only");

    // 3. Thinking sub-window strips internal jargon (pgvector, RBAC, PLATFORM_ADMIN, ws-1) and shows single duration in seconds
    const stepListText =
      screen.getByTestId("assistant-step-progress-list").textContent ?? "";
    expect(stepListText).toContain(
      "Analyse de la question et préparation du contexte",
    );
    expect(stepListText).toContain(
      "Analyse de votre demande : « code la fonction factorielle en python ».",
    );
    expect(stepListText).not.toContain("pgvector");
    expect(stepListText).not.toContain("RBAC");
    expect(stepListText).not.toContain("PLATFORM_ADMIN");
    expect(stepListText).not.toContain("33786.39 ms");
    expect(
      screen.getByTestId("assistant-step-live-timer-NODES_1_TO_4_DETERMINISTIC")
        .textContent,
    ).toBe("< 1s");
    expect(
      screen.getByTestId("assistant-step-live-timer-NODE_5_SINGLE_STREAM_LLM")
        .textContent,
    ).toBe("34s");

    // 4. Typing a question and clicking Send clears the input field immediately
    const input = screen.getByTestId(
      "assistant-three-speed-input",
    ) as HTMLInputElement;
    fireEvent.change(input, {
      target: { value: "code la fonction factorielle en python" },
    });
    expect(input.value).toBe("code la fonction factorielle en python");
    fireEvent.click(screen.getByTestId("assistant-three-speed-send-btn"));
    expect(input.value).toBe("");
  });

  it("Story 10.2d — renders right-aligned blue user question bubble, animated thinking slider, display:none duplicate suppression, response actions bar (Like, Dislike, Copy, Regenerate), French auto-saving settings with green badge, @Agent and /Skill dynamic autocomplete, and clickable RAG source links", () => {
    const onSendTurn = vi.fn();
    const onRegenerate = vi.fn();
    const onOpenFolders = vi.fn();
    const onSaveUserPrefs = vi.fn();
    const speedLabels: AssistantSpeedSelectorAndStreamViewLabels = {
      headerTitle: "Routage Conversationnel",
      speed1PillLabel: "⚡ Rapide",
      speed2PillLabel: "🛠️ Outils",
      speed3DeepAuditPillLabel: "🧠 Approfondi",
      cacheHitBadge: "HIT",
      cacheMissBadge: "MISS",
      nodesDeterministicLabel: "Préparation",
      ttftBadgePrefix: "TTFT",
      inputPlaceholder: "Posez votre question...",
      sendPromptCta: "Envoyer",
    };

    const { rerender } = render(
      <AssistantSpeedSelectorAndStreamView
        workspaceId="ws-1"
        userId="admin@orcia.io"
        hat="PLATFORM_ADMIN"
        hideTechnicalCacheHeader={true}
        hideLegacySpeedPills={true}
        activeUserPrompt="Comment sécuriser les accès aux documents ?"
        isGenerating={true}
        stepProgress={[]}
        streamedText=""
        ragCitations={[
          {
            title: "Politique de Sécurité des Espaces",
            uri: "https://docs.orcia.local/securite/espaces",
          },
        ]}
        labels={speedLabels}
        onOpenFoldersFromPlus={onOpenFolders}
        onRegenerateLastTurn={onRegenerate}
        onSendTurn={onSendTurn}
      />,
    );

    // 1. User question bubble is right-aligned on blue background while generating, and thinking slider indicator is shown
    const userBubble = screen.getByTestId("assistant-user-question-bubble");
    expect(userBubble.textContent).toBe("Comment sécuriser les accès aux documents ?");
    expect(userBubble.style.backgroundColor).toBe("var(--color-action-primary)");
    expect(userBubble.style.marginLeft).toBe("auto");
    expect(screen.getByTestId("assistant-thinking-slider-indicator")).toBeDefined();

    // Legacy speed pills have display: none
    expect(
      screen.getByTestId("assistant-legacy-speed-pills-row").style.display,
    ).toBe("none");

    // 2. When response finishes streaming, response actions bar and clickable RAG citation links appear
    rerender(
      <AssistantSpeedSelectorAndStreamView
        workspaceId="ws-1"
        userId="admin@orcia.io"
        hat="PLATFORM_ADMIN"
        hideTechnicalCacheHeader={true}
        hideLegacySpeedPills={true}
        activeUserPrompt="Comment sécuriser les accès aux documents ?"
        isGenerating={false}
        stepProgress={[]}
        streamedText="Voici les recommandations de sécurité."
        ragCitations={[
          {
            title: "Politique de Sécurité des Espaces",
            uri: "https://docs.orcia.local/securite/espaces",
          },
        ]}
        labels={speedLabels}
        onOpenFoldersFromPlus={onOpenFolders}
        onRegenerateLastTurn={onRegenerate}
        onSendTurn={onSendTurn}
      />,
    );

    const citationLink = screen.getByTestId(
      "assistant-rag-citation-link-0",
    ) as HTMLAnchorElement;
    expect(citationLink.getAttribute("href")).toBe(
      "https://docs.orcia.local/securite/espaces",
    );
    expect(citationLink.textContent).toContain("Politique de Sécurité des Espaces");

    const likeBtn = screen.getByTestId("assistant-action-like-btn");
    expect(likeBtn.textContent).toBe("👍");
    fireEvent.click(likeBtn);
    expect(likeBtn.getAttribute("aria-pressed")).toBe("true");

    const copyBtn = screen.getByTestId("assistant-action-copy-btn");
    expect(copyBtn.textContent).toBe("📋");
    fireEvent.click(copyBtn);
    expect(copyBtn.textContent).toBe("✓");
    expect(copyBtn.getAttribute("title")).toContain("Copié");

    const detailsBtn = screen.getByTestId("assistant-action-details-btn");
    fireEvent.click(detailsBtn);
    expect(
      screen.getByTestId("assistant-response-details-popover").textContent,
    ).toContain("Modèle :");

    fireEvent.click(screen.getByTestId("assistant-action-regenerate-btn"));
    expect(onRegenerate).toHaveBeenCalledTimes(1);

    // 3. Typing @ and letters filters agents autocomplete dropdown; Enter inserts @slug at head of prompt without sending
    const input = screen.getByTestId("assistant-three-speed-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "@arch" } });
    const dropdown = screen.getByTestId("assistant-autocomplete-dropdown");
    expect(dropdown.getAttribute("data-trigger-kind")).toBe("agent");
    expect(dropdown.textContent).toContain("@architecte-solution");

    fireEvent.keyDown(input, { key: "Enter" });
    expect(input.value).toBe("@architecte-solution ");
    expect(onSendTurn).not.toHaveBeenCalled();

    // Typing / filters skills and clicking an option inserts /slug at head of prompt
    fireEvent.change(input, { target: { value: "/risq" } });
    expect(
      screen.getByTestId("assistant-autocomplete-dropdown").getAttribute("data-trigger-kind"),
    ).toBe("skill");
    fireEvent.click(screen.getByTestId("assistant-autocomplete-option-analyse-risques"));
    expect(input.value).toBe("/analyse-risques ");

    // Opening + menu, attaching an ORCIA document places pill inside prompt box and clears it immediately on send
    fireEvent.click(screen.getByTestId("assistant-prompt-plus-btn"));
    expect(screen.getByTestId("assistant-prompt-plus-popover")).toBeDefined();
    fireEvent.click(screen.getByTestId("assistant-plus-attach-orcia-doc-btn"));
    fireEvent.click(screen.getByTestId("assistant-orcia-doc-option-orcia-doc-1"));
    expect(screen.getByTestId("assistant-attached-file-pill").textContent).toContain(
      "Référentiel Métier & Règles de l'Espace",
    );

    fireEvent.change(input, { target: { value: "Explique ce document" } });
    fireEvent.click(screen.getByTestId("assistant-three-speed-send-btn"));
    expect(screen.queryByTestId("assistant-attached-files-bar")).toBeNull();
    expect(
      screen.getByTestId("assistant-user-question-attached-pill").textContent,
    ).toContain("Référentiel Métier & Règles de l'Espace");

    // Opening + menu and clicking '📁 Gérer les dossiers thématiques' closes menus and calls callback
    fireEvent.click(screen.getByTestId("assistant-prompt-plus-btn"));
    fireEvent.click(screen.getByTestId("assistant-plus-open-folders-btn"));
    expect(onOpenFolders).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("assistant-prompt-plus-popover")).toBeNull();

    // 4. Governance settings show French labels, Role dropdown, and auto-save with green badge
    render(
      <AssistantGovernanceModalAndStudio
        workspaceId="ws-1"
        canEditWorkspaceLayer={true}
        canOpenStudioModeB={true}
        assembledLayers={[]}
        studioNodes={[]}
        labels={GOV_LABELS}
        onSaveUserPreferences={onSaveUserPrefs}
      />,
    );

    const toneSelect = screen.getByTestId("assistant-gov-tone-select");
    expect(toneSelect.textContent).toContain("Équilibré & Structuré (Recommandé)");
    expect(toneSelect.textContent).not.toContain("STRUCTURED_SECTIONS");

    const hatSelect = screen.getByTestId("assistant-gov-hat-input") as HTMLSelectElement;
    expect(hatSelect.tagName).toBe("SELECT");
    fireEvent.change(hatSelect, { target: { value: "TECH_LEAD" } });

    expect(onSaveUserPrefs).toHaveBeenCalledWith(
      expect.objectContaining({ defaultHat: "TECH_LEAD" }),
    );
    expect(screen.getByTestId("assistant-gov-autosaved-badge").textContent).toContain(
      "✓ Enregistré",
    );
  });

  it("Story 10.2e — enforces progressive step thinking (collapse show on RUNNING step -> collapse hide on COMPLETED step, sticky manual user step toggle), static summary without fake steps when stepProgress is empty, streamlined Standard/Approfondi single-model pill, borderless action icons, and PLATFORM_ADMIN purge", () => {
    const onSendTurn = vi.fn();
    const speedLabels: AssistantSpeedSelectorAndStreamViewLabels = {
      headerTitle: "Routage Conversationnel",
      speed1PillLabel: "⚡ Rapide",
      speed2PillLabel: "🛠️ Outils",
      speed3DeepAuditPillLabel: "🧠 Approfondi",
      cacheHitBadge: "HIT",
      cacheMissBadge: "MISS",
      nodesDeterministicLabel: "Préparation",
      ttftBadgePrefix: "TTFT",
      inputPlaceholder: "Posez votre question...",
      sendPromptCta: "Envoyer",
    };

    const singleModelOptions = [
      {
        tier: "simple" as const,
        title: "gemma4:12b",
        subtitle: "Modèle IA configuré",
        configuredModelName: "gemma4:12b",
        hiddenDuplicate: true,
      },
      {
        tier: "medium" as const,
        title: "gemma4:12b",
        subtitle: "Modèle IA configuré",
        configuredModelName: "gemma4:12b",
      },
      {
        tier: "complex" as const,
        title: "gemma4:12b",
        subtitle: "Modèle IA configuré",
        configuredModelName: "gemma4:12b",
        hiddenDuplicate: true,
      },
    ];

    // 1. Rule A: Standard simple mode with no steps -> shows static "Réflexion pendant Xs" without toggle button or fake list
    const { rerender } = render(
      <AssistantSpeedSelectorAndStreamView
        workspaceId="ws-1"
        userId="admin@orcia.io"
        hat="PLATFORM_ADMIN"
        modelOptions={singleModelOptions}
        hideTechnicalCacheHeader={true}
        hideLegacySpeedPills={true}
        isGenerating={false}
        stepProgress={[]}
        streamedText="Réponse directe (rôle : PLATFORM_ADMIN) sans fausse étape."
        labels={speedLabels}
        onSendTurn={onSendTurn}
      />,
    );

    // Single-model pill shows "Standard ▾" without repeating model name
    const pickerTrigger = screen.getByTestId("assistant-model-and-effort-picker-trigger");
    expect(pickerTrigger.textContent).toContain("Standard");
    expect(pickerTrigger.textContent).not.toContain("gemma4:12b");

    // Open popover -> fast option is hidden (display: none), only Standard & Approfondi are shown visibly
    fireEvent.click(pickerTrigger);
    expect(screen.getByTestId("assistant-effort-option-fast").style.display).toBe("none");
    expect(screen.getByTestId("assistant-effort-option-balanced").textContent).toContain("Standard");
    expect(screen.getByTestId("assistant-effort-option-deep").textContent).toContain("Approfondi");

    // Sanitized response strips (rôle : PLATFORM_ADMIN) and action buttons have border-0 bg-transparent
    const responseBox = screen.getByTestId("assistant-streamed-response-box");
    expect(responseBox.textContent).not.toContain("PLATFORM_ADMIN");
    expect(screen.getByTestId("assistant-action-like-btn").className).toContain("border-0");
    expect(screen.getByTestId("assistant-action-regenerate-btn").textContent).toBe("↻");

    // 2. Rule B: Progressive steps in Approfondi mode -> Step 1 starts RUNNING (collapse show)
    rerender(
      <AssistantSpeedSelectorAndStreamView
        workspaceId="ws-1"
        userId="admin@orcia.io"
        hat="PLATFORM_ADMIN"
        modelOptions={singleModelOptions}
        hideTechnicalCacheHeader={true}
        hideLegacySpeedPills={true}
        isGenerating={true}
        stepProgress={[
          {
            stepCode: "STEP_1_SPEC_EDGE_CASES",
            label: "Spécification et cas limites",
            durationMs: 0,
            status: "RUNNING",
            intermediateOutput: "Cadrage des entrées/sorties et cas particuliers.",
          },
        ]}
        streamedText=""
        labels={speedLabels}
        onSendTurn={onSendTurn}
      />,
    );

    const step1Item = screen.getByTestId("assistant-step-item-STEP_1_SPEC_EDGE_CASES");
    expect(step1Item.getAttribute("data-step-expanded")).toBe("true");
    expect(
      screen.getByTestId("assistant-step-intermediate-output-STEP_1_SPEC_EDGE_CASES").style.display,
    ).not.toBe("none");

    // 3. When Step 2 starts RUNNING, Step 1 transitions to COMPLETED and auto-collapses (collapse hide), while Step 2 opens (collapse show)
    rerender(
      <AssistantSpeedSelectorAndStreamView
        workspaceId="ws-1"
        userId="admin@orcia.io"
        hat="PLATFORM_ADMIN"
        modelOptions={singleModelOptions}
        hideTechnicalCacheHeader={true}
        hideLegacySpeedPills={true}
        isGenerating={true}
        stepProgress={[
          {
            stepCode: "STEP_1_SPEC_EDGE_CASES",
            label: "Spécification et cas limites",
            durationMs: 1200,
            status: "COMPLETED",
            intermediateOutput: "Cadrage des entrées/sorties et cas particuliers.",
          },
          {
            stepCode: "STEP_2_IMPLEMENTATION_DESIGN",
            label: "Conception de l'implémentation",
            durationMs: 0,
            status: "RUNNING",
            intermediateOutput: "Structuration du code et choix techniques.",
          },
        ]}
        streamedText=""
        labels={speedLabels}
        onSendTurn={onSendTurn}
      />,
    );

    expect(
      screen.getByTestId("assistant-step-item-STEP_1_SPEC_EDGE_CASES").getAttribute("data-step-expanded"),
    ).toBe("false");
    expect(
      screen.getByTestId("assistant-step-intermediate-output-STEP_1_SPEC_EDGE_CASES").style.display,
    ).toBe("none");
    expect(
      screen.getByTestId("assistant-step-item-STEP_2_IMPLEMENTATION_DESIGN").getAttribute("data-step-expanded"),
    ).toBe("true");

    // 4. User manually clicks Step 1 toggle to re-open it (collapse show) -> it stays open even when all steps complete!
    fireEvent.click(screen.getByTestId("assistant-step-toggle-STEP_1_SPEC_EDGE_CASES"));
    expect(
      screen.getByTestId("assistant-step-item-STEP_1_SPEC_EDGE_CASES").getAttribute("data-step-expanded"),
    ).toBe("true");

    rerender(
      <AssistantSpeedSelectorAndStreamView
        workspaceId="ws-1"
        userId="admin@orcia.io"
        hat="PLATFORM_ADMIN"
        modelOptions={singleModelOptions}
        hideTechnicalCacheHeader={true}
        hideLegacySpeedPills={true}
        isGenerating={false}
        stepProgress={[
          {
            stepCode: "STEP_1_SPEC_EDGE_CASES",
            label: "Spécification et cas limites",
            durationMs: 1200,
            status: "COMPLETED",
            intermediateOutput: "Cadrage des entrées/sorties et cas particuliers.",
          },
          {
            stepCode: "STEP_2_IMPLEMENTATION_DESIGN",
            label: "Conception de l'implémentation",
            durationMs: 1400,
            status: "COMPLETED",
            intermediateOutput: "Structuration du code et choix techniques.",
          },
        ]}
        streamedText="Voici l'implémentation finale."
        labels={speedLabels}
        onSendTurn={onSendTurn}
      />,
    );

    // Step 1 remains expanded (manually opened by user), while Step 2 auto-collapsed on completion
    expect(
      screen.getByTestId("assistant-step-item-STEP_1_SPEC_EDGE_CASES").getAttribute("data-step-expanded"),
    ).toBe("true");
    expect(
      screen.getByTestId("assistant-step-item-STEP_2_IMPLEMENTATION_DESIGN").getAttribute("data-step-expanded"),
    ).toBe("false");
  });
});
