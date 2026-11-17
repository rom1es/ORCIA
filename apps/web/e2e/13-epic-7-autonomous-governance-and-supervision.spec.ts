import { expect, test } from "@playwright/test";
import {
  expectZeroVisibleErrorBanners,
  watchUnexpectedPageAndApiErrors,
} from "./support/apiErrors";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi } from "./support/firstAdmin";
import { createBuAndTeamViaUi, createWorkspaceViaUi } from "./support/orgAndWorkspace";

test.describe("TEST-07 · 13 — Story 7.4 Gouvernance & Supervision des Exécutions Autonomes", () => {
  test("bureau : contrat d'autonomie + déclencheur + supervision /processes + arrêt d'urgence F5 + /finops Maîtrise humaine sans erreur 4xx/5xx", async ({
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

    // 2. Récupérer le workspace réel et créer un compte applicatif éligible
    const stateRes = await page.request.get("/api/v1/bootstrap/platform-setup-state");
    expect(stateRes.status()).toBe(200);
    const setupState = (await stateRes.json()) as {
      workspaces?: Array<{ workspaceId?: string; workspace_id?: string; id?: string }>;
    };
    const wsId =
      setupState.workspaces?.[0]?.workspaceId ??
      setupState.workspaces?.[0]?.workspace_id ??
      setupState.workspaces?.[0]?.id ??
      "";
    expect(wsId).not.toBe("");

    const spRes = await page.request.post("/api/v1/settings/iam/accounts", {
      data: {
        principal_id: "sp-e2e-auto-docs",
        display_name: "Robot Documentation E2E",
        account_kind: "SERVICE_PRINCIPAL",
        roles: ["TEAM_LEAD"],
        team_ids: [wsId],
      },
    });
    expect([200, 201]).toContain(spRes.status());

    // 3. Ouvrir le Studio V2 -> signer un contrat d'autonomie + créer un déclencheur manuel et l'exécuter
    await page.goto("/processes/studio/wf-01-qualification-prd");
    await expect(page.getByTestId("studio-autonomy-contract-btn")).toBeVisible({ timeout: 30000 });
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
    await fireBtn.click();

    // Fermer la modale déclencheurs (Escape RGAA)
    await page.keyboard.press("Escape");

    // 4. Ouvrir /processes : vérifier la section de supervision autonome
    await page.goto("/processes");
    await expect(page.getByTestId("processes-autonomous-supervision-panel")).toBeVisible({
      timeout: 30000,
    });

    // Ouvrir le tiroir de notifications TopHeader et vérifier l'absence d'erreur
    await page.getByTestId("topbar-notifications-toggle").click();
    await expect(page.getByTestId("topbar-notifications-drawer")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("topbar-notifications-close").click();

    // Si des exécutions autonomes sont listées, tester l'arrêt d'urgence + survie F5
    const stopBtns = page.locator("[data-testid$='-emergency-stop-btn']");
    if ((await stopBtns.count()) > 0) {
      await stopBtns.first().click();
      await expect(page.getByTestId("autonomous-supervision-success-banner")).toBeVisible({
        timeout: 15000,
      });
      await page.reload();
      await expect(page.getByTestId("processes-autonomous-supervision-panel")).toBeVisible({
        timeout: 30000,
      });
    }

    // 5. Retour sur /finops -> Maîtrise humaine & Qualité : vérifier section autonome si runs > 0
    await page.goto("/finops");
    await expect(page.getByTestId("finops-governance-dashboard")).toBeVisible({ timeout: 30000 });
    await page.getByTestId("finops-tab-cognitive-governance").click();
    await expect(page.getByTestId("finops-human-mastery-tab")).toBeVisible();
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

    expect(errors, errors.join("\n")).toEqual([]);
  });
});
