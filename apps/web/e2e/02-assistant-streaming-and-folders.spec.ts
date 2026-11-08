import { expect, test } from "@playwright/test";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi, E2E_ADMIN } from "./support/firstAdmin";

test.describe("TEST-04 · 02 — Mon Assistant : flux réel (cassette LLM) et dossiers", () => {
  test.beforeEach(async ({ page }) => {
    resetDay0();
    await createFirstAdminViaUi(page);
    await expect
      .poll(async () => {
        const res = await page.request.get("/api/v1/bootstrap/accostage-status");
        return ((await res.json()) as { first_admin_email: string | null }).first_admin_email;
      })
      .toBe(E2E_ADMIN.email);
  });

  test("un tour d'assistant traverse le navigateur, l'API et la cassette LLM (0 $) et affiche une réponse", async ({
    page,
  }) => {
    await page.goto("/assistant");
    const input = page.getByRole("textbox", { name: /Tapez @ pour les agents/ });
    await expect(input).toBeVisible({ timeout: 30000 });
    await input.fill("Bonjour, présente-toi en une phrase.");

    const apiTurn = page.waitForResponse(
      (r) => r.url().includes("/api/v1/assistant/") && r.request().method() === "POST",
      { timeout: 30000 },
    );
    await page.getByRole("button", { name: "Envoyer à Mon Assistant" }).click();
    const response = await apiTurn;
    expect(response.status(), `tour assistant: ${response.url()}`).toBeLessThan(400);

    // La réponse (cassette déterministe) s'affiche dans le fil.
    await expect(page.getByTestId("assistant-streamed-response-box").first()).not.toBeEmpty({
      timeout: 30000,
    });
  });

  test("un dossier créé survit à un vrai F5 (réhydratation depuis PostgreSQL)", async ({ page }) => {
    // DÉFAUT PRODUIT RÉEL (BUG-E2E-01) : après F5 sans localStorage, « Dossiers (0) » — les dossiers
    // ne sont réhydratés que depuis localStorage (aucun GET au démarrage sans espace de travail).
    // `test.fail` : le test passe tant que le défaut existe et ÉCHOUE dès qu'il est corrigé
    // (retirer alors cette ligne).
    test.fail(true, "BUG-E2E-01 : dossiers non réhydratés depuis PostgreSQL après F5");
    await page.goto("/assistant");
    await page.getByRole("button", { name: /^Dossiers \(\d+\)$/ }).click();
    await page.getByTestId("assistant-new-folder-title-input").fill("Dossier E2E persistant");
    const created = page.waitForResponse(
      (r) => r.url().includes("/folders") && r.request().method() === "POST",
      { timeout: 20000 },
    );
    await page.getByTestId("assistant-create-folder-btn").click();
    expect((await created).status()).toBeLessThan(400);

    await page.evaluate(() => {
      window.localStorage.clear();
      window.sessionStorage.clear();
    });
    await page.reload();
    await page.getByRole("button", { name: /^Dossiers \(\d+\)$/ }).click();
    await expect(page.getByText("Dossier E2E persistant").first()).toBeVisible({ timeout: 20000 });
  });
});
