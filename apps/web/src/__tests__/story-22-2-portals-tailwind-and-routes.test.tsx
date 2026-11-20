import {
  CommandPaletteModal,
  UpstreamChallengeRewindModal,
  UserSettingsModalDialog,
} from "@orcia/ui";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { orciaTailwindV4Plugin } from "../../viteTailwindV4Plugin";
import { FirstBootAdminSetupModal } from "../components/FirstBootAdminSetupModal";
import { clearPlatformSetupStorage } from "../components/platformSetupStore";
import { AiModelConfigModal } from "../features/admin/ai-models/AiModelConfigModal";
import { I18nProvider } from "../i18n";
import { frDictionary } from "../i18n/locales/fr";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { seedVitestPlatformSetupState } from "./vitest.setup";

afterEach(() => {
  cleanup();
  clearPlatformSetupStorage();
  vi.restoreAllMocks();
});

const SAMPLE_TIER_LABELS = {
  tierLabel: "Palier Cognitif",
  effortLabel: "Effort",
  simpleBadge: "Simple",
  mediumBadge: "Standard",
  complexBadge: "Approfondi",
  autoBadge: "Automatique",
  effortDefault: "Par défaut",
  effortFast: "Rapide",
  effortBalanced: "Équilibré",
  effortDeep: "Approfondi",
};

async function renderRouteAsAdmin(initialPath: string) {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: "0192c4e0-0000-7000-8000-000000000101",
          name: "Direction Produit",
          slug: "dir-produit",
          kind: "BU",
          parent_id: null,
          billing_enabled: true,
        },
        {
          id: "0192c4e0-0000-7000-8000-000000000102",
          name: "Équipe Plateforme",
          slug: "equipe-plateforme",
          kind: "TEAM",
          parent_id: "0192c4e0-0000-7000-8000-000000000101",
          billing_enabled: true,
        },
      ],
    },
    {
      email: "admin@orcia.test",
      displayName: "Admin 22.2",
      roles: ["PLATFORM_ADMIN"],
    },
  );
  useAuthSessionStore.getState().setAuthSession({
    isAuthenticated: true,
    email: "admin@orcia.test",
    displayName: "Admin 22.2",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "PLATFORM_ADMIN",
  });

  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [initialPath] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  const rendered = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...rendered, router, queryClient };
}

