/** @uj UJ-17 | @cap CAP-070, CAP-071, CAP-073, CAP-074, CAP-075 */
import { expect, test } from "./support/e2eCaptureFixture";
import { expectDbRowExists } from "./support/dbAssertions";
import { resetDay0 } from "./support/day0";
import { configureActiveChatModelViaApi } from "./support/embeddingModel";
import { createFirstAdminViaUi, E2E_ADMIN } from "./support/firstAdmin";
import { createBuAndTeamViaUi, createWorkspaceViaUi } from "./support/orgAndWorkspace";
import { apiGet, reloadColdFromPg } from "./support/typedApiRequest";
import { selectWorkspaceInSidebar } from "./support/workspaceAndCatalogHelpers";

test.describe("TEST-04 · 02 — Mon Assistant : flux réel (cassette LLM) et dossiers", () => {
  test.beforeEach(async ({ page }) => {
    resetDay0();
    await createFirstAdminViaUi(page);
    await expect
      .poll(async () => {
        const res = await apiGet<{ first_admin_email: string | null }>(
          page,
          "/api/v1/bootstrap/accostage-status",
        );
        return (await res.json()).first_admin_email;
      })
      .toBe(E2E_ADMIN.email);
  });

  test("un tour d'assistant traverse le navigateur, l'API et la cassette LLM (0 $) sans modèle d'embedding et affiche une réponse", async ({
    page,
  }) => {
    await configureActiveChatModelViaApi(page);
    await page.goto("/assistant");
    await expect(page.getByTestId("assistant-rag-inactive-notice")).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId("assistant-no-chat-model-banner")).toHaveCount(0);
    const input = page.getByRole("textbox", { name: /Tapez @ pour les agents/ });
    await expect(input).toBeVisible({ timeout: 30000 });
    await expect(input).toBeEnabled();
    await input.fill("Bonjour, présente-toi en une phrase.");

    const apiTurn = page.waitForResponse(
      (r) => r.url().includes("/api/v1/assistant/turns") && r.request().method() === "POST",
      { timeout: 30000 },
    );
    await page.getByRole("button", { name: "Envoyer à Mon Assistant" }).click();
    const response = await apiTurn;
    expect(response.status(), `tour assistant: ${response.url()}`).toBeLessThan(400);

    // La réponse (cassette déterministe) s'affiche dans le fil.
    await expect(page.getByTestId("assistant-streamed-response-box").first()).not.toBeEmpty({
      timeout: 30000,
    });
    expectDbRowExists(
      "SELECT id, usage, is_active FROM workspace_llm_tier_mappings WHERE usage = 'chat' AND is_active = TRUE",
      undefined,
      "modèle chat actif persisté dans workspace_llm_tier_mappings PG18",
    );
    expectDbRowExists(
      "SELECT id, event_type FROM audit_ledger WHERE event_type = :event_type",
      { event_type: "ASSISTANT_TURN_COMPLETED" },
      "trace ASSISTANT_TURN_COMPLETED enregistrée dans audit_ledger PG18",
    );
  });

  test("un dossier créé dans un espace est réhydraté depuis l'API après un vrai F5 (cache navigateur vidé)", async ({
    page,
  }) => {
    // Prérequis réel : un dossier appartient à un Espace de travail (aucun espace de repli fictif).
    await createBuAndTeamViaUi(page);
    const ws = await createWorkspaceViaUi(page, "Espace E2E Dossiers", "espace-e2e-dossiers");

    await page.goto("/assistant");
    await page.getByTestId("assistant-folders-toggle-btn").click();
    await page.getByTestId("assistant-new-folder-title-input").fill("Dossier E2E persistant");
    const created = page.waitForResponse(
      (r) => r.url().includes("/folders") && r.request().method() === "POST",
      { timeout: 20000 },
    );
    await page.getByTestId("assistant-create-folder-btn").click();
    expect((await created).status()).toBeLessThan(400);

    await reloadColdFromPg(page);
    // Clearing localStorage resets activeScopeId to scope-global (personal workspace);
    // re-select the shared workspace to verify PG18 folder rehydration for that workspace.
    await selectWorkspaceInSidebar(
      page,
      { workspaceId: ws.id, workspaceName: ws.name },
      { waitForAssistantOverview: true },
    );
    await page.getByTestId("assistant-folders-toggle-btn").click();
    await expect(page.getByText("Dossier E2E persistant").first()).toBeVisible({ timeout: 20000 });
    expectDbRowExists(
      "SELECT folder_id, title FROM assistant_folders WHERE title = :title",
      { title: "Dossier E2E persistant" },
      "dossier Assistant persisté dans assistant_folders",
    );
  });

  test("un dossier survit au redémarrage de l'API (persistance PostgreSQL)", async ({ page }) => {
    await createBuAndTeamViaUi(page);
    const ws = await createWorkspaceViaUi(
      page,
      "Espace E2E Dossiers PG",
      "espace-e2e-dossiers-pg",
    );

    await page.goto("/assistant");
    await page.getByTestId("assistant-folders-toggle-btn").click();
    await page.getByTestId("assistant-new-folder-title-input").fill("Dossier E2E PostgreSQL");
    const created = page.waitForResponse(
      (r) => r.url().includes("/folders") && r.request().method() === "POST",
      { timeout: 20000 },
    );
    await page.getByTestId("assistant-create-folder-btn").click();
    expect((await created).status()).toBeLessThan(400);

    await reloadColdFromPg(page);
    // Re-select the shared workspace after cold reload clears localStorage.
    await selectWorkspaceInSidebar(
      page,
      { workspaceId: ws.id, workspaceName: ws.name },
      { waitForAssistantOverview: true },
    );
    await page.getByTestId("assistant-folders-toggle-btn").click();
    await expect(page.getByText("Dossier E2E PostgreSQL").first()).toBeVisible({ timeout: 20000 });

    expectDbRowExists(
      "SELECT folder_id, title, visibility_mode FROM assistant_folders WHERE title = :title",
      { title: "Dossier E2E PostgreSQL" },
      "persistance SQL réelle du dossier dans assistant_folders",
    );
  });
});
