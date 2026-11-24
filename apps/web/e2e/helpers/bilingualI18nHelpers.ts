import { expect, type Page } from "@playwright/test";
import { openSettingsTabViaUi, openUserSettingsTab } from "../support/authAndOrgHelpers";
import { expectDbRowExists } from "../support/dbAssertions";
import { apiGet, apiPatch } from "../support/typedApiRequest";

const FORBIDDEN_TECHNICAL_JARGON_RE =
  /\b(DBOS|pgvector|halfvec|domain_events_outbox|Wasmtime|Starlark|Argon2id)\b/i;

/** Assert shell navigation and topbar copy match the expected locale with zero jargon. */
export async function assertShellAndCockpitLocale(
  page: Page,
  locale: "fr" | "en",
): Promise<void> {
  await expect(page.getByTestId("four-zone-direction-c-shell")).toBeVisible({ timeout: 20000 });
  const viewportWidth = page.viewportSize()?.width ?? 1440;

  if (viewportWidth >= 768) {
    const expected =
      locale === "fr"
        ? {
            assistant: "Mon Assistant",
            processes: "Mes Processus",
            spaces: "Mes Espaces",
            organization: "Mon Organisation",
            help: "Aide",
            search: "Rechercher… (⌘K)",
          }
        : {
            assistant: "My Assistant",
            processes: "My Processes",
            spaces: "My Spaces",
            organization: "My Organization",
            help: "Help",
            search: "Search… (⌘K)",
          };
    await expect(page.getByTestId("eight-menu-item-assistant")).toContainText(expected.assistant, {
      timeout: 15000,
    });
    await expect(page.getByTestId("eight-menu-item-processes")).toContainText(expected.processes, {
      timeout: 15000,
    });
    await expect(page.getByTestId("eight-menu-item-spaces")).toContainText(expected.spaces, {
      timeout: 15000,
    });
    await expect(page.getByTestId("eight-menu-item-organization")).toContainText(
      expected.organization,
      { timeout: 15000 },
    );
    await expect(page.getByTestId("eight-menu-item-help")).toContainText(expected.help, {
      timeout: 15000,
    });
    await expect(page.getByTestId("topbar-federated-search-trigger")).toContainText(
      expected.search,
      { timeout: 15000 },
    );
  } else {
    const mobileBar = page.getByTestId("mobile-bottom-tab-bar");
    await expect(mobileBar).toBeVisible({ timeout: 15000 });
    await expect(mobileBar).toContainText(locale === "fr" ? "Mon Assistant" : "My Assistant", {
      timeout: 15000,
    });
    await expect(mobileBar).toContainText(locale === "fr" ? "Décisions" : "Decisions", {
      timeout: 15000,
    });
  }

  const workspaceText = await page.getByTestId("four-zone-central-workspace").innerText();
  expect(workspaceText).not.toMatch(FORBIDDEN_TECHNICAL_JARGON_RE);
}

/** Open Zone 4 contextual help panel and assert localized content without mixed-language leaks. */
export async function assertContextualHelpPanelLocale(
  page: Page,
  locale: "fr" | "en",
): Promise<void> {
  const helpColumn = page.getByTestId("four-zone-contextual-help-column");
  if (!(await helpColumn.isVisible())) {
    await page.getByTestId("topbar-contextual-help-toggle").click();
  }
  await expect(helpColumn).toBeVisible({ timeout: 15000 });
  const panel = page.getByTestId("contextual-help-hybrid-panel");
  await expect(panel).toBeVisible();

  if (locale === "fr") {
    await expect(panel).toContainText("À quoi sert cet écran ?");
    await expect(panel).toContainText("Un exemple réel");
    await expect(panel).toContainText("Ce qui coince souvent");
    await expect(panel).not.toContainText("What is this screen for?");
    await expect(panel).not.toContainText("Common pitfalls");
  } else {
    await expect(panel).toContainText("What is this screen for?");
    await expect(panel).toContainText("A real example");
    await expect(panel).toContainText("Common pitfalls");
    await expect(panel).not.toContainText("À quoi sert cet écran ?");
    await expect(panel).not.toContainText("Ce qui coince souvent");
  }

  await expect(page.getByTestId("contextual-help-ask-assistant-btn")).toContainText(
    locale === "fr"
      ? "Poser une question à Mon Assistant sur cet écran"
      : "Ask My Assistant about this screen",
  );
  await page.getByTestId("contextual-help-close-btn").click();
  await expect(helpColumn).toBeHidden();
}

