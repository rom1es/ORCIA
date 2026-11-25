/** @uj UJ-13, UJ-16, UJ-20 | @cap CAP-001, CAP-100 */
import type { Page } from "@playwright/test";
import { expect, test } from "./support/e2eCaptureFixture";
import {
  expectZeroVisibleErrorBanners,
  watchUnexpectedPageAndApiErrors,
} from "./support/apiErrors";
import { resetDay0 } from "./support/day0";
import { expectDbRowCount, expectDbRowExists } from "./support/dbAssertions";
import { configureActiveChatModelViaApi } from "./support/embeddingModel";
import { createFirstAdminViaUi, E2E_ADMIN } from "./support/firstAdmin";
import { createOrgAndWorkspaceWithId } from "./support/workspaceAndCatalogHelpers";
import { switchUiLocaleViaUserSettings } from "./helpers/bilingualI18nHelpers";

const FORBIDDEN_EMOJI_RE =
  /[\u{1F916}\u{1F6E0}\u{1F50C}\u{1F512}\u{1F4C1}\u{1F4E6}\u{1F9ED}\u{1F9E0}\u{1F4DA}]/u;

interface PrimaryScreenExpectation {
  readonly route: string;
  readonly expectedTitleFr?: string;
  readonly expectedTitleEn?: string;
  readonly isHelpCenter?: boolean;
}

const PRIMARY_SCREENS: readonly PrimaryScreenExpectation[] = [
  { route: "/cockpit", expectedTitleFr: "Cockpit", expectedTitleEn: "Cockpit" },
  { route: "/assistant", expectedTitleFr: "Mon Assistant", expectedTitleEn: "My Assistant" },
  { route: "/processes", expectedTitleFr: "Mes Processus", expectedTitleEn: "My Processes" },
  {
    route: "/agents",
    expectedTitleFr: "Mes Agents & Compétences",
    expectedTitleEn: "My Agents & Skills",
  },
  { route: "/spaces" },
  {
    route: "/organization",
    expectedTitleFr: "Mon Organisation",
    expectedTitleEn: "My Organization",
  },
  {
    route: "/finops",
    expectedTitleFr: "FinOps et Gouvernance Économique",
    expectedTitleEn: "FinOps and Economic Governance",
  },
  {
    route: "/help",
    expectedTitleFr: "Centre d'Aide",
    expectedTitleEn: "Help Center",
    isHelpCenter: true,
  },
];

