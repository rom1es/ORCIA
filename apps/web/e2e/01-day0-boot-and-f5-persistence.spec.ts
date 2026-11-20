/** @uj UJ-13 | @cap CAP-004, CAP-005, CAP-061 */
import { expect, test } from "./support/e2eCaptureFixture";
import { expectDbRowExists, queryDbRows } from "./support/dbAssertions";
import { configureActiveEmbeddingModelViaApi } from "./support/embeddingModel";
import { createFirstAdminViaUi, E2E_ADMIN } from "./support/firstAdmin";
import { resetDay0 } from "./support/day0";
import { apiGet, reloadColdFromPg } from "./support/typedApiRequest";

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
          const res = await apiGet<{ first_admin_email: string | null }>(
            page,
            "/api/v1/bootstrap/accostage-status",
          );
          return res.ok() ? await res.json() : null;
        },
        { timeout: 20000, message: "le premier admin doit être persisté côté API/PostgreSQL" },
      )
      .toMatchObject({ first_admin_email: E2E_ADMIN.email });

    // Vrai F5 à froid : éviction des caches RAM API + purge navigateur — seule la base PostgreSQL peut réhydrater.
    await reloadColdFromPg(page);

    await expect(page.getByTestId("four-zone-direction-c-shell")).toBeVisible({ timeout: 30000 });
    await expect(page.getByTestId("first-boot-admin-setup-modal")).toBeHidden({ timeout: 15000 });
    // Réhydraté depuis l'API : l'accostage-status reste « initialisé » après le rechargement.
    const after = await apiGet<{ first_admin_initialized: boolean }>(
      page,
      "/api/v1/bootstrap/accostage-status",
    );
    expect((await after.json()).first_admin_initialized).toBe(true);
    expectDbRowExists(
      "SELECT id, email, platform_role FROM users WHERE email = :email AND platform_role = 'PLATFORM_ADMIN'",
      { email: E2E_ADMIN.email },
      "premier administrateur persisté dans users",
    );

    // Story 25.1: espace personnel PRIVATE_USER créé automatiquement en PG18 sans valider le jalon 4 d'équipe
    expectDbRowExists(
      "SELECT id, slug, visibility_mode FROM workspaces WHERE slug LIKE 'personal-%' AND visibility_mode = 'CONFIDENTIAL_RESTRICTED'",
      undefined,
      "espace personnel privé provisionné automatiquement pour le premier admin",
    );

    // Story 25.1: guide unifié 6 jalons non repliable tant que < 6/6, sans sous-blocs Step 1/2/3
    await expect(page.getByTestId("accostage-milestones-list")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("accostage-milestones-list").locator("button")).toHaveCount(6);
    await expect(page.getByTestId("progressive-day0-accostage-banner")).not.toContainText(
      /Step [123]:|6-step setup path/i,
    );
    await expect(page.getByTestId("accostage-compact-toggle-btn")).toHaveCount(0);
    await expect(page.getByTestId("progressive-day0-accostage-banner")).toHaveAttribute(
      "data-compact",
      "false",
    );
    await expect(page.getByTestId("accostage-progress-pill")).toHaveText("1 / 6 complétées");
    const teamSpaceMilestone = page.getByTestId("accostage-milestone-step-workspaces");
    await expect(teamSpaceMilestone).toContainText("4. Premier Espace d'équipe");
    await expect(teamSpaceMilestone).toHaveAttribute("data-completed", "false");

    // 0 modèle IA -> Mes Processus grisé dans la barre latérale ET dans les cartes Cockpit
    await expect(page.getByTestId("eight-menu-item-processes")).toBeDisabled();
    await expect(page.getByTestId("cockpit-orientation-card-processes")).toBeDisabled();

    // Story 25.1: 1 modèle IA actif + Espace Personnel -> 2/6 et dégrisage immédiat de Mes Processus (sidebar + Cockpit)
    await configureActiveEmbeddingModelViaApi(page);
    await reloadColdFromPg(page);
    await expect(page.getByTestId("accostage-progress-pill")).toHaveText("2 / 6 complétées", {
      timeout: 20000,
    });
    await expect(page.getByTestId("accostage-milestone-step-workspaces")).toHaveAttribute(
      "data-completed",
      "false",
    );
    await expect(page.getByTestId("eight-menu-item-processes")).toBeEnabled({ timeout: 15000 });
    await expect(page.getByTestId("cockpit-orientation-card-processes")).toBeEnabled({
      timeout: 15000,
    });

    // USER24-BUG-2: vérifier le vrai nom d'admin et cliquer sur '1. Compte Admin' -> /profile sans 'Not Found'
    await expect(page.getByTestId("welcome-setup-admin-identity-name")).toContainText(
      E2E_ADMIN.name,
    );
    const firstAdminMilestone = page.getByTestId("accostage-milestone-first-admin");
    await expect(firstAdminMilestone).toBeVisible({ timeout: 15000 });
    await firstAdminMilestone.click();
    await expect(page).toHaveURL(/\/profile(?:\?|$)/, { timeout: 15000 });
    await expect(page.locator("body")).not.toContainText("Not Found");
  });

  test("après reset Jour 0, la modale revient (0 utilisateur en base)", async ({ page }) => {
    await createFirstAdminViaUi(page);
    resetDay0();
    await page.evaluate(() => window.localStorage.clear());
    await page.reload();
    await expect(page.getByTestId("first-boot-admin-setup-modal")).toBeVisible({ timeout: 30000 });
    const countRows = queryDbRows<{ count: number }>("SELECT COUNT(*)::int AS count FROM users");
    expect(countRows[0]?.count).toBe(0);
  });
});
