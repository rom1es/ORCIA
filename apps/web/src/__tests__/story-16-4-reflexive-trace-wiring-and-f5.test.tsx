// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { ShellContainer } from "../components/ShellContainer";
import { CatalogFeaturePanel } from "../features/catalog";
import { InboxFeaturePanel } from "../features/inbox";
import { clearSavedAssistantConversationsStorage } from "../features/inbox/savedConversationsStore";
import { resetPersistedWorkflowsV2 } from "../features/processes/processStudioV2Data";
import { I18nProvider } from "../i18n";
import { enDictionary } from "../i18n/locales/en";
import { frDictionary } from "../i18n/locales/fr";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import {
  getRecordedVitestApiCalls,
  seedVitestPlatformSetupState,
} from "./vitest.setup";
import { setVitestForceNextSourceRedacted } from "./vitestReflexiveBackend";

afterEach(() => {
  cleanup();
});

const FORBIDDEN_JARGON =
  /\b(DBOS|asyncio|Redis|SSE|Claim-Check|déterministe|non-déterministe|deterministic|non-deterministic)\b/i;

function seedBaseWorkspaceState(): void {
  seedVitestPlatformSetupState({
    org_units: [],
    rbac_grants: [],
    llm_tiers: [],
    workspaces: [
      {
        workspaceId: "ws-16-4",
        name: "Espace Architecture",
        visibilityMode: "STANDARD",
        ownerOrgUnitName: "Direction Produit",
        lifecyclePhase: "BUILD",
        suggestedWorkflows: [],
        accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
        finopsCostUsd: 0,
      },
    ],
    datasources: [
      {
        id: "ds-cap",
        alias: "capabilities",
        uri: "docs/product/capabilities.yaml",
        connectorType: "LOCAL_REPO",
        status: "READY",
      },
    ],
    packs: [{ packKey: "orcia-pack-sdlc", displayName: "Pack SDLC" }],
    workflows: [],
    runs: [],
    catalog_items: [],
    ontology_concepts: [],
  });
}

