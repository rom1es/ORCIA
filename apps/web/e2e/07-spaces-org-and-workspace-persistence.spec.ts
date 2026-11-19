/** @uj UJ-9, UJ-14, UJ-18 | @cap CAP-050, CAP-067, CAP-080 */
import { expect, test } from "./support/e2eCaptureFixture";
import { expectDbRowExists } from "./support/dbAssertions";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi } from "./support/firstAdmin";
import { createBuAndTeamViaUi, createWorkspaceViaUi } from "./support/orgAndWorkspace";
import { apiGet, reloadColdFromPg } from "./support/typedApiRequest";

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
          const res = await apiGet<{ org_units: unknown[]; workspaces: unknown[] }>(
            page,
            "/api/v1/bootstrap/platform-setup-state",
          );
          const body = await res.json();
          return { orgUnits: body.org_units.length, workspaces: body.workspaces.length };
        },
        { timeout: 20000 },
      )
      .toEqual({ orgUnits: 2, workspaces: 1 });

    await page.goto("/spaces");
    await reloadColdFromPg(page);
    await expect(page.getByText("Espace E2E Comptabilité").first()).toBeVisible({ timeout: 20000 });
    expectDbRowExists(
      "SELECT id, slug, unit_type FROM org_units WHERE slug = :slug AND unit_type = 'BU'",
      { slug: "bu-e2e" },
      "Direction BU persistée dans org_units PG18",
    );
    expectDbRowExists(
      "SELECT id, slug, unit_type FROM org_units WHERE slug = :slug AND unit_type = 'TEAM'",
      { slug: "team-e2e" },
      "Équipe persistée dans org_units PG18",
    );
    expectDbRowExists(
      "SELECT id, slug, name FROM workspaces WHERE slug = :slug",
      { slug: "espace-e2e-compta" },
      "Espace de travail persisté dans workspaces PG18",
    );
  });
});
