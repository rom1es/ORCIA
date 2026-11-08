import { expect, type Page } from "@playwright/test";

async function createOrgUnit(page: Page, level: "BU" | "TEAM", name: string, slug: string) {
  await page.getByTestId("org-unit-level-select").selectOption(level);
  await page.getByTestId("org-unit-name-input").fill(name);
  await page.getByTestId("org-unit-slug-input").fill(slug);
  await page.getByTestId("create-org-unit-btn").click();
}

/** Crée une Direction (BU) puis une Équipe rattachée, via /configuration (parcours réel). */
export async function createBuAndTeamViaUi(page: Page): Promise<void> {
  await page.goto("/configuration");
  await expect(page.getByTestId("create-org-unit-form")).toBeVisible({ timeout: 30000 });
  await createOrgUnit(page, "BU", "Direction E2E", "bu-e2e");
  await expect(page.getByTestId("iam-org-units-empty-state")).toBeHidden({ timeout: 15000 });
  await createOrgUnit(page, "TEAM", "Equipe E2E", "team-e2e");
}

/** Crée un Espace de Travail rattaché à l'équipe via /spaces. */
export async function createWorkspaceViaUi(page: Page, name: string, slug: string) {
  await page.goto("/spaces");
  await expect(page.getByTestId("create-workspace-form")).toBeVisible({ timeout: 30000 });
  await page.getByTestId("workspace-name-input").fill(name);
  await page.getByTestId("workspace-slug-input").fill(slug);
  await page.getByTestId("create-workspace-submit-btn").click();
}
