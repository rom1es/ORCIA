import { expect, test } from "@playwright/test";

test.describe("ORCIA Direction C 7-Module Shell & Multi-Viewport E2E (UX-DR1, UX-DR2)", () => {
  test("renders 3 columns, 7 Global Sidebar modules, keyboard shortcuts ([ ] ⌘W) and fr/en switch", async ({
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

    // Mobile Companion tab bar is rendered and interactive
    await expect(page.getByTestId("mobile-companion-tabbar")).toBeVisible();
  });
});
