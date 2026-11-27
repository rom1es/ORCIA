import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { InboxFeaturePanel } from "../features/inbox";
import {
  ensureZone4HelpOpen,
  renderOrciaRoute,
  renderShellModule,
  resetShellTestState,
} from "./setup/shellTestHelpers";
import { seedVitestPlatformSetupState } from "./vitest.setup";

describe("@orcia/web Mon Assistant, Mes Agents, Mes Processus, and Help", () => {
  beforeEach(() => {
    resetShellTestState();
  });

  it("mounts the all-in-one Mon Assistant screen on /assistant with 3-Speed selector, Folders, Citations, and 4-Level Governance (Story 12.2)", async () => {
    await renderOrciaRoute("/assistant");

    expect(screen.getByTestId("inbox-feature-panel")).toBeDefined();
    expect(screen.getByTestId("assistant-folders-and-collaborative-thread-view")).toBeDefined();
    expect(screen.getByTestId("assistant-speed-selector-and-stream")).toBeDefined();
    expect(screen.queryByTestId("assistant-citations-card-wrapper")).toBeNull();

    fireEvent.click(screen.getByTestId("assistant-open-governance-btn"));
    expect(screen.getByTestId("assistant-governance-container")).toBeDefined();
  });

  it("mounts Mes Espaces 5-tabs, DNA Starlark compiler, MCP/A2A Test Bench, Pack Builder Studio, and Help Generator across /spaces, /agents, /processes, and /help (Story 12.3)", async () => {
    seedVitestPlatformSetupState(
      {
        workspaces: [
          {
            workspaceId: "0195f000-0000-7000-8000-000000000311",
            slug: "ws-equipe-alpha",
            name: "Espace Équipe Alpha",
            ownerOrgUnitId: "0192c4e0-0000-7000-8000-000000000101",
            ownerOrgUnitName: "Direction Technique",
            visibilityMode: "STANDARD",
            lifecyclePhase: "BUILD",
            accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
            finopsCostUsd: 0,
          },
        ],
      },
      { email: "admin@orcia.fr", displayName: "Admin", roles: ["PLATFORM_ADMIN"] },
    );
    const { router } = await renderOrciaRoute("/spaces");

    expect(await screen.findByTestId("workspace-five-tabs-view")).toBeDefined();
    expect(screen.queryByTestId("dna-starlark-glossary-view")).toBeNull();
    fireEvent.click(screen.getByTestId("workspace-tab-GLOSSARY_RULES"));
    expect(await screen.findByTestId("dna-starlark-glossary-view")).toBeDefined();

    await act(async () => { await router.navigate({ to: "/agents" }); });
    fireEvent.click(screen.getByTestId("agents-subview-tab-connections"));
    expect(screen.getByTestId("remote-service-test-bench")).toBeDefined();

    await act(async () => { await router.navigate({ to: "/processes" }); });
    expect(screen.getByTestId("processes-hub-v2-page")).toBeDefined();
    expect(screen.getByTestId("processes-hub-tabs")).toBeDefined();
    fireEvent.click(screen.getByTestId("processes-tab-validations"));
    expect(screen.getByTestId("processes-active-dossiers-card")).toBeDefined();
    expect(screen.queryByTestId("settings-workflows-section")).toBeNull();
    expect(screen.queryByTestId("pack-builder-studio-view")).toBeNull();

    await act(async () => { await router.navigate({ to: "/gates" }); });
    expect(screen.getByTestId("gates-dedicated-review-page")).toBeDefined();
    expect(screen.getByTestId("gates-adaptive-human-review-section")).toBeDefined();
    expect(screen.getByTestId("gates-open-human-review-btn")).toBeDefined();
    expect(screen.queryByTestId("settings-workflows-section")).toBeNull();
    expect(screen.queryByTestId("pack-builder-studio-view")).toBeNull();

    await act(async () => { await router.navigate({ to: "/settings/packs" }); });
    const studioText = screen.getByTestId("settings-workflows-section").textContent ?? "";
    expect(screen.getByTestId("settings-workflows-section")).toBeDefined();
    expect(screen.getByTestId("pack-builder-studio-view")).toBeDefined();
    expect(screen.getByTestId("help-article-generator-validator-view")).toBeDefined();
    for (const forbidden of [
      "PUBLISHED 0",
      "DRAFT 0",
      "TRASH 0",
      "ACTIVE_RUNS",
      "PAUSED_ARBITRATION",
      "(0p / 0s)",
      "e3b0c44298fc", // pragma: allowlist secret
    ]) {
      expect(studioText).not.toContain(forbidden);
    }

    expect(screen.queryByTestId("contextual-info-trigger-workflows-overview")).toBeNull();
    ensureZone4HelpOpen();
    expect(screen.getByTestId("four-zone-contextual-help-column")).toBeDefined();
    expect(screen.getByTestId("help-section-workflows-overview")).toBeDefined();
    fireEvent.click(screen.getByTestId("open-create-process-modal-btn"));
    expect(screen.getByTestId("workflow-title-input")).toBeDefined();
    fireEvent.click(screen.getByTestId("contextual-info-trigger-workflows-instructions"));
    expect(screen.getByTestId("help-section-workflows-instructions").getAttribute("data-active")).toBe("true");
    fireEvent.click(screen.getByTestId("contextual-info-trigger-workflows-deliverable-contract"));
    expect(screen.getByTestId("help-section-workflows-deliverable-contract").getAttribute("data-active")).toBe("true");
    fireEvent.change(screen.getByTestId("workflow-title-input"), { target: { value: "Revue de contrat fournisseur" } });
    fireEvent.click(screen.getByTestId("save-workflow-btn"));
    expect(screen.getByTestId("workflow-row-revue-de-contrat-fournisseur").textContent).toContain("Revue de contrat fournisseur");

    const docProcessCard = screen.getByTestId("orcia-doc-generation-process-card");
    expect(docProcessCard.textContent).toContain("Génération de la Documentation ORCIA");
    expect(docProcessCard.textContent).toContain("@Rédacteur-Documentation-Orcia");
    fireEvent.click(screen.getByTestId("run-orcia-doc-generation-process-btn"));
    expect(screen.getByTestId("workflow-row-generate-orcia-documentation")).toBeDefined();
    const stepsSummary = screen.getByTestId("orcia-doc-generation-steps-summary");
    expect(stepsSummary.textContent).toContain("Étape 1 — Inventaire du dépôt ORCIA");
    expect(stepsSummary.textContent).toContain("Étape 2 — Génération & Enrichissement des Guides et de la FAQ");
    expect(stepsSummary.textContent).toContain("Étape 3 — Contrôle Qualité Déterministe (validate_help_article)");
    expect(stepsSummary.textContent).toContain("Étape 4 — Publication & Rattachement à Chaud (/showcase & docs/help/)");
    const outputPreview = screen.getByTestId("orcia-doc-generation-output-preview");
    expect(outputPreview.textContent).toContain("Guide Fonctionnel par Écran");
    expect(outputPreview.textContent).toContain("Architecture & Modèle Métier");
    fireEvent.click(screen.getByTestId("load-orcia-doc-process-in-builder-btn"));
    expect((screen.getByTestId("workflow-key-input") as HTMLInputElement).value).toBe("generate-orcia-documentation");

    await act(async () => { await router.navigate({ to: "/help" }); });
    const helpPanels = screen.getAllByTestId("contextual-help-hybrid-panel");
    expect(helpPanels.some((el) => el.getAttribute("data-mode") === "HELP_MENU_CENTER")).toBe(true);
    expect(screen.getByTestId("topbar-breadcrumb").textContent).toContain("Aide");
  });

  it("supports creating Skills, creating Agents via modals, configuring & executing both in sandbox modals, and surviving F5 reload on /agents", async () => {
    const { resetCachedAgentsAndSkillsForTest } = await import("../features/catalog/index");
    resetCachedAgentsAndSkillsForTest();

    const firstRender = await renderOrciaRoute("/agents");
    expect(screen.getByTestId("agents-and-skills-manager-view")).toBeDefined();
    expect(screen.getByTestId("workspace-assistant-pinned-card")).toBeDefined();
    expect(screen.getByTestId("agents-empty-state")).toBeDefined();
    expect(screen.queryByTestId("create-agent-modal")).toBeNull();

    fireEvent.click(screen.getByTestId("agents-subview-tab-skills"));
    fireEvent.click(screen.getByTestId("open-create-skill-drawer-btn"));
    expect(screen.getByTestId("create-skill-modal")).toBeDefined();
    fireEvent.change(screen.getByTestId("skill-name-input"), { target: { value: "Analyse Conformité Fournisseur" } });
    fireEvent.change(screen.getByTestId("skill-objective-input"), { target: { value: "Détecter les clauses à risque" } });
    fireEvent.change(screen.getByTestId("skill-instructions-input"), { target: { value: "Vérifier responsabilité." } });
    fireEvent.click(screen.getByTestId("create-skill-submit-btn"));
    expect(screen.queryByTestId("create-skill-modal")).toBeNull();

    const skillId = "skill-analyse-conformite-fournisseur";
    expect(screen.getByTestId(`skill-card-${skillId}`)).toBeDefined();
    fireEvent.click(screen.getByTestId(`open-skill-detail-modal-btn-${skillId}`));
    expect(screen.getByTestId(`skill-detail-modal-${skillId}`)).toBeDefined();
    fireEvent.change(screen.getByTestId(`skill-test-input-${skillId}`), { target: { value: "Article 12" } });
    fireEvent.click(screen.getByTestId(`run-skill-btn-${skillId}`));
    expect(screen.getAllByTestId(`skill-execution-output-${skillId}`)[0]?.textContent).toContain("Analyse Conformité Fournisseur");
    expect(screen.getAllByTestId(`skill-execution-output-${skillId}`)[0]?.textContent).toContain("Article 12");
    fireEvent.click(screen.getByTestId(`close-skill-detail-modal-btn-${skillId}`));
    expect(screen.queryByTestId(`skill-detail-modal-${skillId}`)).toBeNull();

    fireEvent.click(screen.getByTestId("agents-subview-tab-agents"));
    fireEvent.click(screen.getByTestId("open-create-agent-drawer-btn"));
    expect(screen.getByTestId("create-agent-modal")).toBeDefined();
    fireEvent.change(screen.getByTestId("agent-name-input"), { target: { value: "Expert Achats IT" } });
    fireEvent.change(screen.getByTestId("agent-role-input"), { target: { value: "Sécuriser les contrats cloud" } });
    fireEvent.change(screen.getByTestId("agent-instructions-input"), { target: { value: "Synthèse claire." } });
    fireEvent.click(screen.getByTestId(`create-agent-skill-checkbox-${skillId}`));
    fireEvent.click(screen.getByTestId("create-agent-submit-btn"));
    expect(screen.queryByTestId("create-agent-modal")).toBeNull();

    const agentId = "agent-expert-achats-it";
    expect(screen.getByTestId(`agent-card-${agentId}`)).toBeDefined();
    fireEvent.click(screen.getByTestId(`open-agent-detail-modal-btn-${agentId}`));
    expect(screen.getByTestId(`agent-detail-modal-${agentId}`)).toBeDefined();
    fireEvent.change(screen.getByTestId(`agent-test-input-${agentId}`), { target: { value: "Examine le contrat SaaS Acme" } });
    fireEvent.click(screen.getByTestId(`run-agent-btn-${agentId}`));
    expect(screen.getAllByTestId(`agent-execution-output-${agentId}`)[0]?.textContent).toContain("Analyse Conformité Fournisseur");
    expect(screen.getAllByTestId(`agent-execution-output-${agentId}`)[0]?.textContent).toContain("Examine le contrat SaaS Acme");
    await waitFor(() => {
      expect(screen.getByTestId(`agent-lifecycle-badge-${agentId}`).textContent).toContain("Actif");
    });
    fireEvent.click(screen.getByTestId(`close-agent-detail-modal-btn-${agentId}`));
    expect(screen.queryByTestId(`agent-detail-modal-${agentId}`)).toBeNull();

    firstRender.unmount();
    await renderOrciaRoute("/agents");
    expect(screen.getByTestId(`agent-card-${agentId}`)).toBeDefined();
    expect(screen.getByTestId(`agent-execution-output-${agentId}`).textContent).toContain("Examine le contrat SaaS Acme");
    fireEvent.click(screen.getByTestId("agents-subview-tab-skills"));
    expect(screen.getByTestId(`skill-card-${skillId}`)).toBeDefined();
    expect(screen.getByTestId("agents-subview-tab-connections").style.display).not.toBe("none");
    expect(screen.queryByTestId("catalog-explorer-panel-wrapper")).toBeNull();
    expect(screen.queryByTestId("remote-service-test-bench-wrapper")).toBeNull();
    fireEvent.click(screen.getByTestId("agents-subview-tab-connections"));
    expect(screen.getByTestId("connections-subview-panel")).toBeDefined();
    expect(screen.getByTestId("remote-service-test-bench")).toBeDefined();

    const { seedVitestActivePacks } = await import("./setup/installedPacksMockHandler");
    seedVitestActivePacks(["orcia-pack-sdlc"]);
    fireEvent.click(screen.getByTestId("agents-subview-tab-agents"));
    fireEvent.click(screen.getByTestId("load-pack-agents-templates-btn"));
    expect(await screen.findByTestId("agent-card-agent-architecte-solution")).toBeDefined();
    const packBadgeEl = screen.getByTestId("agent-visibility-badge-agent-architecte-solution");
    expect(packBadgeEl.querySelector("svg")).not.toBeNull();
    expect(packBadgeEl.textContent).toContain("Pack Métier (orcia-pack-sdlc)");
    expect(screen.queryByTestId("delete-agent-btn-agent-architecte-solution")).toBeNull();

    fireEvent.click(screen.getByTestId("use-agent-in-assistant-btn-agent-architecte-solution"));
    const assistantInput = screen.getByTestId("assistant-three-speed-input") as HTMLInputElement;
    expect(assistantInput.value).toBe("@architecte-solution ");
    fireEvent.change(assistantInput, { target: { value: "@expert" } });
    expect(screen.getByTestId("assistant-autocomplete-dropdown")).toBeDefined();
    fireEvent.click(screen.getByTestId("assistant-autocomplete-option-expert-achats-it"));
    expect(assistantInput.value).toBe("@expert-achats-it ");
    resetCachedAgentsAndSkillsForTest();
  });

  it("preserves the user question bubble, animated ThinkingDots spinner, and ongoing thinking counter when navigating away from Mon Assistant (/assistant) and returning while thinking is in progress", () => {
    (globalThis as Record<string, unknown>).__ORCIA_TEST_KEEP_STREAM_PENDING__ = true;
    const { unmount } = renderShellModule("inbox", "fr", <InboxFeaturePanel />);

    const promptInput = screen.getByTestId("assistant-three-speed-input") as HTMLInputElement;
    fireEvent.change(promptInput, { target: { value: "affiche une solution du jeu du déplacement du cavalier" } });
    fireEvent.click(screen.getByTestId("assistant-three-speed-send-btn"));
    expect(screen.getByTestId("assistant-user-question-bubble").textContent).toBe(
      "affiche une solution du jeu du déplacement du cavalier",
    );
    expect(screen.getByTestId("assistant-thinking-pulsing-dots")).toBeDefined();
    expect(screen.getByTestId("assistant-stop-square-icon").querySelector("svg")).not.toBeNull();

    unmount();
    renderShellModule("inbox", "fr", <InboxFeaturePanel />);
    expect(screen.getByTestId("assistant-user-question-bubble").textContent).toBe(
      "affiche une solution du jeu du déplacement du cavalier",
    );
    expect(screen.getByTestId("assistant-thinking-pulsing-dots").querySelectorAll(".orcia-thinking-dot").length).toBe(3);
    expect(screen.getByTestId("assistant-stop-square-icon").querySelector("svg")).not.toBeNull();
    expect(screen.getByTestId("assistant-thinking-subwindow-header-label").textContent).toContain("Réflexion en cours");
  });
});
