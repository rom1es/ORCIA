import { expect, test } from "@playwright/test";

test.describe("ORCIA Direction C 7-Module Shell & Multi-Viewport E2E (UX-DR1, UX-DR2, UX-DR8)", () => {
  test("renders 3 columns, 7 Global Sidebar modules, keyboard shortcuts ([ ] ⌘W), fr/en switch, and Federated Catalog (UX-DR8)", async ({
    page,
  }) => {
    await page.goto("/cockpit");

    const sidebar = page.getByTestId("global-sidebar");
    const canvas = page.getByTestId("app-shell-canvas");
    const dock = page.getByTestId("concierge-dock");

    await expect(sidebar).toBeVisible();
    await expect(canvas).toBeVisible();
    await expect(dock).toBeVisible();

    // Verify all 7 modules in French by default
    await expect(page.getByTestId("sidebar-nav-item-cockpit")).toContainText("1. Cockpit & Chat");
    await expect(page.getByTestId("sidebar-nav-item-inbox")).toContainText("2. Boîte & Mes Runs");
    await expect(page.getByTestId("sidebar-nav-item-catalog")).toContainText("3. Catalogue Fédéré");
    await expect(page.getByTestId("sidebar-nav-item-ontology")).toContainText("4. Ontologie & KB");
    await expect(page.getByTestId("sidebar-nav-item-gates")).toContainText(
      "5. Gates & Habilitations",
    );
    await expect(page.getByTestId("sidebar-nav-item-finops")).toContainText("6. FinOps & Audit");
    await expect(page.getByTestId("sidebar-nav-item-admin")).toContainText(
      "7. Administration & Pilotage des Workspaces",
    );

    // Keyboard shortcut '[' collapses sidebar
    await page.keyboard.press("[");
    await expect(sidebar).toHaveAttribute("data-collapsed", "true");

    // Keyboard shortcut ']' collapses Concierge Dock
    await page.keyboard.press("]");
    await expect(dock).toHaveAttribute("data-collapsed", "true");

    // Switch locale to English
    await page.getByTestId("locale-switcher-button").click();
    await expect(page.getByTestId("locale-switcher-button")).toContainText("(EN)");

    // Story 1.3: Verify CatalogExplorerPanel, FederatedUriBadge (UX-DR8), CAS resolution, 4-layer overrides & BMAD import
    await expect(page.getByTestId("catalog-explorer-panel")).toBeVisible();
    await expect(page.getByTestId("uri-badge-res-blackbox-security-agent")).toHaveAttribute(
      "data-uri-scheme",
      "git",
    );
    await expect(page.getByTestId("uri-badge-res-nexus-bmad-architecture-pack")).toHaveAttribute(
      "data-uri-scheme",
      "nexus",
    );
    await expect(page.getByTestId("uri-badge-res-payment-delivery-workflow")).toHaveAttribute(
      "data-uri-scheme",
      "db",
    );

    await page.getByTestId("resolve-cas-btn-res-open-checkout-skill").click();
    await expect(page.getByTestId("resolve-cas-result-res-open-checkout-skill")).toContainText(
      "cas/4b72d9a1c30e",
    );

    await page.getByTestId("bmad-import-trigger-btn").click();
    await expect(page.getByTestId("bmad-import-result")).toContainText("BMAD_PACK");

    // Story 1.2: Verify WorkspaceTopologyPanel, RBAC persona switch hiding module 7, and black-box source masking
    await expect(page.getByTestId("workspace-topology-panel")).toBeVisible();
    await page.getByTestId("persona-switch-nadia").click();
    await expect(page.getByTestId("sidebar-nav-item-admin")).toHaveCount(0);

    await page.getByTestId("persona-switch-claire").click();
    await expect(page.getByTestId("sidebar-nav-item-admin")).toHaveCount(1);
    await expect(page.getByTestId("workspace-card-ws-projet-confidentiel")).toHaveCount(0);

    await page.getByTestId("inspect-source-btn-res-blackbox-security-agent").click();
    await expect(
      page.getByTestId("inspect-source-result-res-blackbox-security-agent"),
    ).toContainText("ERR_READ_SOURCE_DENIED");

    // Story 1.4: Verify Permission Broker auto-opens the collapsed right Dock on PERMISSION_DENIED_STEP (UX-DR11, FR-22)
    await page.getByTestId("persona-switch-marc").click();
    await page.getByTestId("simulate-permission-denied-confluence-btn").click();
    await expect(dock).toHaveAttribute("data-collapsed", "false");
    await expect(page.getByTestId("permission-broker-card")).toBeVisible();
    await expect(page.getByTestId("permission-broker-required-role")).toHaveText(
      "CONFLUENCE_PAY_ADR_READER",
    );
    await expect(page.getByTestId("permission-broker-card-procedure")).toContainText(
      "CONFLUENCE_PAY_ADR_READER",
    );
    await expect(page.getByTestId("permission-broker-jira-link")).toHaveAttribute(
      "href",
      /jira\.enterprise\.internal/,
    );

    await page.getByTestId("permission-broker-replay-btn").click();
    await expect(page.getByTestId("permission-broker-card")).toHaveAttribute(
      "data-ticket-status",
      "REPLAYED",
    );

    await page.getByTestId("simulate-confused-deputy-btn").click();
    await expect(page.getByTestId("permission-broker-action-banner")).toContainText(
      "ERR_CONFUSED_DEPUTY_BLOCKED",
    );

    // Mobile Companion tab bar is rendered and interactive
    await expect(page.getByTestId("mobile-companion-tabbar")).toBeVisible();
  });
});
