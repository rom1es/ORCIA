import { expect, test } from "@playwright/test";
import { resetDay0 } from "./support/day0";

test.describe("Socle E2E bi-serveur (TEST-01 & Story 16.1 Surgical Exploration)", () => {
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

  test("Story 16.1 — l'inspection chirurgicale #L1-40 retourne 40 lignes badge Y et bloque ../ en RFC 9457", async ({
    request,
  }) => {
    const sliceResp = await request.get(
      "/api/v1/sources/inspect-lines?uri=docs/product/capabilities.yaml&start_line=1&end_line=40",
    );
    expect(sliceResp.status()).toBe(200);
    const sliceBody = (await sliceResp.json()) as {
      file_badge_code: string;
      formatted_badge: string;
      lines: Array<{ line_number: number; content: string }>;
      redacted: boolean;
    };
    expect(sliceBody.file_badge_code).toBe("Y");
    expect(sliceBody.formatted_badge).toBe("Analyzed Y capabilities.yaml #L1-40");
    expect(sliceBody.redacted).toBe(false);
    expect(sliceBody.lines).toHaveLength(40);
    expect(sliceBody.lines[0]?.line_number).toBe(1);
    expect(sliceBody.lines[39]?.line_number).toBe(40);

    const traversalResp = await request.get(
      "/api/v1/sources/inspect-lines?uri=../pyproject.toml&start_line=1&end_line=10",
    );
    expect([400, 422]).toContain(traversalResp.status());
    expect(traversalResp.headers()["content-type"]).toContain("application/problem+json");
    const problem = (await traversalResp.json()) as { error_code?: string; trace_id?: string };
    expect(problem.error_code).toBe("ERR_VALIDATION_FAILED");
    expect(Boolean(problem.trace_id)).toBe(true);
  });
});