/** Assert key admin and help views render cleanly in the expected locale. */
export async function assertAdminModelsAndHelpViewsLocale(
  page: Page,
  locale: "fr" | "en",
): Promise<void> {
  await openSettingsTabViaUi(page, "models");
  await expect(page.getByTestId("settings-tab-models")).toContainText(
    locale === "fr" ? "Modèles IA" : "AI Models",
  );
  await expect(page.getByTestId("open-create-ai-model-modal-btn")).toContainText(
    locale === "fr" ? "+ Connecter un modèle" : "+ Connect a model",
  );

  await page.goto("/help");
  const helpCenter = page.getByTestId("contextual-help-hybrid-panel");
  await expect(helpCenter).toBeVisible({ timeout: 20000 });
  await expect(helpCenter).toHaveAttribute(
    "aria-label",
    locale === "fr"
      ? "Centre d'Aide & Guides Pratiques"
      : "Help Center & Practical Guides",
  );
  await expect(helpCenter).toContainText(
    locale === "fr" ? "Centre d'Aide" : "Help Center",
    { timeout: 15000 },
  );
  await expect(helpCenter).toContainText(
    locale === "fr" ? "À quoi sert cet écran ?" : "What is this screen for?",
  );
}

/** Switch user UI locale via User Settings General tab and assert PG18 persistence. */
export async function switchUiLocaleViaUserSettings(
  page: Page,
  targetLocale: "fr" | "en",
): Promise<void> {
  await openUserSettingsTab(page, "GENERAL");
  const localeBtn =
    targetLocale === "en"
      ? page.getByTestId("settings-locale-en")
      : page.getByTestId("settings-locale-fr");

  const [prefRes] = await Promise.all([
    page.waitForResponse(
      (res) =>
        res.url().includes("/api/v1/users/me/preferences") &&
        res.request().method() === "PATCH" &&
        res.status() === 200,
      { timeout: 15000 },
    ),
    localeBtn.click(),
  ]);
  expect(prefRes.status()).toBe(200);
  await expect(localeBtn).toHaveAttribute("aria-pressed", "true");
  await page.getByTestId("user-settings-modal-close-btn").click();
  await expect(page.getByTestId("user-settings-modal")).toBeHidden({ timeout: 10000 });

  expectDbRowExists(
    "SELECT user_id, locale FROM user_preferences WHERE locale = :locale",
    { locale: targetLocale },
    `user_preferences locale=${targetLocale} persisted in PostgreSQL 18`,
  );
}

/** Trigger a client-side network error in federated search and verify localized ClientErrorCode copy. */
export async function assertLocalizedCmdkNetworkErrorBanner(
  page: Page,
  locale: "fr" | "en",
): Promise<void> {
  await page.route("**/api/v1/search**", (route) => route.abort("failed"));
  try {
    await page.getByTestId("topbar-federated-search-trigger").click();
    const palette = page.getByTestId("top-header-search-command");
    await expect(palette).toBeVisible({ timeout: 10000 });
    await page.getByTestId("cmdk-search-input").fill("agents");
    await page.getByTestId("cmdk-trigger-speed2-btn").click();

    const banner = page.getByTestId("cmdk-speed2-error-banner");
    await expect(banner).toBeVisible({ timeout: 10000 });
    if (locale === "fr") {
      await expect(banner).toContainText("Erreur lors de la recherche approfondie");
      await expect(banner).not.toContainText("Deep search failed");
    } else {
      await expect(banner).toContainText("Deep search failed across the platform");
      await expect(banner).not.toContainText("Erreur lors de la recherche");
    }

    await page.getByTestId("cmdk-search-input").fill("");
    await page.getByTestId("cmdk-cancel-btn").click();
    await expect(palette).toBeHidden({ timeout: 10000 });
  } finally {
    await page.unroute("**/api/v1/search**");
  }
}

