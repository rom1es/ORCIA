import { expect, test } from "@playwright/test";
import { watchApiServerErrors } from "./support/apiErrors";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi } from "./support/firstAdmin";

const FORBIDDEN_JARGON_REGEX =
  /\b(DBOS|asyncio|SQL|Redis|SSE|Claim-Check|déterministe|non-déterministe|deterministic|non-deterministic)\b/i;

test.describe("TEST-06 · 09 — Mes Processus (Objectif vs Jalons), Studio 5 blocs & aide contextuelle ⓘ", () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "parcours bureau");
    resetDay0();
    await createFirstAdminViaUi(page);
  });

  test("affiche les badges Objectif/Jalons sans jargon, persiste le basculement Studio en PostgreSQL 18 après F5 et ouvre l'aide ⓘ", async ({
    page,
  }) => {
    const serverErrors = watchApiServerErrors(page);
    await page.goto("/processes");

    const hub = page.getByTestId("processes-hub-v2-page");
    await expect(hub).toBeVisible({ timeout: 30000 });
    await expect(
      page.getByText("Génération & Validation d'Article d'Aide Contextuelle ORCIA").first(),
    ).toBeVisible();
    await expect(
      page.getByText("Qualification de demande, Rédaction PRD & Création Feature Jira").first(),
    ).toBeVisible();

    await expect(
      page.getByTestId("workflow-card-mode-badge-wf-generate-orcia-documentation"),
    ).toContainText("Piloté par l'objectif");
    await expect(
      page.getByTestId("workflow-card-mode-badge-wf-01-qualification-prd"),
    ).toContainText("Piloté par les jalons");

    const hubVisibleText = await hub.innerText();
    expect(hubVisibleText).not.toMatch(FORBIDDEN_JARGON_REGEX);

    // Bouton ⓘ → colonne d'aide contextuelle (zone 4).
    const helpColumn = page.getByTestId("four-zone-contextual-help-column");
    if (!(await helpColumn.isVisible())) {
      await page.getByTestId("topbar-contextual-help-toggle").click();
    }
    await expect(helpColumn).toBeVisible();
    await expect(page.getByTestId("contextual-help-hybrid-panel")).toBeVisible();
    await page.getByTestId("contextual-help-close-btn").click();
    await expect(helpColumn).toBeHidden();

    // Ouverture du Studio 5 blocs sur wf-01-qualification-prd, basculement en mode Objectif et survie F5 via PG18
    await page.getByTestId("open-studio-btn-wf-01-qualification-prd").click();
    await expect(page.getByTestId("workflow-five-blocks-studio-page")).toBeVisible({
      timeout: 30000,
    });
    await expect(page.getByTestId("mode-option-milestone-driven")).toHaveAttribute(
      "aria-checked",
      "true",
    );

    await page.getByTestId("mode-option-goal-driven").click();
    await expect(page.getByTestId("mode-option-goal-driven")).toHaveAttribute(
      "aria-checked",
      "true",
    );

    const customObjective =
      "Qualifier la demande client de manière adaptative et produire une synthèse priorisée.";
    await page.getByTestId("studio-goal-reflexive-objective-input").fill(customObjective);
    await page.getByTestId("toggle-delegate-agent-orchestrateur-produit").click();

    await Promise.all([
      page.waitForResponse(
        (res) =>
          res.url().includes("/api/v1/workflows/v2/wf-01-qualification-prd") &&
          res.request().method() === "PUT" &&
          res.status() === 200,
      ),
      page.getByTestId("studio-save-draft-btn").click(),
    ]);

    // Vider le cache localStorage pour prouver la réhydratation réelle depuis PostgreSQL 18 au F5
    await page.evaluate(() => {
      window.localStorage.removeItem("orcia_studio_v2_workflows");
    });
    await page.reload();

    await expect(page.getByTestId("workflow-five-blocks-studio-page")).toBeVisible({
      timeout: 30000,
    });
    await expect(page.getByTestId("mode-option-goal-driven")).toHaveAttribute(
      "aria-checked",
      "true",
      { timeout: 15000 },
    );
    await expect(page.getByTestId("studio-goal-reflexive-objective-input")).toHaveValue(
      customObjective,
    );

    const studioVisibleText = await page
      .getByTestId("workflow-five-blocks-studio-page")
      .innerText();
    expect(studioVisibleText).not.toMatch(FORBIDDEN_JARGON_REGEX);
    expect(serverErrors, serverErrors.join("\n")).toEqual([]);
  });
});
