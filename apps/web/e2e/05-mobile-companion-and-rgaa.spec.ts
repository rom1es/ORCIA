/** @uj UJ-20 | @cap CAP-042 */
import { expect, test } from "./support/e2eCaptureFixture";
import { resetDay0 } from "./support/day0";
import { expectDbRowCount, expectDbRowExists, queryDbRows } from "./support/dbAssertions";
import { createFirstAdminViaUi } from "./support/firstAdmin";
import {
  assertModalActionClickableViaElementFromPoint,
  assertNoHorizontalOverflow,
  attachErrorAlertProbe,
} from "./support/layoutGeometryAssertions";

test.describe("TEST-04 · 05 — Mobile Companion (390x844) et sorties de secours RGAA", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("Escape sur un formulaire modifié demande confirmation avant d'abandonner (garde isDirty)", async ({
    page,
  }) => {
    const alertProbe = attachErrorAlertProbe(page);
    await page.goto("/");
    const modal = page.getByTestId("first-boot-admin-setup-modal");
    await expect(modal).toBeVisible({ timeout: 30000 });
    await assertModalActionClickableViaElementFromPoint(page, "first-boot-admin-submit-btn");
    await page.getByTestId("first-boot-admin-name-input").fill("Saisie non enregistrée");
    await page.keyboard.press("Escape");
    await expect(page.getByRole("alertdialog")).toBeVisible();
    // La saisie n'est pas perdue tant que l'utilisateur n'a pas confirmé l'abandon.
    await expect(modal).toBeAttached();

    const countRows = queryDbRows<{ count: number }>("SELECT COUNT(*)::int AS count FROM users");
    expect(countRows[0]?.count).toBe(0);
    alertProbe.assertNoUnexpectedHttpErrors([]);
  });

  test("aucun débordement horizontal sur mobile une fois la plateforme initialisée", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "mobile-companion", "viewport mobile uniquement");
    await createFirstAdminViaUi(page);
    const alertProbe = attachErrorAlertProbe(page);
    expectDbRowExists(
      "SELECT singleton_key, auth_mode FROM platform_auth_settings WHERE singleton_key = :key",
      { key: "GLOBAL" },
      "politique platform_auth_settings persistée en PG18 avant parcours mobile",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM declarative_pack_bundles",
      undefined,
      1,
      "packs déclaratifs actifs dans declarative_pack_bundles PG18",
    );
    for (const route of ["/cockpit", "/assistant", "/spaces", "/configuration"]) {
      await page.goto(route);
      await expect(page.getByTestId("four-zone-direction-c-shell")).toBeVisible({ timeout: 30000 });
      await expect(page.getByTestId("four-zone-sidebar")).toHaveCount(0);
      await expect(page.getByTestId("mobile-bottom-tab-bar")).toBeVisible();
      if (route === "/configuration") {
        await expect(page.getByTestId("mobile-desktop-recommended-banner")).toBeVisible();
      }
      await assertNoHorizontalOverflow(page, `mobile ${route}`);
    }
    alertProbe.assertNoUnexpectedHttpErrors([]);
  });
});
