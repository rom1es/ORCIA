import { expect, test } from "@playwright/test";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi } from "./support/firstAdmin";
import { createBuAndTeamViaUi, createWorkspaceViaUi } from "./support/orgAndWorkspace";

test.describe("TEST-05 · 07 — Mes Espaces : organisation, espace de travail et vrai F5", () => {
  test.beforeEach(async ({ page }) => {
    resetDay0();
    await createFirstAdminViaUi(page);
  });

  test("BU + équipe + espace créés par l'UI sont persistés côté API et survivent à un F5", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "parcours de saisie : bureau");
    await createBuAndTeamViaUi(page);
    await createWorkspaceViaUi(page, "Espace E2E Comptabilité", "espace-e2e-compta");

    // Persistance côté serveur (PostgreSQL) — et non seulement dans le navigateur.
    await expect
      .poll(
        async () => {
          const res = await page.request.get("/api/v1/bootstrap/platform-setup-state");
          const body = (await res.json()) as { org_units: unknown[]; workspaces: unknown[] };
          return { orgUnits: body.org_units.length, workspaces: body.workspaces.length };
        },
        { timeout: 20000 },
      )
      .toEqual({ orgUnits: 2, workspaces: 1 });

    await page.evaluate(() => {
      window.localStorage.clear();
      window.sessionStorage.clear();
    });
    await page.goto("/spaces");
    await expect(page.getByText("Espace E2E Comptabilité").first()).toBeVisible({ timeout: 20000 });
  });
});
