import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { describe, expect, it } from "vitest";
import { ShellContainer } from "../components/ShellContainer";
import { I18nProvider } from "../i18n";
import {
  simulateUnauthenticatedBrowser,
  useAuthSessionStore,
} from "../stores/authSessionStore";
import { seedVitestPlatformSetupState } from "./vitest.setup";

describe("Auth, Incognito Navigation, Logout & Temporary Password Warning Banner", () => {
  it("renders BiModeLoginView when unauthenticated in an incognito / private browser session", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.test", displayName: "Admin Test" });
    simulateUnauthenticatedBrowser();

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={() => undefined}>
          <div data-testid="protected-workspace-content">Contenu Espace</div>
        </ShellContainer>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("unauthenticated-shell-fallback")).toBeDefined();
      expect(screen.getByTestId("bi-mode-login-view")).toBeDefined();
    });
    expect(screen.queryByTestId("protected-workspace-content")).toBeNull();
  });

  it("displays persistent amber warning banner when mustChangePassword is true and opens account security tab on click", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.test", displayName: "Admin Test" });
    useAuthSessionStore.getState().loginWithSession({
      email: "nouveau.collaborateur@orcia.fr",
      display_name: "Nouveau Collaborateur",
      roles: ["CONTRIBUTOR"],
      mustChangePassword: true,
    });

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={() => undefined}>
          <div data-testid="protected-workspace-content">Contenu Espace</div>
        </ShellContainer>
      </I18nProvider>,
    );

    // Banner is rendered
    const banner = await screen.findByTestId("temporary-password-warning-banner");
    expect(banner).toBeDefined();
    expect(banner.textContent).toContain("Attention : vous utilisez un mot de passe temporaire");

    // Click banner CTA
    const changeBtn = screen.getByTestId("temporary-password-open-settings-btn");
    fireEvent.click(changeBtn);

    // Modal settings dialog is opened
    await waitFor(() => {
      expect(screen.getByTestId("user-settings-modal")).toBeDefined();
    });
  });

  it("handles logout by clearing auth session and navigating to /login", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.test", displayName: "Admin Test" });
    let redirectedRoute = "";
    useAuthSessionStore.getState().loginWithSession({
      email: "romain@orcia.fr",
      display_name: "Romain Admin",
      roles: ["PLATFORM_ADMIN"],
      mustChangePassword: false,
    });

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={(href) => { redirectedRoute = href; }}>
          <div data-testid="protected-workspace-content">Contenu Espace</div>
        </ShellContainer>
      </I18nProvider>,
    );

    expect(screen.getByTestId("protected-workspace-content")).toBeDefined();

    // Open user account dropdown
    fireEvent.click(screen.getByTestId("user-account-dropdown-trigger"));
    const logoutBtn = screen.getByTestId("dropdown-logout-btn");

    fireEvent.click(logoutBtn);

    await waitFor(() => {
      const state = useAuthSessionStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(redirectedRoute).toBe("/login");
    });
  });
});
