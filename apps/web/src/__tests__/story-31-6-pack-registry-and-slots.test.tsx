// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

const WS_ID = "0195f000-0000-7000-8000-000000000311";

function seedAdminWithWorkspace() {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: "0192c4e0-0000-7000-8000-000000000101",
          name: "Direction Technique",
          slug: "dir-tech",
          level: "BU",
          parentId: null,
          billingEnabled: true,
        },
      ],
      workspaces: [
        {
          workspaceId: WS_ID,
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
      datasources: [
        {
          id: "0195f000-0000-7000-8000-000000009001",
          workspaceName: "Espace Équipe Alpha",
          alias: "depot-core",
          scheme: "git",
          uri: "git://internal/core.git",
          executionIdentity: "SERVICE_PRINCIPAL",
          freshnessTtlDays: 7,
          tripartiteStatus: "ALIGNED",
        },
      ],
    },
    { email: "admin@orcia.test", displayName: "Admin Test", roles: ["PLATFORM_ADMIN"] },
  );
  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "mock-token-316", // pragma: allowlist secret
    email: "admin@orcia.test",
    displayName: "Admin Test",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "PLATFORM_ADMIN",
    readOnlyObserver: false,
  });
}

async function mountRoute(initialPath: string, locale: "fr" | "en" = "fr") {
  const qc = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [initialPath] });
  const router = createOrciaRouter({ queryClient: qc, history });
  await router.load();
  const rendered = render(
    <I18nProvider initialLocale={locale}>
      <QueryClientProvider client={qc}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </I18nProvider>,
  );
  return { ...rendered, router };
}

describe("Story 31.6 — Unified Pack Registry, Import, Slot Drawer & Workspace Activation", () => {
  beforeEach(() => {
    resetVitestApiBackend();
    seedAdminWithWorkspace();
  });

  afterEach(() => {
    cleanup();
  });

  it("handles executable hook 422 alert on import, imports valid zip, uninstalls custom bundle, and enforces observer disabled state", async () => {
    await mountRoute("/settings/packs", "en");

    await waitFor(() => {
      expect(screen.getByTestId("declarative-pack-card-sdlc")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("open-pack-import-modal-btn"));
    expect(screen.getByTestId("pack-import-modal")).toBeDefined();

    const fileInput = screen.getByTestId("pack-import-file-input") as HTMLInputElement;
    const badFile = new File(["#!/bin/sh"], "bad-hook.sh", { type: "text/plain" });
    fireEvent.change(fileInput, { target: { files: [badFile] } });
    fireEvent.click(screen.getByTestId("pack-import-submit-btn"));

    await waitFor(() => {
      const alert = screen.getByTestId("pack-import-error-alert");
      expect(alert.getAttribute("role")).toBe("alert");
      expect(alert.textContent).toContain("ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN");
    });

    const validZip = new File(["PK\x05\x06"], "billing-pack.zip", { type: "application/zip" });
    fireEvent.change(fileInput, { target: { files: [validZip] } });
    fireEvent.click(screen.getByTestId("pack-import-submit-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("declarative-pack-card-billing-pack")).toBeDefined();
    });

    // Observer mode disables import, compose, and uninstall mutations
    useAuthSessionStore.setState({ readOnlyObserver: true, roles: ["OBSERVER"] });
    await waitFor(() => {
      expect((screen.getByTestId("open-pack-import-modal-btn") as HTMLButtonElement).disabled).toBe(true);
      expect((screen.getByTestId("uninstall-pack-billing-pack-btn") as HTMLButtonElement).disabled).toBe(true);
    });

    // Restore admin and uninstall custom bundle
    useAuthSessionStore.setState({ readOnlyObserver: false, roles: ["PLATFORM_ADMIN"] });
    await waitFor(() => {
      expect((screen.getByTestId("uninstall-pack-billing-pack-btn") as HTMLButtonElement).disabled).toBe(false);
    });
    fireEvent.click(screen.getByTestId("uninstall-pack-billing-pack-btn"));
    await waitFor(() => {
      expect(screen.queryByTestId("declarative-pack-card-billing-pack")).toBeNull();
    });
  });

  it("blocks unbound activation with 422 drawer alert, binds slot, activates & reorders workspace packs, and survives F5", async () => {
    const first = await mountRoute("/settings?tab=packs", "fr");

    await waitFor(() => {
      expect(screen.getByTestId("workspace-pack-row-sdlc")).toBeDefined();
    });

    // Attempt activation of sdlc with unbound required git_repo slot -> 422 opens slot drawer with [role="alert"]
    fireEvent.click(screen.getByTestId("workspace-pack-toggle-sdlc"));
    await waitFor(() => {
      const drawerAlert = screen.getByTestId("pack-slot-drawer-error-alert");
      expect(drawerAlert.getAttribute("role")).toBe("alert");
      expect(drawerAlert.textContent).toContain("ERR_PACK_SLOT_UNBOUND");
      expect(screen.getByTestId("pack-slot-row-git_repo").getAttribute("data-slot-missing")).toBe("true");
    });

    // Bind git_repo slot to workspace datasource & save
    fireEvent.change(screen.getByTestId("pack-slot-select-git_repo"), {
      target: { value: "WORKSPACE_DATASOURCE::0195f000-0000-7000-8000-000000009001" },
    });
    fireEvent.click(screen.getByTestId("save-pack-slot-bindings-btn"));

    await waitFor(() => {
      expect(screen.queryByTestId("pack-slot-binding-drawer")).toBeNull();
    });

    // Activate sdlc now that git_repo is bound
    fireEvent.click(screen.getByTestId("workspace-pack-toggle-sdlc"));
    await waitFor(() => {
      expect(screen.getByTestId("workspace-pack-move-up-sdlc")).toBeDefined();
    });

    // Move sdlc priority up above orcia-docs
    fireEvent.click(screen.getByTestId("workspace-pack-move-up-sdlc"));
    await waitFor(() => {
      expect(screen.getByTestId("workspace-pack-row-sdlc").textContent).toContain("Priorité #1");
    });

    // Simulate full F5 reload
    first.unmount();
    await mountRoute("/settings?tab=packs", "fr");
    await waitFor(() => {
      expect(screen.getByTestId("workspace-pack-row-sdlc").textContent).toContain("Priorité #1");
    });
  });
});
