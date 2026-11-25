/** @uj UJ-9, UJ-14, UJ-18 | @cap CAP-050, CAP-067, CAP-080 */
import { expect, test } from "./support/e2eCaptureFixture";
import { switchUiLocaleViaUserSettings } from "./helpers/bilingualI18nHelpers";
import { getBearerTokenFromSession } from "./support/authAndOrgHelpers";
import { expectDbRowExists } from "./support/dbAssertions";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi } from "./support/firstAdmin";
import { createBuAndTeamViaUi, createWorkspaceViaUi } from "./support/orgAndWorkspace";
import { apiGet, reloadColdFromPg } from "./support/typedApiRequest";

test.describe("TEST-05 · 07 — My Spaces: organization, workspace and real F5", () => {
  test.beforeEach(async ({ page }) => {
    resetDay0();
    await createFirstAdminViaUi(page);
  });

  test("BU + team + workspace created via UI persist on API and survive F5 in FR and EN", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "desktop input journey only");
    await createBuAndTeamViaUi(page);
    await createWorkspaceViaUi(page, "Espace E2E Comptabilité", "espace-e2e-compta");

    // Verify server-side persistence in PostgreSQL (not only browser state).
    const adminToken = await getBearerTokenFromSession(page);
    await expect
      .poll(
        async () => {
          const [orgRes, wsRes] = await Promise.all([
            apiGet<{ org_units: unknown[] }>(page, "/api/v1/org-units", { token: adminToken }),
            apiGet<{ workspaces: Array<{ is_personal?: boolean }> }>(page, "/api/v1/workspaces", {
              token: adminToken,
            }),
          ]);
          if (!orgRes.ok() || !wsRes.ok()) return { orgUnits: -1, workspaces: -1 };
          const orgBody = await orgRes.json();
          const wsBody = await wsRes.json();
          const nonPersonalCount = (wsBody.workspaces ?? []).filter((w) => !w.is_personal).length;
          return { orgUnits: orgBody.org_units.length, workspaces: nonPersonalCount };
        },
        { timeout: 20000 },
      )
      .toEqual({ orgUnits: 2, workspaces: 1 });

    await page.goto("/spaces");
    await reloadColdFromPg(page);
    await expect(page.getByTestId("workspaces-compact-header")).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId("sidebar-unified-scope-selector").locator("select")).toHaveCount(1);
    const scopeSelect = page.getByTestId("sidebar-workspace-selector");
    await expect(scopeSelect).toBeVisible();
    await expect(scopeSelect).toContainText("Espace E2E Comptabilité");
    const comptaOptionValue = await scopeSelect
      .locator("option")
      .filter({ hasText: "Espace E2E Comptabilité" })
      .first()
      .getAttribute("value");
    expect(comptaOptionValue).toBeTruthy();
    await scopeSelect.selectOption(comptaOptionValue!);
    await expect(scopeSelect).toHaveValue(comptaOptionValue!);
    await page.getByTestId("eight-menu-item-finops").click();
    await expect(page).toHaveURL(/\/finops$/);
    await expect(page.getByTestId("sidebar-workspace-selector")).toHaveValue(comptaOptionValue!);
    // Real user F5 reload (evict server RAM cache while keeping active workspace in localStorage)
    await reloadColdFromPg(page, { clearBrowserStorage: false });
    await expect(page.getByTestId("sidebar-workspace-selector")).toHaveValue(comptaOptionValue!, {
      timeout: 20000,
    });
    await page.getByTestId("eight-menu-item-spaces").click();
    await expect(page).toHaveURL(/\/spaces$/);
    await expect(page.getByTestId("sidebar-workspace-selector")).toHaveValue(comptaOptionValue!);
    await expect(page.getByTestId("workspaces-compact-header")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("workspaces-active-title")).toHaveText("Espace E2E Comptabilité");
    await expect(page.getByTestId("workspace-five-tabs-view")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("workspace-five-tabs-view").locator('[role="tablist"]')).toHaveCount(1);
    await expect(page.getByTestId("workspace-five-tabs-view").locator('[role="tab"]')).toHaveCount(5);
    await expect(page.getByTestId("dna-starlark-glossary-view")).toHaveCount(0);
    await expect(page.getByTestId("workspace-tab-GLOSSARY_RULES")).toBeVisible();
    await page.getByTestId("workspace-tab-GLOSSARY_RULES").click();
    await expect(page.getByTestId("dna-starlark-glossary-view")).toBeVisible({ timeout: 15000 });

    // Bilingual English (en) verification on /spaces, then restore French (fr)
    await switchUiLocaleViaUserSettings(page, "en");
    await expect(page.getByTestId("toggle-create-workspace-form-btn")).toContainText("+ New space");
    await expect(page.getByTestId("workspace-tab-OVERVIEW")).toContainText("Overview");
    await expect(page.getByTestId("workspace-tab-GLOSSARY_RULES")).toContainText("Glossary");
    await switchUiLocaleViaUserSettings(page, "fr");

    expectDbRowExists(
      "SELECT id, slug, unit_type FROM org_units WHERE slug = :slug AND unit_type = 'BU'",
      { slug: "bu-e2e" },
      "BU persisted in PG18 org_units",
    );
    expectDbRowExists(
      "SELECT id, slug, unit_type FROM org_units WHERE slug = :slug AND unit_type = 'TEAM'",
      { slug: "team-e2e" },
      "Team persisted in PG18 org_units",
    );
    expectDbRowExists(
      "SELECT id, slug, name FROM workspaces WHERE slug = :slug",
      { slug: "espace-e2e-compta" },
      "Workspace persisted in PG18 workspaces",
    );
  });
});
