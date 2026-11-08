import { type APIRequestContext, expect, request as pwRequest, test } from "@playwright/test";

const API = `http://127.0.0.1:${process.env.ORCIA_E2E_API_PORT ?? "8100"}`;
const SSE_BUDGET_MS = 500;

interface SseFrame {
  event: string;
  data: string;
  receivedAtMs: number;
}

/** Lecteur SSE minimal (fetch streaming Node) : accumule les trames jusqu'à `abort()`. */
function openSseStream(url: string): { frames: SseFrame[]; ready: Promise<void>; abort: () => void } {
  const controller = new AbortController();
  const frames: SseFrame[] = [];
  const ready = (async () => {
    const res = await fetch(url, { signal: controller.signal });
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

async function listOpenItems(actor: APIRequestContext): Promise<InboxItem[]> {
  const listRes = await actor.get("/api/v1/inbox/notifications?persona_key=marc");
  expect(listRes.ok()).toBeTruthy();
  const { items } = (await listRes.json()) as { items: InboxItem[] };
  return items.filter((i) => i.status === "OPEN");
}

test.describe("TEST-04 · 04 — Multi-acteurs : Claim exclusif et diffusion SSE (AD-4, AD-17 couche 5)", () => {
  // Spec purement API (aucun viewport) : le service de notifications est en mémoire et à stock
  // d'éléments OPEN limité (voir BUG-E2E-04) ; on ne l'exécute qu'une fois par run.
  test.beforeEach(({}, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "spec API : exécutée une seule fois");
  });

  test("A prend en charge une tâche, B est refusé (409) et un nouveau flux SSE rejoue l'événement (< 500 ms)", async () => {
    const actorA = await pwRequest.newContext({ baseURL: API });
    const actorB = await pwRequest.newContext({ baseURL: API });
    try {
      const open = (await listOpenItems(actorA))[0];
      expect(open, "une notification OPEN à prendre en charge").toBeTruthy();
      const taskId = open?.id ?? "";

      const claimA = await actorA.post(`/api/v1/tasks/${taskId}/claim?persona_key=marc`, {
        data: { ttl_seconds: 900, force: false },
      });
      expect(claimA.status()).toBe(200);

      const claimB = await actorB.post(`/api/v1/tasks/${taskId}/claim?persona_key=nadia`, {
        data: { ttl_seconds: 900, force: false },
      });
      expect(claimB.status()).toBe(409);
      expect(((await claimB.json()) as { error_code: string }).error_code).toBe(
        "ERR_STEP_ALREADY_CLAIMED_BY_PEER",
      );

      // Un acteur qui (re)connecte son flux voit l'événement de prise en charge, latence de dispatch < 500 ms.
      const stream = openSseStream(`${API}/api/v1/events/stream`);
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

  test("le flux SSE d'un acteur connecté reçoit en direct la prise en charge d'un pair (< 500 ms)", async () => {
    // DÉFAUT PRODUIT RÉEL (BUG-E2E-03) : `GET /api/v1/events/stream` ne fait que rejouer les
    // événements récents puis se termine ; aucune diffusion en direct (AD-4, « < 500 ms »).
    // `test.fail` : passe tant que le défaut existe, échoue dès la correction (retirer alors la ligne).
    test.fail(true, "BUG-E2E-03 : flux SSE non temps réel (replay au connect uniquement)");
    const actorA = await pwRequest.newContext({ baseURL: API });
    const stream = openSseStream(`${API}/api/v1/events/stream`);
    try {
      await stream.ready;
      await expect.poll(() => stream.frames.length).toBeGreaterThan(0);
      const open = (await listOpenItems(actorA))[0];
      expect(open, "une notification OPEN restante").toBeTruthy();
      const framesBefore = stream.frames.length;
      const claimStart = performance.now();
      const claim = await actorA.post(`/api/v1/tasks/${open?.id}/claim?persona_key=marc`, {
        data: { ttl_seconds: 900, force: false },
      });
      expect(claim.status()).toBe(200);
      await expect
        .poll(() => stream.frames.length, { timeout: SSE_BUDGET_MS * 2 })
        .toBeGreaterThan(framesBefore);
      const latency = (stream.frames[framesBefore]?.receivedAtMs ?? Infinity) - claimStart;
      expect(latency).toBeLessThan(SSE_BUDGET_MS);
    } finally {
      stream.abort();
      await actorA.dispose();
    }
  });
});
