import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import { LoginScreenView } from "../components/LoginScreenView";
import { OrciaNavigationProvider } from "../components/navigationAdapter";
import { ShellContainer } from "../components/ShellContainer";
import { I18nProvider } from "../i18n";
import {
  resolveWebApiBaseUrl,
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

  it("displays persistent amber warning banner when mustChangePassword is true, handles wrong current password, and collapses inputs after valid change with F5 survival", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.test", displayName: "Admin Test" });
    useAuthSessionStore.getState().loginWithSession({
      email: "nouveau.collaborateur@orcia.fr",
      display_name: "Nouveau Collaborateur",
      roles: ["CONTRIBUTOR"],
      access_token: "mock-vitest-access-token",
      mustChangePassword: true,
    });

    const { unmount } = render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={() => undefined}>
          <div data-testid="protected-workspace-content">Contenu Espace</div>
        </ShellContainer>
      </I18nProvider>,
    );

    // 1. Banner is rendered
    const banner = await screen.findByTestId("temporary-password-warning-banner");
    expect(banner).toBeDefined();
    expect(banner.textContent).toContain("Attention : vous utilisez un mot de passe temporaire");

    // 2. Click banner CTA -> Modal settings dialog is opened
    const changeBtn = screen.getByTestId("temporary-password-open-settings-btn");
    fireEvent.click(changeBtn);

    await waitFor(() => {
      expect(screen.getByTestId("user-settings-modal")).toBeDefined();
      expect(screen.getByTestId("user-password-change-card")).toBeDefined();
      expect(screen.getByTestId("user-current-password-input")).toBeDefined();
    });

    // 3. Attempt with wrong current password -> error banner without OIDC / email text
    const currentInput = screen.getByTestId("user-current-password-input");
    const newInput = screen.getByTestId("user-new-password-input");
    const confirmInput = screen.getByTestId("user-confirm-password-input");

    fireEvent.change(currentInput, { target: { value: "WrongCurrentPassword123" } }); // pragma: allowlist secret
    fireEvent.change(newInput, { target: { value: "NewValidPassword2026" } }); // pragma: allowlist secret
    fireEvent.change(confirmInput, { target: { value: "NewValidPassword2026" } }); // pragma: allowlist secret

    fireEvent.click(screen.getByTestId("user-change-password-submit-btn"));

    await waitFor(() => {
      const feedback = screen.getByTestId("user-change-password-feedback");
      expect(feedback.textContent).toContain("Le mot de passe actuel saisi est incorrect");
      expect(feedback.textContent).not.toContain("OIDC");
      expect(feedback.textContent.toLowerCase()).not.toContain("e-mail");
      // Form inputs remain rendered
      expect(screen.getByTestId("user-current-password-input")).toBeDefined();
      expect(screen.getByTestId("user-new-password-input")).toBeDefined();
      expect(screen.getByTestId("user-confirm-password-input")).toBeDefined();
      expect(screen.getByTestId("user-change-password-submit-btn")).toBeDefined();
    });

    // 4. Valid password change -> form inputs are removed from DOM, success banner displayed
    fireEvent.change(screen.getByTestId("user-current-password-input"), {
      target: { value: "ValidTempSecret1" }, // pragma: allowlist secret
    });
    fireEvent.click(screen.getByTestId("user-change-password-submit-btn"));

    await waitFor(() => {
      // Inputs and submit button are completely hidden
      expect(screen.queryByTestId("user-current-password-input")).toBeNull();
      expect(screen.queryByTestId("user-new-password-input")).toBeNull();
      expect(screen.queryByTestId("user-confirm-password-input")).toBeNull();
      expect(screen.queryByTestId("user-change-password-submit-btn")).toBeNull();
      expect(screen.queryByTestId("user-must-change-password-alert")).toBeNull();
      expect(screen.queryByTestId("temporary-password-warning-banner")).toBeNull();
      const feedback = screen.getByTestId("user-change-password-feedback");
      expect(feedback.textContent).toContain("Mot de passe mis à jour avec succès.");
      expect(useAuthSessionStore.getState().mustChangePassword).toBe(false);
    });

    // 5. Gate of « Survie au F5 »: unmount and re-render simulates page reload
    unmount();

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={() => undefined}>
          <div data-testid="protected-workspace-content">Contenu Espace Après Reload</div>
        </ShellContainer>
      </I18nProvider>,
    );

    // Warning banner remains gone after F5 rehydration
    expect(screen.queryByTestId("temporary-password-warning-banner")).toBeNull();
    expect(screen.getByTestId("protected-workspace-content")).toBeDefined();
  });

  it("handles logout by clearing auth session and navigating to /login", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.test", displayName: "Admin Test" });
    let redirectedRoute = "";
    useAuthSessionStore.getState().loginWithSession({
      email: "romain@orcia.fr",
      display_name: "Romain Admin",
      roles: ["PLATFORM_ADMIN"],
      access_token: "mock-vitest-access-token",
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

    // Open sidebar account popover & click logout
    fireEvent.keyDown(screen.getByTestId("sidebar-open-my-account-btn"), { key: "Enter" });
    const logoutBtn = await screen.findByTestId("account-popover-logout-btn");

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

    // 2. Wait for silent session bootstrap to complete and standalone login to mount
    await waitFor(() => {
      expect(screen.queryByTestId("auth-hydrating-loader")).toBeNull();
      expect(screen.getByTestId("unauthenticated-shell-fallback")).toBeDefined();
      expect(screen.getByTestId("bi-mode-login-view")).toBeDefined();
    });

    // 3. Confirm 4-zone shell navigation and user elements are NOT rendered
    expect(screen.queryByTestId("protected-workspace-content")).toBeNull();
    expect(screen.queryByTestId("user-account-dropdown-trigger")).toBeNull();
    expect(screen.queryByTestId("eight-menu-item-cockpit")).toBeNull();

    // 4. Verify GET /api/v1/auth/session was called (never noisy 401 POST /refresh)
    const sessionCalls = getRecordedVitestApiCalls().filter(
      (c) => c.path === "/api/v1/auth/session",
    );
    expect(sessionCalls.length).toBeGreaterThanOrEqual(1);
    const refreshCalls = getRecordedVitestApiCalls().filter(
      (c) => c.path === "/api/v1/auth/refresh",
    );
    expect(refreshCalls).toHaveLength(0);

    // 5. In default exclusive LOCAL mode, credentials inputs are directly rendered (no accordion)
    expect(screen.queryByTestId("login-local-accordion-toggle")).toBeNull();

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

    // 2. StrictMode double-mount must have issued exactly 1 GET /api/v1/auth/session
    const sessionCalls = getRecordedVitestApiCalls().filter(
      (c) => c.path === "/api/v1/auth/session",
    );
    expect(sessionCalls).toHaveLength(1);

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
      access_token: "mock-vitest-access-token",
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

    // Open sidebar account popover & click logout
    fireEvent.keyDown(screen.getByTestId("sidebar-open-my-account-btn"), { key: "Enter" });
    const logoutBtn = await screen.findByTestId("account-popover-logout-btn");
    fireEvent.click(logoutBtn);

    // Wait for logout call and standalone login screen
    await waitFor(() => {
      expect(useAuthSessionStore.getState().isAuthenticated).toBe(false);
      expect(screen.getByTestId("unauthenticated-shell-fallback")).toBeDefined();
      expect(screen.getByTestId("bi-mode-login-view")).toBeDefined();
    });

    // 4-zone shell is gone
    expect(screen.queryByTestId("protected-workspace-content")).toBeNull();
    expect(screen.queryByTestId("sidebar-open-my-account-btn")).toBeNull();
    expect(screen.queryByTestId("eight-menu-item-cockpit")).toBeNull();

    // Verify POST /api/v1/auth/logout was recorded
    const logoutCalls = getRecordedVitestApiCalls().filter(
      (c) => c.path === "/api/v1/auth/logout",
    );
    expect(logoutCalls.length).toBeGreaterThanOrEqual(1);
  });

  it("normalizes redundant /api baseUrl suffix and keeps /login free of error banner when public-config fails on mount", async () => {
    vi.stubEnv("VITE_ORCIA_API_BASE_URL", "/api/");
    expect(resolveWebApiBaseUrl()).toBe("");
    vi.stubEnv("VITE_ORCIA_API_BASE_URL", "http://localhost:8000/api");
    expect(resolveWebApiBaseUrl()).toBe("http://localhost:8000");
    vi.unstubAllEnvs();

    const originalFetch = globalThis.fetch;
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    globalThis.fetch = vi.fn(async () =>
      new Response(
        JSON.stringify({
          type: "about:blank",
          title: "Not Found",
          status: 404,
          error_code: "ERR_RESOURCE_NOT_FOUND",
          detail: "La ressource ou la route demandée n'existe pas sur la plateforme ORCIA.",
          instance: "/api/v1/auth/public-config",
          trace_id: "01a1dea0ae92746cb77fe642462647f0",
        }),
        { status: 404, headers: { "Content-Type": "application/problem+json" } },
      ),
    ) as typeof fetch;

    try {
      render(
        <I18nProvider initialLocale="fr">
          <LoginScreenView />
        </I18nProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("bi-mode-login-view")).toBeDefined();
        expect(warnSpy).toHaveBeenCalled();
      });
      // Pre-flight config failure must NOT display the "Impossible de vous connecter" red alert
      expect(screen.queryByTestId("login-rfc9457-error")).toBeNull();
    } finally {
      globalThis.fetch = originalFetch;
      warnSpy.mockRestore();
    }
  });

  it("does not redirect away from /cockpit during initial session hydration when platformAdmin is cached", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.test", displayName: "Admin Test" });
    setVitestMockRefreshFails(false);
    useAuthSessionStore.setState({ ...UNAUTHENTICATED_SESSION_STATE, isHydrating: true });
    const navigatedRoutes: string[] = [];

    render(
      <I18nProvider initialLocale="fr">
        <OrciaNavigationProvider
          adapter={{
            pathname: "/cockpit",
            navigateTo: (href) => navigatedRoutes.push(href),
          }}
        >
          <ShellContainer>
            <div data-testid="protected-cockpit-content">Cockpit Protégé</div>
          </ShellContainer>
        </OrciaNavigationProvider>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("protected-cockpit-content")).toBeDefined();
    });
    expect(navigatedRoutes).not.toContain("/login");
    const sessionCalls = getRecordedVitestApiCalls().filter(
      (c) => c.path === "/api/v1/auth/session",
    );
    expect(sessionCalls.length).toBeGreaterThanOrEqual(1);
  });
});
