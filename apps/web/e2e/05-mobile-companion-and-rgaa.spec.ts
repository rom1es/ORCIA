import { expect, test } from "@playwright/test";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi } from "./support/firstAdmin";

test.describe("TEST-04 · 05 — Mobile Companion (390x844) et sorties de secours RGAA", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("Escape sur un formulaire modifié demande confirmation avant d'abandonner (garde isDirty)", async ({
    page,
  }) => {
    await page.goto("/");
    const modal = page.getByTestId("first-boot-admin-setup-modal");
    await expect(modal).toBeVisible({ timeout: 30000 });
    await page.getByTestId("first-boot-admin-name-input").fill("Saisie non enregistrée");
    await page.keyboard.press("Escape");
    await expect(page.getByRole("alertdialog")).toBeVisible();
    // La saisie n'est pas perdue tant que l'utilisateur n'a pas confirmé l'abandon.
    await expect(modal).toBeAttached();
  });

  test("aucun débordement horizontal sur mobile une fois la plateforme initialisée", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "mobile-companion", "viewport mobile uniquement");
    await createFirstAdminViaUi(page);
    for (const route of ["/cockpit", "/assistant", "/spaces", "/configuration"]) {
      await page.goto(route);
      await expect(page.getByTestId("four-zone-direction-c-shell")).toBeVisible({ timeout: 30000 });
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      );
      expect(overflow, `débordement horizontal sur ${route}: ${overflow}px`).toBeLessThanOrEqual(1);
    }
  });
});
