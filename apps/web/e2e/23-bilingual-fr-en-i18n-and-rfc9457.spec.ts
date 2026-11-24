/** @uj UJ-13, UJ-16 | @cap CAP-001, CAP-100 */
import { expect, test } from "./support/e2eCaptureFixture";
import { watchUnexpectedPageAndApiErrors } from "./support/apiErrors";
import {
  getBearerTokenFromSession,
  logoutViaAccountPopover,
} from "./support/authAndOrgHelpers";
import { resetDay0 } from "./support/day0";
import { expectDbRowExists } from "./support/dbAssertions";
import { createFirstAdminViaUi, E2E_ADMIN } from "./support/firstAdmin";
import { reloadColdFromPg } from "./support/typedApiRequest";
import {
  assertAdminModelsAndHelpViewsLocale,
  assertBilingualRfc9457ApiResponses,
  assertContextualHelpPanelLocale,
  assertLocalizedCmdkNetworkErrorBanner,
  assertShellAndCockpitLocale,
  submitLocalLoginForm,
  switchUiLocaleViaUserSettings,
} from "./helpers/bilingualI18nHelpers";

test.describe("Story 27.8 — Bilingual FR/EN Web App, Cold F5 Locale Persistence & RFC 9457 Errors", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("renders Day-0 and cockpit in French, switches to English across cold F5 reload, localizes client errors, and restores French", async ({
    page,
  }) => {
    const unexpectedErrors = watchUnexpectedPageAndApiErrors(page, {
      allowedApiStatuses: [{ pathIncludes: "/api/v1/search", status: 500 }],
    });

    await page.goto("/");
    const day0Modal = page.getByTestId("first-boot-admin-setup-modal");
    await expect(day0Modal).toBeVisible({ timeout: 30000 });
    await expect(day0Modal).toContainText("Création du compte Administrateur de la plateforme");
    await expect(page.getByTestId("first-boot-admin-submit-btn")).toContainText(
      "Créer le compte Administrateur",
    );

    await createFirstAdminViaUi(page);

    // 1. Verify initial French rendering across shell, contextual help, key routes, and client error banner.
    await assertShellAndCockpitLocale(page, "fr");
    await assertContextualHelpPanelLocale(page, "fr");
    await assertAdminModelsAndHelpViewsLocale(page, "fr");
    await assertLocalizedCmdkNetworkErrorBanner(page, "fr");

    // 2. Switch user preference fr -> en, verify immediate switch across views and client error banner.
    await switchUiLocaleViaUserSettings(page, "en");
    await page.goto("/cockpit");
    await assertShellAndCockpitLocale(page, "en");
    await assertContextualHelpPanelLocale(page, "en");
    await assertAdminModelsAndHelpViewsLocale(page, "en");
    await assertLocalizedCmdkNetworkErrorBanner(page, "en");

    // 3. Cold PG18 reload (F5 with localStorage cleared) must preserve English preference from DB.
    await page.goto("/cockpit");
    await reloadColdFromPg(page);
    await assertShellAndCockpitLocale(page, "en");
    await assertContextualHelpPanelLocale(page, "en");
    const htmlLangEn = await page.evaluate(() => document.documentElement.lang);
    expect(htmlLangEn).toBe("en");

    // 4. Switch back en -> fr and verify cold reload restores French cleanly.
    await switchUiLocaleViaUserSettings(page, "fr");
    await reloadColdFromPg(page);
    await assertShellAndCockpitLocale(page, "fr");
    const htmlLangFr = await page.evaluate(() => document.documentElement.lang);
    expect(htmlLangFr).toBe("fr");
    expectDbRowExists(
      "SELECT user_id, locale FROM user_preferences WHERE locale = :locale",
      { locale: "fr" },
      "restored French locale preference persisted in user_preferences",
    );

    expect(unexpectedErrors, unexpectedErrors.join("\n")).toEqual([]);
  });

  test("localizes backend RFC 9457 application/problem+json envelopes via Accept-Language and login error banner", async ({
    page,
  }) => {
    const unexpectedErrors = watchUnexpectedPageAndApiErrors(page, {
      allowedApiStatuses: [
        { pathIncludes: "/api/v1/sources/inspect-lines", status: 422 },
        { pathIncludes: "/api/v1/org-units/", status: 404 },
        { pathIncludes: "/api/v1/auth/login/local", status: 401 },
      ],
    });

    await createFirstAdminViaUi(page);
    const token = await getBearerTokenFromSession(page);

    // 1. Live backend RFC 9457 localization via Accept-Language: fr vs en with invariant error_code & trace_id.
    await assertBilingualRfc9457ApiResponses(page, token);

    // 2. Trigger localized RFC 9457 login error banner in French, then in English via active locale session.
    await logoutViaAccountPopover(page);
    await submitLocalLoginForm(page, E2E_ADMIN.email, "Wrong-Password-Probe-1!");
    const loginErrFr = page.getByTestId("login-rfc9457-error");
    await expect(loginErrFr).toBeVisible({ timeout: 15000 });
    await expect(loginErrFr).toContainText("ERR_AUTH_INVALID_CREDENTIALS");
    await expect(loginErrFr).toContainText("fourni est invalide");

    // Sign in validly, switch UI locale to English, sign out without reloading, and verify English login banner.
    await submitLocalLoginForm(page, E2E_ADMIN.email, E2E_ADMIN.password);
    await expect(page.getByTestId("four-zone-direction-c-shell")).toBeVisible({ timeout: 20000 });
    await switchUiLocaleViaUserSettings(page, "en");

    await logoutViaAccountPopover(page);
    await submitLocalLoginForm(page, E2E_ADMIN.email, "Wrong-Password-Probe-2!");
    const loginErrEn = page.getByTestId("login-rfc9457-error");
    await expect(loginErrEn).toBeVisible({ timeout: 15000 });
    await expect(loginErrEn).toContainText("ERR_AUTH_INVALID_CREDENTIALS");
    await expect(loginErrEn).toContainText("The supplied email, password, or OIDC token is invalid.");
    expectDbRowExists(
      "SELECT user_id, locale FROM user_preferences WHERE locale = :locale",
      { locale: "en" },
      "English locale preference persisted in user_preferences",
    );
    expectDbRowExists(
      "SELECT id, email, platform_role FROM users WHERE email = :email AND platform_role = 'PLATFORM_ADMIN'",
      { email: E2E_ADMIN.email },
      "admin identity persisted in users for RFC 9457 verification",
    );

    expect(unexpectedErrors, unexpectedErrors.join("\n")).toEqual([]);
  });
});
