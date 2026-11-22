import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as bridgeStore from "../components/agentsAndSkillsBridgeStore";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import { writeSavedAssistantFolders } from "../features/inbox/assistantFoldersAndPrefsStore";
import { backendState } from "./setup/mockBackendState";
import { clearSavedAssistantConversationsStorage } from "../features/inbox/savedConversationsStore";
import {
  AssistantTopToolbar,
  SavedConversationsPanel,
} from "../features/inbox/SavedConversationsAndThreadView";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

const WS_ID = "0195f000-0000-7000-8000-000000000301";
const TEAM_ID = "0192c4e0-0000-7000-8000-000000000103";

function seedAdminSession(withRun = false): void {
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
          id: TEAM_ID,
          name: "Équipe Socle",
          slug: "equipe-socle",
          kind: "TEAM",
          parent_id: "0192c4e0-0000-7000-8000-000000000101",
          billing_enabled: true,
        },
      ],
      workspaces: [
        {
          workspaceId: WS_ID,
          name: "Espace Socle 23.5",
          slug: "espace-socle-23-5",
          ownerOrgUnitId: TEAM_ID,
          ownerOrgUnitName: "Équipe Socle",
          visibilityMode: "STANDARD",
          lifecyclePhase: "BUILD",
          suggestedWorkflows: [],
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
      runs: withRun
        ? [
            {
              runId: "0195f000-0000-7000-8000-000000000777",
              workspaceId: WS_ID,
              workspaceName: "Espace Socle 23.5",
              title: "Revue Architecture 23.5",
              workflowKey: "assistant-agent",
              status: "RUNNING",
              currentStepKey: "frame-architecture-intent",
              createdAtIso: "2026-11-20T01:00:00Z",
            },
          ]
        : [],
    },
    {
      email: "admin235@orcia.test",
      displayName: "Admin 23.5",
      roles: ["PLATFORM_ADMIN"],
    },
  );
  useAuthSessionStore.getState().setAuthSession({
    isAuthenticated: true,
    isHydrating: false,
    email: "admin235@orcia.test",
    displayName: "Admin 23.5",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "PLATFORM_ADMIN",
  });
}

async function mountAppAt(initialPath: string) {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [initialPath] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...view, router };
}

beforeEach(() => {
  resetVitestApiBackend();
  clearPlatformSetupStorage();
  bridgeStore.resetCachedAgentsAndSkillsForTest();
  clearSavedAssistantConversationsStorage();
  writeSavedAssistantFolders([]);
});

afterEach(() => {
  cleanup();
});

