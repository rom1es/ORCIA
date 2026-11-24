// @vitest-environment jsdom
import { createOrciaApiClient } from "@orcia/api-client";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import {
  clearSavedActiveScopeId,
  ORCIA_ACTIVE_SCOPE_STORAGE_KEY,
} from "../components/useShellContainerState";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

function ensureWorkingLocalStorage(): void {
  if (typeof window !== "undefined" && typeof window.localStorage?.getItem === "function") {
    return;
  }
  const backing = new Map<string, string>();
  const memoryStorage: Storage = {
    get length() {
      return backing.size;
    },
    clear() {
      backing.clear();
    },
    getItem(key: string) {
      return backing.get(key) ?? null;
    },
    key(index: number) {
      return Array.from(backing.keys())[index] ?? null;
    },
    removeItem(key: string) {
      backing.delete(key);
    },
    setItem(key: string, value: string) {
      backing.set(key, String(value));
    },
  };
  Object.defineProperty(window, "localStorage", { value: memoryStorage, configurable: true });
  Object.defineProperty(globalThis, "localStorage", { value: memoryStorage, configurable: true });
}

const PERSONAL_WS_ID = "0195f000-0000-7000-8000-000000000111";
const PERSONAL_WS_SLUG = `personal-${PERSONAL_WS_ID}`;
const TEAM_WS_ID = "0195f000-0000-7000-8000-000000000222";

function seedWorkspacesState() {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: "0195f000-0000-7000-8000-000000000010",
          name: "Équipe Produit",
          slug: "equipe-produit",
          level: "TEAM",
          parentId: null,
          billingEnabled: true,
        },
      ],
      workspaces: [
        {
          workspaceId: PERSONAL_WS_ID,
          slug: PERSONAL_WS_SLUG,
          name: "Mon Espace Personnel",
          ownerUserId: "alice@orcia.fr",
          ownerOrgUnitId: "0195f000-0000-7000-8000-000000000010",
          ownerOrgUnitName: "Équipe Produit",
          visibilityMode: "PRIVATE_USER",
          lifecyclePhase: "BUILD",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
        {
          workspaceId: TEAM_WS_ID,
          slug: "espace-socle-ia",
          name: "Espace Socle IA",
          ownerOrgUnitId: "0195f000-0000-7000-8000-000000000010",
          ownerOrgUnitName: "Équipe Produit",
          visibilityMode: "STANDARD",
          lifecyclePhase: "RUN",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
    },
    {
      email: "alice@orcia.fr",
      displayName: "Alice Produit",
      roles: ["PLATFORM_ADMIN"],
    },
  );
  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "test-jwt-token",
    displayName: "Alice Produit",
    email: "alice@orcia.fr",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "PLATFORM_ADMIN",
  });
}

async function mountAtWorkspaces(locale: "fr" | "en") {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: ["/workspaces"] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  const rendered = render(
    <I18nProvider initialLocale={locale}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </I18nProvider>,
  );
  return { ...rendered, router };
}

beforeEach(() => {
  ensureWorkingLocalStorage();
  resetVitestApiBackend();
  clearPlatformSetupStorage();
  clearSavedActiveScopeId();
});

afterEach(() => {
  cleanup();
});

