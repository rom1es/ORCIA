/** @uj UJ-13, UJ-20 | @cap CAP-060, CAP-061 */
import { expect, test } from "./support/e2eCaptureFixture";
import { expectDbRowExists, queryDbRows } from "./support/dbAssertions";
import { createFirstAdminViaUi, E2E_ADMIN } from "./support/firstAdmin";
import { resetDay0 } from "./support/day0";
import {
  expectZeroVisibleErrorBanners,
  watchUnexpectedPageAndApiErrors,
} from "./support/apiErrors";

const PUBLIC_DAY0_MENU_KEYS = [
  "cockpit",
  "assistant",
  "processes",
  "agents",
  "spaces",
  "finops",
  "help",
] as const;

test.describe("Shell 4 zones Direction C — structure et état Jour 0 (UX-DR1, UX-DR8)", () => {
  let trackedErrors: string[] = [];

  test.beforeEach(async ({ page }) => {
    trackedErrors = watchUnexpectedPageAndApiErrors(page);
    resetDay0();
    await page.goto("/");
    await expect(page.getByTestId("first-boot-admin-setup-modal")).toBeVisible({
      timeout: 30000,
    });
    await expectZeroVisibleErrorBanners(page);
  });

  test.afterEach(() => {
    expect(trackedErrors, trackedErrors.join("\n")).toEqual([]);
  });

  test("présente les 4 zones, masque Paramètres tant qu'aucun PLATFORM_ADMIN n'est connecté et l'affiche après création admin", async ({
    page,
  }, testInfo) => {
    const isMobile = testInfo.project.name === "mobile-companion";
    await expect(page.getByTestId("four-zone-direction-c-shell")).toBeVisible();
    await expect(page.getByTestId("four-zone-top-header-bar")).toBeVisible();
    await expect(page.getByTestId("four-zone-central-workspace")).toBeAttached();

    if (isMobile) {
      await expect(page.getByTestId("four-zone-sidebar")).toHaveCount(0);
      await expect(page.getByTestId("mobile-bottom-tab-bar")).toBeVisible();
      await page.getByTestId("mobile-menu-drawer-toggle").click();
      await expect(page.getByTestId("mobile-navigation-drawer")).toBeVisible();
    } else {
      await expect(page.getByTestId("four-zone-sidebar")).toBeVisible();
    }

    // Sans rôle PLATFORM_ADMIN actif, le menu Paramètres de la plateforme est absent du DOM.
    await expect(page.getByTestId("eight-menu-item-configuration")).toHaveCount(0);

    for (const key of PUBLIC_DAY0_MENU_KEYS) {
      const entry = page.getByTestId(`eight-menu-item-${key}`);
      await expect(entry).toBeAttached();
      const text =
        (await entry.innerText()).trim() ||
        (await entry.getAttribute("aria-label"))?.trim() ||
        "";
      expect(text.length, `libellé vide pour ${key}`).toBeGreaterThan(0);
      expect(text, `préfixe numérique interdit pour ${key}`).not.toMatch(/^\d+[.)]?\s/);
    }

    if (isMobile) {
      await page.keyboard.press("Escape");
    }

    // Une fois le premier PLATFORM_ADMIN créé et connecté, Paramètres devient visible.
    await createFirstAdminViaUi(page);
    if (isMobile) {
      await page.getByTestId("mobile-menu-drawer-toggle").click();
    }
    await expect(page.getByTestId("eight-menu-item-configuration")).toBeVisible({ timeout: 20000 });
    expectDbRowExists(
      "SELECT id, email, platform_role FROM users WHERE email = :email AND platform_role = 'PLATFORM_ADMIN'",
      { email: E2E_ADMIN.email },
      "PLATFORM_ADMIN persisté dans users PG18",
    );
  });

  test("grise les entrées de menu tant que la plateforme n'est pas initialisée (Jour 0)", async ({
    page,
  }, testInfo) => {
    if (testInfo.project.name === "mobile-companion") {
      await page.getByTestId("mobile-menu-drawer-toggle").click();
      await expect(page.getByTestId("mobile-navigation-drawer")).toBeVisible();
    }
    const disabledReasons: string[] = [];
    for (const key of PUBLIC_DAY0_MENU_KEYS) {
      const entry = page.getByTestId(`eight-menu-item-${key}`);
      if ((await entry.getAttribute("aria-disabled")) === "true") {
        const reason = await entry.getAttribute("data-disabled-reason");
        expect(reason, `raison de grisage manquante pour ${key}`).toBeTruthy();
        disabledReasons.push(key);
      }
    }
    expect(disabledReasons.length, "au moins une entrée grisée au Jour 0").toBeGreaterThan(0);
    const countRows = queryDbRows<{ count: number }>("SELECT COUNT(*)::int AS count FROM users");
    expect(countRows[0]?.count).toBe(0);
  });

  test("le raccourci « [ » replie et déplie la barre latérale", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "raccourci clavier : bureau uniquement");
    await createFirstAdminViaUi(page);
    expectDbRowExists(
      "SELECT id, email, platform_role FROM users WHERE email = :email AND platform_role = 'PLATFORM_ADMIN'",
      { email: E2E_ADMIN.email },
      "PLATFORM_ADMIN persisté dans users PG18",
    );
    const sidebar = page.getByTestId("four-zone-sidebar");
    await expect(sidebar).toHaveAttribute("data-rail-collapsed", "false");
    await page.getByTestId("four-zone-central-workspace").click({ position: { x: 5, y: 5 } });
    await page.keyboard.press("[");
    await expect(sidebar).toHaveAttribute("data-rail-collapsed", "true");
    await page.keyboard.press("[");
    await expect(sidebar).toHaveAttribute("data-rail-collapsed", "false");
  });

  test("la modale Jour 0 est un dialogue accessible qui bloque le shell", async ({ page }) => {
    const modal = page.getByTestId("first-boot-admin-setup-modal");
    await expect(modal).toHaveAttribute("role", "dialog");
    await expect(modal).toHaveAttribute("aria-modal", "true");
    await expect(
      page.getByTestId("sidebar-rail-toggle-btn").click({ timeout: 2000 }),
    ).rejects.toThrow(/intercepts pointer events/);
    const countRows = queryDbRows<{ count: number }>("SELECT COUNT(*)::int AS count FROM users");
    expect(countRows[0]?.count).toBe(0);
  });
});
