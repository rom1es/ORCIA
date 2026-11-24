import { expect, type Page } from "@playwright/test";

async function createOrgUnit(page: Page, level: "BU" | "TEAM", name: string, slug: string) {
  await page.getByTestId("open-create-org-unit-modal-btn").click();
  await expect(page.getByTestId("create-org-unit-form")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("org-unit-level-select").selectOption(level);
  await page.getByTestId("org-unit-name-input").fill(name);
  await page.getByTestId("org-unit-slug-input").fill(slug);
  const [createRes] = await Promise.all([
    page.waitForResponse(
      (res) => res.url().includes("/api/v1/org-units") && res.request().method() === "POST",
      { timeout: 15000 },
    ),
    page.getByTestId("create-org-unit-btn").click(),
  ]);
  expect(createRes.ok()).toBe(true);
  await expect(page.getByTestId("create-org-unit-form")).toBeHidden({ timeout: 15000 });
}

/** Create a Business Unit (BU) then an attached Team via `/organization` (real UI flow). */
export async function createBuAndTeamViaUi(page: Page): Promise<void> {
  await page.goto("/organization");
  await expect(page.getByTestId("settings-organization-section")).toBeVisible({ timeout: 30000 });
  await createOrgUnit(page, "BU", "Direction E2E", "bu-e2e");
  await expect(page.getByTestId("iam-org-units-empty-state")).toBeHidden({ timeout: 15000 });
  await createOrgUnit(page, "TEAM", "Equipe E2E", "team-e2e");
}

/** Create a Workspace attached to the team via `/spaces`. */
export async function createWorkspaceViaUi(page: Page, name: string, slug: string) {
  await page.goto("/spaces");
  const toggleBtn = page.getByTestId("toggle-create-workspace-form-btn");
  await expect(toggleBtn).toBeVisible({ timeout: 30000 });
  const form = page.getByTestId("create-workspace-form");
  if (!(await form.isVisible())) {
    await toggleBtn.click();
  }
  await expect(form).toBeVisible({ timeout: 15000 });
  await page.getByTestId("workspace-name-input").fill(name);
  await page.getByTestId("workspace-slug-input").fill(slug);
  const [createRes, syncRes] = await Promise.all([
    page.waitForResponse(
      (res) => res.url().includes("/api/v1/workspaces") && res.request().method() === "POST",
      { timeout: 15000 },
    ),
    page.waitForResponse(
      (res) =>
        res.url().includes("/api/v1/bootstrap/platform-setup-state") &&
        res.request().method() === "PUT",
      { timeout: 15000 },
    ),
    page.getByTestId("create-workspace-submit-btn").click(),
  ]);
  expect(createRes.ok()).toBe(true);
  expect(syncRes.ok()).toBe(true);
  await expect(page.locator("main").getByText(name).first()).toBeVisible({ timeout: 15000 });
}
