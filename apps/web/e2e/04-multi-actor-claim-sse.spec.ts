/** @uj UJ-4 | @cap CAP-040 */
import { type APIRequestContext, request as pwRequest } from "@playwright/test";
import { resetDay0 } from "./support/day0";
import { expectDbRowExists } from "./support/dbAssertions";
import { loginLocalViaUi } from "./support/authAndOrgHelpers";
import { expect, test } from "./support/e2eCaptureFixture";
import { E2E_ADMIN } from "./support/firstAdmin";
import { apiGet, apiPost } from "./support/typedApiRequest";

const API = `http://127.0.0.1:${process.env.ORCIA_E2E_API_PORT ?? "8100"}`;
const SSE_BUDGET_MS = 500;

interface SseFrame {
  event: string;
  data: string;
  receivedAtMs: number;
}

/** Lecteur SSE minimal (fetch streaming Node) : accumule les trames jusqu'à `abort()`. */
function openSseStream(
  url: string,
  options?: { readonly token?: string },
): { frames: SseFrame[]; ready: Promise<void>; abort: () => void } {
  const controller = new AbortController();
  const frames: SseFrame[] = [];
  const headers = options?.token ? { Authorization: `Bearer ${options.token}` } : undefined;
  const ready = (async () => {
    const res = await fetch(url, {
      signal: controller.signal,
      ...(headers ? { headers } : {}),
    });
    expect(res.status).toBe(200);
    const reader = res.body?.getReader();
    if (!reader) throw new Error("flux SSE sans corps");
    const decoder = new TextDecoder();
    let buffer = "";
    const pump = async (): Promise<void> => {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) return;
        buffer += decoder.decode(value, { stream: true });
        let idx = buffer.indexOf("\n\n");
        while (idx >= 0) {
          const raw = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const event = /^event: (.*)$/m.exec(raw)?.[1] ?? "message";
          const data = /^data: (.*)$/m.exec(raw)?.[1] ?? "";
          frames.push({ event, data, receivedAtMs: performance.now() });
          idx = buffer.indexOf("\n\n");
        }
      }
    };
    void pump().catch(() => undefined); // arrêt volontaire via abort()
  })();
  return { frames, ready, abort: () => controller.abort() };
}

interface InboxItem {
  id: string;
  status: string;
  step_execution_id: string;
}

