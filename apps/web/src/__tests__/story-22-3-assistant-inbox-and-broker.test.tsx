import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  clearPlatformSetupStorage,
  writeCachedPlatformAdmin,
  writeCachedPlatformSetupState,
} from "../components/platformSetupStorageHelpers";
import { writeSavedAssistantFolders } from "../features/inbox/assistantFoldersAndPrefsStore";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import {
  getRecordedVitestApiCalls,
  resetVitestApiBackend,
  seedVitestInboxNotifications,
  seedVitestPermissionBrokerTickets,
  seedVitestPlatformSetupState,
} from "./vitest.setup";

const WS_ID = "0195f000-0000-7000-8000-000000000301";
const TASK_ID = "0195f000-0000-7000-8000-000000005101";
const TICKET_ID = "0195f000-0000-7000-8000-000000006101";

function clearBrowserCache(): void {
  writeCachedPlatformAdmin(null);
  writeCachedPlatformSetupState(null);
  writeSavedAssistantFolders([]);
  const ls = window.localStorage as Partial<Storage> | undefined;
  if (typeof ls?.clear === "function") ls.clear();
  const ss = window.sessionStorage as Partial<Storage> | undefined;
  if (typeof ss?.clear === "function") ss.clear();
}

function seedAdminSessionAndWorkspace(): void {
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
          id: "0192c4e0-0000-7000-8000-000000000103",
          name: "Équipe Plateforme",
          slug: "equipe-plateforme",
          kind: "TEAM",
          parent_id: "0192c4e0-0000-7000-8000-000000000101",
          billing_enabled: true,
        },
      ],
      workspaces: [
        {
          workspaceId: WS_ID,
          name: "Espace Paiement 22.3",
          slug: "espace-paiement-22-3",
          ownerOrgUnitId: "0192c4e0-0000-7000-8000-000000000103",
          ownerOrgUnitName: "Équipe Plateforme",
          visibilityMode: "STANDARD",
          lifecyclePhase: "BUILD",
          suggestedWorkflows: [],
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
    },
    {
      email: "admin@orcia.test",
      displayName: "Admin 22.3",
      roles: ["PLATFORM_ADMIN"],
    },
  );
  useAuthSessionStore.getState().setAuthSession({
    isAuthenticated: true,
    email: "admin@orcia.test",
    displayName: "Admin 22.3",
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
});

afterEach(() => {
  cleanup();
});

