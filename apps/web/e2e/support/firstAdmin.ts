import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { apiPost } from "./typedApiRequest";

export const E2E_ADMIN = {
  name: "Alice Admin E2E",
  email: "alice.admin@e2e.orcia.test",
  password: "E2e-Passw0rd-Sup3r-Secret!", // pragma: allowlist secret
} as const;

/** Crée le premier administrateur via API (Jour 0) et retourne son jeton JWT Bearer. */
export async function createFirstAdminAndGetBearerToken(
  request: APIRequestContext,
): Promise<string> {
  const firstAdminRes = await apiPost<{ access_token?: string }>(
    request,
    "/api/v1/bootstrap/welcome-setup/first-admin",
    {
      data: {
        email: E2E_ADMIN.email,
        display_name: E2E_ADMIN.name,
        password: E2E_ADMIN.password,
        orcia_env: "local",
      },
    },
  );
  expect(firstAdminRes.status()).toBe(200);
  const token = (await firstAdminRes.json()).access_token ?? "";
  expect(token).toBeTruthy();
  return token;
}

/** Crée le premier administrateur via la modale Jour 0 (parcours réel, sans simulation). */
export async function createFirstAdminViaUi(page: Page): Promise<void> {
  await page.goto("/");
  const modal = page.getByTestId("first-boot-admin-setup-modal");
  await expect(modal).toBeVisible({ timeout: 30000 });
  await page.getByTestId("first-boot-admin-name-input").fill(E2E_ADMIN.name);
  await page.getByTestId("first-boot-admin-email-input").fill(E2E_ADMIN.email);
  await page.getByTestId("first-boot-admin-password-input").fill(E2E_ADMIN.password);
  const [firstAdminRes] = await Promise.all([
    page.waitForResponse(
      (res) =>
        res.url().includes("/api/v1/bootstrap/welcome-setup/first-admin") &&
        res.request().method() === "POST",
      { timeout: 30000 },
    ),
    page.getByTestId("first-boot-admin-submit-btn").click(),
  ]);
  expect(firstAdminRes.status()).toBe(200);
  await expect(modal).toBeHidden({ timeout: 30000 });
  const viewport = page.viewportSize();
  if (!viewport || viewport.width >= 768) {
    await expect(page.getByTestId("sidebar-open-my-account-btn")).toBeVisible({ timeout: 15000 });
  } else {
    await expect(page.getByTestId("mobile-bottom-tab-bar")).toBeVisible({ timeout: 15000 });
  }
}
