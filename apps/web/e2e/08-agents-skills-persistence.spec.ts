import { expect, test } from "@playwright/test";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi } from "./support/firstAdmin";
import { createBuAndTeamViaUi } from "./support/orgAndWorkspace";

test.describe("TEST-05 · 08 — Mes Agents : création et survie au F5 (BDD)", () => {
  test("un agent créé via le tiroir est persisté en base et réaffiché après un vrai F5", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "parcours de saisie : bureau");
    resetDay0();
    await createFirstAdminViaUi(page);
    await createBuAndTeamViaUi(page); // l'équipe de facturation déverrouille « Mes Agents »

    await page.goto("/agents");
    await expect(page.getByTestId("agents-and-skills-manager-view")).toBeVisible({ timeout: 30000 });
    await page.getByTestId("open-create-agent-drawer-btn").click();
    await expect(page.getByTestId("create-agent-modal")).toBeVisible();
    await page.getByTestId("agent-name-input").fill("Agent E2E Conformité");
    await page.getByTestId("agent-role-input").fill("Analyste conformité");
    await page.getByTestId("agent-instructions-input").fill("Vérifie la conformité des livrables.");

    const created = page.waitForResponse(
      (r) => r.url().includes("/api/v1/agents-and-skills") && r.request().method() === "POST",
      { timeout: 20000 },
    );
    await page.getByTestId("create-agent-submit-btn").click();
    expect((await created).status()).toBeLessThan(400);

    await page.evaluate(() => {
      window.localStorage.clear();
      window.sessionStorage.clear();
    });
    await page.goto("/agents");
    await expect(page.getByText("Agent E2E Conformité").first()).toBeVisible({ timeout: 20000 });
  });
});
