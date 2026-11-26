/** @uj UJ-1, UJ-9, UJ-10, UJ-17, UJ-19 | @cap CAP-070, CAP-082, CAP-090, CAP-140, CAP-160 */
import { createHash } from "node:crypto";
import { expect, type Page, test } from "./support/e2eCaptureFixture";
import { watchUnexpectedPageAndApiErrors } from "./support/apiErrors";
import { getBearerTokenFromSession } from "./support/authAndOrgHelpers";
import { resetDay0 } from "./support/day0";
import { expectDbRowExists } from "./support/dbAssertions";
import { configureActiveChatModelViaApi } from "./support/embeddingModel";
import { createFirstAdminViaUi } from "./support/firstAdmin";
import {
  openAgentsPage,
  openAssistantPage,
  openProcessesHubPage,
} from "./support/processAndAssistantHelpers";
import { apiPatch, apiPost, reloadColdFromPg } from "./support/typedApiRequest";
import {
  createOrgAndWorkspaceWithId,
  selectWorkspaceInSidebar,
} from "./support/workspaceAndCatalogHelpers";
import { switchUiLocaleViaUserSettings } from "./helpers/bilingualI18nHelpers";

const EMPTY_SHA256 = createHash("sha256").update("").digest("hex");

async function runEpic30BilingualJourney(
  page: Page,
  locale: "fr" | "en",
): Promise<{
  readonly workspacePgId: string;
  readonly agentId: string;
  readonly updatedRole: string;
}> {
  const isFr = locale === "fr";
  await createFirstAdminViaUi(page);
  if (!isFr) {
    await switchUiLocaleViaUserSettings(page, "en");
  }

  const ws = await createOrgAndWorkspaceWithId(page, {
    name: isFr ? "Espace Epic 30 FR" : "Workspace Epic 30 EN",
    slug: isFr ? "ws-epic30-fr" : "ws-epic30-en",
  });
  await configureActiveChatModelViaApi(page);

  const token = await getBearerTokenFromSession(page);
  const attachDsRes = await apiPost(page, `/api/v1/workspaces/${ws.pgWorkspaceId}/datasources`, {
    token,
    data: {
      alias: isFr ? "repo-epic30-fr" : "repo-epic30-en",
      scheme: "git",
      uri: `https://git.internal.orcia/epic30/${locale}.git`,
      source_nature: "SOURCE_CODE",
      target_scope: "main",
      target_ref: "refs/heads/main",
      sync_mode: "WEBHOOK_PUSH",
      codegraph_enabled: true,
    },
  });
  expect([200, 201]).toContain(attachDsRes.status());

  // 1. Assistant Governance Modal: empty personal instructions, explicit Save, clean Close/Escape, Cancel discard.
  await openAssistantPage(page);
  await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/assistant/governance") &&
        r.request().method() === "GET" &&
        r.status() === 200,
      { timeout: 20000 },
    ),
    selectWorkspaceInSidebar(
      page,
      { workspaceId: ws.uiWorkspaceId, workspaceName: ws.name },
      { waitForAssistantOverview: true },
    ),
  ]);
  await page.getByTestId("assistant-open-governance-btn").click();
  const govModal = page.getByTestId("assistant-governance-container");
  await expect(govModal).toBeVisible({ timeout: 10000 });
  const personalInput = page.getByTestId("assistant-user-instructions-input");
  await expect(personalInput).toHaveValue("");
  const savePrefsBtn = page.getByTestId("assistant-save-user-prefs-btn");
  await expect(savePrefsBtn).toBeDisabled();

  await personalInput.fill(isFr ? "Réponses synthétiques" : "Concise replies");
  await expect(savePrefsBtn).toBeEnabled();
  await expect(page.getByTestId("assistant-gov-autosaved-badge")).toHaveCount(0);
  await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/v1/assistant/governance/mode-a/user") &&
        r.request().method() === "PUT" &&
        r.status() === 200,
      { timeout: 15000 },
    ),
    page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/assistant/governance") &&
        !r.url().includes("/mode-a/") &&
        r.request().method() === "GET" &&
        r.status() === 200,
      { timeout: 15000 },
    ),
    savePrefsBtn.click(),
  ]);
  await expect(page.getByTestId("assistant-gov-autosaved-badge")).toBeVisible({ timeout: 10000 });

  await personalInput.fill("");
  await expect(savePrefsBtn).toBeEnabled();
  await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/v1/assistant/governance/mode-a/user") &&
        r.request().method() === "PUT" &&
        r.status() === 200,
      { timeout: 15000 },
    ),
    page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/assistant/governance") &&
        !r.url().includes("/mode-a/") &&
        r.request().method() === "GET" &&
        r.status() === 200,
      { timeout: 15000 },
    ),
    savePrefsBtn.click(),
  ]);
  await expect(page.getByTestId("assistant-gov-autosaved-badge")).toBeVisible({ timeout: 10000 });
  await expect(savePrefsBtn).toBeDisabled();
  await page.getByTestId("assistant-gov-cancel-btn").click();
  await expect(page.getByTestId("assistant-gov-unsaved-changes-alert")).toHaveCount(0);
  await expect(govModal).toBeHidden();

  await page.getByTestId("assistant-open-governance-btn").click();
  await expect(govModal).toBeVisible({ timeout: 10000 });
  await page.getByTestId("assistant-gov-tab-WORKSPACE_SETTINGS").click();
  await page.getByTestId("assistant-workspace-instructions-input").fill("ab");
  await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/v1/assistant/governance/mode-a/workspace") &&
        r.request().method() === "PUT" &&
        r.status() === 422,
      { timeout: 15000 },
    ),
    savePrefsBtn.click(),
  ]);
  const govAlert = govModal.getByTestId("assistant-gov-error-banner");
  await expect(govAlert).toBeVisible({ timeout: 10000 });
  await expect(govAlert).toHaveAttribute("role", "alert");

  await page.keyboard.press("Escape");
  await expect(page.getByTestId("assistant-gov-unsaved-changes-alert")).toBeVisible();
  await page.getByTestId("assistant-gov-unsaved-discard-btn").click();
  await expect(govModal).toBeHidden();

  await page.getByTestId("assistant-open-governance-btn").click();
  await expect(personalInput).toHaveValue("");
  await page.keyboard.press("Escape");
  await expect(govModal).toBeHidden();

  // 2. My Assistant: clean greeting without internal markers, orcia://, or unverified badges.
  await page.getByTestId("assistant-three-speed-input").fill(isFr ? "Bonjour !" : "Hello!");
  await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes("/api/v1/assistant/turns") && r.request().method() === "POST",
      { timeout: 25000 },
    ),
    page.getByTestId("assistant-three-speed-send-btn").click(),
  ]);
  const replyBox = page.getByTestId("assistant-streamed-response-box").first();
  await expect(replyBox).not.toBeEmpty({ timeout: 25000 });
  const replyText = await replyBox.innerText();
  for (const forbidden of [
    "[CONSTITUTIONAL_IMMUTABLE_LAYER_1]",
    "[NO_HUMAN_ANCHOR_WRITE]",
    "human_authored_required",
    "[ACTIVE_DOMAIN_PACK:",
    "[ADAPTATION_RUNTIME_METADATA]",
    "orcia://",
    "[Citation non vérifiée]",
    EMPTY_SHA256,
  ]) {
    expect(replyText).not.toContain(forbidden);
  }

  // 3. Mes Processus: Day-0 defaults to Business Processes with 0 pending badge -> explicit run Focus Review.
  await openProcessesHubPage(page);
  await expect(page.getByTestId("processes-tab-catalog")).toHaveAttribute("aria-selected", "true");
  await expect(page.getByTestId("processes-tab-badge-validations")).toHaveCount(0);
  await expect(page.getByTestId("interactive-run-hitl-drawer")).toHaveCount(0);

  await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/workflows/v2/wf-01-qualification-prd/runs") &&
        r.request().method() === "POST" &&
        r.status() === 200,
      { timeout: 25000 },
    ),
    page.getByTestId("execute-workflow-btn-wf-01-qualification-prd").click(),
  ]);
  await expect(page.getByTestId("process-run-focus-review-page")).toBeVisible({ timeout: 25000 });
  const actionBanner = page.getByTestId("process-run-zone1-action-banner");
  await expect(actionBanner).toBeVisible();
  await expect(actionBanner.locator("button.orcia-ds-btn-primary")).toHaveCount(1);
  await expect(page.getByTestId("approve-substep-checkpoint-btn")).toBeVisible();
  await expect(page.getByTestId("focus-review-zone2-artifact")).toBeVisible();
  await expect(page.getByTestId("focus-review-zone3-reasoning")).toBeVisible();
  const traceGroupBtn = page.getByTestId("trace-group-header-btn");
  if ((await traceGroupBtn.count()) > 0) {
    await expect(traceGroupBtn.first()).toHaveAttribute("aria-expanded", "false");
    await expect(page.getByTestId("trace-group-items")).toHaveCount(0);
  }

  // 4. My Agents & Skills: DRAFT/UNTESTED -> inline modal alert -> @agent block -> Save -> Test Bench ACTIVE.
  const agentName = isFr ? "Epic30 FR" : "Epic30 EN";
  const agentSlug = isFr ? "epic30-fr" : "epic30-en";
  const agentId = `agent-${agentSlug}`;
  const updatedRole = isFr ? "Rôle mis à jour PG18 FR" : "Updated PG18 role EN";

  await openAgentsPage(page);
  await page.getByTestId("open-create-agent-drawer-btn").click();
  await expect(page.getByTestId("create-agent-modal")).toBeVisible({ timeout: 10000 });
  await page.getByTestId("agent-name-input").fill(agentName);
  await page.getByTestId("agent-role-input").fill("Validate Epic 30 lifecycle");
  await page.getByTestId("agent-instructions-input").fill("Verify controls cleanly.");
  await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/v1/agents-and-skills/agents") &&
        r.request().method() === "POST" &&
        r.status() === 200,
      { timeout: 20000 },
    ),
    page.getByTestId("create-agent-submit-btn").click(),
  ]);
  await expect(page.getByTestId(`agent-lifecycle-badge-${agentId}`)).toContainText(
    isFr ? "Brouillon" : "Draft",
  );
  await expect(page.getByTestId(`agent-test-bench-badge-${agentId}`)).toContainText(
    isFr ? "À tester" : "To test",
  );

  // Backend 422 guards while DRAFT: @agent mention in Assistant and external MCP exposure
  const draftMentionRes = await apiPost<{ error_code?: string }>(page, "/api/v1/assistant/turns", {
    token,
    data: {
      workspace_id: ws.pgWorkspaceId,
      user_prompt: `Please ask @${agentSlug} for status`,
    },
  });
  expect(draftMentionRes.status()).toBe(422);
  expect((await draftMentionRes.json()).error_code).toBe("ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED");

  const draftMcpRes = await apiPatch<{ error_code?: string }>(
    page,
    `/api/v1/agents-and-skills/agents/${agentId}/governance`,
    { token, data: { mcp_exposed: true } },
  );
  expect(draftMcpRes.status()).toBe(422);
  expect((await draftMcpRes.json()).error_code).toBe("ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED");

  // Modal guards: disabled MCP checkbox, explicit Save, Test Bench promotion -> ACTIVE
  await page.getByTestId(`open-agent-detail-modal-btn-${agentId}`).click();
  const agentModal = page.getByTestId(`agent-detail-modal-${agentId}`);
  await expect(agentModal).toBeVisible({ timeout: 10000 });
  await expect(page.getByTestId(`agent-mcp-expose-checkbox-${agentId}`)).toBeDisabled();
  await expect(page.getByTestId(`agent-mcp-disabled-hint-${agentId}`)).toBeVisible();

  await page.getByTestId("edit-agent-role-input").fill(updatedRole);
  await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/v1/agents-and-skills/agents") &&
        r.request().method() === "POST" &&
        r.status() === 200,
      { timeout: 15000 },
    ),
    page.getByTestId(`save-agent-detail-modal-btn-${agentId}`).click(),
  ]);
  await expect(page.getByTestId(`agent-modal-saved-badge-${agentId}`)).toBeVisible({
    timeout: 10000,
  });

  await page.getByTestId(`agent-test-input-${agentId}`).fill("Run lifecycle verification");
  await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().includes(`/api/v1/agents-and-skills/agents/${agentId}/execute`) &&
        r.request().method() === "POST" &&
        r.status() === 200,
      { timeout: 20000 },
    ),
    page.getByTestId(`run-agent-btn-${agentId}`).click(),
  ]);
  await expect(page.getByTestId(`agent-execution-output-${agentId}`).first()).toBeVisible({
    timeout: 15000,
  });
  await expect(page.getByTestId(`agent-modal-lifecycle-badge-${agentId}`)).toContainText(
    isFr ? "Actif" : "Active",
  );
  await expect(page.getByTestId(`agent-bench-status-badge-${agentId}`)).toContainText(
    isFr ? "Validé au Banc de Test" : "Verified in Test Bench",
  );
  await expect(page.getByTestId(`agent-mcp-expose-checkbox-${agentId}`)).toBeEnabled();

  await page.getByTestId(`cancel-agent-detail-modal-btn-${agentId}`).click();
  await reloadColdFromPg(page);
  await expect(page.getByTestId(`agent-lifecycle-badge-${agentId}`)).toContainText(
    isFr ? "Actif" : "Active",
    { timeout: 20000 },
  );

  return { workspacePgId: ws.pgWorkspaceId, agentId, updatedRole };
}

