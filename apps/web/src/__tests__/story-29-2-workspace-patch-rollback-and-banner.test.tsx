// @vitest-environment jsdom
import { createOrciaApiClient } from "@orcia/api-client";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  clearPlatformSetupStorage,
  PLATFORM_SETUP_STATE_STORAGE_KEY,
  readStorageItem,
  writeCachedPlatformAdmin,
  writeCachedPlatformSetupState,
} from "../components/platformSetupStorageHelpers";
import { clearSavedActiveScopeId } from "../components/useShellContainerState";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import {
  getRecordedVitestApiCalls,
  resetVitestApiBackend,
  seedVitestPlatformSetupState,
} from "./vitest.setup";

const WS_PERSONAL_ID = "0195f292-0000-7000-8000-000000000101";
const WS_TEAM_ID = "0195f292-0000-7000-8000-000000000102";
const TEAM_ID = "0195f292-0000-7000-8000-000000000011";

function seedTeamLeadWorkspaces() {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: TEAM_ID,
          name: "Équipe Rouge Gorge",
          slug: "equipe-rouge-gorge",
          kind: "TEAM",
          level: "TEAM",
          parentId: null,
          billingEnabled: true,
          lead_user_id: "marc.lead@orcia.fr",
          lead_user_ids: ["marc.lead@orcia.fr"],
          member_user_ids: [],
        },
      ],
      workspaces: [
        {
          workspaceId: WS_PERSONAL_ID,
          slug: "personal-marc-01",
          name: "Espace personnel — Rouge Gorge",
          ownerUserId: "marc.lead@orcia.fr",
          ownerOrgUnitId: TEAM_ID,
          ownerOrgUnitName: "Équipe Rouge Gorge",
          visibilityMode: "PRIVATE_USER",
          lifecyclePhase: "BUILD",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
        {
          workspaceId: WS_TEAM_ID,
          slug: "rouge-gorge-team",
          name: "Projet Rouge Gorge",
          ownerOrgUnitId: TEAM_ID,
          ownerOrgUnitName: "Équipe Rouge Gorge",
          visibilityMode: "STANDARD",
          lifecyclePhase: "BUILD",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
    },
    { email: "marc.lead@orcia.fr", displayName: "Marc Lead", roles: ["TEAM_LEAD"] },
  );
  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "test-jwt-token",
    displayName: "Marc Lead",
    email: "marc.lead@orcia.fr",
    roles: ["TEAM_LEAD"],
    activeHat: "TEAM_LEAD",
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

beforeEach(() => {
  resetVitestApiBackend();
  clearPlatformSetupStorage();
  clearSavedActiveScopeId();
});

afterEach(() => {
  cleanup();
});

describe("Story 29.2 — Scoped PATCH /api/v1/workspaces/{id}, Rollback & Single Banner", () => {
  it("routes team workspace visibility updates via PATCH /api/v1/workspaces/{id} (never PUT platform-setup-state)", async () => {
    seedTeamLeadWorkspaces();
    const view = await mountWorkspaces("fr");

    const switcher = (await screen.findByTestId(
      "workspaces-active-switcher-select",
    )) as HTMLSelectElement;
    fireEvent.change(switcher, { target: { value: WS_TEAM_ID } });
    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Projet Rouge Gorge");
    });

    fireEvent.change(screen.getByTestId(`workspace-card-visibility-select-${WS_TEAM_ID}`), {
      target: { value: "CONFIDENTIAL_RESTRICTED" },
    });

    await waitFor(() => {
      expect(screen.getByTestId(`workspace-visibility-badge-${WS_TEAM_ID}`).textContent).toContain(
        "Confidentiel",
      );
    });

    const calls = getRecordedVitestApiCalls();
    expect(
      calls.some((c) => c.method === "PATCH" && c.path === `/api/v1/workspaces/${WS_TEAM_ID}`),
    ).toBe(true);
    expect(
      calls.some((c) => c.method === "PUT" && c.path === "/api/v1/bootstrap/platform-setup-state"),
    ).toBe(false);
    expect(screen.queryByTestId("platform-sync-error-banner")).toBeNull();

    view.unmount();
  });

  it("rolls back React state & never writes localStorage on 403, rendering strictly 1 banner without ⚠️", async () => {
    seedTeamLeadWorkspaces();
    const view = await mountWorkspaces("fr");

    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe(
        "Espace personnel — Rouge Gorge",
      );
    });

    const cachedBefore = readStorageItem(PLATFORM_SETUP_STATE_STORAGE_KEY);
    // Attempt in-place conversion of PRIVATE_USER -> STANDARD -> backend returns 403
    fireEvent.change(screen.getByTestId(`workspace-card-visibility-select-${WS_PERSONAL_ID}`), {
      target: { value: "STANDARD" },
    });

    const alertBanner = await screen.findByTestId("workspaces-action-feedback-banner");
    expect(alertBanner.getAttribute("role")).toBe("alert");
    // Zero ⚠️ emoji colliding with OrciaIcon cross, strictly 1 error banner (no platform-sync-error-banner)
    expect(alertBanner.textContent).not.toContain("⚠️");
    expect(screen.queryByTestId("platform-sync-error-banner")).toBeNull();
    expect(screen.getAllByRole("alert")).toHaveLength(1);

    // State must NOT mutate into Team visibility, and localStorage must not change
    expect(screen.getByTestId(`workspace-visibility-badge-${WS_PERSONAL_ID}`).textContent).toContain(
      "Personnel",
    );
    expect(
      (screen.getByTestId(`workspace-card-visibility-select-${WS_PERSONAL_ID}`) as HTMLSelectElement)
        .value,
    ).toBe("PRIVATE_USER");
    expect(readStorageItem(PLATFORM_SETUP_STATE_STORAGE_KEY)).toBe(cachedBefore);

    view.unmount();
  });

  it("renders localized EN error banner without ⚠️ when PATCH fails in English locale", async () => {
    seedTeamLeadWorkspaces();
    await createOrciaApiClient({ baseUrl: "" }).updateUserPreferences({ locale: "en" });
    const view = await mountWorkspaces("en");

    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe(
        "Espace personnel — Rouge Gorge",
      );
    });

    fireEvent.click(await screen.findByTestId(`share-private-workspace-btn-${WS_PERSONAL_ID}`));
    const alertBanner = await screen.findByTestId("workspaces-action-feedback-banner");
    expect(alertBanner.getAttribute("role")).toBe("alert");
    expect(alertBanner.textContent).toContain("Personal workspace visibility locked");
    expect(alertBanner.textContent).toContain("Workspace sharing");
    expect(alertBanner.textContent).not.toContain("⚠️");
    expect(screen.queryByTestId("platform-sync-error-banner")).toBeNull();

    view.unmount();
  });

  it("persists POST create + PATCH visibility/phase across cold storage clear and remount (F5)", async () => {
    seedVitestPlatformSetupState(
      { org_units: [] },
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

    const firstView = await mountWorkspaces("fr");
    fireEvent.click(await screen.findByTestId("toggle-create-workspace-form-btn"));
    fireEvent.change(await screen.findByTestId("workspace-name-input"), {
      target: { value: "Espace Persistant" },
    });
    fireEvent.change(screen.getByTestId("workspace-slug-input"), {
      target: { value: "espace-persistant" },
    });
    fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Espace Persistant");
    });

    const switcher = screen.getByTestId("workspaces-active-switcher-select") as HTMLSelectElement;
    const wsId = switcher.value;
    fireEvent.change(screen.getByTestId(`workspace-card-visibility-select-${wsId}`), {
      target: { value: "CONFIDENTIAL_RESTRICTED" },
    });
    await waitFor(() => {
      expect(screen.getByTestId(`workspace-visibility-badge-${wsId}`).textContent).toContain(
        "Confidentiel",
      );
    });
    fireEvent.change(screen.getByTestId(`workspace-card-phase-select-${wsId}`), {
      target: { value: "RUN" },
    });
    await waitFor(() => {
      expect(
        (screen.getByTestId(`workspace-card-phase-select-${wsId}`) as HTMLSelectElement).value,
      ).toBe("RUN");
    });

    await waitFor(() => {
      expect(screen.queryByTestId("create-workspace-form")).toBeNull();
    });
    firstView.unmount();
    // Clear only browser storage (do not wipe Vitest mock backend state) to simulate cold F5 reload.
    writeCachedPlatformSetupState(null);
    writeCachedPlatformAdmin(null);

    const remountView = await mountWorkspaces("fr");
    await waitFor(() => {
      expect(screen.getByTestId(`workspace-visibility-badge-${wsId}`).textContent).toContain(
        "Confidentiel",
      );
      expect(
        (screen.getByTestId(`workspace-card-phase-select-${wsId}`) as HTMLSelectElement).value,
      ).toBe("RUN");
    });

    remountView.unmount();
  });
});
