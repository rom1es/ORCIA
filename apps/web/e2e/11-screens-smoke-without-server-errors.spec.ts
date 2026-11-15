import { expect, test } from "@playwright/test";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi, E2E_ADMIN } from "./support/firstAdmin";
import {
  expectZeroVisibleErrorBanners,
  watchUnexpectedPageAndApiErrors,
} from "./support/apiErrors";

const SCREENS: ReadonlyArray<{ route: string; testId: string }> = [
  { route: "/cockpit", testId: "four-zone-central-workspace" },
  { route: "/configuration", testId: "settings-organization-section" },
  { route: "/ontology", testId: "four-zone-central-workspace" },
  { route: "/catalog", testId: "four-zone-central-workspace" },
  { route: "/activity", testId: "four-zone-central-workspace" },
  { route: "/finops", testId: "four-zone-central-workspace" },
  { route: "/help", testId: "four-zone-central-workspace" },
];

test.describe("TEST-06 · 11 — Écrans Configuration, Ontologie, Catalogue, Activité, Coûts & /login : zéro 4xx/5xx", () => {
  test("chaque écran authentifié se charge au Jour 0 sans erreur HTTP 4xx/5xx ni bannière d'erreur", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "parcours bureau");
    const errors = watchUnexpectedPageAndApiErrors(page);
    resetDay0();
    await createFirstAdminViaUi(page);
    for (const { route, testId } of SCREENS) {
      await page.goto(route);
      await expect(page.getByTestId(testId).first(), `écran ${route}`).toBeAttached({
        timeout: 30000,
      });
      await page.waitForLoadState("networkidle");
      await expectZeroVisibleErrorBanners(page);
    }
    expect(errors, errors.join("\n")).toEqual([]);
  });

  test("la mire /login s'ouvre sans erreur 404/401 ni bannière d'alerte après création admin et permet la reconnexion", async ({
    browser,
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "parcours bureau");
    resetDay0();
    await createFirstAdminViaUi(page);

    const anonContext = await browser.newContext();
    const anonPage = await anonContext.newPage();
    const anonErrors = watchUnexpectedPageAndApiErrors(anonPage);
    try {
      await anonPage.goto("/login");
      await expect(anonPage.getByTestId("bi-mode-login-view")).toBeVisible({ timeout: 30000 });
      await expect(anonPage.getByTestId("login-local-email")).toBeVisible();
      await expect(anonPage.getByTestId("login-local-password")).toBeVisible();
      await anonPage.waitForLoadState("networkidle");
      await expectZeroVisibleErrorBanners(anonPage);
      expect(anonErrors, anonErrors.join("\n")).toEqual([]);

      await anonPage.getByTestId("login-local-email").fill(E2E_ADMIN.email);
      await anonPage.getByTestId("login-local-password").fill(E2E_ADMIN.password);
      await anonPage.getByTestId("login-local-submit").click();
      await expect(anonPage.getByTestId("four-zone-direction-c-shell")).toBeVisible({
        timeout: 30000,
      });
      expect(anonErrors, anonErrors.join("\n")).toEqual([]);
    } finally {
      await anonContext.close();
    }
  });
});