describe("Story 28.1 — Single Compact Workspace Header, Sidebar Scope Sync & Zero UUID Leak", () => {
  it("renders a single compact header synced bidirectionally with the Sidebar selector, survives F5, and leaks zero personal-<uuid> strings", async () => {
    seedWorkspacesState();
    const first = await mountAtWorkspaces("fr");

    const header = await screen.findByTestId("workspaces-compact-header");
    expect(header).toBeDefined();
    expect(screen.queryByTestId("workspaces-header-and-filters-bar")).toBeNull();
    expect(screen.queryByTestId("workspaces-summary-cards-grid")).toBeNull();
    expect(screen.queryByTestId("module-uri-badge-admin")).toBeNull();
    expect(screen.queryByTestId("workspace-default-destination")).toBeNull();

    expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Mon Espace Personnel");
    expect(screen.getByTestId(`workspace-visibility-badge-${PERSONAL_WS_ID}`).textContent).toContain(
      "Personnel",
    );
    expect(screen.getByTestId(`workspace-phase-badge-${PERSONAL_WS_ID}`).textContent).toContain(
      "Construction",
    );
    expect(screen.getByTestId("toggle-create-workspace-form-btn")).toBeDefined();
    expect(screen.getByTestId("spaces-open-glossary-link")).toBeDefined();

    // Zero raw personal-<uuid> or UUIDv7 in rendered text (including Deliverables tab destination URI)
    expect(first.container.textContent ?? "").not.toContain(PERSONAL_WS_SLUG);
    expect(first.container.textContent ?? "").not.toContain(PERSONAL_WS_ID);

    fireEvent.click(screen.getByTestId("workspace-tab-DELIVERABLES_ARTIFACTS")); // pragma: allowlist secret
    const deliverablesPanel = await screen.findByTestId("workspace-deliverables-panel");
    expect(deliverablesPanel.textContent).toContain(
      "orcia://workspaces/mon-espace-personnel/deliverables",
    );
    expect(deliverablesPanel.textContent).not.toContain(PERSONAL_WS_SLUG);

    // Switch via compact /workspaces switcher -> updates Sidebar selector + TopHeader + localStorage
    const compactSwitcher = screen.getByTestId(
      "workspaces-active-switcher-select",
    ) as HTMLSelectElement;
    await act(async () => {
      fireEvent.change(compactSwitcher, { target: { value: TEAM_WS_ID } });
    });

    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Espace Socle IA");
      expect(
        (screen.getByTestId("sidebar-workspace-selector") as HTMLSelectElement).value,
      ).toBe(TEAM_WS_ID);
      expect(window.localStorage.getItem(ORCIA_ACTIVE_SCOPE_STORAGE_KEY)).toBe(TEAM_WS_ID);
    });
    expect(screen.getByTestId(`workspace-visibility-badge-${TEAM_WS_ID}`).textContent).toContain(
      "Équipe",
    );
    expect(screen.getByTestId(`workspace-phase-badge-${TEAM_WS_ID}`).textContent).toContain(
      "Exploitation",
    );

    // F5 reload simulation -> Sidebar & /workspaces compact header remain synchronized
    first.unmount();
    cleanup();

    const reloaded = await mountAtWorkspaces("fr");
    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Espace Socle IA");
      expect(
        (screen.getByTestId("sidebar-workspace-selector") as HTMLSelectElement).value,
      ).toBe(TEAM_WS_ID);
    });

    // Reverse sync: switch via Sidebar selector -> /workspaces compact header updates immediately
    await act(async () => {
      fireEvent.change(screen.getByTestId("sidebar-workspace-selector"), {
        target: { value: PERSONAL_WS_ID },
      });
    });
    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe(
        "Mon Espace Personnel",
      );
      expect(
        (screen.getByTestId("workspaces-active-switcher-select") as HTMLSelectElement).value,
      ).toBe(PERSONAL_WS_ID);
    });
    reloaded.unmount();
  });

  it("renders the single compact workspace header cleanly in English (en) without French leakage or raw UUIDs", async () => {
    seedWorkspacesState();
    await createOrciaApiClient({ baseUrl: "" }).updateUserPreferences({ locale: "en" });
    const view = await mountAtWorkspaces("en");

    await screen.findByTestId("workspaces-compact-header");
    await waitFor(() => {
      expect(screen.getByTestId(`workspace-visibility-badge-${PERSONAL_WS_ID}`).textContent).toContain(
        "Personal",
      );
    });
    expect(screen.getByTestId(`workspace-phase-badge-${PERSONAL_WS_ID}`).textContent).toContain(
      "Build",
    );
    expect(screen.getByTestId("toggle-create-workspace-form-btn").textContent).toContain(
      "+ New space",
    );
    expect(screen.getByTestId("spaces-open-glossary-link").textContent).toContain(
      "Business Glossary",
    );
    expect(view.container.textContent ?? "").not.toContain(PERSONAL_WS_SLUG);

    await act(async () => {
      fireEvent.change(screen.getByTestId("workspaces-active-switcher-select"), {
        target: { value: TEAM_WS_ID },
      });
    });
    await waitFor(() => {
      expect(screen.getByTestId(`workspace-visibility-badge-${TEAM_WS_ID}`).textContent).toContain(
        "Team",
      );
      expect(screen.getByTestId(`workspace-phase-badge-${TEAM_WS_ID}`).textContent).toContain(
        "Operations",
      );
    });
    view.unmount();
  });
});
