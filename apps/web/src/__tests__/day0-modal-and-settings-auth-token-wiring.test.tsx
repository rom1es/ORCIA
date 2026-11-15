import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FirstBootAdminSetupModal } from "../components/FirstBootAdminSetupModal";
import { LoginScreenView } from "../components/LoginScreenView";
import { PlatformSetupProvider } from "../components/platformSetupStore";
import { EnterpriseConnectorsSettingsSection } from "../features/admin/connectors/EnterpriseConnectorsSettingsSection";
import { SettingsAuthenticationSection } from "../features/admin/auth/SettingsAuthenticationSection";
import { SettingsOrganizationUnitsBlock } from "../routes/SettingsOrganizationUnitsBlock";
import { I18nProvider, useI18n } from "../i18n";
import {
  resetAuthSessionStore,
  useAuthSessionStore,
} from "../stores/authSessionStore";
import { getRecordedVitestApiCalls, seedVitestPlatformSetupState } from "./vitest.setup";

afterEach(() => {
  cleanup();
  resetAuthSessionStore();
  vi.restoreAllMocks();
});

function OrganizationUnitsWrapper({ canMutate = true }: { canMutate?: boolean }) {
  const { dictionary } = useI18n();
  return (
    <SettingsOrganizationUnitsBlock
      isFr={true}
      canMutate={canMutate}
      orgUnits={[]}
      openHelpSection={() => {}}
      syncOrgUnitsFromServer={() => {}}
    />
  );
}

function ConnectorsWrapper({ canMutate = true }: { canMutate?: boolean }) {
  const { dictionary } = useI18n();
  return (
    <EnterpriseConnectorsSettingsSection
      isFr={true}
      copy={dictionary.settingsHub}
      openHelpSection={() => {}}
      canMutate={canMutate}
    />
  );
}

describe("Day-0 Modal Constraint, Login Screen Day-0 Isolation & Settings Bearer Token F5 Wiring", () => {
  it("Point 1 — FirstBootAdminSetupModal is strictly bounded with max-w-lg and 520px maxWidth Direction C style", () => {
    const onCreateAdmin = vi.fn();
    render(
      <FirstBootAdminSetupModal
        isOpen={true}
        isFr={true}
        onClose={() => {}}
        onCreatePlatformAdmin={onCreateAdmin}
      />,
    );

    const modal = screen.getByTestId("first-boot-admin-setup-modal");
    expect(modal).toBeDefined();

    // The inner modal card
    const modalCard = modal.firstElementChild as HTMLElement;
    expect(modalCard).toBeDefined();
    expect(modalCard.className).toContain("max-w-lg");
    expect(modalCard.style.maxWidth).toBe("min(520px, calc(100vw - 2rem))");
    expect(modalCard.style.backgroundColor).toBe("var(--color-surface)");
    expect(modalCard.style.borderColor).toBe("var(--color-border-strong)");
  });

  it("Point 2 — LoginScreenView on Day-0 (platformAdmin === null) renders discrete neutral state without duplicate login form", async () => {
    // Seed platform setup with 0 admin (Day-0 unconfigured)
    seedVitestPlatformSetupState({}, null);

    render(
      <I18nProvider initialLocale="fr">
        <PlatformSetupProvider>
          <LoginScreenView />
        </PlatformSetupProvider>
      </I18nProvider>,
    );

    // Ensure the root container is present
    const container = screen.getByTestId("login-page-container");
    expect(container).toBeDefined();

    // Verify BiModeLoginView form is suppressed in background of Day-0 modal
    expect(screen.queryByTestId("bi-mode-login-view")).toBeNull();
    expect(screen.queryByTestId("login-local-form")).toBeNull();
    expect(screen.getByText(/Initialisation de la plateforme en cours/i)).toBeDefined();
  });

  it("Point 3 — Organization, Authentication and Connectors sections send Bearer token and survive F5 unmount/remount without ERR_AUTH_REQUIRED", async () => {
    seedVitestPlatformSetupState(
      {},
      { email: "romain.esnault@orcia.internal", displayName: "Romain Esnault" },
    );

    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      isHydrating: false,
      accessToken: "orcia-test-admin-jwt-token-777",
      email: "romain.esnault@orcia.internal",
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });

    // 1. SettingsOrganizationUnitsBlock
    const orgRender = render(
      <I18nProvider initialLocale="fr">
        <OrganizationUnitsWrapper />
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("settings-organization-section")).toBeDefined();
    });

    // Verify org-units API call received Bearer token
    await waitFor(() => {
      const calls = getRecordedVitestApiCalls();
      const orgCall = calls.find((c) => c.path.includes("/org-units"));
      expect(orgCall).toBeDefined();
      expect(orgCall?.headers?.authorization).toBe(
        "Bearer orcia-test-admin-jwt-token-777",
      );
    });

    // F5 unmount & remount
    orgRender.unmount();
    const orgRemount = render(
      <I18nProvider initialLocale="fr">
        <OrganizationUnitsWrapper />
      </I18nProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("settings-organization-section")).toBeDefined();
      expect(screen.queryByTestId("org-unit-delete-feedback")).toBeNull();
    });
    orgRemount.unmount();

    // 2. SettingsAuthenticationSection
    const authRender = render(
      <I18nProvider initialLocale="fr">
        <SettingsAuthenticationSection canMutate={true} onNavigateToConnectors={() => {}} />
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("settings-authentication-section")).toBeDefined();
    });

    await waitFor(() => {
      const calls = getRecordedVitestApiCalls();
      const authCall = calls.find((c) => c.path.includes("/settings/authentication"));
      expect(authCall).toBeDefined();
      expect(authCall?.headers?.authorization).toBe(
        "Bearer orcia-test-admin-jwt-token-777",
      );
    });

    // F5 unmount & remount
    authRender.unmount();
    const authRemount = render(
      <I18nProvider initialLocale="fr">
        <SettingsAuthenticationSection canMutate={true} onNavigateToConnectors={() => {}} />
      </I18nProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("settings-authentication-section")).toBeDefined();
      expect(screen.queryByTestId("auth-save-feedback")).toBeNull();
    });
    authRemount.unmount();

    // 3. EnterpriseConnectorsSettingsSection
    const connRender = render(
      <I18nProvider initialLocale="fr">
        <ConnectorsWrapper />
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("settings-connectors-section")).toBeDefined();
    });

    await waitFor(() => {
      const calls = getRecordedVitestApiCalls();
      const connCall = calls.find((c) => c.path.includes("/settings/connectors"));
      expect(connCall).toBeDefined();
      expect(connCall?.headers?.authorization).toBe(
        "Bearer orcia-test-admin-jwt-token-777",
      );
    });

    // F5 unmount & remount
    connRender.unmount();
    const connRemount = render(
      <I18nProvider initialLocale="fr">
        <ConnectorsWrapper />
      </I18nProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("settings-connectors-section")).toBeDefined();
      expect(screen.queryByTestId("connectors-error-banner")).toBeNull();
    });
    connRemount.unmount();
  });
});
