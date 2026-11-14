import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import { EnterpriseConnectorsSettingsSection } from "../features/admin/connectors/EnterpriseConnectorsSettingsSection";
import { WorkspaceSourcesRagTab } from "../features/workspaces/WorkspaceSourcesRagTab";
import { ShellHeaderAccountControl } from "../components/ShellHeaderAccountControl";
import { frDictionary } from "../i18n/locales/fr";
import { useAuthSessionStore } from "../stores/authSessionStore";
import {
  seedVitestPlatformSetupState,
  resetVitestApiBackend,
} from "./vitest.setup";
import { seedVitestConnectorsInitialData } from "./vitestConnectorsMockHandlers";

afterEach(() => {
  cleanup();
  clearPlatformSetupStorage();
  resetVitestApiBackend();
});

describe("Story 17.4 — Connecteurs Socle, Mon Compte Passthrough & RAG Référent", () => {
  it("manages Enterprise Connectors at platform level without workspace pollution (Write-Only secrets & danger buttons)", async () => {
    seedVitestPlatformSetupState(
      { org_units: [], rbac_grants: [], llm_tiers: [], workspaces: [{ id: "ws-forbidden-pollute", name: "Pollution Guard WS" }] },
      { email: "admin@orcia.fr", displayName: "Admin Orcia" },
    );

    const { unmount } = render(
      <EnterpriseConnectorsSettingsSection
        isFr={true}
        copy={frDictionary.settingsHub}
        openHelpSection={() => {}}
        canMutate={true}
      />,
    );

    // 1. Initial state rendered
    await waitFor(() => {
      expect(screen.getByTestId("settings-connectors-section")).toBeDefined();
    });

    // 2. Add Jira connector with admin secret
    fireEvent.change(screen.getByTestId("connector-name-input"), {
      target: { value: "Jira Entreprise" },
    });
    fireEvent.change(screen.getByTestId("connector-base-url-input"), {
      target: { value: "https://jira.corp.internal/api" },
    });
    fireEvent.change(screen.getByTestId("connector-admin-secret-input"), {
      target: { value: "SECRET_ADMIN_CANARY_VALUE" },
    });

    fireEvent.click(screen.getByTestId("register-connector-submit-btn"));

    // 3. Connector is rendered with Write-Only fingerprint and danger delete button
    await waitFor(() => {
      expect(screen.getByText("Jira Entreprise")).toBeDefined();
    });

    const card = screen.getByTestId("enterprise-connector-row-conn-1");
    expect(card).toBeDefined();
    expect(card.textContent).toContain("sha256:conn1");
    expect(card.textContent).not.toContain("SECRET_ADMIN_CANARY_VALUE");

    const deleteBtn = screen.getByTestId("delete-connector-btn-conn-1");
    expect(deleteBtn.className).toContain("orcia-ds-btn-danger");

    // 4. Zero workspace pollution: workspaces in setup state is untouched
    const rawSaved =
      typeof window.localStorage?.getItem === "function"
        ? window.localStorage.getItem("orcia_platform_setup_state")
        : null;
    if (rawSaved) {
      const parsed = JSON.parse(rawSaved);
      expect(parsed.workspaces[0].id).toBe("ws-forbidden-pollute");
      expect(parsed.workspaces[0]).not.toHaveProperty("connector_id");
    }

    unmount();
  });

  it("handles Mon Compte profile, FinOps team attachments, and personal token F5 survival", async () => {
    seedVitestPlatformSetupState(
      {
        org_units: [
          { id: "ou-bu-1", name: "Direction Tech", slug: "tech", kind: "BU", billing_enabled: true },
          { id: "ou-team-1", name: "Équipe Plateforme", slug: "plateforme", kind: "TEAM", billing_enabled: false },
        ],
        rbac_grants: [],
        llm_tiers: [],
        workspaces: [],
      },
      { email: "marie.curie@orcia.fr", displayName: "Marie Curie" },
    );

    seedVitestConnectorsInitialData({
      connectors: [
        {
          id: "conn-jira",
          connector_kind: "JIRA",
          name: "Jira Central",
          base_url: "https://jira.corp.internal",
          auth_mode: "PERSONAL_ACCESS_TOKEN",
          enabled: true,
          admin_secret_status: { configured: true, fingerprint: "sha256:j", updated_at_iso: null },
          created_at_iso: "2026-11-14T10:00:00Z",
          updated_at_iso: "2026-11-14T10:00:00Z",
        },
      ],
    });

    useAuthSessionStore.getState().setAuthSession({
      email: "marie.curie@orcia.fr",
      displayName: "Marie Curie",
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });

    // Mount header control
    const { unmount } = render(
      <ShellHeaderAccountControl
        userDisplayName="Marie Curie"
        userEmail="marie.curie@orcia.fr"
        userRole="PLATFORM_ADMIN"
        activeHat="PLATFORM_ADMIN"
        locale="fr"
        labels={frDictionary.userAccountAndSettings}
      />,
    );

    // Open User Settings Modal at PASSTHROUGH_SOURCES tab
    useAuthSessionStore.getState().openUserSettingsModalAtTab("PASSTHROUGH_SOURCES");

    await waitFor(() => {
      expect(screen.getByTestId("user-settings-panel-PASSTHROUGH_SOURCES")).toBeDefined();
    });

    // Check connector is listed as disconnected
    expect(screen.getByText("Jira Central")).toBeDefined();

    // Click configure button to expand edit form
    fireEvent.click(screen.getByTestId("passthrough-configure-btn-conn-jira"));

    // Fill login and personal token
    const loginInput = screen.getByTestId("passthrough-login-input-conn-jira");
    const tokenInput = screen.getByTestId("passthrough-token-input-conn-jira");
    fireEvent.change(loginInput, { target: { value: "mcurie" } });
    fireEvent.change(tokenInput, { target: { value: "PAT_SECRET_USER_TOKEN" } });

    fireEvent.click(screen.getByTestId("passthrough-save-btn-conn-jira"));

    // Verify token is configured
    await waitFor(() => {
      const badge = screen.getByTestId("passthrough-connected-badge-conn-jira");
      expect(badge.textContent).toContain("sha256:usr-conn-jira");
      expect(document.body.textContent).not.toContain("PAT_SECRET_USER_TOKEN");
    });

    // F5 Survival: unmount and remount
    unmount();

    render(
      <ShellHeaderAccountControl
        userDisplayName="Marie Curie"
        userEmail="marie.curie@orcia.fr"
        userRole="PLATFORM_ADMIN"
        activeHat="PLATFORM_ADMIN"
        locale="fr"
        labels={frDictionary.userAccountAndSettings}
      />,
    );

    useAuthSessionStore.getState().openUserSettingsModalAtTab("PASSTHROUGH_SOURCES");

    await waitFor(() => {
      const badge = screen.getByTestId("passthrough-connected-badge-conn-jira");
      expect(badge.textContent).toContain("sha256:usr-conn-jira");
    });
  });

  it("renders Workspace Sources RAG tab with cold-start banner, identity selector, and referent pause & renewal", async () => {
    seedVitestConnectorsInitialData({
      connectors: [
        {
          id: "conn-confluence",
          connector_kind: "CONFLUENCE",
          name: "Confluence Documentation",
          base_url: "https://wiki.corp.internal",
          auth_mode: "PERSONAL_ACCESS_TOKEN",
          enabled: true,
          admin_secret_status: { configured: true, fingerprint: "sha256:c", updated_at_iso: null },
          created_at_iso: "2026-11-14T10:00:00Z",
          updated_at_iso: "2026-11-14T10:00:00Z",
        },
      ],
      datasources: [
        {
          id: "ds-ref-1",
          workspace_id: "ws-1",
          alias: "wiki-product",
          scheme: "confluence",
          uri: "https://wiki.corp.internal/product",
          connector_id: "conn-confluence",
          sync_identity_mode: "TEAM_REFERENT_USER",
          service_account_id: null,
          referent_user_id: "absent.user@orcia.fr",
          created_at_iso: "2026-11-14T10:00:00Z",
        },
      ],
    });

    render(
      <WorkspaceSourcesRagTab
        isFr={true}
        activeWorkspace={{
          workspaceId: "ws-1",
          name: "Espace Produit",
          slug: "espace-produit",
          ownerOrgUnitId: "ou-1",
          visibilityMode: "STANDARD",
          finopsCostUsd: 0,
        } as any}
      />,
    );

    // 1. Soft cold-start banner is present
    await waitFor(() => {
      expect(screen.getByTestId("rag-passthrough-cold-start-banner")).toBeDefined();
    });

    // 2. Datasource is PAUSED because absent.user has no token
    await waitFor(() => {
      const badge = screen.getByTestId("rag-sync-paused-badge-ds-ref-1");
      expect(badge.textContent?.toLowerCase()).toContain("en pause");
      expect(badge.textContent?.toLowerCase()).toContain("référent");
    });

    // 3. Quick referent renewal action button is present
    const renewBtn = screen.getByTestId("renew-referent-btn-ds-ref-1");
    expect(renewBtn).toBeDefined();

    // 4. Click renew to expand inline form
    fireEvent.click(renewBtn);
    const renewInput = screen.getByTestId("renew-referent-input-ds-ref-1");
    expect(renewInput).toBeDefined();

    // 5. 1-click cold-start banner opens Mon Compte
    const coldstartBtn = screen.getByTestId("open-my-account-passthrough-cta");
    fireEvent.click(coldstartBtn);
    expect(useAuthSessionStore.getState().userSettingsModalOpen).toBe(true);
    expect(useAuthSessionStore.getState().userSettingsModalInitialTab).toBe("PASSTHROUGH_SOURCES");
  });
});
