import { expect, test } from "@playwright/test";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi } from "./support/firstAdmin";
import { watchApiServerErrors } from "./support/apiErrors";

test.describe("TEST-06 · 09 — Atelier de processus (pack-builder) et aide contextuelle ⓘ", () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "parcours bureau");
    resetDay0();
    await createFirstAdminViaUi(page);
  });

  test("l'écran Processus présente le processus du pack ORCIA et l'aide ⓘ ouvre la colonne contextuelle", async ({
    page,
  }) => {
    const serverErrors = watchApiServerErrors(page);
    await page.goto("/processes");
    await expect(page.getByText("Génération de la Documentation ORCIA").first()).toBeVisible({
      timeout: 30000,
    });
    await expect(page.getByText("Créer et Gérer mes Processus Métiers")).toBeVisible();

    // Bouton ⓘ → colonne d'aide contextuelle (zone 4).
    const helpColumn = page.getByTestId("four-zone-contextual-help-column");
    if (!(await helpColumn.isVisible())) {
      await page.getByTestId("topbar-contextual-help-toggle").click();
    }
    await expect(helpColumn).toBeVisible();
    await expect(page.getByTestId("contextual-help-hybrid-panel")).toBeVisible();
    await page.getByTestId("contextual-help-close-btn").click();
    await expect(helpColumn).toBeHidden();
    expect(serverErrors, serverErrors.join("\n")).toEqual([]);
  });
});
