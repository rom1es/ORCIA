/** @cap CAP-071, CAP-072, CAP-075, CAP-260 */
import { expect, test } from "./support/e2eCaptureFixture";
import { watchUnexpectedPageAndApiErrors } from "./support/apiErrors";
import { bootstrapAdminSession, getBearerTokenFromSession } from "./support/authAndOrgHelpers";
import { resetDay0 } from "./support/day0";
import { expectDbRowCount, expectDbRowExists } from "./support/dbAssertions";
import {
  configureActiveChatModelViaApi,
  configureActiveEmbeddingModelViaApi,
} from "./support/embeddingModel";
import { openAssistantPage } from "./support/processAndAssistantHelpers";
import { apiGet, apiPost, reloadColdFromPg } from "./support/typedApiRequest";
import {
  createOrgAndWorkspaceWithId,
  selectWorkspaceInSidebar,
} from "./support/workspaceAndCatalogHelpers";

test.describe("Story 26.9 — Assistant Mode A, PG18 Thread History, SSE Re-Attach, Tool Loop & Deepen", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("hydrates thread history across cold F5 reload, deepens with parent_turn_id, replays SSE ?after=, persists Mode A, and removes duplicate turns route", async ({
    page,
  }) => {
    const errors = watchUnexpectedPageAndApiErrors(page, {
      allowedApiStatuses: [
        { pathIncludes: "/threads/thread-nonexistent/turns", status: 404 },
        { pathIncludes: "/threads/thread-nonexistent/turns", status: 405 },
        { pathIncludes: "/approve", status: 422 },
      ],
    });
    await bootstrapAdminSession(page);
    const ws = await createOrgAndWorkspaceWithId(page, {
      name: "Workspace Story 26.9",
      slug: "ws-story-26-9",
    });
    await configureActiveChatModelViaApi(page);
    await configureActiveEmbeddingModelViaApi(page);
    const token = await getBearerTokenFromSession(page);

    const dupRouteRes = await apiPost(
      page,
      "/api/v1/assistant/threads/thread-nonexistent/turns",
      { token, data: { workspace_id: ws.pgWorkspaceId, user_prompt: "test" } },
    );
    expect([404, 405]).toContain(dupRouteRes.status());

    await openAssistantPage(page);

    const turnReqBodies: Array<Record<string, unknown>> = [];
    page.on("request", (req) => {
      if (req.url().endsWith("/api/v1/assistant/turns") && req.method() === "POST") {
        const raw = req.postData();
        if (raw) {
          turnReqBodies.push(JSON.parse(raw) as Record<string, unknown>);
        }
      }
    });

    const input = page.getByTestId("assistant-three-speed-input");
    await input.fill("Summarize the active architecture guidelines.");
    const [threadRes, turnRes] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().endsWith("/api/v1/assistant/threads") && r.request().method() === "POST",
        { timeout: 25000 },
      ),
      page.waitForResponse(
        (r) => r.url().endsWith("/api/v1/assistant/turns") && r.request().method() === "POST",
        { timeout: 25000 },
      ),
      page.getByTestId("assistant-three-speed-send-btn").click(),
    ]);
    expect(threadRes.status()).toBeLessThan(400);
    expect(turnRes.status()).toBe(202);
    const createdThread = (await threadRes.json()) as { thread_id: string; workspace_id: string };
    const acceptedTurn1 = (await turnRes.json()) as { turn_id: string };
    expect(createdThread.thread_id).toBeTruthy();
    expect(acceptedTurn1.turn_id).toBeTruthy();
    expect(turnReqBodies[0]?.thread_id).toBe(createdThread.thread_id);
    expect(turnReqBodies[0]?.conversation_history).toBeUndefined();

    await expect(page.getByTestId("assistant-conversation-turn-1")).toBeVisible({ timeout: 30000 });
    await expect(page.getByTestId("assistant-deepen-turn-btn")).toBeVisible({ timeout: 15000 });

    const messagesRes = await apiGet<{ messages: Array<{ role: string; turn_id: string }> }>(
      page,
      `/api/v1/assistant/threads/${createdThread.thread_id}/messages?workspace_id=${createdThread.workspace_id}`,
      { token },
    );
    expect(messagesRes.status()).toBe(200);
    const persistedMessages = (await messagesRes.json()).messages;
    expect(persistedMessages.length).toBeGreaterThanOrEqual(2);

    const replayRes = await apiGet(
      page,
      `/api/v1/assistant/turns/${acceptedTurn1.turn_id}/stream?after=0-0`,
      { token, headers: { Accept: "text/event-stream" } },
    );
    expect(replayRes.status()).toBe(200);
    const replayText = await replayRes.text();
    expect(replayText).toContain("turn_completed");

    await reloadColdFromPg(page);
    // Clearing localStorage resets activeScopeId to scope-global (personal workspace);
    // re-select the target workspace so its persisted thread history hydrates from PG18.
    await selectWorkspaceInSidebar(
      page,
      { workspaceId: ws.uiWorkspaceId, workspaceName: ws.name },
      { waitForAssistantOverview: true },
    );
    await expect(page.getByTestId("assistant-conversation-turn-1")).toBeVisible({ timeout: 30000 });
    await expect(page.getByTestId("assistant-conversation-turn-1")).toContainText(
      "Summarize the active architecture guidelines.",
    );

    const [deepenRes] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().endsWith("/api/v1/assistant/turns") && r.request().method() === "POST",
        { timeout: 25000 },
      ),
      page.getByTestId("assistant-deepen-turn-btn").click(),
    ]);
    expect(deepenRes.status()).toBe(202);
    const latestTurnReq = turnReqBodies[turnReqBodies.length - 1];
    expect(latestTurnReq?.requested_speed).toBe("SPEED_2_AGENT_TOOLS");
    expect(latestTurnReq?.parent_turn_id).toBe(acceptedTurn1.turn_id);
    await expect(page.getByTestId("assistant-conversation-turn-2")).toBeVisible({ timeout: 30000 });

    const approveMissingAnchor = await apiPost<{ error_code: string }>(
      page,
      `/api/v1/assistant/turns/${acceptedTurn1.turn_id}/approve`,
      {
        token,
        data: {
          workspace_id: createdThread.workspace_id,
          proposal_id: "prop-26-9-e2e",
          approved: true,
          human_authored_required: true,
        },
      },
    );
    expect(approveMissingAnchor.status()).toBe(422);
    expect((await approveMissingAnchor.json()).error_code).toBe("ERR_HUMAN_ANCHOR_REQUIRED");

    const approveOk = await apiPost<{ status: string }>(
      page,
      `/api/v1/assistant/turns/${acceptedTurn1.turn_id}/approve`,
      {
        token,
        data: {
          workspace_id: createdThread.workspace_id,
          proposal_id: "prop-26-9-e2e",
          approved: true,
          human_authored_required: true,
          human_anchor_markdown: "Approved during Story 26.9 E2E verification.",
        },
      },
    );
    expect(approveOk.status()).toBe(200);
    expect((await approveOk.json()).status).toBe("APPROVED");

    await page.getByTestId("assistant-open-governance-btn").click();
    await expect(page.getByTestId("assistant-governance-container")).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("assistant-governance-mode-a")).toBeVisible();
    await expect(page.getByTestId("assistant-governance-mode-b-studio")).toHaveCount(0);
    const customInstr = "Always cite verified documents concisely (Story 26.9).";
    await page.getByTestId("assistant-user-instructions-input").fill(customInstr);
    await Promise.all([
      page.waitForResponse(
        (r) => r.url().endsWith("/api/v1/assistant/governance/mode-a/user") && r.request().method() === "PUT",
        { timeout: 15000 },
      ),
      page.getByTestId("assistant-save-user-prefs-btn").evaluate((el) => (el as HTMLElement).click()),
    ]);
    await page.getByTestId("assistant-gov-cancel-btn").click();

    await reloadColdFromPg(page);
    // Re-select the target workspace so Mode A user governance preferences hydrate for that workspace.
    await selectWorkspaceInSidebar(
      page,
      { workspaceId: ws.uiWorkspaceId, workspaceName: ws.name },
      { waitForAssistantOverview: true },
    );
    await page.getByTestId("assistant-open-governance-btn").click();
    await expect(page.getByTestId("assistant-user-instructions-input")).toHaveValue(customInstr, {
      timeout: 15000,
    });
    await page.getByTestId("assistant-gov-cancel-btn").click();

    expectDbRowExists(
      "SELECT thread_id::text AS thread_id FROM assistant_threads WHERE thread_id = CAST(:tid AS uuid)",
      { tid: createdThread.thread_id },
      "Thread persisted in PG18 assistant_threads",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM assistant_thread_messages WHERE thread_id = CAST(:tid AS uuid)",
      { tid: createdThread.thread_id },
      4,
      "User and assistant turns persisted across cold F5 + Deepen",
    );
    expect(errors).toEqual([]);
  });
});