describe("Story 16.4 — Vertical Wiring Across 3 Surfaces, Surgical Line Inspector & F5 Survival", () => {
  it("wires Mon Assistant (/assistant): 2 visible effort modes only, unified AgentExecutionTrace (zero duplicate thinking box), and surgical #Lstart-end drawer", async () => {
    clearSavedAssistantConversationsStorage();
    seedBaseWorkspaceState();

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <InboxFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    expect(document.body.textContent ?? "").not.toContain("Moteur :");
    fireEvent.click(
      screen.getByTestId("assistant-model-and-effort-picker-trigger"),
    );
    const fastBtn = screen.queryByTestId("assistant-effort-option-fast");
    if (fastBtn) {
      expect(fastBtn.style.display).toBe("none");
    }
    expect(
      screen.getByTestId("assistant-effort-option-balanced"),
    ).toBeDefined();
    expect(screen.getByTestId("assistant-effort-option-deep")).toBeDefined();
    fireEvent.click(screen.getByTestId("assistant-effort-option-deep"));

    fireEvent.change(screen.getByTestId("assistant-three-speed-input"), {
      target: {
        value: "Vérifie le registre capabilities et ses preuves d'exécution",
      },
    });
    fireEvent.click(screen.getByTestId("assistant-three-speed-send-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("agent-execution-trace")).toBeDefined();
    });
    expect(screen.queryByTestId("assistant-thinking-subwindow")).toBeNull();

    const headerToggles = screen.getAllByTestId("trace-group-header-btn");
    for (const btn of headerToggles) {
      if (btn.getAttribute("aria-expanded") === "false") {
        fireEvent.click(btn);
      }
    }

    const filePill = await waitFor(() => {
      const pills = screen.getAllByTestId("trace-file-analyzed-pill");
      expect(pills.length).toBeGreaterThan(0);
      return pills[0]!;
    });
    fireEvent.click(filePill);

    await waitFor(() => {
      expect(screen.getByTestId("source-line-inspector-drawer")).toBeDefined();
      expect(screen.getByTestId("inspector-code-line-1")).toBeDefined();
    });
    expect(
      screen
        .getByTestId("inspector-code-line-1")
        .getAttribute("data-highlighted"),
    ).toBe("true");

    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => {
      expect(screen.queryByTestId("source-line-inspector-drawer")).toBeNull();
    });
  });

  it("wires Mes Agents (/catalog) sandbox to AgentExecutionTrace and enforces READ_SOURCE redaction (0 lines leaked)", async () => {
    seedBaseWorkspaceState();

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <CatalogFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    const openAgentBtn = await waitFor(() => {
      const buttons = screen.getAllByTestId(/^open-agent-detail-modal-/);
      expect(buttons.length).toBeGreaterThan(0);
      return buttons[0]!;
    });
    fireEvent.click(openAgentBtn);

    const testInput = await waitFor(() => {
      const inputs = screen.getAllByTestId(/^agent-test-input-/);
      expect(inputs.length).toBeGreaterThan(0);
      return inputs[0]!;
    });
    fireEvent.change(testInput, {
      target: { value: "Audite la couverture des capacités livrées" },
    });

    const runButtons = screen.getAllByTestId(/^run-agent-btn-/);
    fireEvent.click(runButtons[0]!);

    const pill = await waitFor(() => {
      expect(screen.getByTestId("agent-sandbox-trace-slot")).toBeDefined();
      const pills = screen.getAllByTestId("trace-file-analyzed-pill");
      expect(pills.length).toBeGreaterThan(0);
      return pills[0]!;
    });

    setVitestForceNextSourceRedacted(true);
    fireEvent.click(pill);

    await waitFor(() => {
      expect(screen.getByTestId("inspector-redacted-banner")).toBeDefined();
    });
    expect(screen.queryAllByTestId(/^inspector-code-line-/).length).toBe(0);
  });

  it("wires Mes Processus (/processes): @Agent delegation, Synthétiser maintenant vs Arrêter, WritePreviewCard, and F5 survival", async () => {
    resetPersistedWorkflowsV2();
    seedBaseWorkspaceState();

    const mountProcessesRoute = async () => {
      const queryClient = createOrciaQueryClient();
      const history = createMemoryHistory({ initialEntries: ["/processes"] });
      const router = createOrciaRouter({ queryClient, history });
      await router.load();
      return render(
        <I18nProvider initialLocale="fr">
          <QueryClientProvider client={queryClient}>
            <RouterProvider router={router} />
          </QueryClientProvider>
        </I18nProvider>,
      );
    };

    const firstMount = await mountProcessesRoute();

    const launchWfBtn = await waitFor(() =>
      screen.getByTestId(
        "execute-workflow-btn-wf-generate-orcia-documentation",
      ),
    );
    fireEvent.click(launchWfBtn);

    await waitFor(() => {
      expect(screen.getByTestId("interactive-run-hitl-drawer")).toBeDefined();
      expect(screen.getByTestId("agent-execution-trace")).toBeDefined();
    });
    expect(screen.getByTestId("agent-execution-trace").textContent).toContain(
      "@analyste-metier",
    );

    // 1. Live run -> Synthétiser maintenant calls /synthesize-now (not /cancel)
    fireEvent.click(
      screen.getByTestId("process-launch-live-investigation-btn"),
    );
    const synthBtn = await waitFor(() =>
      screen.getByTestId("trace-synthesize-now-btn"),
    );
    fireEvent.click(synthBtn);

    await waitFor(() => {
      const calls = getRecordedVitestApiCalls();
      expect(
        calls.some(
          (c) => c.method === "POST" && c.path.endsWith("/synthesize-now"),
        ),
      ).toBe(true);
    });

    // 2. Live run -> Arrêter calls /cancel (not /synthesize-now)
    fireEvent.click(
      screen.getByTestId("process-launch-live-investigation-btn"),
    );
    const stopBtn = await waitFor(() =>
      screen.getByTestId("process-stop-execution-btn"),
    );
    fireEvent.click(stopBtn);

    await waitFor(() => {
      const calls = getRecordedVitestApiCalls();
      expect(
        calls.some((c) => c.method === "POST" && c.path.endsWith("/cancel")),
      ).toBe(true);
    });

    // 3. Stage WritePreview -> simulate F5 (unmount + render) -> rehydrates intact -> Approve write
    fireEvent.click(screen.getByTestId("process-request-write-preview-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("trace-write-preview-card")).toBeDefined();
    });

    firstMount.unmount();
    await mountProcessesRoute();

    await waitFor(() => {
      expect(screen.getByTestId("interactive-run-hitl-drawer")).toBeDefined();
      expect(screen.getByTestId("trace-write-preview-card")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("trace-approve-write-btn"));
    await waitFor(() => {
      expect(screen.queryByTestId("trace-write-preview-card")).toBeNull();
      expect(
        screen.getByTestId("artifact-markdown-preview").textContent,
      ).toContain("Publication externe exécutée");
    });
  });

  it("enforces zero forbidden technical jargon across FR and EN Epic 16 dictionaries", () => {
    const inspectStrings = (obj: unknown): string[] => {
      if (typeof obj === "string") return [obj];
      if (typeof obj === "function") {
        try {
          return [
            String(
              (obj as (a: unknown, b: unknown, c: unknown) => unknown)(2, 12, 80),
            ),
          ];
        } catch {
          return [];
        }
      }
      if (obj && typeof obj === "object") {
        return Object.values(obj).flatMap(inspectStrings);
      }
      return [];
    };

    const allEpic16Texts = [
      ...inspectStrings(frDictionary.executionTrace),
      ...inspectStrings(frDictionary.sourceLineInspector),
      ...inspectStrings(frDictionary.processOrchestrationModes),
      ...inspectStrings(enDictionary.executionTrace),
      ...inspectStrings(enDictionary.sourceLineInspector),
      ...inspectStrings(enDictionary.processOrchestrationModes),
    ];

    for (const txt of allEpic16Texts) {
      expect(txt).not.toMatch(FORBIDDEN_JARGON);
    }
  });
});
