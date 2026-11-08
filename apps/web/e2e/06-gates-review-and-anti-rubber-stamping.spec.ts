import { expect, test } from "@playwright/test";
import { watchApiServerErrors } from "./support/apiErrors";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi } from "./support/firstAdmin";

/**
 * TEST-05 · 06 — Gates tri-modales (UJ-6, Epic 4, FR-6/FR-18/FR-19).
 *
 * Vérifie bout en bout :
 * 1. Ouverture d'une revue humaine adaptative (Briefing 4 blocs + découpage + action Jira STAGED).
 * 2. Inspection explicite du Bloc 4 (`Hypothèses Retenues`) encadré en ambre.
 * 3. Validation / co-édition des sections (`chunk-validation-card-*`).
 * 4. Déclenchement du garde-fou anti-rubber-stamping (`< 15 s` sur `> 1 000` mots) tant côté API
 *    (`422 ERR_RUBBER_STAMPING_GUARD_TRIGGERED` sans confirmation explicite) que côté modale UI.
 * 5. Confirmation explicite des hypothèses -> Gate `PASS` + exécution de l'action Jira (`EXECUTED`)
 *    et survie de l'état au rafraîchissement (`F5` après purge du stockage navigateur).
 */
test.describe("TEST-05 · 06 — Gates : briefing de revue et anti-rubber-stamping", () => {
  test("inspection du Bloc 4, approbation par découpage, garde-fou < 15 s, action Jira et survie F5", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "parcours complet : bureau");
    resetDay0();
    await createFirstAdminViaUi(page);

    const serverErrors = watchApiServerErrors(page);
    await page.goto("/gates");
    await expect(page.getByTestId("gates-adaptive-human-review-section")).toBeVisible({
      timeout: 30000,
    });

    // 1. Préparer la revue humaine (4 blocs + sections > 1 000 mots + action Jira STAGED)
    await page.getByTestId("gates-open-human-review-btn").click();
    await expect(page.getByTestId("review-briefing-grid")).toBeVisible();
    await expect(page.getByTestId("gates-human-evaluation-status-badge")).toContainText(
      "PENDING_HUMAN_REVIEW",
    );
    await expect(page.getByTestId("gates-staged-jira-status-badge")).toContainText("STAGED");

    // 2. Tant que le Bloc 4 et les sections sont en attente, le bouton de finalisation est désactivé
    await expect(page.getByTestId("review-briefing-block-4")).toHaveAttribute(
      "data-amber-highlighted",
      "true",
    );
    await expect(page.getByTestId("finalize-human-gate-btn")).toBeDisabled();

    // 3. Inspecter le Bloc 4 (Hypothèses Retenues) et valider/co-éditer chaque découpage
    await page.getByTestId("inspect-hypotheses-btn").click();
    await expect(page.getByTestId("review-briefing-block-4")).toHaveAttribute(
      "data-amber-highlighted",
      "false",
    );

    await page.getByTestId("chunk-approve-btn-sec-architecture").click();
    await expect(page.getByTestId("chunk-status-badge-sec-architecture")).toHaveText("APPROVED");

    await page.getByTestId("chunk-coedit-btn-sec-security-jira").click();
    await expect(page.getByTestId("chunk-status-badge-sec-security-jira")).toHaveText("CO_EDITED");

    // 4. Vérifier que le garde-fou API rejette une finalisation < 15 s sans confirmation explicite
    const listRes = await page.request.get("/api/v1/gates/human/evaluations");
    expect(listRes.ok()).toBeTruthy();
    const listBody = (await listRes.json()) as {
      evaluations: Array<{ id: string }>;
    };
    const evalId = listBody.evaluations[listBody.evaluations.length - 1]?.id ?? "";
    expect(evalId).toBeTruthy();

    const prematureRes = await page.request.post(`/api/v1/gates/human/${evalId}/finalize`, {
      data: {
        review_duration_ms: 2100,
        explicit_hypotheses_confirmation: false,
      },
    });
    expect(prematureRes.status()).toBe(422);
    const prematureProblem = (await prematureRes.json()) as { error_code?: string };
    expect(prematureProblem.error_code).toBe("ERR_RUBBER_STAMPING_GUARD_TRIGGERED");

    // 5. Cliquer sur Finaliser dans l'UI (< 15 s sur > 1 000 mots) -> ouvre la modale de garde-fou
    await expect(page.getByTestId("finalize-human-gate-btn")).toBeEnabled();
    await page.getByTestId("finalize-human-gate-btn").click();
    const guardModal = page.getByTestId("anti-rubber-stamping-guard-modal");
    await expect(guardModal).toBeVisible();
    await expect(page.getByTestId("rubber-stamp-confirm-submit-btn")).toBeDisabled();

    // 6. Cocher la confirmation explicite et soumettre -> Gate PASS + Jira EXECUTED
    await page.getByTestId("rubber-stamp-confirm-checkbox").check();
    await expect(page.getByTestId("rubber-stamp-confirm-submit-btn")).toBeEnabled();
    await page.getByTestId("rubber-stamp-confirm-submit-btn").click();

    await expect(page.getByTestId("gates-human-evaluation-status-badge")).toContainText("PASS");
    await expect(page.getByTestId("gates-staged-jira-status-badge")).toContainText("EXECUTED");

    // 7. Survie au F5 après purge du stockage navigateur
    await page.evaluate(() => {
      window.localStorage.clear();
      window.sessionStorage.clear();
    });
    await page.reload();
    await expect(page.getByTestId("gates-human-evaluation-status-badge")).toContainText("PASS", {
      timeout: 20000,
    });
    await expect(page.getByTestId("gates-staged-jira-status-badge")).toContainText("EXECUTED");
    expect(serverErrors, serverErrors.join("\n")).toEqual([]);
  });
});
