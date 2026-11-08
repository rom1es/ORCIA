import { expect, test } from "@playwright/test";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi } from "./support/firstAdmin";
import { watchApiServerErrors } from "./support/apiErrors";

const SCREENS: ReadonlyArray<{ route: string; testId: string }> = [
  { route: "/cockpit", testId: "four-zone-central-workspace" },
  { route: "/configuration", testId: "create-org-unit-form" },
  { route: "/ontology", testId: "four-zone-central-workspace" },
  { route: "/catalog", testId: "four-zone-central-workspace" },
  { route: "/activity", testId: "four-zone-central-workspace" },
  { route: "/finops", testId: "four-zone-central-workspace" },
  { route: "/help", testId: "four-zone-central-workspace" },
];

test.describe("TEST-06 · 11 — Écrans Configuration, Ontologie, Catalogue, Activité, Coûts : aucun 5xx", () => {
  test("chaque écran se charge au Jour 0 sans erreur serveur /api", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "parcours bureau");
    const serverErrors = watchApiServerErrors(page);
    resetDay0();
    await createFirstAdminViaUi(page);
    for (const { route, testId } of SCREENS) {
      await page.goto(route);
      await expect(page.getByTestId(testId).first(), `écran ${route}`).toBeAttached({
        timeout: 30000,
      });
      await page.waitForLoadState("networkidle");
    }
    expect(serverErrors, serverErrors.join("\n")).toEqual([]);
  });
});
