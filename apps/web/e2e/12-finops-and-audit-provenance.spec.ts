/** @uj UJ-8, UJ-14 | @cap CAP-065, CAP-200 */
import { expect, test } from "./support/e2eCaptureFixture";
import { expectDbRowExists } from "./support/dbAssertions";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi, E2E_ADMIN } from "./support/firstAdmin";
import {
  expectZeroVisibleErrorBanners,
  watchUnexpectedPageAndApiErrors,
} from "./support/apiErrors";
import {
  assertModalActionClickableViaElementFromPoint,
  assertNoHorizontalOverflow,
  attachErrorAlertProbe,
} from "./support/layoutGeometryAssertions";
import { reloadColdFromPg } from "./support/typedApiRequest";

test.describe("TEST-06 · 12 — FinOps Gouvernance, Services externes & Journal de Provenance", () => {
  test("bureau : /activity et /finops (état vide, modale plafond, 4 onglets dont Services externes) sans erreur 4xx/5xx", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "parcours bureau");
    const errors = watchUnexpectedPageAndApiErrors(page);
    resetDay0();
    await createFirstAdminViaUi(page);

    // 1. Parcours /activity : présence des traces persistées et filtres fonctionnels
    await page.goto("/activity");
    await expect(page.getByTestId("activity-log-explorer-page")).toBeVisible({ timeout: 30000 });
    await expectZeroVisibleErrorBanners(page);

    // 2. Parcours /finops et commutation des périmètres sans erreur 4xx/5xx
    await page.goto("/finops");
    await expect(page.getByTestId("finops-governance-dashboard")).toBeVisible({ timeout: 30000 });
    await expect(page.getByTestId("finops-empty-state")).toBeVisible();

    await page.getByTestId("finops-scope-workspace").click();
    await page.getByTestId("finops-scope-team").click();
    await page.getByTestId("finops-scope-global").click();
    await expectZeroVisibleErrorBanners(page);

    // Ouverture de la modale "+ Configurer un plafond" et sauvegarde + survie F5 à froid PG18
    await page.getByTestId("finops-configure-budget-btn").click();
    await expect(page.getByTestId("finops-budget-modal")).toBeVisible();
    await assertModalActionClickableViaElementFromPoint(page, "finops-budget-save-btn");
    await page.getByTestId("finops-budget-monthly-limit").fill("250");
    await page.getByTestId("finops-budget-save-btn").click();
    await expect(page.getByTestId("finops-success-banner")).toBeVisible({ timeout: 15000 });

    await reloadColdFromPg(page);
    await expect(page.getByTestId("finops-governance-dashboard")).toBeVisible({ timeout: 30000 });
    expectDbRowExists(
      "SELECT id, scope_type, monthly_budget_usd FROM finops_scope_budgets WHERE scope_type = :scope_type AND monthly_budget_usd > 0",
      { scope_type: "GLOBAL" },
      "plafond budgétaire GLOBAL persisté dans finops_scope_budgets PG18",
    );

    // Bascule entre les 4 onglets (dont Services et agents externes & Maîtrise humaine)
    await page.getByTestId("finops-tab-processes").click();
    await expect(page.getByTestId("finops-processes-tab")).toBeVisible();

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
    const alertProbe = attachErrorAlertProbe(page);
    resetDay0();
    await createFirstAdminViaUi(page);

    await page.goto("/finops");
    await expect(page.getByTestId("four-zone-central-workspace")).toBeVisible({ timeout: 30000 });
    await expect(page.getByTestId("finops-governance-dashboard")).toBeVisible({ timeout: 15000 });
    await page.waitForLoadState("load");
    await expectZeroVisibleErrorBanners(page);
    await assertNoHorizontalOverflow(page, "mobile /finops");

    await page.goto("/activity");
    await expect(page.getByTestId("four-zone-central-workspace")).toBeVisible({ timeout: 30000 });
    await expect(page.getByTestId("activity-log-explorer-page")).toBeVisible({ timeout: 15000 });
    await page.waitForLoadState("load");
    await expectZeroVisibleErrorBanners(page);
    await assertNoHorizontalOverflow(page, "mobile /activity");

    expectDbRowExists(
      "SELECT id, email, platform_role FROM users WHERE email = :email AND platform_role = 'PLATFORM_ADMIN'",
      { email: E2E_ADMIN.email },
      "admin Jour 0 présent dans users PG18 lors du parcours FinOps/Activity mobile",
    );
    alertProbe.assertNoUnexpectedHttpErrors();
    expect(errors, errors.join("\n")).toEqual([]);
  });
});
