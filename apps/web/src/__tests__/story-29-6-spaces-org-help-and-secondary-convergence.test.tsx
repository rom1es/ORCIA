// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import { clearSavedActiveScopeId } from "../components/useShellContainerState";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

const BU_OPS_ID = "0195f296-0000-7000-8000-000000000001";
const TEAM_CORE_ID = "0195f296-0000-7000-8000-000000000002";
const TEAM_SIBLING_ID = "0195f296-0000-7000-8000-000000000003";
const WS_PERSONAL_ID = "0195f296-0000-7000-8000-000000000101";
const WS_TEAM_ID = "0195f296-0000-7000-8000-000000000102";

function seedAdminOrLeadState(options: { readonly role: "PLATFORM_ADMIN" | "TEAM_LEAD" }) {
  const isAdmin = options.role === "PLATFORM_ADMIN";
  const email = isAdmin ? "admin296@orcia.test" : "lead296@orcia.test";
  const displayName = isAdmin ? "Admin 296" : "Lead 296";

  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: BU_OPS_ID,
          name: "Division Operations",
          slug: "div-ops",
          kind: "BU",
          level: "BU",
          parentId: null,
          billingEnabled: true,
        },
        {
          id: TEAM_CORE_ID,
          name: "Core Platform Team",
          slug: "team-core",
          kind: "TEAM",
          level: "TEAM",
          parentId: BU_OPS_ID,
          billingEnabled: true,
          lead_user_id: email,
          lead_user_ids: [email],
          member_user_ids: ["member@orcia.test"],
        },
        {
          id: TEAM_SIBLING_ID,
          name: "Sibling CRL Team",
          slug: "team-crl",
          kind: "TEAM",
          level: "TEAM",
          parentId: BU_OPS_ID,
          billingEnabled: true,
        },
      ],
      workspaces: [
        {
          workspaceId: WS_PERSONAL_ID,
          slug: `personal-${WS_PERSONAL_ID}`,
          name: "Personal Lab 29.6",
          ownerUserId: email,
          ownerOrgUnitId: TEAM_CORE_ID,
          ownerOrgUnitName: "Core Platform Team",
          visibilityMode: "PRIVATE_USER",
          lifecyclePhase: "BUILD",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
        {
          workspaceId: WS_TEAM_ID,
          slug: "team-space-296",
          name: "Team Space 29.6",
          ownerOrgUnitId: TEAM_CORE_ID,
          ownerOrgUnitName: "Core Platform Team",
          visibilityMode: "STANDARD",
          lifecyclePhase: "BUILD",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
      llm_tiers: [{ id: "llm-1", provider: "openai", model_id: "gpt-4o-mini", tier: "standard", enabled: true }],
    },
    { email, displayName, roles: [options.role] },
  );

  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "mock-token-296",
    email,
    displayName,
    roles: [options.role],
    activeHat: options.role,
    readOnlyObserver: false,
  });
}

