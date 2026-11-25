/** @uj UJ-11, UJ-12 | @cap CAP-201 */
import { expect, test } from "./support/e2eCaptureFixture";
import { expectDbRowExists } from "./support/dbAssertions";
import {
  expectZeroVisibleErrorBanners,
  watchUnexpectedPageAndApiErrors,
} from "./support/apiErrors";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi } from "./support/firstAdmin";
import { createBuAndTeamViaUi, createWorkspaceViaUi } from "./support/orgAndWorkspace";
import { apiGet, apiPost, reloadColdFromPg } from "./support/typedApiRequest";

test.describe("TEST-07 · 13 — Story 7.4 Gouvernance & Supervision des Exécutions Autonomes", () => {
  test("bureau : Publication V2 + contrat + déclencheur + supervision /processes + arrêt d'urgence F5 + /finops échantillon & rollback F5", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "parcours bureau");
    const errors = watchUnexpectedPageAndApiErrors(page);
    resetDay0();
    await createFirstAdminViaUi(page);
    await createBuAndTeamViaUi(page);
    await createWorkspaceViaUi(page, "Espace Autonome E2E", "ws-auto-e2e");

    // 1. Sur /finops sans run autonome : section autonome strictement masquée
    await page.goto("/finops");
    await expect(page.getByTestId("finops-governance-dashboard")).toBeVisible({ timeout: 30000 });
    await page.getByTestId("finops-tab-cognitive-governance").click();
    await expect(page.getByTestId("finops-human-mastery-tab")).toBeVisible();
    await expect(page.getByTestId("finops-autonomous-governance-section")).toHaveCount(0);

    // 2. Récupérer le JWT admin (cookie refresh) + le workspace réel et créer un SP éligible
    const refreshRes = await apiPost<{ access_token?: string }>(page, "/api/v1/auth/refresh");
    expect(refreshRes.status()).toBe(200);
    const refreshJson = await refreshRes.json();
    const adminToken = refreshJson.access_token ?? "";
    expect(adminToken).not.toBe("");

    const wsRes = await apiGet<{
      workspaces?: Array<{ id?: string; slug?: string; is_personal?: boolean }>;
    }>(page, "/api/v1/workspaces", { token: adminToken });
    expect(wsRes.status()).toBe(200);
    const wsPayload = await wsRes.json();
    const targetWs =
      (wsPayload.workspaces ?? []).find((w) => w.slug === "ws-auto-e2e") ??
      (wsPayload.workspaces ?? []).find((w) => !w.is_personal);
    const wsId = targetWs?.id ?? "";
    expect(wsId).not.toBe("");

    const spRes = await apiPost(page, "/api/v1/settings/iam/accounts", {
      token: adminToken,
      data: {
        principal_id: "sp-e2e-auto-docs",
        display_name: "Robot Documentation E2E",
        account_kind: "SERVICE_PRINCIPAL",
        roles: ["TEAM_LEAD"],
        team_ids: [wsId],
      },
    });
    expect([200, 201]).toContain(spRes.status());

    // 3. Ouvrir le Studio V2 -> publier via API PUT /api/v1/workflows/v2/{id}
    await page.goto("/processes/studio/wf-01-qualification-prd");
    await expect(page.getByTestId("studio-publish-workflow-btn")).toBeVisible({ timeout: 30000 });
    const [pubResp] = await Promise.all([
      page.waitForResponse(
        (res) =>
          res.url().includes("/api/v1/workflows/v2/wf-01-qualification-prd") &&
          res.request().method() === "PUT",
      ),
      page.getByTestId("studio-publish-workflow-btn").click(),
    ]);
    expect(pubResp.status()).toBe(200);
    await expect(page.getByTestId("studio-status-banner")).toBeVisible({ timeout: 10000 });

    // Signer le contrat d'autonomie + créer un déclencheur manuel et l'exécuter
    await page.getByTestId("studio-autonomy-contract-btn").click();
    await expect(page.getByTestId("autonomy-contract-modal")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("autonomy-contract-sp-select")).toBeVisible();
    await page.getByTestId("autonomy-contract-sign-btn").click();
    await expect(page.getByTestId("studio-autonomy-contract-active-badge")).toBeVisible({
      timeout: 15000,
    });

    await page.getByTestId("studio-triggers-btn").click();
    await expect(page.getByTestId("workflow-triggers-modal")).toBeVisible({ timeout: 15000 });
    await page.getByTestId("trigger-create-type-select").selectOption("MANUAL_AUTONOMOUS");
    await page.getByTestId("trigger-create-submit-btn").click();

    const fireBtn = page.locator("[data-testid^='trigger-fire-btn-']").first();
    await expect(fireBtn).toBeVisible({ timeout: 15000 });
    const [fireResp] = await Promise.all([
      page.waitForResponse(
        (res) => res.url().includes("/fire") && res.request().method() === "POST",
      ),
      fireBtn.click(),
    ]);
    expect(fireResp.status()).toBe(201);
    const fireJson = (await fireResp.json()) as { dispatched?: boolean; run_id?: string };
    expect(fireJson.dispatched).toBe(true);
    expect(fireJson.run_id).toBeTruthy();

    await page.keyboard.press("Escape");

    // Créer un second run échantillonné post-hoc pour valider de façon déterministe /finops
    const sampledRunRes = await apiPost(
      page,
      `/api/v1/workspaces/${wsId}/workflows/wf-01-qualification-prd/runs/autonomous`,
      {
        token: adminToken,
        data: {
          criticality: "STANDARD",
          actions: [],
          estimated_cost_usd: 0.05,
          force_post_hoc_sample: true,
        },
      },
    );
    expect(sampledRunRes.status()).toBe(201);

    // 4. Ouvrir /processes : vérifier sans condition la supervision, arrêt d'urgence & survie F5
    await page.goto("/processes");
    await expect(page.getByTestId("processes-autonomous-supervision-panel")).toBeVisible({
      timeout: 30000,
    });

    await page.getByTestId("topbar-notifications-toggle").click();
    await expect(page.getByTestId("topbar-notifications-drawer")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("topbar-notifications-close").click();

    const stopBtns = page.locator("[data-testid$='-emergency-stop-btn']");
    await expect(stopBtns.first()).toBeVisible({ timeout: 15000 });
    await stopBtns.first().click();
    await expect(page.getByTestId("autonomous-supervision-success-banner")).toBeVisible({
      timeout: 15000,
    });
    await reloadColdFromPg(page);
    await expect(page.getByTestId("processes-autonomous-supervision-panel")).toBeVisible({
      timeout: 30000,
    });

    // 5. Retour sur /finops -> Maîtrise humaine : section autonome + invalidation @v(N-1) + F5
    await page.goto("/finops");
    await expect(page.getByTestId("finops-governance-dashboard")).toBeVisible({ timeout: 30000 });
    await page.getByTestId("finops-tab-cognitive-governance").click();
    await expect(page.getByTestId("finops-human-mastery-tab")).toBeVisible();
    await expect(page.getByTestId("finops-autonomous-governance-section")).toBeVisible({
      timeout: 15000,
    });

    const restoreBtn = page.locator("[data-testid^='finops-sample-restore-btn-']").first();
    await expect(restoreBtn).toBeVisible({ timeout: 15000 });
    await restoreBtn.click();
    await expect(page.getByTestId("finops-autonomous-invalidation-alert")).toBeVisible({
      timeout: 15000,
    });

    await reloadColdFromPg(page);
    await expect(page.getByTestId("finops-governance-dashboard")).toBeVisible({ timeout: 30000 });
    await page.getByTestId("finops-tab-cognitive-governance").click();
    await expect(page.getByTestId("finops-autonomous-invalidation-alert")).toBeVisible({
      timeout: 15000,
    });

    expectDbRowExists(
      "SELECT id, workflow_id, status FROM autonomy_contracts WHERE workflow_id = :workflow_id AND status = 'ACTIVE'",
      { workflow_id: "wf-01-qualification-prd" },
      "contrat d'autonomie signé persisté dans autonomy_contracts PG18",
    );
    expectDbRowExists(
      "SELECT id, workflow_id, trigger_type FROM workflow_triggers WHERE workflow_id = :workflow_id AND trigger_type = 'MANUAL_AUTONOMOUS'",
      { workflow_id: "wf-01-qualification-prd" },
      "déclencheur autonome persisté dans workflow_triggers PG18",
    );
    expectDbRowExists(
      "SELECT id, status FROM workflow_runs WHERE status = 'KILL_SWITCH_STOPPED'",
      undefined,
      "arrêt d'urgence KILL_SWITCH_STOPPED persisté dans workflow_runs PG18",
    );
    expectDbRowExists(
      "SELECT id, review_status FROM autonomous_post_hoc_audits WHERE review_status = 'INVALIDATED_ROLLED_BACK'",
      undefined,
      "audit post-hoc invalidé persisté dans autonomous_post_hoc_audits PG18",
    );
    expectDbRowExists(
      "SELECT id, event_type FROM audit_ledger",
      undefined,
      "trace de provenance immuable persistée dans audit_ledger PG18",
    );

    await expectZeroVisibleErrorBanners(page);
    expect(errors, errors.join("\n")).toEqual([]);
  });

  test("mobile : /processes et /finops s'affichent sans débordement horizontal ni erreur serveur", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "mobile-companion", "parcours mobile");
    const errors = watchUnexpectedPageAndApiErrors(page);
    resetDay0();
    await createFirstAdminViaUi(page);
    await createBuAndTeamViaUi(page);
    await createWorkspaceViaUi(page, "Espace Mobile E2E", "ws-mobile-e2e");

    await page.goto("/processes");
    await expect(page.getByTestId("four-zone-central-workspace")).toBeVisible({ timeout: 30000 });
    await expect(page.getByTestId("processes-autonomous-supervision-panel")).toBeVisible({
      timeout: 20000,
    });
    await expectZeroVisibleErrorBanners(page);
    const procOverflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(procOverflow.scrollWidth).toBeLessThanOrEqual(procOverflow.innerWidth);

    await page.goto("/finops");
    await expect(page.getByTestId("four-zone-central-workspace")).toBeVisible({ timeout: 30000 });
    await page.getByTestId("finops-tab-cognitive-governance").click();
    await expect(page.getByTestId("finops-human-mastery-tab")).toBeVisible();
    await expectZeroVisibleErrorBanners(page);
    const finopsOverflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(finopsOverflow.scrollWidth).toBeLessThanOrEqual(finopsOverflow.innerWidth);

    expectDbRowExists(
      "SELECT id, event_type FROM audit_ledger WHERE event_type = 'ORG_UNIT_CREATED'",
      undefined,
      "événement ORG_UNIT_CREATED persisté dans audit_ledger PG18",
    );
    expect(errors, errors.join("\n")).toEqual([]);
  });
});
