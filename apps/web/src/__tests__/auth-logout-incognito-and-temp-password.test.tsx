import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { describe, expect, it } from "vitest";
import { ShellContainer } from "../components/ShellContainer";
import { I18nProvider } from "../i18n";
import {
  simulateUnauthenticatedBrowser,
  UNAUTHENTICATED_SESSION_STATE,
  useAuthSessionStore,
} from "../stores/authSessionStore";
import {
  getRecordedVitestApiCalls,
  seedVitestPlatformSetupState,
  setVitestMockRefreshFails,
} from "./vitest.setup";

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

  it("simulates real incognito browser boot: shows loader initially, triggers POST /api/v1/auth/refresh, falls back to standalone login without 4-zone shell, and unlocks cockpit on local login", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.test", displayName: "Admin Test" });
    setVitestMockRefreshFails(true);
    useAuthSessionStore.setState({ ...UNAUTHENTICATED_SESSION_STATE, isHydrating: true });

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={() => undefined}>
          <div data-testid="protected-workspace-content">Contenu Espace Protégé</div>
        </ShellContainer>
      </I18nProvider>,
    );

    // 1. Loader is rendered initially
    expect(screen.getByTestId("auth-hydrating-loader")).toBeDefined();
    expect(screen.getByText("Chargement de la session...")).toBeDefined();

    // 2. Wait for refresh to complete (401) and standalone login to mount
    await waitFor(() => {
      expect(screen.queryByTestId("auth-hydrating-loader")).toBeNull();
      expect(screen.getByTestId("unauthenticated-shell-fallback")).toBeDefined();
      expect(screen.getByTestId("bi-mode-login-view")).toBeDefined();
    });

    // 3. Confirm 4-zone shell navigation and user elements are NOT rendered
    expect(screen.queryByTestId("protected-workspace-content")).toBeNull();
    expect(screen.queryByTestId("user-account-dropdown-trigger")).toBeNull();
    expect(screen.queryByTestId("eight-menu-item-cockpit")).toBeNull();

    // 4. Verify POST /api/v1/auth/refresh was called
    const refreshCalls = getRecordedVitestApiCalls().filter(
      (c) => c.path === "/api/v1/auth/refresh",
    );
    expect(refreshCalls.length).toBeGreaterThanOrEqual(1);

    // 5. Expand local login accordion and submit valid login credentials via the form
    const accordionToggle = screen.getByTestId("login-local-accordion-toggle");
    fireEvent.click(accordionToggle);

    const emailInput = screen.getByTestId("login-local-email") as HTMLInputElement;
    const passwordInput = screen.getByTestId("login-local-password") as HTMLInputElement;
    fireEvent.change(emailInput, { target: { value: "admin@orcia.test" } });
    fireEvent.change(passwordInput, { target: { value: "SecretPassword123" } });

    const submitBtn = screen.getByTestId("login-local-submit");
    fireEvent.click(submitBtn);

    // 6. Cockpit is unlocked and same-origin /api/v1/auth/login/local was invoked
    await waitFor(() => {
      expect(screen.getByTestId("protected-workspace-content")).toBeDefined();
    });
    const loginCalls = getRecordedVitestApiCalls().filter(
      (c) => c.path === "/api/v1/auth/login/local",
    );
    expect(loginCalls).toHaveLength(1);
    expect(loginCalls[0]?.body).toMatchObject({
      email: "admin@orcia.test",
    });
  });

  it("simulates authenticated reload inside <React.StrictMode>: calls POST /api/v1/auth/refresh only once and restores session", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.test", displayName: "Admin Test" });
    setVitestMockRefreshFails(false);
    useAuthSessionStore.setState({ ...UNAUTHENTICATED_SESSION_STATE, isHydrating: true });

    render(
      <React.StrictMode>
        <I18nProvider initialLocale="fr">
          <ShellContainer onNavigate={() => undefined}>
            <div data-testid="protected-workspace-content">Contenu Espace Protégé</div>
          </ShellContainer>
        </I18nProvider>
      </React.StrictMode>,
    );

    // 1. Wait for single-flight refresh to settle and restore session
    await waitFor(() => {
      expect(screen.queryByTestId("auth-hydrating-loader")).toBeNull();
      expect(screen.getByTestId("protected-workspace-content")).toBeDefined();
    });

    // 2. StrictMode double-mount must have issued exactly 1 POST /api/v1/auth/refresh
    const refreshCalls = getRecordedVitestApiCalls().filter(
      (c) => c.path === "/api/v1/auth/refresh",
    );
    expect(refreshCalls).toHaveLength(1);

    // 3. Session state is authenticated
    const session = useAuthSessionStore.getState();
    expect(session.isAuthenticated).toBe(true);
    expect(session.accessToken).toBe("mock-refreshed-token");
  });

  it("sign-out: calls POST /api/v1/auth/logout, clears session, and immediately returns to standalone login view without 4-zone shell", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.test", displayName: "Admin Test" });
    useAuthSessionStore.getState().loginWithSession({
      email: "admin@orcia.test",
      display_name: "Admin Test",
      roles: ["PLATFORM_ADMIN"],
      mustChangePassword: false,
    });

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={() => undefined}>
          <div data-testid="protected-workspace-content">Contenu Espace Protégé</div>
        </ShellContainer>
      </I18nProvider>,
    );

    expect(screen.getByTestId("protected-workspace-content")).toBeDefined();

    // Open user account dropdown & click logout
    fireEvent.click(screen.getByTestId("user-account-dropdown-trigger"));
    const logoutBtn = screen.getByTestId("dropdown-logout-btn");
    fireEvent.click(logoutBtn);

    // Wait for logout call and standalone login screen
    await waitFor(() => {
      expect(useAuthSessionStore.getState().isAuthenticated).toBe(false);
      expect(screen.getByTestId("unauthenticated-shell-fallback")).toBeDefined();
      expect(screen.getByTestId("bi-mode-login-view")).toBeDefined();
    });

    // 4-zone shell is gone
    expect(screen.queryByTestId("protected-workspace-content")).toBeNull();
    expect(screen.queryByTestId("user-account-dropdown-trigger")).toBeNull();
    expect(screen.queryByTestId("eight-menu-item-cockpit")).toBeNull();

    // Verify POST /api/v1/auth/logout was recorded
    const logoutCalls = getRecordedVitestApiCalls().filter(
      (c) => c.path === "/api/v1/auth/logout",
    );
    expect(logoutCalls.length).toBeGreaterThanOrEqual(1);
  });
});