async function setupActorsAndOpenNotification(
  actorA: APIRequestContext,
  actorB: APIRequestContext,
  suffix: string,
): Promise<{
  readonly adminToken: string;
  readonly peerToken: string;
  readonly workspaceId: string;
  readonly taskId: string;
}> {
  const firstAdminRes = await apiPost<{ access_token?: string }>(
    actorA,
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
  const adminToken = (await firstAdminRes.json()).access_token ?? "";
  expect(adminToken).toBeTruthy();

  const wsRes = await apiPost<{ id: string }>(actorA, "/api/v1/workspaces", {
    token: adminToken,
    data: {
      name: `Espace SSE ${suffix}`,
      slug: `ws-sse-${suffix}`,
      visibility_mode: "STANDARD",
      lifecycle_phase: "BUILD",
    },
  });
  expect(wsRes.status()).toBe(201);
  const workspaceId = (await wsRes.json()).id;
  expect(workspaceId).toBeTruthy();

  const peerEmail = `peer.sse.${suffix}@e2e.orcia.test`;
  const peerCreateRes = await apiPost<{ temporary_password?: string | null }>(
    actorA,
    "/api/v1/settings/iam/accounts",
    {
      token: adminToken,
      data: {
        account_kind: "HUMAN",
        display_name: "Pair SSE E2E",
        email: peerEmail,
        principal_id: peerEmail,
        roles: ["TEAM_LEAD"],
        team_ids: [],
        status: "ACTIVE",
      },
    },
  );
  expect([200, 201]).toContain(peerCreateRes.status());
  const peerPass = (await peerCreateRes.json()).temporary_password ?? "";
  expect(peerPass).toBeTruthy();

  const peerLoginRes = await apiPost<{ access_token?: string }>(
    actorB,
    "/api/v1/auth/login/local",
    {
      data: { email: peerEmail, password: peerPass },
    },
  );
  expect(peerLoginRes.status()).toBe(200);
  const peerToken = (await peerLoginRes.json()).access_token ?? "";
  expect(peerToken).toBeTruthy();

  const runId = `0195f200-0000-7000-8000-0000000007${suffix.slice(-2).padStart(2, "0")}`;
  const stepId = `0195f200-0000-7000-8000-0000000008${suffix.slice(-2).padStart(2, "0")}`;
  const seedClaimRes = await apiPost<{ notification: { id: string } }>(
    actorA,
    `/api/v1/runs/${runId}/steps/${stepId}/claim`,
    {
      token: adminToken,
      data: {
        workspace_id: workspaceId,
        step_key: `sse-arbitration-${suffix}`,
        ttl_seconds: 900,
        force: false,
      },
    },
  );
  expect(seedClaimRes.status()).toBe(200);
  const taskId = (await seedClaimRes.json()).notification.id;

  const releaseRes = await apiPost(actorA, `/api/v1/tasks/${taskId}/release`, {
    token: adminToken,
    data: { force: false },
  });
  expect(releaseRes.status()).toBe(200);

  return { adminToken, peerToken, workspaceId, taskId };
}

async function listOpenItems(
  actor: APIRequestContext,
  workspaceId: string,
  token: string,
): Promise<InboxItem[]> {
  const listRes = await apiGet<{ items: InboxItem[] }>(
    actor,
    `/api/v1/inbox/notifications?workspace_id=${encodeURIComponent(workspaceId)}`,
    { token },
  );
  expect(listRes.ok()).toBeTruthy();
  const { items } = await listRes.json();
  return items.filter((i) => i.status === "OPEN");
}

test.describe("TEST-04 · 04 — Multi-acteurs : Claim exclusif et diffusion SSE (AD-4, AD-17 couche 5)", () => {
  test.beforeEach(({}, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "spec API : exécutée une seule fois");
    resetDay0();
  });

  test("A prend en charge une tâche, B est refusé (409) et un nouveau flux SSE rejoue l'événement (< 500 ms)", async () => {
    const actorA = await pwRequest.newContext({ baseURL: API });
    const actorB = await pwRequest.newContext({ baseURL: API });
    try {
      const { adminToken, peerToken, workspaceId, taskId } = await setupActorsAndOpenNotification(
        actorA,
        actorB,
        "01",
      );
      const open = (await listOpenItems(actorA, workspaceId, adminToken)).find(
        (item) => item.id === taskId,
      );
      expect(open, "une notification OPEN créée par API authentifiée").toBeTruthy();

      const claimA = await apiPost(actorA, `/api/v1/tasks/${taskId}/claim`, {
        token: adminToken,
        data: { workspace_id: workspaceId, ttl_seconds: 900, force: false },
      });
      expect(claimA.status()).toBe(200);
      expectDbRowExists(
        "SELECT id, status FROM task_notifications WHERE id::text = :task_id AND status = 'CLAIMED'",
        { task_id: taskId },
        "prise en charge persistée dans task_notifications PG18",
      );

      const claimB = await apiPost<{ error_code: string }>(
        actorB,
        `/api/v1/tasks/${taskId}/claim`,
        {
          token: peerToken,
          data: { workspace_id: workspaceId, ttl_seconds: 900, force: false },
        },
      );
      expect(claimB.status()).toBe(409);
      expect((await claimB.json()).error_code).toBe("ERR_STEP_ALREADY_CLAIMED_BY_PEER");

      // L'endpoint SSE unifié rejette les appels anonymes sous ORCIA_ENV="e2e" (401 fail-closed).
      const anonSse = await apiGet<{ error_code?: string }>(
        actorA,
        `/api/v1/events/stream?workspace_id=${encodeURIComponent(workspaceId)}&live=false`,
      );
      expect(anonSse.status()).toBe(401);
      expect((await anonSse.json()).error_code).toBe("ERR_AUTH_REQUIRED");

      // Un acteur qui (re)connecte son flux avec un jeton Bearer valide voit l'événement de prise en charge (< 500 ms).
      const stream = openSseStream(
        `${API}/api/v1/events/stream?workspace_id=${encodeURIComponent(workspaceId)}`,
        { token: adminToken },
      );
      try {
        await stream.ready;
        await expect
          .poll(() => stream.frames.length, { timeout: 5000 })
          .toBeGreaterThan(1);
        const claimFrames = stream.frames
          .filter((f) => f.event !== "connected")
          .map((f) => JSON.parse(f.data) as { dispatch_latency_ms?: number });
        expect(claimFrames.length).toBeGreaterThan(0);
        for (const frame of claimFrames) {
          if (typeof frame.dispatch_latency_ms === "number") {
            expect(frame.dispatch_latency_ms).toBeLessThan(SSE_BUDGET_MS);
          }
        }
      } finally {
        stream.abort();
      }
    } finally {
      await actorA.dispose();
      await actorB.dispose();
    }
  });

  test("le flux SSE d'un acteur connecté reçoit en direct la prise en charge d'un pair (< 500 ms)", async ({
    page,
  }) => {
    const actorA = await pwRequest.newContext({ baseURL: API });
    const actorB = await pwRequest.newContext({ baseURL: API });
    const { adminToken, peerToken, workspaceId, taskId } = await setupActorsAndOpenNotification(
      actorA,
      actorB,
      "02",
    );
    const stream = openSseStream(
      `${API}/api/v1/events/stream?workspace_id=${encodeURIComponent(workspaceId)}`,
      { token: peerToken },
    );
    try {
      await stream.ready;
      await expect.poll(() => stream.frames.length).toBeGreaterThan(0);
      const open = (await listOpenItems(actorA, workspaceId, adminToken)).find(
        (item) => item.id === taskId,
      );
      expect(open, "une notification OPEN créée par API authentifiée").toBeTruthy();
      const framesBefore = stream.frames.length;
      const claimStart = performance.now();
      const claim = await apiPost(actorA, `/api/v1/tasks/${taskId}/claim`, {
        token: adminToken,
        data: { workspace_id: workspaceId, ttl_seconds: 900, force: false },
      });
      expect(claim.status()).toBe(200);
      await expect
        .poll(() => stream.frames.length, { timeout: SSE_BUDGET_MS * 2 })
        .toBeGreaterThan(framesBefore);
      const latency = (stream.frames[framesBefore]?.receivedAtMs ?? Infinity) - claimStart;
      expect(latency).toBeLessThan(SSE_BUDGET_MS);

      expectDbRowExists(
        "SELECT id, status FROM task_notifications WHERE id::text = :task_id AND status = 'CLAIMED'",
        { task_id: taskId },
        "prise en charge temps réel persistée dans task_notifications PG18",
      );
      await loginLocalViaUi(page, { email: E2E_ADMIN.email, password: E2E_ADMIN.password });
      await expect(page.getByTestId("four-zone-central-workspace")).toBeVisible({ timeout: 20000 });
      await page.goto("/inbox");
      await expect(page.getByTestId("inbox-notifications-center")).toBeVisible({ timeout: 20000 });
      await expect(page.getByTestId("auth-hydrating-loader")).toBeHidden({ timeout: 10000 });
    } finally {
      stream.abort();
      await actorA.dispose();
      await actorB.dispose();
    }
  });
});
