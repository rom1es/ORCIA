/** @uj UJ-20 | @cap CAP-062 */
import { expect, test } from "./support/e2eCaptureFixture";
import { watchApiServerErrors } from "./support/apiErrors";
import { resetDay0 } from "./support/day0";
import { expectDbRowCount, expectDbRowExists } from "./support/dbAssertions";
import { configureActiveEmbeddingModelViaApi } from "./support/embeddingModel";
import { createFirstAdminViaUi, E2E_ADMIN } from "./support/firstAdmin";

test.describe("TEST-06 · 10 — Recherche ⌘K à 2 vitesses", () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "raccourci clavier : bureau");
    resetDay0();
    await createFirstAdminViaUi(page);
    await page.goto("/cockpit");
    await expect(page.getByTestId("four-zone-direction-c-shell")).toBeVisible({ timeout: 30000 });
  });

  test("Ctrl+K ouvre la palette, accepte une saisie et Escape la ferme", async ({ page }) => {
    const serverErrors = watchApiServerErrors(page);
    await page.keyboard.press("Control+k");
    const palette = page.getByTestId("top-header-search-command");
    await expect(palette).toBeVisible();
    await page.getByTestId("cmdk-search-input").fill("agents");
    await page.keyboard.press("Escape");
    await expect(palette).toBeHidden();
    expect(serverErrors, serverErrors.join("\n")).toEqual([]);
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM catalog_items",
      undefined,
      1,
      "entrées catalogue indexables présentes dans catalog_items PG18",
    );
    expectDbRowExists(
      "SELECT id, email FROM users WHERE email = :email",
      { email: E2E_ADMIN.email },
      "session admin présente dans users PG18",
    );
  });

  test("la recherche fédérée (vitesse 2) aboutit côté API", async ({ page }) => {
    await configureActiveEmbeddingModelViaApi(page);
    await page.keyboard.press("Control+k");
    await page.getByTestId("cmdk-search-input").fill("agents");
    const federated = page.waitForResponse(
      (r) => r.url().includes("/api/") && /search/i.test(r.url()),
      { timeout: 20000 },
    );
    await page.getByTestId("cmdk-trigger-speed2-btn").click();
    const res = await federated;
    expect(res.status(), "recherche fédérée (vitesse 2)").toBeLessThan(400);
    await expect(page.getByTestId("cmdk-speed2-error-banner")).toHaveCount(0);
    await expect(page.getByTestId("cmdk-speed2-appended-group")).toBeVisible();
    expectDbRowExists(
      "SELECT id, usage, is_active FROM workspace_llm_tier_mappings WHERE usage = 'embedding' AND is_active = TRUE",
      undefined,
      "modèle d'embedding actif persisté dans workspace_llm_tier_mappings PG18",
    );
  });
});
