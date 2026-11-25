// @vitest-environment jsdom
import type { ControlCenterWorkspaceGovItem } from "@orcia/ui";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EMPTY_CACHED_PLATFORM_SETUP_STATE } from "../components/platformSetupContextTypes";
import {
  clearPlatformSetupStorage,
  type CachedPlatformSetupState,
} from "../components/platformSetupStorageHelpers";
import { createPlatformWorkspaceActions } from "../components/platformSetupWorkspaceActions";
import {
  createWorkspaceViaServer,
  patchWorkspaceViaServer,
} from "../components/platformSetupWorkspaces";
import { persistSetupSnapshotStrict } from "../components/usePlatformSetupHydrationEffect";
import { clearSavedActiveScopeId } from "../components/useShellContainerState";
import { WorkspaceMembersInstructionsCard } from "../features/workspaces/WorkspaceMembersInstructionsCard";
import { WorkspaceSourcesRagTab } from "../features/workspaces/WorkspaceSourcesRagTab";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import {
  getRecordedVitestApiCalls,
  resetVitestApiBackend,
  seedVitestPlatformSetupState,
} from "./vitest.setup";

const TEAM_ID = "0195f292-0000-7000-8000-000000000021";
const WS_ID = "0195f292-0000-7000-8000-000000000201";
const WS_ITEM: ControlCenterWorkspaceGovItem = {
  workspaceId: WS_ID,
  slug: "platform-ws",
  name: "Platform Workspace",
  visibilityMode: "STANDARD",
  lifecyclePhase: "BUILD",
  suggestedWorkflows: [],
  accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
  finopsCostUsd: 0,
};

function seedAdminWorkspace() {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: TEAM_ID,
          name: "Platform Team",
          slug: "platform-team",
          kind: "TEAM",
          level: "TEAM",
          parentId: null,
          billingEnabled: true,
        },
      ],
      workspaces: [WS_ITEM],
    },
    { email: "admin@orcia.fr", displayName: "Admin", roles: ["PLATFORM_ADMIN"] },
  );
  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "test-jwt-token",
    displayName: "Admin",
    email: "admin@orcia.fr",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "PLATFORM_ADMIN",
  });
}

async function mountWorkspaces(locale: "fr" | "en") {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: ["/workspaces"] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  return render(
    <I18nProvider initialLocale={locale}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </I18nProvider>,
  );
}

function mockWorkspaceSubTab403Fetch(originalFetch: typeof fetch): typeof fetch {
  return (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    if (url.includes(`/api/v1/workspaces/${WS_ID}/datasources`) || url.includes("/api/v1/assistant/governance")) {
      return new Response(
        JSON.stringify({
          type: "https://orcia.io/problems/err-forbidden",
          title: "Forbidden",
          status: 403,
          detail: "Access denied",
          error_code: "ERR_SCOPE_ACCESS_DENIED",
        }),
        { status: 403, headers: { "Content-Type": "application/problem+json" } },
      );
    }
    return originalFetch(input, init);
  }) as typeof fetch;
}

beforeEach(() => {
  resetVitestApiBackend();
  clearPlatformSetupStorage();
  clearSavedActiveScopeId();
});

afterEach(() => {
  cleanup();
});

