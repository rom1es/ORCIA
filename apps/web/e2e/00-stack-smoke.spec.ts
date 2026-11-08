import { expect, test } from "@playwright/test";
import { resetDay0 } from "./support/day0";

test.describe("Socle E2E bi-serveur (TEST-01)", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("l'API FastAPI répond via le proxy Vite (Navigateur → Vite → FastAPI)", async ({
    request,
  }) => {
    const response = await request.get("/api/v1/health");
    expect(response.status()).toBe(200);
    const body = (await response.json()) as Record<string, unknown>;
    expect(JSON.stringify(body)).toContain("ok");
  });

  test("après reset Jour 0 la modale de premier administrateur est présentée", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page.getByTestId("first-boot-admin-setup-modal")).toBeVisible({
      timeout: 30000,
    });
  });
});
