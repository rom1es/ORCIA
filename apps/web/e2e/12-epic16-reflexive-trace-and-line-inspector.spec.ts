/** @uj UJ-10, UJ-17 | @cap CAP-160 */
import type { Page } from "@playwright/test";
import { expect, test } from "./support/e2eCaptureFixture";
import { expectDbRowExists } from "./support/dbAssertions";
import { watchApiServerErrors } from "./support/apiErrors";
import { getBearerTokenFromSession } from "./support/authAndOrgHelpers";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi } from "./support/firstAdmin";
import { apiPost } from "./support/typedApiRequest";
import { selectWorkspaceInSidebar } from "./support/workspaceAndCatalogHelpers";

const FORBIDDEN_JARGON_REGEX =
  /\b(DBOS|asyncio|Redis|SSE|Claim-Check|déterministe|non-déterministe|deterministic|non-deterministic)\b/i;

async function expectZeroHorizontalOverflow(page: Page, contextLabel: string): Promise<void> {
  const overflowPx = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  expect(overflowPx, `horizontal overflow on ${contextLabel}`).toBeLessThanOrEqual(1);
}

async function ensureCentralWorkspaceVisibleOnMobile(
  page: Page,
  isMobile: boolean,
): Promise<void> {
  if (!isMobile) return;
  const helpCloseBtn = page.getByTestId("contextual-help-close-btn");
  if (await helpCloseBtn.isVisible()) {
    await helpCloseBtn.click();
  }
  const sidebar = page.getByTestId("four-zone-sidebar");
  if ((await sidebar.getAttribute("data-rail-collapsed")) === "false") {
    await page.getByTestId("sidebar-rail-toggle-btn").click();
  }
}

