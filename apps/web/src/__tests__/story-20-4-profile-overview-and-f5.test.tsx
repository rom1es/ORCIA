import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";
import { seedVitestUserProfileSummary } from "./vitestUserSettingsMockHandlers";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

afterEach(() => {
  cleanup();
  resetAuthSessionStore();
  resetVitestApiBackend();
});

async function renderAtProfileRoute() {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: ["/profile"] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  const rendered = render(
    <QueryClientProvider client={queryClient}>
      <I18nProvider initialLocale="fr">
        <RouterProvider router={router} />
      </I18nProvider>
    </QueryClientProvider>,
  );
  return { ...rendered, router };
}

describe("Story 20.4 — Mon Profil (/profile), 4 KPIs, Éléments Populaires & Survie F5", () => {
  it("renders Day-0 empty state cleanly without fake stats and opens Settings modal on Modifier", async () => {
    seedVitestPlatformSetupState({}, { email: "nadia@orcia.ia", displayName: "Nadia Benali" });
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      email: "nadia@orcia.ia",
      displayName: "Nadia Benali",
      roles: ["CONTRIBUTOR"],
      readOnlyObserver: false,
    });
    seedVitestUserProfileSummary({
      user_id: "u-nadia",
      display_name: "Nadia Benali",
      handle: "nadia",
      email: "nadia@orcia.ia",
      primary_role: "CONTRIBUTOR",
      roles: ["CONTRIBUTOR"],
      total_tokens: 0,
      peak_daily_tokens: 0,
      longest_streak_days: 0,
      current_streak_days: 0,
      popular_items: [],
    });

    await renderAtProfileRoute();

    const page = await screen.findByTestId("user-profile-overview-page");
    expect(page).toBeDefined();
    expect((await screen.findByTestId("profile-display-name")).textContent).toBe("Nadia Benali");
    expect(screen.getByTestId("profile-handle-email").textContent).toContain("@nadia · nadia@orcia.ia");
    expect(screen.getByTestId("profile-kpis-empty-state")).toBeDefined();
    expect(screen.queryByTestId("profile-kpi-total-tokens")).toBeNull();
    expect(screen.queryByTestId("profile-kpi-longest-streak")).toBeNull();
    expect(await screen.findByTestId("profile-popular-items-empty")).toBeDefined();

    // Clicking "Modifier" opens the unified Settings modal on ACCOUNT_SECURITY tab
    fireEvent.click(screen.getByTestId("profile-open-account-settings-btn"));
    const modal = await screen.findByTestId("user-settings-modal");
    expect(modal).toBeDefined();
    expect(useAuthSessionStore.getState().userSettingsModalInitialTab).toBe("ACCOUNT_SECURITY");
  });

  it("displays BU/team attachments, 4 KPIs, popular items, and survives F5 unmount/remount", async () => {
    seedVitestPlatformSetupState({}, { email: "claire@orcia.ia", displayName: "Claire Moreau" });
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      email: "claire@orcia.ia",
      displayName: "Claire Moreau",
      roles: ["BU_LEAD", "ONTOLOGY_LEAD"],
      readOnlyObserver: false,
    });
    seedVitestUserProfileSummary({
      user_id: "u-claire",
      display_name: "Claire Moreau",
      handle: "claire",
      email: "claire@orcia.ia",
      primary_role: "BU_LEAD",
      roles: ["BU_LEAD", "ONTOLOGY_LEAD"],
      led_business_units: ["Direction Sinistres"],
      ontology_business_units: ["Direction Sinistres"],
      led_teams: ["Équipe Paiement"],
      member_teams: ["Équipe Architecture"],
      total_tokens: 48200,
      peak_daily_tokens: 14500,
      longest_streak_days: 12,
      current_streak_days: 5,
      popular_items: [
        {
          item_type: "AGENT",
          item_key: "agent-dora",
          title: "Agent Conformité DORA",
          usage_count: 14,
          target_route: "/agents",
        },
        {
          item_type: "PROCESS",
          item_key: "wf-claims",
          title: "Analyse Sinistres",
          usage_count: 6,
          target_route: "/processes",
        },
      ],
    });

    const first = await renderAtProfileRoute();

    await waitFor(() => {
      expect(screen.getByTestId("profile-org-badges").textContent).toContain("Direction Sinistres");
    });
    expect(screen.getByTestId("profile-org-badges").textContent).toContain("Équipe Paiement");
    expect(screen.getByTestId("profile-org-badges").textContent).toContain("Équipe Architecture");
    expect(screen.getByTestId("profile-kpi-total-tokens").textContent).toMatch(/48[\s\u00a0\u202f]?200/);
    expect(screen.getByTestId("profile-kpi-peak-tokens").textContent).toMatch(/14[\s\u00a0\u202f]?500/);
    expect(screen.getByTestId("profile-kpi-longest-streak").textContent).toContain("12 jours");
    expect(screen.getByTestId("profile-kpi-current-streak").textContent).toContain("5 jours");
    expect(screen.getByTestId("profile-popular-item-agent-dora").textContent).toContain(
      "Agent Conformité DORA",
    );

    // Simulate F5 full page reload (unmount + remount at /profile)
    first.unmount();
    cleanup();
    const second = await renderAtProfileRoute();
    await waitFor(() => {
      expect(screen.getByTestId("profile-kpi-longest-streak").textContent).toContain("12 jours");
    });
    expect(screen.getByTestId("profile-popular-item-wf-claims").textContent).toContain(
      "Analyse Sinistres",
    );

    // Click on popular item navigates to its target_route
    fireEvent.click(screen.getByTestId("profile-popular-item-agent-dora"));
    await waitFor(() => {
      expect(second.router.state.location.pathname).toBe("/agents");
    });
  });
});
