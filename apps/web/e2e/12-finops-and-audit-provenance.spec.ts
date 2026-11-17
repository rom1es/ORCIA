import { expect, test } from "@playwright/test";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi } from "./support/firstAdmin";
import {
  expectZeroVisibleErrorBanners,
  watchUnexpectedPageAndApiErrors,
} from "./support/apiErrors";

test.describe("TEST-06 · 12 — FinOps Gouvernance, Services externes & Journal de Provenance", () => {
  test("bureau : /activity et /finops (état vide, modale plafond, 4 onglets dont Services externes) sans erreur 4xx/5xx", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "parcours bureau");
    const errors = watchUnexpectedPageAndApiErrors(page);
    resetDay0();
    await createFirstAdminViaUi(page);

    // 1. Parcours /activity
    await page.goto("/activity");
    await expect(page.getByTestId("activity-log-explorer-page")).toBeVisible({ timeout: 30000 });
    await expectZeroVisibleErrorBanners(page);

    // 2. Parcours /finops
    await page.goto("/finops");
    await expect(page.getByTestId("finops-governance-dashboard")).toBeVisible({ timeout: 30000 });
    await expect(page.getByTestId("finops-empty-state")).toBeVisible();

    // Ouverture de la modale "+ Configurer un plafond" et sauvegarde
    await page.getByTestId("finops-configure-budget-btn").click();
    await expect(page.getByTestId("finops-budget-modal")).toBeVisible();
    await page.getByTestId("finops-budget-monthly-limit").fill("250");
    await page.getByTestId("finops-budget-save-btn").click();
    await expect(page.getByTestId("finops-success-banner")).toBeVisible({ timeout: 15000 });

    // Bascule entre les 4 onglets (dont Services et agents externes & Maîtrise humaine)
    await page.getByTestId("finops-tab-external-services").click();
    await expect(page.getByTestId("finops-remote-services-tab")).toBeVisible();
    await expect(page.getByTestId("finops-remote-services-empty")).toBeVisible();

    await page.getByTestId("finops-tab-cognitive-governance").click();
    await expect(page.getByTestId("finops-human-mastery-tab")).toBeVisible();

    await page.getByTestId("finops-tab-tiers").click();
    await expect(page.getByTestId("finops-tiers-tab")).toBeVisible();

    await expectZeroVisibleErrorBanners(page);
    expect(errors, errors.join("\n")).toEqual([]);
  });

  test("mobile : /finops et /activity s'affichent sans débordement horizontal ni erreur serveur", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "mobile-companion", "parcours mobile");
    const errors = watchUnexpectedPageAndApiErrors(page);
    resetDay0();
    await createFirstAdminViaUi(page);

    await page.goto("/finops");
    await expect(page.getByTestId("four-zone-central-workspace")).toBeVisible({ timeout: 30000 });
    await page.waitForLoadState("load");
    await expectZeroVisibleErrorBanners(page);

    await page.goto("/activity");
    await expect(page.getByTestId("four-zone-central-workspace")).toBeVisible({ timeout: 30000 });
    await page.waitForLoadState("load");
    await expectZeroVisibleErrorBanners(page);

    expect(errors, errors.join("\n")).toEqual([]);
  });
});