test.describe("Story 16.4 — Trace d'exécution réflexive, Inspecteur chirurgical #L & survie F5 (desktop + mobile)", () => {
  test.beforeEach(async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    resetDay0();
    await createFirstAdminViaUi(page);

    const token = await getBearerTokenFromSession(page);
    const buRes = await apiPost<{ id?: string }>(page, "/api/v1/org-units", {
      token,
      data: {
        name: "Direction Trace E2E",
        kind: "BU",
        slug: "bu-trace-e2e",
        billing_enabled: true,
      },
    });
    expect(buRes.status()).toBe(200);
    const buId = (await buRes.json()).id ?? "";
    expect(buId).toBeTruthy();

    const teamRes = await apiPost<{ id?: string }>(page, "/api/v1/org-units", {
      token,
      data: {
        name: "Equipe Trace E2E",
        kind: "TEAM",
        slug: "team-trace-e2e",
        parent_id: buId,
        billing_enabled: true,
      },
    });
    expect(teamRes.status()).toBe(200);
    const teamId = (await teamRes.json()).id ?? "";
    expect(teamId).toBeTruthy();

    const wsRes = await apiPost<{ id?: string }>(page, "/api/v1/workspaces", {
      token,
      data: {
        name: "Espace Trace E2E",
        slug: "ws-trace-e2e",
        owner_org_unit_id: teamId,
      },
    });
    expect(wsRes.status()).toBe(201);
    const wsId = (await wsRes.json()).id ?? "";
    expect(wsId).toBeTruthy();

    const dsRes = await apiPost<{ id?: string }>(
      page,
      `/api/v1/workspaces/${wsId}/datasources`,
      {
        token,
        data: {
          alias: "capabilities-registry",
          scheme: "git",
          uri: "docs/product/capabilities.yaml",
          source_nature: "SOURCE_CODE",
        },
      },
    );
    expect(dsRes.status()).toBe(201);
    expectDbRowExists(
      "SELECT id::text AS id FROM workspace_datasources WHERE workspace_id = :ws_id AND uri = :uri",
      { ws_id: wsId, uri: "docs/product/capabilities.yaml" },
      "Source locale docs/product/capabilities.yaml persistée dans workspace_datasources PG18",
    );
  });

  test("affiche la trace réflexive sans jargon (@Agent + #Lstart-end), ouvre l'inspecteur chirurgical + garde READ_SOURCE, et survit au F5 sur WAITING_WRITE_PREVIEW", async ({
    page,
  }, testInfo) => {
    const serverErrors = watchApiServerErrors(page);
    const viewportLabel = testInfo.project.name;
    const isMobile = viewportLabel === "mobile-companion";

    await page.goto("/processes");
    if (isMobile) {
      const sidebar = page.getByTestId("four-zone-sidebar");
      if ((await sidebar.getAttribute("data-rail-collapsed")) === "true") {
        await page.getByTestId("sidebar-rail-toggle-btn").click();
      }
    }
    await selectWorkspaceInSidebar(page, { workspaceName: "Espace Trace E2E" });
    await ensureCentralWorkspaceVisibleOnMobile(page, isMobile);
    const hub = page.getByTestId("processes-hub-v2-page");
    await expect(hub).toBeVisible({ timeout: 30000 });
    await expectZeroHorizontalOverflow(page, `${viewportLabel} /processes`);

    await Promise.all([
      page.waitForResponse(
        (res) =>
          res.url().includes("/api/v1/workflows/v2/wf-generate-orcia-documentation/runs") &&
          res.request().method() === "POST" &&
          res.status() === 200,
      ),
      page.getByTestId("execute-workflow-btn-wf-generate-orcia-documentation").click(),
    ]);

    const runDrawer = page.getByTestId("interactive-run-hitl-drawer");
    await expect(runDrawer).toBeVisible({ timeout: 20000 });

    const trace = page.getByTestId("agent-execution-trace");
    await expect(trace).toBeVisible({ timeout: 20000 });
    const traceText = await trace.innerText();
    expect(traceText.match(/Synthèse prête/g)?.length ?? 0).toBeLessThanOrEqual(1);

    const drawerText = await runDrawer.innerText();
    expect(drawerText).not.toMatch(FORBIDDEN_JARGON_REGEX);

    const delegatedBlock = page.getByTestId("trace-delegated-agent-block").first();
    await expect(delegatedBlock).toBeVisible();
    await expect(delegatedBlock).toContainText("@redacteur-documentation-orcia");

    const thoughtToggle = page.getByTestId("trace-thought-toggle-btn").first();
    await expect(thoughtToggle).toBeVisible();
    await thoughtToggle.click();
    await expect(page.getByTestId("trace-thought-content").first()).toBeVisible();
    await thoughtToggle.click();
    await expect(page.getByTestId("trace-thought-content")).toHaveCount(0);

    const filePill = page.getByTestId("trace-file-analyzed-pill").first();
    await expect(filePill).toBeVisible();
    await expect(filePill).toContainText("#L1-35");

    // 1. Inspection chirurgicale nominale (#L1-35) + copie + fermeture Escape
    await Promise.all([
      page.waitForResponse(
        (res) =>
          res.url().includes("/api/v1/sources/inspect-lines") &&
          res.request().method() === "GET" &&
          res.status() === 200,
      ),
      filePill.click(),
    ]);

    const inspectorDrawer = page.getByTestId("source-line-inspector-drawer");
    await expect(inspectorDrawer).toBeVisible({ timeout: 15000 });
    await expectZeroHorizontalOverflow(page, `${viewportLabel} inspector drawer`);

    const line1 = page.getByTestId("inspector-code-line-1");
    await expect(line1).toBeVisible();
    await expect(line1).toHaveAttribute("data-highlighted", "true");

    await page.getByTestId("inspector-copy-slice-btn").click();
    await page.keyboard.press("Escape");
    await expect(inspectorDrawer).toBeHidden();

    // 2. Garde de confidentialité READ_SOURCE refusée de bout en bout (FastAPI redacted=true)
    await page.route("**/api/v1/sources/inspect-lines*", async (route) => {
      await route.continue({
        headers: {
          ...route.request().headers(),
          "x-orcia-read-source": "denied",
        },
      });
    });

    await Promise.all([
      page.waitForResponse(
        (res) =>
          res.url().includes("/api/v1/sources/inspect-lines") &&
          res.request().method() === "GET" &&
          res.status() === 200,
      ),
      filePill.click(),
    ]);

    await expect(inspectorDrawer).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("inspector-redacted-banner")).toBeVisible();
    await expect(page.locator('[data-testid^="inspector-code-line-"]')).toHaveCount(0);

    await page.unroute("**/api/v1/sources/inspect-lines*");
    await page.keyboard.press("Escape");
    await expect(inspectorDrawer).toBeHidden();

    // 3. Aperçu d'écriture gouvernée WAITING_WRITE_PREVIEW + survie au F5 via PostgreSQL 18 + approbation
    await Promise.all([
      page.waitForResponse(
        (res) =>
          res.url().includes("/api/v1/executions/reflexive") &&
          res.request().method() === "POST" &&
          res.status() === 200,
      ),
      page.getByTestId("process-request-write-preview-btn").click(),
    ]);

    const writePreviewCard = page.getByTestId("trace-write-preview-card");
    await expect(writePreviewCard).toBeVisible({ timeout: 15000 });

    await page.reload();
    await ensureCentralWorkspaceVisibleOnMobile(page, isMobile);
    await expect(page.getByTestId("interactive-run-hitl-drawer")).toHaveCount(0);
    await page.getByTestId("resume-featured-dossier-btn").click();
    await expect(page.getByTestId("interactive-run-hitl-drawer")).toBeVisible({
      timeout: 30000,
    });
    await expect(page.getByTestId("trace-write-preview-card")).toBeVisible({
      timeout: 20000,
    });
    await expectZeroHorizontalOverflow(page, `${viewportLabel} after F5 write preview`);

    await Promise.all([
      page.waitForResponse(
        (res) =>
          res.url().includes("/approve-write") &&
          res.request().method() === "POST" &&
          res.status() === 200,
      ),
      page.getByTestId("trace-approve-write-btn").click(),
    ]);

    await expect(page.getByTestId("trace-write-preview-card")).toBeHidden({
      timeout: 15000,
    });
    expectDbRowExists(
      "SELECT id, execution_id, actor_slug, status FROM reflexive_execution_sessions WHERE status = 'COMPLETED'",
      undefined,
      "session réflexive COMPLETED persistée dans reflexive_execution_sessions PG18",
    );
    expect(serverErrors, serverErrors.join("\n")).toEqual([]);
  });
});
