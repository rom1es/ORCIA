/** @uj UJ-8, UJ-11, UJ-12, UJ-19 | @cap CAP-092, CAP-140, CAP-200, CAP-201 */
import { captureMilestoneScreenshot, expect, test } from "./support/e2eCaptureFixture";
import { resetDay0 } from "./support/day0";
import { expectDbRowCount, expectDbRowExists } from "./support/dbAssertions";
import { bootstrapAdminSession, getBearerTokenFromSession } from "./support/authAndOrgHelpers";
import { createOrgAndWorkspaceWithId } from "./support/workspaceAndCatalogHelpers";
import {
  openAgentsPage,
  openFinopsPage,
  openProcessesHubPage,
  openVsmPage,
  openWorkflowStudioPage,
  reloadClearingStorage,
} from "./support/processAndAssistantHelpers";
import { apiPost, apiPut } from "./support/typedApiRequest";

test.describe("Catalogue agents, chaîne de valeur, studio cinq blocs, autonomie, alertes applicatives et FinOps", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("Catalogue agents avec pont assistant, chaîne de valeur, studio cinq blocs, tiroir HITL et survie F5", async ({
    page,
  }, testInfo) => {
    await bootstrapAdminSession(page);
    await createOrgAndWorkspaceWithId(page, {
      name: "Espace Studio V2",
      slug: "ws-studio-v2",
    });

    await openAgentsPage(page);
    await expect(page.getByTestId("workspace-assistant-pinned-card")).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByTestId("load-pack-agents-templates-btn")).toBeVisible();
    await page.getByTestId("load-pack-agents-templates-btn").click();
    await expect(page.getByTestId("pinned-assistant-open-btn")).toBeVisible();

    await openProcessesHubPage(page);
    await page.getByTestId("open-interactive-vsm-btn").click();
    await expect(page.getByTestId("vsm-interactive-view")).toBeVisible({ timeout: 30000 });
    await openVsmPage(page, "vsm-mon-compte-idea-to-prod");
    await expect(page.getByTestId("vsm-step-detail-sheet-01")).toBeVisible({ timeout: 15000 });
    await captureMilestoneScreenshot(page, testInfo, "vsm-11-steps");

    await openWorkflowStudioPage(page, "wf-01-qualification-prd", "design");
    await expect(page.getByTestId("studio-five-blocks-canvas")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("studio-block-1-triggers-contract")).toBeVisible();
    await expect(page.getByTestId("studio-block-3-mcp-toolboxes")).toBeVisible();
    await expect(page.getByTestId("studio-block-4-skills-knowledge")).toBeVisible();
    await expect(page.getByTestId("studio-block-5-gates-pipeline")).toBeVisible();

    await page.getByTestId("studio-view-mode-whatif").click();
    await expect(page.getByTestId("studio-what-if-sandbox-panel")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("studio-view-mode-yaml").click();
    await expect(page.getByTestId("studio-yaml-preview-panel")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("studio-view-mode-design").click();

    await page.getByTestId("studio-save-draft-btn").click();
    const [pubRes] = await Promise.all([
      page.waitForResponse(
        (res) =>
          res.url().includes("/api/v1/workflows/v2/wf-01-qualification-prd") &&
          res.request().method() === "PUT",
      ),
      page.getByTestId("studio-publish-workflow-btn").click(),
    ]);
    expect(pubRes.status()).toBe(200);
    await expect(page.getByTestId("studio-status-banner")).toBeVisible({ timeout: 10000 });

    await page.getByTestId("studio-launch-interactive-run-btn").click();
    await expect(page.getByTestId("interactive-run-hitl-drawer")).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId("anchor-action-1-accept-btn")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("anchor-action-2-amend-diff-btn")).toBeVisible();
    await expect(page.getByTestId("anchor-action-3-reject-loop-btn")).toBeVisible();
    await expect(page.getByTestId("anchor-action-4-suspend-sla-btn")).toBeVisible();
    await page.getByTestId("anchor-action-1-accept-btn").click();

    await reloadClearingStorage(page);
    await expect(page.getByTestId("workflow-five-blocks-studio-page")).toBeVisible({
      timeout: 30000,
    });

    expectDbRowExists(
      "SELECT id::text AS id, slug, status FROM workflow_definitions_v2 WHERE slug = :slug OR workflow_id = :slug",
      { slug: "wf-01-qualification-prd" },
      "Processus V2 persisté dans workflow_definitions_v2 PG18",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM vsm_definitions_v2",
      undefined,
      1,
      "Chaîne de valeur persistée dans vsm_definitions_v2 PG18",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM reflexive_execution_sessions",
      undefined,
      1,
      "Session réflexive persistée dans reflexive_execution_sessions PG18",
    );
  });

  test("Contrat d'autonomie, alerte applicative dédupliquée, arrêt d'urgence et gouvernance FinOps survivent à F5", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    const ws = await createOrgAndWorkspaceWithId(page, {
      name: "Espace Autonomie et FinOps",
      slug: "ws-auto-finops",
    });
    const token = await getBearerTokenFromSession(page);

    const spRes = await apiPost(page, "/api/v1/settings/iam/accounts", {
      token,
      data: {
        principal_id: "sp-logsink-finops",
        display_name: "Robot Alertes Applicatives",
        account_kind: "SERVICE_PRINCIPAL",
        roles: ["TEAM_LEAD"],
        team_ids: [ws.pgWorkspaceId],
      },
    });
    expect([200, 201]).toContain(spRes.status());

    await openWorkflowStudioPage(page, "wf-01-qualification-prd");
    await page.getByTestId("studio-publish-workflow-btn").click();
    await expect(page.getByTestId("studio-status-banner")).toBeVisible({ timeout: 10000 });

    await page.getByTestId("studio-autonomy-contract-btn").click();
    await expect(page.getByTestId("autonomy-contract-modal")).toBeVisible({ timeout: 15000 });
    await page.getByTestId("autonomy-contract-sign-btn").click();
    await expect(page.getByTestId("studio-autonomy-contract-active-badge")).toBeVisible({
      timeout: 15000,
    });

    await page.getByTestId("studio-triggers-btn").click();
    await expect(page.getByTestId("workflow-triggers-modal")).toBeVisible({ timeout: 15000 });
    await page.getByTestId("trigger-create-type-select").selectOption("LOG_SINK_ALERT");
    await page.getByTestId("trigger-create-log-service-input").fill("orcia-api");
    await page.getByTestId("trigger-create-submit-btn").click();
    await expect(page.getByTestId("workflow-triggers-list")).toBeVisible({ timeout: 15000 });
    await page.keyboard.press("Escape");

    const alertSecret = "orcia-alert-webhook-key-01"; // pragma: allowlist secret
    const apiTriggerRes = await apiPost<{ id: string }>(
      page,
      `/api/v1/workspaces/${ws.pgWorkspaceId}/workflows/wf-01-qualification-prd/triggers`,
      {
        token,
        data: {
          trigger_type: "LOG_SINK_ALERT",
          log_sink_service: "orcia-worker",
          log_sink_query_text: "level:ERROR",
          cooldown_window_seconds: 0,
          webhook_secret: { action: "set", plaintext_value: alertSecret },
        },
      },
    );
    expect(apiTriggerRes.status()).toBe(201);
    const createdTrigger = await apiTriggerRes.json();

    const alertPayload = {
      trigger_id: createdTrigger.id,
      service: "orcia-worker",
      exception_type: "TimeoutError",
      message: "Upstream gateway timeout",
      traceback: "File worker/tasks.py, line 42, in run_step\nTimeoutError: 504",
    };
    const firstAlert = await apiPost<{ outcome: string }>(page, "/api/v1/triggers/alerts", {
      headers: { "x-orcia-alert-secret": alertSecret },
      data: alertPayload,
    });
    expect(firstAlert.status()).toBe(200);
    expect((await firstAlert.json()).outcome).toBe("DISPATCHED");

    const duplicateAlert = await apiPost<{ outcome: string }>(page, "/api/v1/triggers/alerts", {
      headers: { "x-orcia-alert-secret": alertSecret },
      data: alertPayload,
    });
    expect(duplicateAlert.status()).toBe(200);
    expect((await duplicateAlert.json()).outcome).toBe("DUPLICATE_SUPPRESSED");

    await openProcessesHubPage(page);
    await expect(page.getByTestId("processes-autonomous-supervision-panel")).toBeVisible({
      timeout: 20000,
    });
    await page.locator("[data-testid$='-emergency-stop-btn']").first().click();
    await expect(page.getByTestId("autonomous-supervision-success-banner")).toBeVisible({
      timeout: 15000,
    });

    const quotaRes = await apiPut(page, "/api/v1/finops/connectors/jira-prod/quota", {
      token,
      data: {
        display_name: "Jira Cloud Prod",
        service_kind: "MCP_SERVER",
        scope_type: "GLOBAL",
        valuation_mode: "FIXED_SCALE",
        fixed_cost_per_call_eur: 0.05,
        max_daily_calls: 500,
        max_monthly_cost_eur: 120,
      },
    });
    expect(quotaRes.status()).toBe(200);

    await openFinopsPage(page);
    await page.getByTestId("finops-scope-global").click();
    await expect(page.getByTestId("finops-scope-global")).toHaveAttribute("aria-selected", "true");
    await page.getByTestId("finops-configure-budget-btn").click();
    await expect(page.getByTestId("finops-budget-modal")).toBeVisible();
    await page.getByTestId("finops-budget-monthly-limit").fill("350");
    await page.getByTestId("finops-budget-save-btn").click();
    await expect(page.getByTestId("finops-success-banner")).toBeVisible({ timeout: 15000 });

    await page.getByTestId("finops-tab-external-services").click();
    await expect(page.getByTestId("finops-remote-services-tab")).toBeVisible();
    await page.getByTestId("finops-tab-cognitive-governance").click();
    await expect(page.getByTestId("finops-human-mastery-tab")).toBeVisible();

    await reloadClearingStorage(page);
    await expect(page.getByTestId("finops-governance-dashboard")).toBeVisible({ timeout: 30000 });

    expectDbRowExists(
      "SELECT id::text AS id, workflow_id, status FROM autonomy_contracts WHERE workflow_id = :workflow_id AND status = 'ACTIVE'",
      { workflow_id: "wf-01-qualification-prd" },
      "Contrat d'autonomie actif persisté dans autonomy_contracts PG18",
    );
    expectDbRowExists(
      "SELECT id::text AS id, trigger_type FROM workflow_triggers WHERE trigger_type = 'LOG_SINK_ALERT'",
      undefined,
      "Déclencheur LOG_SINK_ALERT persisté dans workflow_triggers PG18",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM trigger_webhook_deliveries WHERE trigger_id::text = :tid",
      { tid: createdTrigger.id },
      1,
      "Déduplication d'alerte persistée dans trigger_webhook_deliveries PG18",
    );
    expectDbRowExists(
      "SELECT id::text AS id, scope_type, monthly_budget_usd FROM finops_scope_budgets WHERE scope_type = 'GLOBAL' AND monthly_budget_usd >= 350",
      undefined,
      "Plafond FinOps persisté dans finops_scope_budgets PG18",
    );
    expectDbRowExists(
      "SELECT id::text AS id, connector_key FROM finops_connector_quotas WHERE connector_key = 'jira-prod'",
      undefined,
      "Quota connecteur persisté dans finops_connector_quotas PG18",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM audit_ledger",
      undefined,
      1,
      "Journal immuable alimenté dans audit_ledger PG18",
    );
  });
});
