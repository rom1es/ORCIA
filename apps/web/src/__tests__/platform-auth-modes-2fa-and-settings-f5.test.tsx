import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LoginScreenView } from "../components/LoginScreenView";
import { readStorageItem, writeStorageItem } from "../components/platformSetupStorageHelpers";
import { ShellContainer } from "../components/ShellContainer";
import { CockpitFeaturePanel } from "../features/cockpit";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";
import {
  getVitestLastChallengeCode,
  rotateVitestBootEpoch,
  seedVitestPlatformAuthPolicy,
} from "./vitestAuthPolicyMockHandlers";
import { seedVitestConnectorsInitialData } from "./vitestConnectorsMockHandlers";
import { getRecordedVitestApiCalls, seedVitestPlatformSetupState } from "./vitest.setup";

afterEach(() => {
  cleanup();
  resetAuthSessionStore();
  vi.restoreAllMocks();
});

async function renderSettingsAtTab(tabUrl: string) {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [tabUrl] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("Exclusive Auth Policy (LOCAL vs SSO), Configurable 2FA, Settings Organization & Boot Epoch Isolation", () => {
  it("renders exclusive LOCAL mode by default without SSO button, without Marc, and without Step-1 6-digit input in FR and EN", async () => {
    const { unmount } = render(
      <I18nProvider initialLocale="fr">
        <LoginScreenView />
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("bi-mode-login-view").getAttribute("data-auth-mode")).toBe("LOCAL");
    });

    const subtitleFr = screen.getByTestId("login-mode-subtitle").textContent ?? "";
    expect(subtitleFr).toBe(
      "Connectez-vous avec votre adresse e-mail professionnelle et votre mot de passe.",
    );
    expect(subtitleFr).not.toContain("compte unique de votre organisation");
    expect(screen.queryByTestId("login-sso-oidc-btn")).toBeNull();
    expect(screen.queryByTestId("login-local-accordion-toggle")).toBeNull();
    expect(screen.queryByTestId("login-local-totp")).toBeNull();
    expect(screen.getByTestId("login-local-email")).toBeDefined();
    expect(screen.getByTestId("login-local-password")).toBeDefined();
    expect(document.body.textContent ?? "").not.toContain("Marc");
    unmount();

    render(
      <I18nProvider initialLocale="en">
        <LoginScreenView />
      </I18nProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("login-mode-subtitle").textContent).toBe(
        "Sign in with your work email address and password.",
      );
    });
  });

  it("renders exclusive SSO mode when policy=SSO, hides local password form, and shows warning when OIDC is incomplete", async () => {
    seedVitestPlatformAuthPolicy({
      authMode: "SSO",
      twoFactorMode: "NONE",
      oidcIssuerUrl: null,
      oidcClientId: null,
      oidcRedirectUri: null,
    });

    const { unmount } = render(
      <I18nProvider initialLocale="fr">
        <LoginScreenView />
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("bi-mode-login-view").getAttribute("data-auth-mode")).toBe("SSO");
    });
    expect(screen.getByTestId("login-mode-subtitle").textContent).toBe(
      "Connectez-vous avec le compte unique (SSO) de votre organisation.",
    );
    expect(screen.queryByTestId("login-local-email")).toBeNull();
    expect(screen.queryByTestId("login-local-password")).toBeNull();
    expect(screen.getByTestId("login-sso-unconfigured-banner")).toBeDefined();
    expect((screen.getByTestId("login-sso-oidc-btn") as HTMLButtonElement).disabled).toBe(true);
    unmount();

    seedVitestPlatformAuthPolicy({
      authMode: "SSO",
      oidcIssuerUrl: "https://idp.example.com",
      oidcClientId: "orcia-web",
      oidcRedirectUri: "https://orcia.local/login",
      ssoButtonLabel: "Connexion Entreprise SSO",
    });

    render(
      <I18nProvider initialLocale="fr">
        <LoginScreenView />
      </I18nProvider>,
    );
    await waitFor(() => {
      expect((screen.getByTestId("login-sso-oidc-btn") as HTMLButtonElement).disabled).toBe(false);
    });
    expect(screen.queryByTestId("login-sso-unconfigured-banner")).toBeNull();
    expect(screen.getByTestId("login-sso-oidc-btn").textContent).toContain(
      "Connexion Entreprise SSO",
    );
  });

  it("executes 2-step EMAIL_OTP login with masked email notice, resend regeneration, and code verification", async () => {
    seedVitestConnectorsInitialData({
      connectors: [
        {
          id: "smtp-1",
          connector_kind: "SMTP_MAIL",
          name: "SMTP Corporate",
          base_url: "smtp://mail.internal:587",
          auth_mode: "SERVICE_SECRET",
          enabled: true,
          admin_secret_status: { configured: true, fingerprint: "sha256:smtp", updated_at_iso: null },
          created_at_iso: "2026-11-15T09:00:00Z",
          updated_at_iso: "2026-11-15T09:00:00Z",
        },
      ],
    });
    seedVitestPlatformAuthPolicy({ authMode: "LOCAL", twoFactorMode: "EMAIL_OTP" });
    seedVitestPlatformSetupState({}, { email: "claire.admin@orcia.fr", displayName: "Claire Admin" });

    const onAuth = vi.fn();
    render(
      <I18nProvider initialLocale="fr">
        <LoginScreenView onAuthenticated={onAuth} />
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("login-local-email")).toBeDefined();
    });
    fireEvent.change(screen.getByTestId("login-local-email"), {
      target: { value: "claire.admin@orcia.fr" },
    });
    fireEvent.change(screen.getByTestId("login-local-password"), {
      target: { value: "SecretPassword123!" },
    });
    fireEvent.click(screen.getByTestId("login-local-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("login-2fa-panel")).toBeDefined();
    });
    expect(screen.getByTestId("login-2fa-destination-info").textContent).toContain("cl***@orcia.fr");
    expect(screen.getByTestId("login-2fa-panel").textContent).toContain("5 minutes");

    fireEvent.click(screen.getByTestId("login-2fa-resend-btn"));
    await waitFor(() => {
      expect(
        getRecordedVitestApiCalls().some((c) => c.path === "/api/v1/auth/login/resend-2fa"),
      ).toBe(true);
    });

    const latestCode = getVitestLastChallengeCode("vitest-chal-1") ?? "246810";
    fireEvent.change(screen.getByTestId("login-2fa-code-input"), { target: { value: latestCode } });
    fireEvent.click(screen.getByTestId("login-2fa-submit-btn"));

    await waitFor(() => {
      expect(onAuth).toHaveBeenCalledTimes(1);
    });
    expect(useAuthSessionStore.getState().isAuthenticated).toBe(true);
  });

  it("guides TOTP_ENROLL on first TOTP login then requires TOTP without re-enrolling on subsequent login", async () => {
    seedVitestPlatformAuthPolicy({ authMode: "LOCAL", twoFactorMode: "TOTP" });
    seedVitestPlatformSetupState({}, { email: "admin@orcia.fr", displayName: "Admin ORCIA" });

    const { unmount } = render(
      <I18nProvider initialLocale="fr">
        <LoginScreenView />
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("login-local-email")).toBeDefined();
    });
    fireEvent.change(screen.getByTestId("login-local-email"), { target: { value: "admin@orcia.fr" } });
    fireEvent.change(screen.getByTestId("login-local-password"), { target: { value: "SecretPassword123!" } });
    fireEvent.click(screen.getByTestId("login-local-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("login-2fa-totp-enroll-box")).toBeDefined();
    });
    expect(screen.getByTestId("login-2fa-totp-manual-key").textContent).toContain("JBSW Y3DP");

    fireEvent.change(screen.getByTestId("login-2fa-code-input"), { target: { value: "654321" } });
    fireEvent.click(screen.getByTestId("login-2fa-submit-btn"));
    await waitFor(() => {
      expect(useAuthSessionStore.getState().isAuthenticated).toBe(true);
    });
    unmount();

    resetAuthSessionStore();
    render(
      <I18nProvider initialLocale="fr">
        <LoginScreenView />
      </I18nProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("login-local-email")).toBeDefined();
    });
    fireEvent.change(screen.getByTestId("login-local-email"), { target: { value: "admin@orcia.fr" } });
    fireEvent.change(screen.getByTestId("login-local-password"), { target: { value: "SecretPassword123!" } });
    fireEvent.click(screen.getByTestId("login-local-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("login-2fa-panel")).toBeDefined();
    });
    expect(screen.queryByTestId("login-2fa-totp-enroll-box")).toBeNull();
  });

  it("configures SMTP_MAIL in Connecteurs + saves Authentification policy (EMAIL_OTP & SSO) and survives F5 unmount/remount", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.fr", displayName: "Admin ORCIA" });
    useAuthSessionStore.getState().setAuthSession({
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
      email: "admin@orcia.fr",
    });

    const firstRender = await renderSettingsAtTab("/settings?tab=connectors");
    expect(screen.getByTestId("settings-tab-authentication").textContent).toBe("Authentification");
    expect(screen.getByTestId("settings-tab-connectors").textContent).toBe("Connecteurs");
    expect(document.body.textContent ?? "").not.toContain("Connecteurs & SSO");

    fireEvent.click(screen.getByTestId("settings-tab-connectors"));
    await screen.findByTestId("connector-kind-select");
    fireEvent.change(screen.getByTestId("connector-kind-select"), { target: { value: "SMTP_MAIL" } });
    fireEvent.change(screen.getByTestId("connector-name-input"), { target: { value: "SMTP Interne" } });
    fireEvent.change(screen.getByTestId("connector-base-url-input"), {
      target: { value: "smtp://mail.internal:587" },
    });
    fireEvent.change(screen.getByTestId("connector-auth-mode-select"), {
      target: { value: "SERVICE_SECRET" },
    });
    fireEvent.click(screen.getByTestId("register-connector-submit-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("connectors-success-banner")).toBeDefined();
    });
    firstRender.unmount();

    const authRender = await renderSettingsAtTab("/settings?tab=authentication");
    fireEvent.click(screen.getByTestId("settings-tab-authentication"));
    await waitFor(() => {
      expect(screen.getByTestId("two-factor-mode-option-EMAIL_OTP")).toBeDefined();
    });
    fireEvent.click(screen.getByTestId("two-factor-mode-option-EMAIL_OTP"));
    await waitFor(() => {
      expect(screen.getByTestId("auth-smtp-status-badge").textContent).toContain("SMTP Interne");
    });
    fireEvent.click(screen.getByTestId("auth-save-settings-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("auth-save-feedback").textContent).toContain("enregistrée");
    });
    authRender.unmount();

    const f5Local = await renderSettingsAtTab("/settings?tab=authentication");
    fireEvent.click(screen.getByTestId("settings-tab-authentication"));
    await waitFor(() => {
      expect(
        screen.getByTestId("two-factor-mode-option-EMAIL_OTP").getAttribute("aria-checked"),
      ).toBe("true");
    });
    fireEvent.click(screen.getByTestId("auth-mode-option-SSO"));
    fireEvent.change(screen.getByTestId("auth-oidc-issuer-input"), {
      target: { value: "https://idp.entreprise.com/realms/orcia" },
    });
    fireEvent.change(screen.getByTestId("auth-oidc-client-id-input"), {
      target: { value: "orcia-web-prod" },
    });
    fireEvent.change(screen.getByTestId("auth-oidc-redirect-uri-input"), {
      target: { value: "https://orcia.entreprise.com/login" },
    });
    fireEvent.click(screen.getByTestId("auth-test-oidc-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("auth-oidc-discovery-result").textContent).toContain("validée");
    });
    fireEvent.click(screen.getByTestId("auth-save-settings-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("auth-save-feedback").textContent).toContain("enregistrée");
    });
    f5Local.unmount();

    await renderSettingsAtTab("/settings?tab=authentication");
    fireEvent.click(screen.getByTestId("settings-tab-authentication"));
    await waitFor(() => {
      expect(screen.getByTestId("auth-mode-option-SSO").getAttribute("aria-checked")).toBe("true");
    });
    expect((screen.getByTestId("auth-oidc-client-id-input") as HTMLInputElement).value).toBe(
      "orcia-web-prod",
    );
  });

  it("hides Configuration sidebar menu for non-admin/non-SecOps roles, ignores activeHat for RBAC, and wipes cache on boot_epoch rotation", async () => {
    for (const nonAdmin of ["BU_LEAD", "TEAM_LEAD", "CONTRIBUTOR", "OBSERVER"] as const) {
      useAuthSessionStore.getState().setAuthSession({
        roles: [nonAdmin],
        activeHat: "PLATFORM_ADMIN",
      });

      const { unmount } = render(
        <I18nProvider initialLocale="fr">
          <ShellContainer>
            <CockpitFeaturePanel />
          </ShellContainer>
        </I18nProvider>,
      );
      expect(screen.queryByTestId("eight-menu-item-configuration")).toBeNull();
      unmount();
    }

    // Boot epoch rotation on pnpm db:reset wipes stale browser session & setup cache
    seedVitestPlatformSetupState({}, { email: "admin@orcia.fr", displayName: "Admin ORCIA" });
    writeStorageItem("orcia.auth.session.v1", "admin@orcia.fr");
    writeStorageItem(
      "orcia.platform_admin.v1",
      JSON.stringify({ email: "admin@orcia.fr", displayName: "Admin ORCIA", role: "PLATFORM_ADMIN" }),
    );
    const firstBoot = render(
      <I18nProvider initialLocale="fr">
        <LoginScreenView />
      </I18nProvider>,
    );
    await waitFor(() => {
      expect(readStorageItem("orcia.boot_epoch.v1")).toBe("vitest-boot-epoch-1");
    });
    firstBoot.unmount();

    rotateVitestBootEpoch("vitest-boot-epoch-reset-2");
    render(
      <I18nProvider initialLocale="fr">
        <LoginScreenView />
      </I18nProvider>,
    );
    await waitFor(() => {
      expect(readStorageItem("orcia.boot_epoch.v1")).toBe(
        "vitest-boot-epoch-reset-2",
      );
    });
    expect(readStorageItem("orcia.auth.session.v1")).toBeNull();
    expect(readStorageItem("orcia.platform_admin.v1")).toBeNull();
  });
});
