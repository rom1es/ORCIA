import { expect, test } from "@playwright/test";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi, E2E_ADMIN } from "./support/firstAdmin";
import { createBuAndTeamViaUi, createWorkspaceViaUi } from "./support/orgAndWorkspace";

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

  test("un dossier créé dans un espace est réhydraté depuis l'API après un vrai F5 (cache navigateur vidé)", async ({
    page,
  }) => {
    // Prérequis réel : un dossier appartient à un Espace de travail (aucun espace de repli fictif).
    await createBuAndTeamViaUi(page);
    await createWorkspaceViaUi(page, "Espace E2E Dossiers", "espace-e2e-dossiers");

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
    const overview = page.waitForResponse(
      (r) => r.url().includes("/api/v1/assistant/workspaces/") && r.url().endsWith("/overview"),
      { timeout: 30000 },
    );
    await page.reload();
    expect((await overview).status()).toBeLessThan(400);
    await page.getByRole("button", { name: /^Dossiers \(\d+\)$/ }).click();
    await expect(page.getByText("Dossier E2E persistant").first()).toBeVisible({ timeout: 20000 });
  });

  test("un dossier survit au redémarrage de l'API (persistance PostgreSQL)", async () => {
    // BUG-E2E-01b : le service des dossiers est encore en mémoire ; l'adaptateur SQL (tables 0025)
    // dépend d'AUTH-01 (propriétaire = vrai compte `users`, clé étrangère). À activer avec ce ticket.
    test.fixme(true, "BUG-E2E-01b : persistance PostgreSQL des dossiers (dépend d'AUTH-01)");
  });
});
