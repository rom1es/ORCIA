import { expect, test } from "@playwright/test";

test.describe("ORCIA Direction C 7-Module Shell & Multi-Viewport E2E (UX-DR1, UX-DR2, UX-DR8)", () => {
  test("renders 3 columns, starts empty by default, and supports ?fixture=test for automated E2E scenarios across 8 feature entries", async ({
    page,
  }) => {
    // 1. Default system starts empty of sample data and filters menu entries by scope
    await page.goto("/cockpit");
    await expect(page.getByTestId("sidebar-nav-item-cockpit")).toBeVisible();
    await expect(page.getByTestId("sidebar-nav-item-catalog")).toBeVisible();
    await expect(page.getByTestId("sidebar-nav-item-admin")).toBeVisible();
    await expect(page.getByTestId("sidebar-nav-item-bootstrap")).toBeVisible();
    await expect(page.getByTestId("sidebar-nav-item-inbox")).toHaveCount(0);

    // 2. Automated test dataset mode (?fixture=test)
    await page.goto("/cockpit?fixture=test");

    const sidebar = page.getByTestId("global-sidebar");
    const canvas = page.getByTestId("app-shell-canvas");
    const dock = page.getByTestId("assistant-dock");

    await expect(sidebar).toBeVisible();
    await expect(canvas).toBeVisible();
    await expect(dock).toBeVisible();
    await expect(page.getByTestId("topbar-search-input")).toBeVisible();

    // Verify all 8 feature entries in French by default (without number prefixes)
    await expect(page.getByTestId("sidebar-nav-item-cockpit")).toContainText("Cockpit & Chat");
    await expect(page.getByTestId("sidebar-nav-item-inbox")).toContainText("Boîte & Mes Runs");
    await expect(page.getByTestId("sidebar-nav-item-catalog")).toContainText("Catalogue Fédéré");
    await expect(page.getByTestId("sidebar-nav-item-ontology")).toContainText("Ontologie & KB");
    await expect(page.getByTestId("sidebar-nav-item-gates")).toContainText(
      "Gates & Habilitations",
    );
    await expect(page.getByTestId("sidebar-nav-item-finops")).toContainText("FinOps & Audit");
    await expect(page.getByTestId("sidebar-nav-item-admin")).toContainText(
      "Administration & Pilotage des Workspaces",
    );
    await expect(page.getByTestId("sidebar-nav-item-bootstrap")).toContainText(
      "Initialisation & Onboarding",
    );

    // Keyboard shortcut '[' collapses sidebar
    await page.keyboard.press("[");
    await expect(sidebar).toHaveAttribute("data-collapsed", "true");
    await page.keyboard.press("[");
    await expect(sidebar).toHaveAttribute("data-collapsed", "false");

    // Keyboard shortcut ']' collapses Assistant Dock
    await page.keyboard.press("]");
    await expect(dock).toHaveAttribute("data-collapsed", "true");

    // Switch locale to English
    await page.getByTestId("locale-switcher-button").click();
    await expect(page.getByTestId("locale-switcher-button")).toContainText("(EN)");

    // Story 1.3: Navigate to Catalog module -> Verify CatalogExplorerPanel
    await page.getByTestId("sidebar-nav-item-catalog").click();
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

    // Story 1.2 & 1.5: Navigate to Admin & Bootstrap dedicated menu entries
    await page.getByTestId("sidebar-nav-item-admin").click();
    await expect(page.getByTestId("workspace-topology-panel")).toBeVisible();

    await page.getByTestId("sidebar-nav-item-bootstrap").click();
    await expect(page.getByTestId("bootstrap-onboarding-panel")).toBeVisible();
    const anchorCard = page.getByTestId("human-led-anchor-card");
    await expect(anchorCard).toBeVisible();
    await expect(anchorCard).toHaveAttribute("data-human-authored-required", "true");

    await page.getByTestId("simulate-single-llm-family-btn").click();
    await expect(page.getByTestId("bootstrap-feedback-banner")).toContainText(
      "ERR_MODEL_ORTHOGONALITY_VIOLATION",
    );
    await page.getByTestId("simulate-dual-llm-family-btn").click();

    await page.getByTestId("execute-init-workspace-btn").click();
    await expect(page.getByTestId("bootstrap-feedback-banner")).toContainText("HTTP 200 OK");

    await page.getByTestId("execute-init-datasource-btn").click();
    await expect(page.getByTestId("bootstrap-feedback-banner")).toContainText("HTTP 200 OK");

    await page.getByTestId("execute-init-user-btn").click();
    await expect(page.getByTestId("bootstrap-feedback-banner")).toContainText("AES-256-GCM");

    // Story 1.4: Navigate to Gates & Permissions -> Verify Permission Broker auto-opens Dock on PERMISSION_DENIED_STEP
    await page.getByTestId("sidebar-nav-item-gates").click();
    await page.getByTestId("simulate-permission-denied-confluence-btn").click();
    await expect(dock).toHaveAttribute("data-collapsed", "false");
    await expect(page.getByTestId("permission-broker-card")).toBeVisible();
    await expect(page.getByTestId("permission-broker-required-role")).toHaveText(
      "CONFLUENCE_PAY_ADR_READER",
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