async function mountAt(path: string, locale: "fr" | "en", role: "PLATFORM_ADMIN" | "TEAM_LEAD" = "PLATFORM_ADMIN") {
  seedAdminOrLeadState({ role });
  const origFetch = globalThis.fetch;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = typeof input === "string" ? input : (input as Request).url;
    if (url.includes("/api/v1/users/me/preferences") && (!init?.method || init.method === "GET")) {
      return new Response(
        JSON.stringify({
          theme: "light",
          locale,
          default_assistant_hat: role,
          auto_open_contextual_help: false,
          notifications_enabled: true,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    if (url.includes("/api/v1/org-units") && (!init?.method || init.method === "GET")) {
      const isLead = role === "TEAM_LEAD";
      return new Response(
        JSON.stringify({
          org_units: [
            {
              id: BU_OPS_ID,
              name: "Division Operations",
              slug: "div-ops",
              kind: "BU",
              parent_id: null,
              billing_enabled: true,
              can_edit: !isLead,
              can_delete: !isLead,
              can_manage_members: !isLead,
              can_create_child: !isLead,
              can_invite_users: !isLead,
            },
            {
              id: TEAM_CORE_ID,
              name: "Core Platform Team",
              slug: "team-core",
              kind: "TEAM",
              parent_id: BU_OPS_ID,
              billing_enabled: true,
              lead_user_id: isLead ? "lead296@orcia.test" : "admin296@orcia.test",
              lead_user_ids: [isLead ? "lead296@orcia.test" : "admin296@orcia.test"],
              member_user_ids: ["member@orcia.test"],
              can_edit: true,
              can_delete: !isLead,
              can_manage_members: true,
              can_create_child: false,
              can_invite_users: true,
            },
            {
              id: TEAM_SIBLING_ID,
              name: "Sibling CRL Team",
              slug: "team-crl",
              kind: "TEAM",
              parent_id: BU_OPS_ID,
              billing_enabled: true,
              can_edit: !isLead,
              can_delete: !isLead,
              can_manage_members: !isLead,
              can_create_child: false,
              can_invite_users: !isLead,
            },
          ],
          known_users: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    return origFetch(input, init);
  });

  const qc = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [path] });
  const router = createOrciaRouter({ queryClient: qc, history });
  await router.load();
  return render(
    <I18nProvider initialLocale={locale}>
      <QueryClientProvider client={qc}>
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
  vi.restoreAllMocks();
  cleanup();
  resetAuthSessionStore();
});

describe("Story 29.6 — Spaces, Organization, Help & Secondary Routes Convergence", () => {
  it("converges Mes Espaces (/spaces) with unnumbered OrciaTabStrip, no Phase/switcher, and Tab 5 visibility in FR & EN", async () => {
    await mountAt("/spaces", "fr");
    const header = await screen.findByTestId("workspaces-compact-header");
    expect(header.className).toContain("orcia-ds-page-header");
    expect(screen.getByTestId("workspaces-active-title").tagName.toLowerCase()).toBe("h1");
    expect(screen.queryByTestId("workspaces-active-switcher-select")).toBeNull();
    expect(screen.queryByTestId(`workspace-card-phase-select-${WS_PERSONAL_ID}`)).toBeNull();
    expect(screen.queryByTestId(`workspace-phase-badge-${WS_PERSONAL_ID}`)).toBeNull();
    expect(screen.queryByTestId(`share-private-workspace-btn-${WS_PERSONAL_ID}`)).toBeNull();

    const tabStrip = screen.getByTestId("workspace-five-tabs-strip");
    expect(tabStrip.className).toContain("orcia-ds-tab-strip");
    expect(screen.getByTestId("workspace-tab-OVERVIEW").textContent).toBe("Vue d'ensemble");
    expect(screen.getByTestId("workspace-tab-DOCUMENTS_SOURCES").textContent).toContain("Documents & Sources");
    expect(screen.getByTestId("workspace-tab-DELIVERABLES_ARTIFACTS").textContent).toBe("Livrables & Artefacts"); // pragma: allowlist secret
    expect(screen.getByTestId("workspace-tab-GLOSSARY_RULES").textContent).toBe("Glossaire & Règles Métiers");
    expect(screen.getByTestId("workspace-tab-MEMBERS_TEAM").textContent).toBe("Membres & Équipe");

    // Switch to Team Space via Left Rail selector and change visibility in Tab 5
    fireEvent.change(screen.getByTestId("sidebar-workspace-selector"), { target: { value: WS_TEAM_ID } });
    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Team Space 29.6");
    });
    fireEvent.click(screen.getByTestId("workspace-tab-MEMBERS_TEAM"));
    const visSelect = (await screen.findByTestId(`workspace-card-visibility-select-${WS_TEAM_ID}`)) as HTMLSelectElement;
    expect(visSelect.disabled).toBe(false);
    fireEvent.change(visSelect, { target: { value: "CONFIDENTIAL_RESTRICTED" } });
    await waitFor(() => {
      expect(screen.getByTestId(`workspace-visibility-badge-${WS_TEAM_ID}`).textContent).toContain("Confidentiel");
    });

    cleanup();
    vi.restoreAllMocks();
    await mountAt("/spaces", "en");
    await screen.findByTestId("workspace-five-tabs-strip");
    expect(screen.getByTestId("workspace-tab-OVERVIEW").textContent).toBe("Overview");
    expect(screen.getByTestId("workspace-tab-MEMBERS_TEAM").textContent).toBe("Members & Team");
  });

  it("converges Mon Organisation (/organization) with header actions, no inline callout, distinct ancestor vs sibling badges, and hidden read-only buttons", async () => {
    await mountAt("/organization", "fr", "TEAM_LEAD");
    const header = await screen.findByTestId("organization-page-header");
    expect(header.className).toContain("orcia-ds-page-header");
    expect(within(header).getByTestId("open-invite-org-user-modal-btn")).toBeDefined();
    expect(within(header).getByTestId("open-create-org-unit-modal-btn")).toBeDefined();
    expect(within(header).getByTestId("organization-open-workspaces-btn")).toBeDefined();
    expect(screen.queryByTestId("organization-pedagogical-callout")).toBeNull();
    expect(screen.getByTestId("settings-organization-section").className).toContain("orcia-ds-data-card");

    expect(screen.getByTestId(`org-unit-readonly-badge-${BU_OPS_ID}`).textContent).toBe("Contexte parent");
    expect(screen.getByTestId(`org-unit-readonly-badge-${TEAM_SIBLING_ID}`).textContent).toBe("Autre équipe — lecture seule");
    expect(screen.getByTestId(`org-unit-active-perimeter-badge-${TEAM_CORE_ID}`).textContent).toBe("Périmètre actif");
    expect(screen.queryByTestId(`edit-org-unit-btn-${BU_OPS_ID}`)).toBeNull();
    expect(screen.queryByTestId(`delete-org-unit-btn-${BU_OPS_ID}`)).toBeNull();
    expect(screen.queryByTestId(`edit-org-unit-btn-${TEAM_SIBLING_ID}`)).toBeNull();
    expect(screen.queryByTestId(`delete-org-unit-btn-${TEAM_SIBLING_ID}`)).toBeNull();

    cleanup();
    vi.restoreAllMocks();
    await mountAt("/organization", "en", "TEAM_LEAD");
    await screen.findByTestId("organization-page-header");
    expect(screen.getByTestId(`org-unit-readonly-badge-${BU_OPS_ID}`).textContent).toBe("Parent context");
    expect(screen.getByTestId(`org-unit-readonly-badge-${TEAM_SIBLING_ID}`).textContent).toBe("Other team — read-only");
  });

  it("converges Aide (/help) to full width, mounts OrciaPageHeader, suppresses Zone 4, and disables TopBar help toggle", async () => {
    await mountAt("/help", "fr");
    const header = await screen.findByTestId("help-page-header");
    expect(header.className).toContain("orcia-ds-page-header");
    expect(screen.getByTestId("help-page-header-title").textContent).toBe("Centre d'Aide");
    const panel = screen.getByTestId("contextual-help-hybrid-panel");
    expect(panel.className).toContain("orcia-ds-data-card");
    expect(panel.className).not.toContain("max-w-4xl");
    expect(screen.queryByTestId("four-zone-contextual-help-column")).toBeNull();

    const topBarToggle = screen.getByTestId("topbar-contextual-help-toggle") as HTMLButtonElement;
    expect(topBarToggle.disabled).toBe(true);
    expect(topBarToggle.getAttribute("aria-current")).toBe("page");
  });

  it("converges secondary routes (/cockpit, /settings, /settings/packs, /profile, /activity) onto OrciaPageHeader and OrciaDataCard", async () => {
    const cases: ReadonlyArray<{ readonly route: string; readonly headerId: string; readonly titleId?: string }> = [
      { route: "/cockpit", headerId: "cockpit-page-header" },
      { route: "/settings", headerId: "settings-page-header" },
      { route: "/settings/packs", headerId: "packs-registry-page-header" },
      { route: "/profile", headerId: "profile-page-header", titleId: "profile-display-name" },
      { route: "/activity", headerId: "activity-page-header" },
    ];
    for (const c of cases) {
      await mountAt(c.route, "en");
      const header = await screen.findByTestId(c.headerId);
      expect(header.className).toContain("orcia-ds-page-header");
      expect(screen.getByTestId(c.titleId ?? `${c.headerId}-title`).tagName.toLowerCase()).toBe("h1");
      cleanup();
      vi.restoreAllMocks();
    }
  });
});
