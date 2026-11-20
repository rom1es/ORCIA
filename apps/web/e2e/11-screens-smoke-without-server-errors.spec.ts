/** @uj UJ-13, UJ-14, UJ-18, UJ-20 | @cap CAP-001, CAP-002, CAP-010 */
import { captureMilestoneScreenshot, expect, test } from "./support/e2eCaptureFixture";
import { expectDbRowCount, expectDbRowExists } from "./support/dbAssertions";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi, E2E_ADMIN } from "./support/firstAdmin";
import {
  expectZeroVisibleErrorBanners,
  watchUnexpectedPageAndApiErrors,
} from "./support/apiErrors";
import {
  assertCockpitSobrietyMaxThreeBlocks,
  assertMaxOneDialogCloseOrCancelButton,
  assertNoHorizontalOverflow,
  assertNoZoneHorizontalTruncation,
  assertSingleDesktopWorkspaceSelector,
  assertZeroBulletPlaceholders,
  assertZone4ContextualHelpRoutesFidelity,
} from "./support/layoutGeometryAssertions";

const SCREENS: ReadonlyArray<{ route: string; testId: string }> = [
  { route: "/cockpit", testId: "four-zone-central-workspace" },
  { route: "/organization", testId: "settings-organization-section" },
  { route: "/configuration", testId: "settings-iam-section" },
  { route: "/ontology", testId: "four-zone-central-workspace" },
  { route: "/catalog", testId: "four-zone-central-workspace" },
  { route: "/activity", testId: "four-zone-central-workspace" },
  { route: "/finops", testId: "four-zone-central-workspace" },
  { route: "/help", testId: "four-zone-central-workspace" },
  { route: "/profile", testId: "user-profile-overview-page" },
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
      await page.waitForLoadState("load");
      await page.waitForTimeout(250);
      await expectZeroVisibleErrorBanners(page);
      await assertNoHorizontalOverflow(page, route);
      await assertNoZoneHorizontalTruncation(page, route);
      await assertSingleDesktopWorkspaceSelector(page);
      await assertZeroBulletPlaceholders(page, route);
      await assertMaxOneDialogCloseOrCancelButton(page);
      if (route === "/cockpit") {
        await assertCockpitSobrietyMaxThreeBlocks(page);
      }
    }
    await assertZone4ContextualHelpRoutesFidelity(page);
    expect(errors, errors.join("\n")).toEqual([]);
    expectDbRowExists(
      "SELECT id, email, platform_role FROM users WHERE email = :email AND platform_role = 'PLATFORM_ADMIN'",
      { email: E2E_ADMIN.email },
      "admin Jour 0 présent dans users PG18",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM declarative_pack_bundles",
      undefined,
      1,
      "packs déclaratifs synchronisés en base PG18",
    );
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
      await expect(anonPage.getByTestId("login-brand-header")).toBeVisible();
      await expect(anonPage.getByTestId("login-local-email")).toBeVisible();
      const pwdInput = anonPage.getByTestId("login-local-password");
      await expect(pwdInput).toBeVisible();
      await expect(pwdInput).toHaveAttribute("type", "password");
      const eyeBtn = anonPage.getByTestId("login-local-password-toggle-visibility");
      await expect(eyeBtn).toBeVisible();
      await eyeBtn.click();
      await expect(pwdInput).toHaveAttribute("type", "text");
      await eyeBtn.click();
      await expect(pwdInput).toHaveAttribute("type", "password");
      await anonPage.waitForLoadState("load");
      await anonPage.waitForTimeout(250);
      await expectZeroVisibleErrorBanners(anonPage);
      await assertNoHorizontalOverflow(anonPage, "/login");
      await assertZeroBulletPlaceholders(anonPage, "/login");
      expect(anonErrors, anonErrors.join("\n")).toEqual([]);
      await captureMilestoneScreenshot(anonPage, testInfo, "login-screen-and-password-eye");

      await anonPage.getByTestId("login-local-email").fill(E2E_ADMIN.email);
      await anonPage.getByTestId("login-local-password").fill(E2E_ADMIN.password);
      await anonPage.getByTestId("login-local-submit").click();
      await expect(anonPage.getByTestId("four-zone-direction-c-shell")).toBeVisible({
        timeout: 30000,
      });
      expect(anonErrors, anonErrors.join("\n")).toEqual([]);
      expectDbRowExists(
        "SELECT id, email, platform_role FROM users WHERE email = :email AND is_active = TRUE",
        { email: E2E_ADMIN.email },
        "compte administrateur authentifié dans users PG18",
      );
    } finally {
      await anonContext.close();
    }
  });
});
