import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { ShellContainer } from "../components/ShellContainer";
import { TemporaryPasswordWarningBanner } from "../components/TemporaryPasswordWarningBanner";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import {
  canAccessMyOrganization,
  canObserveGlobalAuditScope,
  isPlatformAdministratorSession,
  resetAuthSessionStore,
  resolveSessionHatLabel,
  useAuthSessionStore,
} from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

afterEach(() => {
  cleanup();
  resetAuthSessionStore();
  resetVitestApiBackend();
});

async function renderAppAtRoute(initialPath: string) {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [initialPath] });
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

describe("Story 20.3 — Clean Top-Right, ChatGPT-Style Sidebar Popover, 5-Tab Settings & F5 Survival", () => {
  it("removes top-right login trigger & dropdown-hat-selector and evaluates RBAC purely on session.roles union", () => {
    // Even if legacy `activeHat` differs, union of `roles` governs RBAC & displayed role comes from authenticated role
    const mixedSession = {
      roles: ["PLATFORM_ADMIN", "TEAM_LEAD"],
      activeHat: "TEAM_LEAD",
      readOnlyObserver: false,
    };
    expect(isPlatformAdministratorSession(mixedSession)).toBe(true);
    expect(canAccessMyOrganization(mixedSession)).toBe(true);
    expect(canObserveGlobalAuditScope(mixedSession)).toBe(true);
    expect(resolveSessionHatLabel(mixedSession, "fr")).toBe("Administrateur de la plateforme");

    // TemporaryPasswordWarningBanner has a single icon (from OrciaAlertBanner) and zero duplicate SVG/emoji (UX-AUTH-DOUBLE-ICON-01)
    const { container } = render(
      <TemporaryPasswordWarningBanner isFr={true} onOpenSettings={() => undefined} />,
    );
    const svgs = container.querySelectorAll("svg");
    expect(svgs.length).toBe(1);
    expect(container.textContent).not.toContain("⚠️");
  });

  it("renders bottom-left ChatGPT-style account popover, 5-tab settings modal, and survives F5 for theme/personalization/MCP keys", async () => {
    seedVitestPlatformSetupState({}, { email: "martin.pecheur@orcia.ia", displayName: "Martin Pecheur" });
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      email: "martin.pecheur@orcia.ia",
      displayName: "Martin Pecheur",
      roles: ["BU_LEAD"],
      readOnlyObserver: false,
    });

    const first = await renderAppAtRoute("/");

    // 1. Top-right keeps ONLY Aide + Notifications (no login trigger, no hat badge)
    expect(screen.getByTestId("topbar-contextual-help-toggle")).toBeDefined();
    expect(screen.getByTestId("topbar-notifications-toggle")).toBeDefined();
    expect(screen.queryByTestId("topbar-user-account-trigger")).toBeNull();
    expect(screen.queryByTestId("topbar-hat-badge")).toBeNull();
    expect(screen.queryByTestId("dropdown-hat-selector")).toBeNull();

    // 2. Bottom-left shows initials + name + readable role
    const accountBtn = await screen.findByTestId("sidebar-open-my-account-btn");
    expect(accountBtn.textContent).toContain("MP");
    expect(accountBtn.textContent).toContain("Martin Pecheur");
    expect(accountBtn.textContent).toContain("Responsable de Direction (BU)");

    // 3. Open ChatGPT-style popover above sidebar footer
    fireEvent.keyDown(accountBtn, { key: "Enter" });
    const popover = await screen.findByTestId("sidebar-account-popover-menu");
    expect(popover.textContent).toContain("Personnalisation");
    expect(popover.textContent).toContain("Profil");
    expect(popover.textContent).toContain("Paramètres");
    expect(popover.textContent).toContain("Aide");
    expect(popover.textContent).toContain("Se déconnecter");
    // Zero emoji prefixes (UX-AUTH-DOUBLE-ICON-01)
    for (const emoji of ["⚙️", "🔗", "🌓", "🌐", "🚪", "🎨", "👤", "💻"]) {
      expect(popover.textContent).not.toContain(emoji);
    }

    // Expand Aide submenu -> Centre d'aide & Guides + Présentation d'ORCIA
    fireEvent.click(screen.getByTestId("account-popover-help-trigger"));
    expect(screen.getByTestId("account-popover-help-center-btn")).toBeDefined();
    expect(screen.getByTestId("account-popover-showcase-btn")).toBeDefined();

    // 4. Open Settings modal via Paramètres -> 5 vertical tabs
    fireEvent.click(screen.getByTestId("account-popover-settings-btn"));
    expect(await screen.findByTestId("user-settings-modal")).toBeDefined();
    for (const tabKey of [
      "GENERAL",
      "PERSONALIZATION",
      "ACCOUNT_SECURITY",
      "PASSTHROUGH_SOURCES",
      "IDE_MCP_KEYS",
    ]) {
      expect(screen.getByTestId(`user-settings-tab-${tabKey}`)).toBeDefined();
    }

    // 5. Update theme in General tab -> persisted via PATCH /api/v1/users/me/preferences
    fireEvent.click(screen.getByTestId("settings-theme-dark"));
    await waitFor(() => {
      expect(document.documentElement.dataset.theme).toBe("dark");
    });

    // 6. Update Personalization tab -> persisted via PATCH /api/v1/users/me/preferences
    fireEvent.click(screen.getByTestId("user-settings-tab-PERSONALIZATION"));
    fireEvent.change(screen.getByTestId("settings-assistant-hat-select"), {
      target: { value: "ARCHITECT" },
    });
    fireEvent.change(screen.getByTestId("settings-assistant-tone-select"), {
      target: { value: "concise" },
    });
    fireEvent.change(screen.getByTestId("settings-personal-instructions-input"), {
      target: { value: "Toujours résumer les risques en 3 points." },
    });
    fireEvent.click(screen.getByTestId("settings-personalization-save-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("settings-personalization-saved-banner")).toBeDefined();
    });

    // 7. Create a real MCP token (not hardcoded pat_mcp_9a8b7c6d5e4f3a2b1c0d)
    fireEvent.click(screen.getByTestId("user-settings-tab-IDE_MCP_KEYS"));
    fireEvent.change(screen.getByTestId("mcp-token-label-input"), {
      target: { value: "Cursor F5 Key" },
    });
    fireEvent.change(screen.getByTestId("mcp-target-slug-input"), {
      target: { value: "ws-sinistres" },
    });
    fireEvent.click(screen.getByTestId("mcp-generate-token-btn"));

    const plaintextVal = await screen.findByTestId("mcp-issued-plaintext-value");
    expect(plaintextVal.textContent).toContain("pat_mcp_");
    expect(plaintextVal.textContent).not.toBe("pat_mcp_9a8b7c6d5e4f3a2b1c0d");

    // 8. Simulate full browser F5 reload (unmount + remount fresh tree)
    first.unmount();
    await renderAppAtRoute("/");
    const accountBtnReloaded = await screen.findByTestId("sidebar-open-my-account-btn");
    fireEvent.keyDown(accountBtnReloaded, { key: "Enter" });
    fireEvent.click(await screen.findByTestId("account-popover-settings-btn"));

    // Verify theme, personalization & MCP token survived F5!
    await waitFor(() => {
      expect(screen.getByTestId("settings-theme-dark").getAttribute("aria-pressed")).toBe("true");
    });

    fireEvent.click(screen.getByTestId("user-settings-tab-PERSONALIZATION"));
    expect((screen.getByTestId("settings-assistant-hat-select") as HTMLSelectElement).value).toBe(
      "ARCHITECT",
    );
    expect((screen.getByTestId("settings-assistant-tone-select") as HTMLSelectElement).value).toBe(
      "concise",
    );
    expect(
      (screen.getByTestId("settings-personal-instructions-input") as HTMLTextAreaElement).value,
    ).toBe("Toujours résumer les risques en 3 points.");

    fireEvent.click(screen.getByTestId("user-settings-tab-IDE_MCP_KEYS"));
    await waitFor(() => {
      expect(screen.getByTestId("mcp-tokens-list").textContent).toContain("Cursor F5 Key");
      expect(screen.getByTestId("mcp-tokens-list").textContent).toContain("/api/v1/mcp/spaces/ws-sinistres");
    });
  });

  it("navigates to /profile stub when clicking Profil in bottom-left popover", async () => {
    seedVitestPlatformSetupState({}, { email: "martin@orcia.ia", displayName: "Martin Pecheur" });
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      email: "martin@orcia.ia",
      displayName: "Martin Pecheur",
      roles: ["BU_LEAD"],
    });

    const { router } = await renderAppAtRoute("/");
    const accountBtn = await screen.findByTestId("sidebar-open-my-account-btn");
    fireEvent.keyDown(accountBtn, { key: "Enter" });
    fireEvent.click(await screen.findByTestId("account-popover-profile-btn"));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/profile");
      expect(screen.getByTestId("user-profile-overview-page")).toBeDefined();
    });
  });
});