describe("Story 23.5 — Cockpit sobriety, ModuleWorkspaceView inbox headerless, toolbar counts, help prefill & citations card wiring", () => {
  it("hides cockpit-human-led-governance-section and removed waiting blocks at 0 runs (<= 3 blocks) and mounts only required anchor card when a real run needs human anchor", async () => {
    seedAdminSession(false);
    const first = await mountAppAt("/cockpit");

    expect(await screen.findByTestId("cockpit-block-accostage")).toBeTruthy();
    expect(screen.getByTestId("cockpit-block-decisions")).toBeTruthy();
    expect(screen.queryByTestId("cockpit-human-led-governance-section")).toBeNull();
    expect(screen.queryByTestId("cockpit-block-governance")).toBeNull();
    expect(screen.queryByTestId("cockpit-zero-decisions-banner")).toBeNull();
    expect(screen.queryByTestId("cockpit-quick-assistant-box")).toBeNull();

    first.unmount();
    cleanup();

    // When a real run requires a mandatory human anchor, only HumanLedAnchorCard mounts (no ArbitrationTieBreakCard)
    seedAdminSession(true);
    await mountAppAt("/cockpit");
    expect(
      await screen.findByTestId("cockpit-human-led-governance-section"),
    ).toBeTruthy();
    expect(screen.getByTestId("cockpit-human-led-anchor-card")).toBeTruthy();
    expect(screen.queryByTestId("cockpit-arbitration-tiebreak-card")).toBeNull();
  });

  it("hides module header card on ModuleWorkspaceView('inbox') and renders it on ('ontology')", async () => {
    seedAdminSession(false);
    const { router } = await mountAppAt("/assistant");
    expect(await screen.findByTestId("module-view-inbox")).toBeTruthy();
    expect(screen.queryByTestId("module-uri-badge-inbox")).toBeNull();

    await router.navigate({ to: "/ontology" });
    expect(await screen.findByTestId("module-view-ontology")).toBeTruthy();
    expect(screen.getByTestId("module-uri-badge-ontology")).toBeTruthy();

    await router.navigate({ to: "/inbox" });
    expect(await screen.findByTestId("module-view-inbox")).toBeTruthy();
    expect(screen.queryByTestId("module-uri-badge-inbox")).toBeNull();
  });

  it("omits '(0)' in SavedConversationsAndThreadView when savedCount=0 and foldersCount=0, and displays counts when > 0", () => {
    const noop = vi.fn();
    const { rerender } = render(
      <>
        <AssistantTopToolbar
          isFr={true}
          savedCount={0}
          foldersCount={0}
          savedConversationsOpen={false}
          foldersPanelOpen={false}
          governanceModalTitle="Gouvernance"
          onNewConversation={noop}
          onToggleSavedConversations={noop}
          onToggleFoldersPanel={noop}
          onToggleGovernanceModal={noop}
          onOpenHelpSection={noop}
        />
        <SavedConversationsPanel
          conversations={[]}
          activeConversationId={null}
          isFr={true}
          onResumeConversation={noop}
          onDeleteConversation={noop}
        />
      </>,
    );

    const savedBtn = screen.getByTestId("assistant-saved-conversations-toggle-btn");
    const foldersBtn = screen.getByTestId("assistant-folders-toggle-btn");
    const panel = screen.getByTestId("assistant-saved-conversations-panel");
    expect(savedBtn.textContent).toContain("Conversations sauvegardées");
    expect(savedBtn.textContent).not.toContain("(0)");
    expect(foldersBtn.textContent).toContain("Dossiers");
    expect(foldersBtn.textContent).not.toContain("(0)");
    expect(panel.textContent).not.toContain("(0)");

    rerender(
      <>
        <AssistantTopToolbar
          isFr={true}
          savedCount={2}
          foldersCount={3}
          savedConversationsOpen={true}
          foldersPanelOpen={false}
          governanceModalTitle="Gouvernance"
          onNewConversation={noop}
          onToggleSavedConversations={noop}
          onToggleFoldersPanel={noop}
          onToggleGovernanceModal={noop}
          onOpenHelpSection={noop}
        />
      </>,
    );

    expect(screen.getByTestId("assistant-saved-conversations-toggle-btn").textContent).toContain(
      "(2)",
    );
    expect(screen.getByTestId("assistant-folders-toggle-btn").textContent).toContain("(3)");
  });

  it("writes writeAssistantPrefillPrompt on contextual help onAskAssistant and navigates to /assistant", async () => {
    seedAdminSession(false);
    const writeSpy = vi.spyOn(bridgeStore, "writeAssistantPrefillPrompt");
    const { router } = await mountAppAt("/cockpit");

    // Ensure contextual help column is visible
    if (!screen.queryByTestId("contextual-help-ask-assistant-btn")) {
      fireEvent.click(screen.getByTestId("topbar-contextual-help-toggle"));
    }
    const askBtn = await screen.findByTestId("contextual-help-ask-assistant-btn");
    fireEvent.click(askBtn);

    expect(writeSpy).toHaveBeenCalledTimes(1);
    const expectedPrefill = writeSpy.mock.calls[0]?.[0] ?? "";
    expect(expectedPrefill.length).toBeGreaterThan(5);

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/assistant");
    });

    const input = (await screen.findByTestId(
      "assistant-three-speed-input",
    )) as HTMLInputElement | HTMLTextAreaElement;
    await waitFor(() => {
      expect(input.value).toBe(expectedPrefill);
    });
    writeSpy.mockRestore();
  });

  it("passes citationCardPreview from inbox/index.tsx to InboxAuxiliaryPanels when a conversation turn exists", async () => {
    seedAdminSession(false);
    const convId = "conv-23-5-citations";
    backendState.assistantThreads = [
      {
        thread_id: convId,
        workspace_id: WS_ID,
        folder_id: null,
        creator_user_id: "0195f000-0000-7000-8000-000000000001",
        last_author_user_id: "0195f000-0000-7000-8000-000000000001",
        title: "Analyse SEPA [S1]",
        thread_summary: "Le rapprochement s'appuie sur le contrat [S1].",
        turn_count: 1,
      },
    ];
    backendState.assistantThreadMessages = [
      {
        message_id: "msg-23-5-u1",
        thread_id: convId,
        workspace_id: WS_ID,
        turn_id: "turn-23-5-1",
        role: "user",
        content: "Explique le rapprochement SEPA.",
        created_at: "2026-11-20T01:00:00Z",
      },
      {
        message_id: "msg-23-5-a1",
        thread_id: convId,
        workspace_id: WS_ID,
        turn_id: "turn-23-5-1",
        role: "assistant",
        content: "Le rapprochement s'appuie sur le contrat [S1].",
        citation_map: {
          sources: [
            {
              tag: "S1",
              index: 1,
              uri: "orcia://kb/sepa-contract.md",
              title: "Contrat SEPA",
              authority_tier: "REFERENCE",
              freshness: "FRESH",
              snippet: "Règle de compensation J+1.",
              line_start: 1,
              line_end: 20,
              restricted_access: false,
              display_pill: "[S1] Contrat SEPA",
            },
          ],
          footer_summary_line: "1 source(s) vérifiée(s) par le serveur",
          sanitized_response_text: "Le rapprochement s'appuie sur le contrat [S1].",
        },
        created_at: "2026-11-20T01:00:10Z",
      },
    ];

    await mountAppAt("/assistant");

    const wrapper = await screen.findByTestId("assistant-citations-card-wrapper");
    expect(wrapper).toBeTruthy();
    expect(wrapper.textContent).toContain("1 source(s) vérifiée(s)");
    expect(wrapper.textContent).toContain("[S1]");
    expect(wrapper.textContent).toContain("Synthèse de réponse");
  });

  it("handles orcia:assistant-prefill event when InboxFeaturePanel is already mounted on /assistant", async () => {
    seedAdminSession(false);
    await mountAppAt("/assistant");

    const input = (await screen.findByTestId(
      "assistant-three-speed-input",
    )) as HTMLInputElement | HTMLTextAreaElement;
    expect(input.value).toBe("");

    bridgeStore.writeAssistantPrefillPrompt("Explique la règle de gouvernance sur cet écran.");

    await waitFor(() => {
      expect(input.value).toBe("Explique la règle de gouvernance sur cet écran.");
    });
  });

  it("renders 'ORCIA > [Équipe] > Module' breadcrumb in topbar and omits redundant global label", async () => {
    seedAdminSession(false);
    const { router } = await mountAppAt("/cockpit");

    const breadcrumb = await screen.findByTestId("topbar-breadcrumb");
    expect(breadcrumb.textContent).toContain("ORCIA");
    expect(breadcrumb.textContent).toContain("Cockpit");
    expect(breadcrumb.textContent).not.toContain("Plateforme Globale ORCIA");

    // Select the workspace scope in sidebar to surface the active team in the breadcrumb
    const wsSelect = (await screen.findByTestId("sidebar-workspace-selector")) as HTMLSelectElement;
    fireEvent.change(wsSelect, { target: { value: WS_ID } });

    await waitFor(() => {
      expect(screen.getByTestId("topbar-breadcrumb").textContent).toContain("Équipe Socle");
      expect(screen.getByTestId("topbar-breadcrumb").textContent).toContain("Cockpit");
    });

    await router.navigate({ to: "/spaces" });
    await waitFor(() => {
      const updated = screen.getByTestId("topbar-breadcrumb").textContent ?? "";
      expect(updated).toContain("ORCIA");
      expect(updated).toContain("Équipe Socle");
      expect(updated).toContain("Mes Espaces");
    });
  });
});