test.describe("Story 30.6 — Bilingual FR/EN Epic 30 Day-0 UX Hardening & Lifecycle Lock", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("French (fr) Day-0 journey: Assistant Settings Save/Cancel, clean reply, Process Focus Review, and Agent DRAFT->ACTIVE PG18 persistence", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "desktop cockpit journey");
    const unexpectedErrors = watchUnexpectedPageAndApiErrors(page, {
      allowedApiStatuses: [
        { pathIncludes: "/api/v1/assistant/turns", status: 422 },
        { pathIncludes: "/api/v1/assistant/governance/mode-a/workspace", status: 422 },
        { pathIncludes: "/governance", status: 422 },
      ],
    });

    const outcome = await runEpic30BilingualJourney(page, "fr");

    expectDbRowExists(
      "SELECT workspace_id::text AS workspace_id, user_id::text AS user_id FROM workspace_customization_overrides WHERE workspace_id = CAST(:ws_id AS uuid)",
      { ws_id: outcome.workspacePgId },
      "French Assistant Mode A preferences persisted in workspace_customization_overrides PG18",
    );
    expectDbRowExists(
      "SELECT id::text AS id FROM workspace_datasources WHERE workspace_id = CAST(:ws_id AS uuid)",
      { ws_id: outcome.workspacePgId },
      "Workspace datasource persisted in PG18",
    );
    expectDbRowExists(
      "SELECT thread_id::text AS thread_id FROM assistant_threads WHERE workspace_id = CAST(:ws_id AS uuid)",
      { ws_id: outcome.workspacePgId },
      "Assistant thread persisted in PG18",
    );
    expectDbRowExists(
      "SELECT run_id FROM workflow_v2_runs WHERE workspace_id = CAST(:ws_id AS uuid)",
      { ws_id: outcome.workspacePgId },
      "Workflow v2 run persisted in PG18",
    );
    expectDbRowExists(
      "SELECT resource_id FROM catalog_items WHERE resource_id = :rid AND description = :role AND metadata_jsonb->>'lifecycle_status' = 'ACTIVE'",
      { rid: outcome.agentId, role: outcome.updatedRole },
      "Updated active agent persisted in catalog_items PG18",
    );
    expect(unexpectedErrors, unexpectedErrors.join("\n")).toEqual([]);
  });

  test("English (en) Day-0 journey: Assistant Settings Save/Cancel, clean reply, Process Focus Review, and Agent DRAFT->ACTIVE PG18 persistence", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "desktop cockpit journey");
    const unexpectedErrors = watchUnexpectedPageAndApiErrors(page, {
      allowedApiStatuses: [
        { pathIncludes: "/api/v1/assistant/turns", status: 422 },
        { pathIncludes: "/api/v1/assistant/governance/mode-a/workspace", status: 422 },
        { pathIncludes: "/governance", status: 422 },
      ],
    });

    const outcome = await runEpic30BilingualJourney(page, "en");

    expectDbRowExists(
      "SELECT user_id, locale FROM user_preferences WHERE locale = :locale",
      { locale: "en" },
      "English user_preferences persisted in PG18",
    );
    expectDbRowExists(
      "SELECT workspace_id::text AS workspace_id, user_id::text AS user_id FROM workspace_customization_overrides WHERE workspace_id = CAST(:ws_id AS uuid)",
      { ws_id: outcome.workspacePgId },
      "English Assistant Mode A preferences persisted in workspace_customization_overrides PG18",
    );
    expectDbRowExists(
      "SELECT id::text AS id FROM workspace_datasources WHERE workspace_id = CAST(:ws_id AS uuid)",
      { ws_id: outcome.workspacePgId },
      "Workspace datasource persisted in PG18",
    );
    expectDbRowExists(
      "SELECT thread_id::text AS thread_id FROM assistant_threads WHERE workspace_id = CAST(:ws_id AS uuid)",
      { ws_id: outcome.workspacePgId },
      "Assistant thread persisted in PG18",
    );
    expectDbRowExists(
      "SELECT run_id FROM workflow_v2_runs WHERE workspace_id = CAST(:ws_id AS uuid)",
      { ws_id: outcome.workspacePgId },
      "Workflow v2 run persisted in PG18",
    );
    expectDbRowExists(
      "SELECT resource_id FROM catalog_items WHERE resource_id = :rid AND description = :role AND metadata_jsonb->>'lifecycle_status' = 'ACTIVE'",
      { rid: outcome.agentId, role: outcome.updatedRole },
      "Updated active agent persisted in catalog_items PG18",
    );
    expect(unexpectedErrors, unexpectedErrors.join("\n")).toEqual([]);
  });
});