async function assertPrimaryScreensInLocale(
  page: Page,
  locale: "fr" | "en",
): Promise<void> {
  const expectedAssistantNavLabel = locale === "fr" ? "Mon Assistant" : "My Assistant";
  const expectedHelpTogglePattern = locale === "fr" ? /Aide/ : /Help/;

  for (const screenSpec of PRIMARY_SCREENS) {
    await page.goto(screenSpec.route);
    const workspace = page.getByTestId("four-zone-central-workspace");
    await expect(workspace).toBeVisible({ timeout: 25000 });

    // Wait for persisted user preferences locale hydration before reading any UI text snapshots.
    await expect(page.getByTestId("eight-menu-item-assistant")).toContainText(
      expectedAssistantNavLabel,
      { timeout: 20000 },
    );
    const helpToggle = page.getByTestId("topbar-contextual-help-toggle");
    await expect(helpToggle).toHaveText(expectedHelpTogglePattern, { timeout: 20000 });

    const headers = workspace.locator("header.orcia-ds-page-header");
    await expect(headers).toHaveCount(1, { timeout: 20000 });
    const header = headers.first();
    await expect(header).toBeVisible();

    const h1 = header.locator("h1");
    await expect(h1).toHaveCount(1);
    const expectedTitle =
      locale === "fr" ? screenSpec.expectedTitleFr : screenSpec.expectedTitleEn;
    if (expectedTitle) {
      await expect(h1).toHaveText(expectedTitle, { timeout: 20000 });
    } else {
      await expect(h1).toHaveText(/\S+/, { timeout: 20000 });
    }

    const h1Text = (await h1.innerText()).trim();
    expect(h1Text.length).toBeGreaterThan(0);
    expect(h1Text).not.toMatch(FORBIDDEN_EMOJI_RE);

    const primaryCtaCount = await header.locator(".orcia-ds-btn-primary").count();
    expect(
      primaryCtaCount,
      `${screenSpec.route} (${locale}) must have <= 1 primary Cobalt header CTA`,
    ).toBeLessThanOrEqual(1);

    const headerText = (await header.innerText()).trim();
    expect(headerText).not.toMatch(FORBIDDEN_EMOJI_RE);

    const tabStrips = workspace.locator(".orcia-ds-tab-strip");
    const stripCount = await tabStrips.count();
    for (let i = 0; i < stripCount; i += 1) {
      const stripText = await tabStrips.nth(i).innerText();
      expect(stripText).not.toMatch(FORBIDDEN_EMOJI_RE);
    }

    const sidebarText = await page.getByTestId("four-zone-sidebar").innerText();
    expect(sidebarText).not.toMatch(FORBIDDEN_EMOJI_RE);

    await expectZeroVisibleErrorBanners(page);

    if (screenSpec.isHelpCenter) {
      await expect(helpToggle).toBeDisabled();
      await expect(helpToggle).toHaveAttribute("aria-current", "page");
      await expect(page.getByTestId("four-zone-contextual-help-column")).toHaveCount(0);
    } else {
      await expect(helpToggle).toBeEnabled();
      const helpCol = page.getByTestId("four-zone-contextual-help-column");
      if (!(await helpCol.isVisible())) {
        await helpToggle.click();
      }
      await expect(helpCol).toBeVisible({ timeout: 15000 });
      const whatForBox = page.getByTestId("contextual-help-what-for-box");
      await expect(whatForBox).toBeVisible({ timeout: 15000 });
      const whatForText = (await whatForBox.innerText()).trim();
      expect(whatForText.length).toBeGreaterThan(0);
      expect(whatForText).not.toMatch(FORBIDDEN_EMOJI_RE);
      const sectionsList = page.getByTestId("contextual-help-sections-list");
      if ((await sectionsList.count()) > 0) {
        const isNarrativeFirst = await page.evaluate(() => {
          const whatFor = document.querySelector('[data-testid="contextual-help-what-for-box"]');
          const sections = document.querySelector('[data-testid="contextual-help-sections-list"]');
          if (!whatFor || !sections) return true;
          return Boolean(whatFor.compareDocumentPosition(sections) & Node.DOCUMENT_POSITION_FOLLOWING);
        });
        expect(isNarrativeFirst).toBe(true);
      }
    }
  }
}

test.describe("Epic 29 — Canonical Page Headers, Monochrome Grammar & Bilingual FR/EN 8-Screen Audit", () => {
  test("verifies all 8 primary screens in FR and EN with canonical headers, <=1 Cobalt CTA, zero emojis, and clean console/HTTP", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "desktop cockpit coverage only");

    const unexpectedApiErrors = watchUnexpectedPageAndApiErrors(page);
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    resetDay0();
    await createFirstAdminViaUi(page);
    await configureActiveChatModelViaApi(page);
    const workspaceRef = await createOrgAndWorkspaceWithId(page, {
      name: "Espace Audit 29",
      slug: "espace-audit-29",
    });

    await assertPrimaryScreensInLocale(page, "fr");
    await switchUiLocaleViaUserSettings(page, "en");
    await assertPrimaryScreensInLocale(page, "en");

    expectDbRowExists(
      "SELECT id, email, platform_role FROM users WHERE email = :email AND platform_role = 'PLATFORM_ADMIN'",
      { email: E2E_ADMIN.email },
      "Day-0 platform admin persisted in PG18 users",
    );
    expectDbRowExists(
      "SELECT id, slug, name FROM workspaces WHERE slug = :slug",
      { slug: workspaceRef.slug },
      "Audit workspace persisted in PG18 workspaces",
    );
    expectDbRowExists(
      "SELECT user_id, locale FROM user_preferences WHERE locale = :locale",
      { locale: "en" },
      "English UI locale preference persisted in PG18 user_preferences",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM declarative_pack_bundles",
      undefined,
      1,
      "Declarative pack bundles synced in PG18",
    );

    expect(unexpectedApiErrors, unexpectedApiErrors.join("\n")).toEqual([]);
    expect(consoleErrors, consoleErrors.join("\n")).toEqual([]);
  });
});