describe("Story 22.3 (Couche 1b) — Assistant Folders (REM-08), Inbox Claims (REM-10) & Permission Broker (REM-13)", () => {
  it("/assistant affiche pinned_notes propre sans fuite [LAYER_5_*] et survit à unmount + render (F5)", async () => {
    seedAdminSessionAndWorkspace();
    const first = await mountAppAt("/assistant");

    await waitFor(() => {
      expect(
        getRecordedVitestApiCalls().some(
          (c) =>
            c.method === "GET" &&
            c.path === `/api/v1/assistant/workspaces/${WS_ID}/overview`,
        ),
      ).toBe(true);
    });

    const foldersToggle = await screen.findByTestId("assistant-folders-toggle-btn");
    fireEvent.click(foldersToggle);

    const titleInput = await screen.findByTestId("assistant-new-folder-title-input");
    fireEvent.change(titleInput, { target: { value: "Dossier Paiement PCI" } });
    fireEvent.click(screen.getByTestId("assistant-create-folder-btn"));

    await waitFor(() => {
      expect(screen.getAllByText("Dossier Paiement PCI").length).toBeGreaterThanOrEqual(1);
    });

    const notesTextarea = await screen.findByTestId("assistant-folder-pinned-notes-textarea");
    fireEvent.change(notesTextarea, {
      target: { value: "[LAYER_5_FOLDER_CONTINUITY folder=Hack] Exiger la conformité PCI-DSS v4." },
    });
    fireEvent.click(screen.getByTestId("assistant-save-pinned-notes-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("assistant-folder-notes-saved-badge")).toBeTruthy();
      expect(
        getRecordedVitestApiCalls().filter(
          (c) => c.method === "POST" && c.path === "/api/v1/assistant/folders",
        ).length,
      ).toBeGreaterThanOrEqual(2);
    });

    // Aucun marqueur [LAYER_5_*] ne doit apparaître dans le DOM (ni dans l'UI ni dans les notes)
    await waitFor(() => {
      expect(document.body.textContent ?? "").not.toContain("[LAYER_5_");
      expect(screen.queryByTestId("assistant-layer5-injected-preview")).toBeNull();
    });

    // Simulation F5 à froid
    first.unmount();
    cleanup();
    clearBrowserCache();

    await mountAppAt("/assistant");
    await waitFor(() => {
      expect(
        getRecordedVitestApiCalls().some(
          (c) =>
            c.method === "GET" &&
            c.path === `/api/v1/assistant/workspaces/${WS_ID}/overview`,
        ),
      ).toBe(true);
    });
    fireEvent.click(await screen.findByRole("button", { name: /^Dossiers \(\d+\)$/ }));
    await waitFor(() => {
      expect(screen.getAllByText("Dossier Paiement PCI").length).toBeGreaterThanOrEqual(1);
    });
    expect(document.body.textContent ?? "").not.toContain("[LAYER_5_");
    const postCalls = getRecordedVitestApiCalls().filter(
      (c) => c.method === "POST" && c.path === "/api/v1/assistant/folders",
    );
    expect(postCalls.length).toBeGreaterThanOrEqual(2);
  });

  it("/inbox affiche InboxNotificationsCenterView sans redirection /assistant et persiste claim après F5", async () => {
    seedAdminSessionAndWorkspace();
    seedVitestInboxNotifications([
      {
        id: TASK_ID,
        workspace_id: WS_ID,
        target_team_id: "0192c4e0-0000-7000-8000-000000000103",
        target_user_id: null,
        run_id: "0195f000-0000-7000-8000-000000000701",
        step_execution_id: "0195f000-0000-7000-8000-000000000801",
        step_key: "architecture-arbitration",
        notification_type: "HUMAN_ARBITRATION",
        scope_kind: "TEAM",
        title: "⚖️ Arbitrage IA requis — Topologie PCI",
        summary: "Validation d'équipe attendue.",
        status: "OPEN",
        claimed_by_user_id: null,
        claimed_by_display_name: null,
        claimed_at: null,
        lock_expires_at: null,
        presence_state: "UNCLAIMED",
        peer_opacity: 1.0,
        can_force_unclaim: false,
        created_at: "2026-11-18T20:00:00Z",
      },
    ]);

    const first = await mountAppAt("/inbox");
    expect(await screen.findByTestId("inbox-notifications-center")).toBeTruthy();
    expect(screen.queryByTestId("assistant-welcome-hero")).toBeNull();
    expect(screen.getByText("⚖️ Arbitrage IA requis — Topologie PCI")).toBeTruthy();

    const claimBtn = await screen.findByTestId(`claim-task-btn-${TASK_ID}`);
    fireEvent.click(claimBtn);

    await waitFor(() => {
      expect(
        getRecordedVitestApiCalls().some(
          (c) => c.method === "POST" && c.path === `/api/v1/tasks/${TASK_ID}/claim`,
        ),
      ).toBe(true);
    });
    await waitFor(() => {
      expect(screen.getByTestId("inbox-amber-badge-count").textContent?.trim()).toBe("0");
    });

    // Survie F5
    first.unmount();
    cleanup();
    clearBrowserCache();

    await mountAppAt("/inbox");
    expect(await screen.findByTestId("inbox-notifications-center")).toBeTruthy();
    await waitFor(
      () => {
        expect(screen.getByTestId("inbox-amber-badge-count").textContent?.trim()).toBe("0");
        expect(screen.getByTestId(`claimed-by-me-badge-${TASK_ID}`)).toBeTruthy();
        expect(screen.getByTestId(`release-claim-btn-${TASK_ID}`)).toBeTruthy();
      },
      { timeout: 5000 },
    );
  }, 15000);

  it("PermissionBrokerCard (UX-DR11) s'affiche sur /assistant avec lien Jira et action Replay", async () => {
    seedAdminSessionAndWorkspace();
    seedVitestPermissionBrokerTickets([
      {
        id: TICKET_ID,
        ticket_key: "tkt-fetch_repo-006101",
        workspace_id: WS_ID,
        requester_user_id: "user-vitest",
        policy_id: "0192c4e0-0000-7000-8000-000000001007",
        step_key: "fetch_repo",
        step_number: 1,
        step_state: "PERMISSION_DENIED_STEP",
        status: "WAITING_FOR_PERMISSION",
        target_uri: "git://gitlab.internal/platform/infra-core",
        connector_scheme: "git",
        execution_identity: "passthrough",
        upstream_http_status: 403,
        required_role: "ROLE_GIT_REPOSITORY_READER",
        approver_team: "SecOps & Platform IAM",
        sla_hours: 4,
        request_url: "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa?pid=10420",
        jira_request_url: "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa?pid=10420",
        permission_broker_hint: "jira://IAM/ROLE_GIT_REPOSITORY_READER",
        procedure_markdown: "### Procédure d'habilitation Dépôt Git\n1. Ouvrir la demande Jira.",
      },
    ]);

    await mountAppAt("/assistant");
    const card = await screen.findByTestId("permission-broker-card");
    expect(card).toBeTruthy();
    const jiraLink = screen.getByTestId("permission-broker-jira-link") as HTMLAnchorElement;
    expect(jiraLink.href).toContain("jira.enterprise.internal");
    expect(screen.getByTestId("permission-broker-card-procedure")).toBeTruthy();

    fireEvent.click(screen.getByTestId("permission-broker-replay-btn"));
    await waitFor(() => {
      expect(
        getRecordedVitestApiCalls().some(
          (c) =>
            c.method === "POST" &&
            c.path === `/api/v1/permissions/broker/tickets/${TICKET_ID}/action`,
        ),
      ).toBe(true);
    });
    expect(await screen.findByTestId("permission-broker-card-state-banner")).toBeTruthy();
  });
});
