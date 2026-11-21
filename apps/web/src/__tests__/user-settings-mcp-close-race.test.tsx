import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { ShellUserSettingsModal } from "../components/ShellUserSettingsModal";
import { I18nProvider } from "../i18n";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

afterEach(() => {
  cleanup();
  resetAuthSessionStore();
  resetVitestApiBackend();
});

describe("UserSettingsModalDialog MCP token close race guard", () => {
  it("closes cleanly when close button is clicked right as MCP plaintext banner appears", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.test", displayName: "Admin Test" });
    useAuthSessionStore.getState().loginWithSession({
      email: "admin@orcia.test",
      display_name: "Admin Test",
      roles: ["PLATFORM_ADMIN"],
      access_token: "mock-vitest-access-token",
      mustChangePassword: false,
    });
    useAuthSessionStore.getState().openUserSettingsModalAtTab("IDE_MCP_KEYS");

    render(
      <I18nProvider initialLocale="fr">
        <ShellUserSettingsModal
          userEmail="admin@orcia.test"
          userRole="PLATFORM_ADMIN"
          locale="fr"
          onLocaleChange={() => undefined}
          onNavigate={() => undefined}
        />
      </I18nProvider>,
    );

    expect(screen.getByTestId("user-settings-modal")).toBeDefined();
    fireEvent.change(screen.getByTestId("mcp-token-label-input"), {
      target: { value: "VSCode Race Test" },
    });
    fireEvent.change(screen.getByTestId("mcp-target-slug-input"), {
      target: { value: "default" },
    });
    fireEvent.click(screen.getByTestId("mcp-generate-token-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("mcp-issued-plaintext-value").textContent).toContain("pat_mcp_");
    });

    fireEvent.click(screen.getByTestId("user-settings-modal-close-btn"));

    await waitFor(() => {
      expect(screen.queryByTestId("user-settings-modal")).toBeNull();
      expect(screen.queryByTestId("user-settings-modal-unsaved-changes-alert")).toBeNull();
    });
  });
});