describe("Story 22.2 — Portals OrciaDialog, Tailwind v4 Compilation, Display:None Purge & Route Decoupling", () => {
  it("mounts UserSettingsModalDialog, FirstBootAdminSetupModal, CommandPaletteModal and UpstreamChallengeRewindModal directly into document.body via Radix Portal", () => {
    // 1. UserSettingsModalDialog
    render(
      <UserSettingsModalDialog
        open={true}
        onOpenChange={vi.fn()}
        activeTab="GENERAL"
        onSelectTab={vi.fn()}
        userEmail="admin@orcia.test"
        userRole="PLATFORM_ADMIN"
        theme="light"
        locale="fr"
        defaultAssistantHat="ANALYST_PM_PO"
        assistantTone="balanced"
        personalInstructions=""
        autoOpenHelp={true}
        notificationsEnabled={true}
        mcpTokens={[]}
        lastIssuedPlaintext={null}
        labels={frDictionary.userAccountAndSettings}
        onUpdatePreferences={vi.fn()}
        onCreateMcpToken={vi.fn()}
        onRevokeMcpToken={vi.fn()}
      />,
    );
    const settingsDialog = screen.getByTestId("user-settings-modal");
    expect(settingsDialog.getAttribute("role")).toBe("dialog");
    expect(settingsDialog.parentElement).toBe(document.body);
    cleanup();

    // 2. FirstBootAdminSetupModal
    render(
      <FirstBootAdminSetupModal
        isOpen={true}
        isFr={true}
        onClose={vi.fn()}
        onCreatePlatformAdmin={vi.fn()}
      />,
    );
    const firstBootDialog = screen.getByTestId("first-boot-admin-setup-modal");
    expect(firstBootDialog.getAttribute("role")).toBe("dialog");
    expect(firstBootDialog.parentElement).toBe(document.body);
    cleanup();

    // 3. CommandPaletteModal
    render(
      <CommandPaletteModal
        isOpen={true}
        items={[]}
        labels={frDictionary.commandPalette}
        onClose={vi.fn()}
      />,
    );
    const paletteDialog = screen.getByTestId("command-palette-modal");
    expect(paletteDialog.getAttribute("role")).toBe("dialog");
    expect(paletteDialog.parentElement).toBe(document.body);
    cleanup();

    // 4. UpstreamChallengeRewindModal
    render(
      <UpstreamChallengeRewindModal
        isOpen={true}
        preview={{
          runId: "run-22-2",
          challengerStepKey: "step-2",
          targetUpstreamStepKey: "step-1",
          challengedSectionKey: "rule-x",
          targetProfileArchetype: "PM_PO",
          translatedSummary: "Impact synthétique",
          invalidatedDownstreamStepKeys: ["step-2"],
          invalidatedArtifactSections: ["step-1:rule-x"],
          invalidatedOntologyAxiomKeys: [],
          preservedUpstreamStepKeys: [],
          upstreamTokensSaved: 100,
        }}
        labels={{
          modalTitle: "Challenge Amont",
          modalSubtitle: "Sous-titre",
          targetStepLabel: "Step cible",
          sectionKeyLabel: "Section",
          reasonLabel: "Raison",
          reasonPlaceholder: "Raison...",
          whatIfTitle: "What-If",
          invalidatedStepsLabel: "Steps invalidés",
          invalidatedSectionsLabel: "Sections invalidées",
          invalidatedAxiomsLabel: "Axiomes",
          preservedStepsLabel: "Préservés",
          translatedSummaryLabel: "Traduction",
          submitChallengeCta: "Soumettre",
          replayStepCta: "Rejouer",
          closeCta: "Fermer",
          challengeSubmittedFeedback: "Transmis",
          replayTriggeredFeedback: "Rejoué",
        }}
      />,
    );
    const challengeDialog = screen.getByRole("dialog");
    expect(challengeDialog.getAttribute("data-ux-component")).toBe(
      "upstream-challenge-rewind-modal",
    );
    expect(challengeDialog.parentElement).toBe(document.body);
  });

  it("renders AiModelConfigModal without initial error before interaction, keeps sticky footer and exposes llm-provider-preset-ollama", async () => {
    render(
      <I18nProvider initialLocale="fr">
        <AiModelConfigModal
          open={true}
          onOpenChange={vi.fn()}
          mode="create"
          initialMapping={null}
          labels={frDictionary.aiModelsHub}
          tierLabels={SAMPLE_TIER_LABELS}
          isFr={true}
          onSubmitCreate={vi.fn().mockResolvedValue(true)}
          onSubmitPatch={vi.fn().mockResolvedValue(true)}
        />
      </I18nProvider>,
    );

    const dialog = screen.getByTestId("ai-model-config-modal");
    expect(dialog.parentElement).toBe(document.body);
    expect(dialog.querySelector(".orcia-ds-dialog-footer")).not.toBeNull();
    expect(screen.queryByTestId("ai-model-primary-model-input-error-msg")).toBeNull();
    expect(screen.queryByTestId("ai-model-form-error")).toBeNull();
    expect(screen.getByTestId("llm-provider-preset-ollama")).toBeDefined();
    expect(screen.getByTestId("save-ai-model-btn")).toBeDefined();
  });

  it("compiles Tailwind v4 utility classes (.z-50, .h-dvh, .overflow-y-auto, .pl-5) via viteTailwindV4Plugin", async () => {
    const plugin = orciaTailwindV4Plugin();
    const loadHook = plugin.load as (id: string) => Promise<string | null>;
    const css = await loadHook("\0virtual:orcia-tailwind.css");
    expect(css).not.toBeNull();
    expect(css).toContain(".z-50");
    expect(css).toContain(".h-dvh");
    expect(css).toContain(".overflow-y-auto");
    expect(css).toContain(".pl-5");
  });

  it("contains zero display: none in purged frontend files", () => {
    const repoRoot = path.resolve(__dirname, "../../../..");
    const purgedFiles = [
      "apps/web/src/features/catalog/index.tsx",
      "apps/web/src/features/workspaces/index.tsx",
      "apps/web/src/features/inbox/InboxAuxiliaryPanels.tsx",
      "packages/ui/src/primitives/FourZoneSidebarRail.tsx",
    ];
    for (const relPath of purgedFiles) {
      const content = fs.readFileSync(path.join(repoRoot, relPath), "utf8");
      expect(content).not.toMatch(/display:\s*["']none["']/);
    }
  });

  it("decouples /catalog, /agents (single remote-service-test-bench), /help (single contextual-help-hybrid-panel & accordion), /organization (invite btn) and studio whatif testid", async () => {
    // 1. /catalog renders visible catalog-explorer-panel
    const catalogRender = await renderRouteAsAdmin("/catalog");
    expect(screen.getByTestId("catalog-explorer-panel")).toBeDefined();
    expect(screen.queryByTestId("remote-service-test-bench")).toBeNull();
    catalogRender.unmount();

    // 2. /agents renders 1 single remote-service-test-bench in connections tab
    const agentsRender = await renderRouteAsAdmin("/agents");
    fireEvent.click(screen.getByTestId("agents-subview-tab-connections"));
    expect(screen.getAllByTestId("remote-service-test-bench").length).toBe(1);
    agentsRender.unmount();

    // 3. /help suppresses ShellContextualHelpColumn (only 1 contextual-help-hybrid-panel) and accordion toggles steps
    const helpRender = await renderRouteAsAdmin("/help");
    expect(screen.queryByTestId("four-zone-contextual-help-column")).toBeNull();
    expect(screen.getAllByTestId("contextual-help-hybrid-panel").length).toBe(1);
    expect(screen.queryByTestId("help-accordion-steps-content")).toBeNull();
    fireEvent.click(screen.getByTestId("help-accordion-steps-btn"));
    expect(screen.getByTestId("help-accordion-steps-content")).toBeDefined();
    helpRender.unmount();

    // 4. /organization always renders open-invite-org-user-modal-btn
    const orgRender = await renderRouteAsAdmin("/organization");
    expect(await screen.findByTestId("open-invite-org-user-modal-btn")).toBeDefined();
    orgRender.unmount();

    // 5. /processes/studio/wf-01-qualification-prd renders studio-view-mode-whatif
    const studioRender = await renderRouteAsAdmin("/processes/studio/wf-01-qualification-prd");
    expect(await screen.findByTestId("studio-view-mode-whatif")).toBeDefined();
    studioRender.unmount();
  });

  it("persists workspace exception waivers via @orcia/api-client across F5 unmount/render", async () => {
    const queryClient1 = createOrciaQueryClient();
    const history1 = createMemoryHistory({ initialEntries: ["/settings"] });
    const router1 = createOrciaRouter({ queryClient: queryClient1, history: history1 });
    await router1.load();

    const firstRender = render(
      <QueryClientProvider client={queryClient1}>
        <RouterProvider router={router1} />
      </QueryClientProvider>,
    );

    fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), {
      target: { value: "Admin 22.2" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), {
      target: { value: "admin@orcia.fr" },
    });
    fireEvent.click(screen.getByTestId("first-boot-admin-submit-btn"));

    await router1.navigate({ to: "/spaces" });
    fireEvent.click(await screen.findByTestId("toggle-create-workspace-form-btn"));
    await screen.findByTestId("workspace-name-input");

    fireEvent.change(screen.getByTestId("workspace-name-input"), {
      target: { value: "Espace Waivers 22.2" },
    });
    fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("workspaces-filter-all").textContent).toContain("Tous (1)");
    });

    const registerWaiverBtn = await screen.findByTestId("register-waiver-btn-workspace-default");
    fireEvent.click(registerWaiverBtn);

    await waitFor(() => {
      expect(screen.getAllByTestId(/^waiver-item-/).length).toBe(1);
    });

    firstRender.unmount();

    const secondQueryClient = createOrciaQueryClient();
    const secondHistory = createMemoryHistory({ initialEntries: ["/spaces"] });
    const secondRouter = createOrciaRouter({
      queryClient: secondQueryClient,
      history: secondHistory,
    });
    await secondRouter.load();
    render(
      <QueryClientProvider client={secondQueryClient}>
        <RouterProvider router={secondRouter} />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      const persistedWaivers = screen.getAllByTestId(/^waiver-item-/);
      expect(persistedWaivers.length).toBe(1);
      expect(persistedWaivers[0]?.textContent).toContain("RULE_FRESHNESS_DRIFT");
    });
  });
});