interface ProblemEnvelope {
  readonly error_code?: string;
  readonly trace_id?: string;
  readonly title?: string;
  readonly detail?: string;
}

/** Verify live RFC 9457 problem+json responses localize title and detail via Accept-Language. */
export async function assertBilingualRfc9457ApiResponses(
  page: Page,
  token: string,
): Promise<void> {
  const valFrRes = await apiGet<ProblemEnvelope>(
    page,
    "/api/v1/sources/inspect-lines?uri=../pyproject.toml&start_line=1&end_line=10",
    { token, headers: { "Accept-Language": "fr" } },
  );
  const valEnRes = await apiGet<ProblemEnvelope>(
    page,
    "/api/v1/sources/inspect-lines?uri=../pyproject.toml&start_line=1&end_line=10",
    { token, headers: { "Accept-Language": "en" } },
  );
  expect([400, 422]).toContain(valFrRes.status());
  expect(valEnRes.status()).toBe(valFrRes.status());
  expect(valFrRes.headers()["content-type"]).toContain("application/problem+json");
  expect(valEnRes.headers()["content-type"]).toContain("application/problem+json");

  const valFr = await valFrRes.json();
  const valEn = await valEnRes.json();
  expect(valFr.error_code).toBe("ERR_VALIDATION_FAILED");
  expect(valEn.error_code).toBe("ERR_VALIDATION_FAILED");
  expect(Boolean(valFr.trace_id)).toBe(true);
  expect(Boolean(valEn.trace_id)).toBe(true);
  expect(valFr.title).toBe("Erreur de validation de la requête");
  expect(valEn.title).toBe("Request validation failed");
  expect(valFr.detail).not.toBe(valEn.detail);

  const orgFrRes = await apiPatch<ProblemEnvelope>(
    page,
    "/api/v1/org-units/01930000-0000-7000-8000-000000000999",
    { token, headers: { "Accept-Language": "fr" }, data: { name: "Bilingual Probe" } },
  );
  const orgEnRes = await apiPatch<ProblemEnvelope>(
    page,
    "/api/v1/org-units/01930000-0000-7000-8000-000000000999",
    { token, headers: { "Accept-Language": "en" }, data: { name: "Bilingual Probe" } },
  );
  expect(orgFrRes.status()).toBe(404);
  expect(orgEnRes.status()).toBe(404);
  expect(orgFrRes.headers()["content-type"]).toContain("application/problem+json");
  expect(orgEnRes.headers()["content-type"]).toContain("application/problem+json");

  const orgFr = await orgFrRes.json();
  const orgEn = await orgEnRes.json();
  expect(orgFr.error_code).toBe("ERR_RESOURCE_NOT_FOUND");
  expect(orgEn.error_code).toBe("ERR_RESOURCE_NOT_FOUND");
  expect(Boolean(orgFr.trace_id)).toBe(true);
  expect(Boolean(orgEn.trace_id)).toBe(true);
  expect(orgFr.title).toBe("Ressource introuvable");
  expect(orgEn.title).toBe("Resource not found");
  expect(orgFr.detail).toContain("Unité organisationnelle introuvable");
  expect(orgEn.detail).toContain("Organizational unit not found");
}

/** Submit the local login form directly on the current `/login` screen without full page reload. */
export async function submitLocalLoginForm(
  page: Page,
  email: string,
  password: string,
): Promise<void> {
  await expect(page.getByTestId("login-page-container")).toBeVisible({ timeout: 20000 });
  await page.getByTestId("login-local-email").fill(email);
  await page.getByTestId("login-local-password").fill(password);
  await page.getByTestId("login-local-submit").click();
}