describe("Story 29.2 — Single Alert Banner in Sub-Tabs, EN Locale Propagation & Consecutive Updates", () => {
  it("renders zero duplicate role=alert in WorkspaceSourcesRagTab & WorkspaceMembersInstructionsCard when onFeedback is provided", async () => {
    seedAdminWorkspace();
    const originalFetch = globalThis.fetch;
    globalThis.fetch = mockWorkspaceSubTab403Fetch(originalFetch);

    try {
      const onFeedbackSources = vi.fn();
      const onFeedbackMembers = vi.fn();
      const view = render(
        <I18nProvider initialLocale="en">
          <WorkspaceSourcesRagTab activeWorkspace={WS_ITEM} onFeedback={onFeedbackSources} />
          <WorkspaceMembersInstructionsCard isFr={false} activeWorkspace={WS_ITEM} onFeedback={onFeedbackMembers} />
        </I18nProvider>,
      );

      await waitFor(() => {
        expect(onFeedbackSources).toHaveBeenCalledWith(expect.objectContaining({ tone: "crimson" }));
        expect(onFeedbackMembers).toHaveBeenCalledWith(expect.objectContaining({ tone: "crimson" }));
      });
      expect(screen.queryByTestId("sources-error-alert")).toBeNull();
      expect(screen.queryByTestId("workspace-instructions-error-alert")).toBeNull();
      expect(screen.queryAllByRole("alert")).toHaveLength(0);
      view.unmount();
      cleanup();

      // Standalone render without onFeedback still surfaces fallback alerts
      const standaloneView = render(
        <I18nProvider initialLocale="en">
          <WorkspaceSourcesRagTab activeWorkspace={WS_ITEM} />
          <WorkspaceMembersInstructionsCard isFr={false} activeWorkspace={WS_ITEM} />
        </I18nProvider>,
      );
      expect(await screen.findByTestId("sources-error-alert")).toBeDefined();
      expect(await screen.findByTestId("workspace-instructions-error-alert")).toBeDefined();
      standaloneView.unmount();
      cleanup();

      // Live WorkspacesFeaturePanel renders strictly 1 [role="alert"] for Tab 5 governance failure
      const fullView = await mountWorkspaces("en");
      fireEvent.click(await screen.findByTestId("workspace-tab-MEMBERS_TEAM"));
      const banner = await screen.findByTestId("workspaces-action-feedback-banner");
      expect(banner.getAttribute("role")).toBe("alert");
      expect(screen.queryByTestId("workspace-instructions-error-alert")).toBeNull();
      expect(screen.getAllByRole("alert")).toHaveLength(1);
      fullView.unmount();
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("propagates Accept-Language: en and English audit/sync strings in createWorkspaceViaServer, patchWorkspaceViaServer, and persistSetupSnapshotStrict", async () => {
    seedAdminWorkspace();
    const created = await createWorkspaceViaServer({
      locale: "en",
      input: {
        name: "Alpha EN",
        slug: "alpha-en",
        visibilityMode: "STANDARD",
        lifecyclePhase: "BUILD",
        ownerOrgUnitId: TEAM_ID,
      },
      orgUnits: [
        {
          id: TEAM_ID,
          name: "Platform Team",
          slug: "platform-team",
          level: "TEAM",
          parentId: "scope-global",
          billingEnabled: true,
        },
      ],
      workflows: [],
      platformAdmin: null,
    });
    expect(created.auditEvent.summary).toContain('Workspace "Alpha EN"');
    expect(created.auditEvent.summary).toContain("Team collective");
    expect(created.auditEvent.scopeLabel).toBe("Workspace · Alpha EN");

    await patchWorkspaceViaServer({ locale: "en", workspaceId: WS_ID, payload: { lifecycle_phase: "RUN" } });

    const calls = getRecordedVitestApiCalls();
    const postCall = calls.find((c) => c.method === "POST" && c.path === "/api/v1/workspaces");
    const patchCall = calls.find((c) => c.method === "PATCH" && c.path === `/api/v1/workspaces/${WS_ID}`);
    expect(postCall?.headers?.["accept-language"]).toBe("en");
    expect(patchCall?.headers?.["accept-language"]).toBe("en");

    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async () =>
      new Response(
        JSON.stringify({
          type: "https://orcia.io/problems/err-forbidden",
          title: "Forbidden",
          status: 403,
          detail: "Sync forbidden",
          error_code: "ERR_SCOPE_ACCESS_DENIED",
        }),
        { status: 403, headers: { "Content-Type": "application/problem+json" } },
      )) as typeof fetch;

    try {
      let syncErr: string | null = null;
      await expect(
        persistSetupSnapshotStrict({
          locale: "en",
          next: EMPTY_CACHED_PLATFORM_SETUP_STATE,
          hasMutatedSinceMountRef: { current: false },
          mutatedSlicesRef: { current: new Set() },
          latestSnapshotRef: { current: EMPTY_CACHED_PLATFORM_SETUP_STATE },
          setLastSyncError: (v) => {
            syncErr = v;
          },
        }),
      ).rejects.toThrow();
      expect(syncErr).toContain("Platform synchronization");
      expect(syncErr).not.toContain("Synchronisation plateforme");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("preserves both phase and visibility across rapid concurrent workspace updates via getLatestSnapshot", async () => {
    seedAdminWorkspace();
    let snapshot: CachedPlatformSetupState = {
      ...EMPTY_CACHED_PLATFORM_SETUP_STATE,
      workspaces: [WS_ITEM],
    };
    const latestRef = { current: snapshot };
    const actions = createPlatformWorkspaceActions({
      locale: "en",
      platformAdmin: null,
      orgUnits: [],
      workflows: [],
      workspaces: snapshot.workspaces,
      datasources: [],
      getLatestSnapshot: () => latestRef.current,
      setWorkspaces: (next) => {
        latestRef.current = { ...latestRef.current, workspaces: next };
        snapshot = latestRef.current;
      },
      setDatasources: () => {},
      setAuditEvents: (next) => {
        latestRef.current = { ...latestRef.current, auditEvents: next };
        snapshot = latestRef.current;
      },
      markMutated: () => {},
      appendAudit: (eventType, summary, meta) => [
        {
          id: `evt-${latestRef.current.auditEvents.length + 1}`,
          timestampIso: new Date().toISOString(),
          eventType,
          summary,
          actorName: "Admin",
          scopePath: meta?.scopePath ?? "GLOBAL",
          scopeLabel: meta?.scopeLabel ?? "GLOBAL",
        },
        ...latestRef.current.auditEvents,
      ],
      buildSnapshot: (overrides) => ({ ...latestRef.current, ...overrides }),
      persistLocalSnapshot: () => {},
      persistSnapshotStrict: async () => {},
    });

    await Promise.all([
      actions.updateWorkspacePhase(WS_ID, "RUN"),
      actions.updateWorkspaceVisibility(WS_ID, "CONFIDENTIAL_RESTRICTED"),
    ]);

    const updated = snapshot.workspaces.find((w) => w.workspaceId === WS_ID);
    expect(updated?.lifecyclePhase).toBe("RUN");
    expect(updated?.visibilityMode).toBe("CONFIDENTIAL_RESTRICTED");
  });
});
