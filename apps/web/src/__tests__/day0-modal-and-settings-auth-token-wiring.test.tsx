import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FirstBootAdminSetupModal } from "../components/FirstBootAdminSetupModal";
import { LoginScreenView } from "../components/LoginScreenView";
import { PlatformSetupProvider } from "../components/platformSetupStore";
import { ShellContainer } from "../components/ShellContainer";
import { CockpitFeaturePanel } from "../features/cockpit";
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
  it("Point 1 — FirstBootAdminSetupModal is rendered via OrciaDialog Portal directly under document.body", () => {
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
    expect(modal.parentElement).toBe(document.body);
    expect(modal.getAttribute("role")).toBe("dialog");
    expect(modal.getAttribute("aria-modal")).toBe("true");
    expect(modal.className).toContain("orcia-ds-dialog-content");
    expect(modal.querySelector(".orcia-ds-dialog-body")).not.toBeNull();
    expect(document.activeElement).toBe(screen.getByTestId("first-boot-admin-name-input"));
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

  it("Story 23.4 — FirstBootAdminSetupModal removes duplicate cancel button and dot placeholder, toggles password eye visibility, and enforces confirmation match", () => {
    const onCreateAdmin = vi.fn();
    render(
      <FirstBootAdminSetupModal
        isOpen={true}
        isFr={true}
        onClose={() => {}}
        onCreatePlatformAdmin={onCreateAdmin}
      />,
    );

    expect(screen.queryByTestId("first-boot-admin-cancel-btn")).toBeNull();
    expect(screen.queryByTestId("first-boot-admin-setup-modal-close-btn")).toBeNull();
    const mandatoryBadge = screen.getByTestId("first-boot-admin-mandatory-badge");
    expect(mandatoryBadge.textContent).toContain("Étape obligatoire · Non ignorable");

    const pwInput = screen.getByTestId("first-boot-admin-password-input") as HTMLInputElement;
    const confirmInput = screen.getByTestId(
      "first-boot-admin-password-confirm-input",
    ) as HTMLInputElement;
    expect(pwInput.placeholder).toBe("");
    expect(confirmInput.placeholder).toBe("");
    expect(pwInput.className).toContain("orcia-masked-secret-input");

    // Toggle eye visibility button
    const eyeToggle = screen.getByTestId("first-boot-admin-password-input-toggle-visibility");
    expect(eyeToggle.getAttribute("aria-pressed")).toBe("false");
    fireEvent.click(eyeToggle);
    expect(eyeToggle.getAttribute("aria-pressed")).toBe("true");
    expect(pwInput.className).not.toContain("orcia-masked-secret-input");

    // Fill fields with mismatched confirmation -> submit disabled and mismatch alert shown
    fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), {
      target: { value: "Alice Admin" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), {
      target: { value: "alice@orcia.fr" },
    });
    fireEvent.change(pwInput, { target: { value: "StrongPass!2026" } });
    fireEvent.change(confirmInput, { target: { value: "OtherPass!2026" } });

    expect(screen.getByTestId("first-boot-admin-password-mismatch")).toBeDefined();
    expect((screen.getByTestId("first-boot-admin-submit-btn") as HTMLButtonElement).disabled).toBe(
      true,
    );

    // Fix confirmation -> submit enabled
    fireEvent.change(confirmInput, { target: { value: "StrongPass!2026" } });
    expect(screen.queryByTestId("first-boot-admin-password-mismatch")).toBeNull();
    expect((screen.getByTestId("first-boot-admin-submit-btn") as HTMLButtonElement).disabled).toBe(
      false,
    );
    fireEvent.click(screen.getByTestId("first-boot-admin-submit-btn"));
    expect(onCreateAdmin).toHaveBeenCalledTimes(1);
  });

  it("Story 23.4 — Day-0 unauthenticated shell renders zero AP avatar, zero Notifications 4, single Accostage 0/6 pill, and zero pre-auth protected calls", async () => {
    seedVitestPlatformSetupState({}, null);
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: false,
      isHydrating: false,
      accessToken: null,
      roles: [],
      email: null,
      displayName: null,
    });

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <CockpitFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("first-boot-admin-setup-modal")).toBeDefined();
    });

    // Zero ghost AP avatar / popover, zero Notifications 4 badge, zero duplicate /5 badge
    expect(screen.queryByTestId("sidebar-account-initials-avatar")).toBeNull();
    expect(screen.queryByTestId("sidebar-open-my-account-btn")).toBeNull();
    expect(screen.queryByText("AP")).toBeNull();
    expect(screen.queryByTestId("onboarding-progress-badge")).toBeNull();
    expect(screen.queryByText(/\/5\b/)).toBeNull();
    expect(screen.getAllByTestId("accostage-progress-pill")).toHaveLength(1);
    expect(screen.getByTestId("accostage-progress-pill").textContent).toBe("Accostage 0/6");

    const notifToggle = screen.getByTestId("topbar-notifications-toggle");
    expect(notifToggle.textContent).not.toContain("4");
    expect(screen.queryByText(/Notifications\s*4/i)).toBeNull();
    expect(screen.queryByTestId("topbar-notifications-badge")).toBeNull();

    // All navigable entries outside Cockpit (including spaces & help) are uniformly disabled at Day 0
    for (const key of ["assistant", "processes", "agents", "spaces", "finops", "help"] as const) {
      const btn = screen.getByTestId(`eight-menu-item-${key}`) as HTMLButtonElement;
      expect(btn.disabled).toBe(true);
      expect(btn.getAttribute("data-disabled-reason")).toBeTruthy();
    }

    // '[' shortcut is ignored while aria-modal dialog is open
    const sidebar = screen.getByTestId("four-zone-sidebar");
    expect(sidebar.getAttribute("data-rail-collapsed")).toBe("false");
    fireEvent.keyDown(window, { key: "[" });
    expect(sidebar.getAttribute("data-rail-collapsed")).toBe("false");

    // Closing Day-0 modal via Escape offers reopen button (no dead-end)
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => {
      expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
    });
    const reopenBtn = screen.getByTestId("reopen-first-boot-admin-modal-btn");
    fireEvent.click(reopenBtn);
    expect(screen.getByTestId("first-boot-admin-setup-modal")).toBeDefined();

    // Zero protected pre-auth API calls (no /org-units, /iam, /platform-setup-state, /preferences, /orchestration/state)
    const calls = getRecordedVitestApiCalls();
    const forbiddenPaths = [
      "/api/v1/org-units",
      "/api/v1/iam",
      "/api/v1/bootstrap/platform-setup-state",
      "/api/v1/users/me/preferences",
      "/api/v1/orchestration/state",
    ];
    expect(calls.filter((c) => forbiddenPaths.some((p) => c.path.includes(p)))).toEqual([]);
  });
});
