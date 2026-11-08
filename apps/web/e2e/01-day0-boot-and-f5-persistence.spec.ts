import { expect, test } from "@playwright/test";
import { createFirstAdminViaUi, E2E_ADMIN } from "./support/firstAdmin";
import { resetDay0 } from "./support/day0";

test.describe("TEST-04 · 01 — Boot Jour 0, premier administrateur et vrai F5 (BDD)", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("le premier administrateur créé survit à un F5 sans localStorage (réhydratation PostgreSQL)", async ({
    page,
  }) => {
    await createFirstAdminViaUi(page);

    // L'API a bien persisté l'administrateur côté serveur.
    // (l'appel `createWelcomeSetupFirstAdmin` de l'UI est asynchrone : on attend la persistance)
    await expect
      .poll(
        async () => {
          const res = await page.request.get("/api/v1/bootstrap/accostage-status");
          return res.ok() ? ((await res.json()) as { first_admin_email: string | null }) : null;
        },
        { timeout: 20000, message: "le premier admin doit être persisté côté API/PostgreSQL" },
      )
      .toMatchObject({ first_admin_email: E2E_ADMIN.email });

    // Vrai F5 : on efface tout stockage navigateur — seule la base PostgreSQL peut réhydrater.
    await page.evaluate(() => {
      window.localStorage.clear();
      window.sessionStorage.clear();
    });
    await page.reload();

    await expect(page.getByTestId("four-zone-direction-c-shell")).toBeVisible({ timeout: 30000 });
    await expect(page.getByTestId("first-boot-admin-setup-modal")).toBeHidden({ timeout: 15000 });
    // Réhydraté depuis l'API : l'accostage-status reste « initialisé » après le rechargement.
    const after = await page.request.get("/api/v1/bootstrap/accostage-status");
    expect(((await after.json()) as { first_admin_initialized: boolean }).first_admin_initialized).toBe(true);
  });

  test("après reset Jour 0, la modale revient (0 utilisateur en base)", async ({ page }) => {
    await createFirstAdminViaUi(page);
    resetDay0();
    await page.evaluate(() => window.localStorage.clear());
    await page.reload();
    await expect(page.getByTestId("first-boot-admin-setup-modal")).toBeVisible({ timeout: 30000 });
  });
});
