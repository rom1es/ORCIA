import { afterEach, describe, expect, it, vi } from "vitest";
import { createRequestJson } from "../helpers";
import {
  createOrciaApiClient,
  createRequestSse,
  OrciaProblemError,
  registerDefaultAccessTokenProvider,
  registerDefaultAccessTokenRefreshedHandler,
} from "../index";

function makeSseResponse(chunks: readonly string[], status = 200): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    status,
    headers: { "Content-Type": "text/event-stream" },
  });
}

function makeProblemResponse(
  status: number,
  errorCode: string,
  detail: string,
  instance = "/api/v1/events/stream",
): Response {
  return new Response(
    JSON.stringify({
      type: "https://orcia.io/problems/error",
      title: "Erreur",
      status,
      detail,
      instance,
      error_code: errorCode,
      trace_id: "0195f000000070008000000000000001",
    }),
    {
      status,
      headers: { "Content-Type": "application/problem+json" },
    },
  );
}

describe("createRequestSse & assistantStreaming (@orcia/api-client)", () => {
  afterEach(() => {
    registerDefaultAccessTokenProvider(null);
    registerDefaultAccessTokenRefreshedHandler(null);
  });

  it("injects Authorization: Bearer, Accept-Language, Accept: text/event-stream and credentials: include", async () => {
    registerDefaultAccessTokenProvider(() => "jwt-sse-default");
    const calls: Array<{ url: string; init?: RequestInit }> = [];
    const mockFetch = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      calls.push({ url, init });
      return Promise.resolve(
        makeSseResponse([
          ": keepalive\r\n\r\n",
          'id: evt-1\nevent: connected\ndata: {"ok":true}\n\n',
        ]),
      );
    });

    const requestSse = createRequestSse({
      baseUrl: "http://api.test",
      locale: "en",
      traceId: "trace-sse-1",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    const received: Array<{ eventName: string; data: Record<string, unknown>; eventId?: string }> = [];
    let openedStatus = 0;

    await requestSse({
      path: "/api/v1/events/stream?workspace_id=ws-1",
      onOpen: (resp) => {
        openedStatus = resp.status;
      },
      onEvent: (eventName, data, eventId) => {
        received.push({ eventName, data, eventId });
      },
    });

    expect(openedStatus).toBe(200);
    expect(calls).toHaveLength(1);
    expect(calls[0]?.url).toBe("http://api.test/api/v1/events/stream?workspace_id=ws-1");
    expect(calls[0]?.init?.credentials).toBe("include");
    const headers = calls[0]?.init?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer jwt-sse-default");
    expect(headers["Accept-Language"]).toBe("en");
    expect(headers.Accept).toBe("text/event-stream");
    expect(headers["X-Trace-Id"]).toBe("trace-sse-1");
    expect(received).toEqual([
      { eventName: "connected", data: { ok: true }, eventId: "evt-1" },
    ]);
  });

  it("attempts a single session refresh on 401 and notifies registerDefaultAccessTokenRefreshedHandler before retrying", async () => {
    registerDefaultAccessTokenProvider(() => "expired-jwt");
    const refreshedTokens: string[] = [];
    registerDefaultAccessTokenRefreshedHandler((token) => refreshedTokens.push(token));

    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce(
        makeProblemResponse(401, "ERR_AUTH_REQUIRED", "Jeton expiré", "/api/v1/assistant/three-speed/stream"),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: "fresh-jwt-2" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        makeSseResponse(['event: turn_completed\ndata: {"response_text":"ok"}\n\n']),
      );

    const requestSse = createRequestSse({
      baseUrl: "http://api.test",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    const events: string[] = [];
    await requestSse({
      path: "/api/v1/assistant/three-speed/stream",
      method: "POST",
      body: { user_prompt: "Bonjour" },
      onEvent: (name) => events.push(name),
    });

    expect(mockFetch).toHaveBeenCalledTimes(3);
    expect(mockFetch.mock.calls[1]?.[0]).toBe("http://api.test/api/v1/auth/refresh");
    const refreshHeaders = (mockFetch.mock.calls[1]?.[1] as RequestInit).headers as Record<string, string>;
    expect(refreshHeaders.Authorization).toBeUndefined();
    const retryHeaders = (mockFetch.mock.calls[2]?.[1] as RequestInit).headers as Record<string, string>;
    expect(retryHeaders.Authorization).toBe("Bearer fresh-jwt-2");
    expect(refreshedTokens).toEqual(["fresh-jwt-2"]);
    expect(events).toEqual(["turn_completed"]);
  });

  it("stops with OrciaProblemError without infinite loop when 401 refresh fails", async () => {
    registerDefaultAccessTokenProvider(() => "expired-jwt");
    const onRefreshed = vi.fn();
    registerDefaultAccessTokenRefreshedHandler(onRefreshed);

    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce(
        makeProblemResponse(401, "ERR_AUTH_REQUIRED", "Session expirée"),
      )
      .mockResolvedValueOnce(
        makeProblemResponse(401, "ERR_REFRESH_INVALID", "Refresh invalide", "/api/v1/auth/refresh"),
      );

    const requestSse = createRequestSse({
      baseUrl: "http://api.test",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    await expect(
      requestSse({ path: "/api/v1/events/stream?workspace_id=ws-1" }),
    ).rejects.toSatisfy((err: unknown) => {
      return (
        err instanceof OrciaProblemError &&
        err.problem.status === 401 &&
        err.problem.error_code === "ERR_AUTH_REQUIRED"
      );
    });

    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(onRefreshed).not.toHaveBeenCalled();
  });

  it("throws OrciaProblemError on non-ok application/problem+json responses (403 / 503) without retrying refresh", async () => {
    registerDefaultAccessTokenProvider(() => "valid-jwt");
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce(
        makeProblemResponse(403, "ERR_FORBIDDEN_SCOPE", "Accès interdit au workspace"),
      )
      .mockResolvedValueOnce(
        makeProblemResponse(503, "ERR_AI_UNAVAILABLE", "Modèle IA indisponible"),
      );

    const requestSse = createRequestSse({
      baseUrl: "http://api.test",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    await expect(
      requestSse({ path: "/api/v1/events/stream?workspace_id=ws-forbidden" }),
    ).rejects.toMatchObject({
      name: "OrciaProblemError",
      problem: { status: 403, error_code: "ERR_FORBIDDEN_SCOPE" },
    });

    await expect(
      requestSse({ path: "/api/v1/assistant/three-speed/stream", method: "POST", body: {} }),
    ).rejects.toMatchObject({
      name: "OrciaProblemError",
      problem: { status: 503, error_code: "ERR_AI_UNAVAILABLE" },
    });

    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("routes assistantStreaming methods to 2-step POST /turns + GET /turns/{id}/stream, /executions/{id}/trace-stream and /events/stream with Bearer", async () => {
    registerDefaultAccessTokenProvider(() => "client-jwt-token");
    const mockFetch = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith("/api/v1/assistant/turns")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              turn_id: "turn-abc",
              workspace_id: "ws-1",
              speed_mode: "SPEED_1_FAST",
              status: "RUNNING",
              stream_url: "/api/v1/assistant/turns/turn-abc/stream",
              trace_id: "trace-1",
            }),
            { status: 202, headers: { "Content-Type": "application/json" } },
          ),
        );
      }
      return Promise.resolve(
        makeSseResponse(['event: ping\ndata: {"ok":true}\n\n']),
      );
    });

    const client = createOrciaApiClient({
      baseUrl: "http://api.test",
      locale: "fr",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    const accepted = await client.streamAssistantTurnSse({
      workspace_id: "ws-1",
      hat: "PM",
      user_prompt: "Synthèse ?",
      requested_speed: "SPEED_1_FAST",
      deep_audit_pill_active: false,
      requested_tier: "medium",
      thinking_effort: "balanced",
      conversation_history: [],
      locale: "fr",
    });

    await client.streamReflexiveExecutionTraceSse("exec/123", {
      personaKey: "karim",
    });

    await client.streamWorkspaceEventsSse("ws-42", {
      live: false,
      personaKey: "karim",
    });

    expect(accepted.turn_id).toBe("turn-abc");
    expect(mockFetch).toHaveBeenCalledTimes(4);
    expect(mockFetch.mock.calls[0]?.[0]).toBe(
      "http://api.test/api/v1/assistant/turns",
    );
    expect((mockFetch.mock.calls[0]?.[1] as RequestInit).method).toBe("POST");
    expect(mockFetch.mock.calls[1]?.[0]).toBe(
      "http://api.test/api/v1/assistant/turns/turn-abc/stream",
    );
    expect((mockFetch.mock.calls[1]?.[1] as RequestInit).method).toBe("GET");
    expect(mockFetch.mock.calls[2]?.[0]).toBe(
      "http://api.test/api/v1/executions/exec%2F123/trace-stream?persona_key=karim",
    );
    expect((mockFetch.mock.calls[2]?.[1] as RequestInit).method).toBe("GET");
    expect(mockFetch.mock.calls[3]?.[0]).toBe(
      "http://api.test/api/v1/events/stream?workspace_id=ws-42&live=false&persona_key=karim",
    );
    expect((mockFetch.mock.calls[3]?.[1] as RequestInit).method).toBe("GET");

    for (const call of mockFetch.mock.calls) {
      const headers = (call[1] as RequestInit).headers as Record<string, string>;
      expect(headers.Authorization).toBe("Bearer client-jwt-token");
      expect(headers["Accept-Language"]).toBe("fr");
    }
  });

  it("shares single-flight /api/v1/auth/refresh lock across concurrent createRequestSse and createRequestJson calls on 401", async () => {
    let activeToken = "expired-jwt-1";
    registerDefaultAccessTokenProvider(() => activeToken);
    const refreshedHandler = vi.fn((next: string) => {
      activeToken = next;
    });
    registerDefaultAccessTokenRefreshedHandler(refreshedHandler);

    let refreshCount = 0;
    let resolveRefresh!: (resp: Response) => void;
    const refreshGate = new Promise<Response>((resolve) => {
      resolveRefresh = resolve;
    });

    const mockFetch = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      const auth = ((init?.headers ?? {}) as Record<string, string>).Authorization;
      if (url.endsWith("/api/v1/auth/refresh")) {
        refreshCount += 1;
        return refreshGate;
      }
      if (auth !== "Bearer fresh-single-flight-jwt") {
        return Promise.resolve(
          makeProblemResponse(401, "ERR_AUTH_REQUIRED", "Jeton expiré", url),
        );
      }
      if (url.includes("/events/stream")) {
        return Promise.resolve(
          makeSseResponse(['event: connected\ndata: {"ok":true}\n\n']),
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify({ ok: true, path: url }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });

    const clientOptions = {
      baseUrl: "http://api.test",
      fetchImpl: mockFetch as unknown as typeof fetch,
    };
    const requestSse = createRequestSse(clientOptions);
    const requestJson = createRequestJson(clientOptions);

    const sseEvents: string[] = [];
    const pSse = requestSse({
      path: "/api/v1/events/stream?workspace_id=ws-1",
      onEvent: (name) => sseEvents.push(name),
    });
    const pJson1 = requestJson<{ ok: boolean }>("/api/v1/workspaces");
    const pJson2 = requestJson<{ ok: boolean }>("/api/v1/org-units");

    // Wait a microtask so all 3 initial requests hit 401 and coalesce onto the single refresh lock
    await new Promise((r) => setTimeout(r, 10));
    expect(refreshCount).toBe(1);

    resolveRefresh(
      new Response(JSON.stringify({ access_token: "fresh-single-flight-jwt" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const [, res1, res2] = await Promise.all([pSse, pJson1, pJson2]);
    expect(refreshCount).toBe(1);
    expect(refreshedHandler).toHaveBeenCalledTimes(1);
    expect(refreshedHandler).toHaveBeenCalledWith("fresh-single-flight-jwt");
    expect(sseEvents).toEqual(["connected"]);
    expect(res1.ok).toBe(true);
    expect(res2.ok).toBe(true);
    expect(activeToken).toBe("fresh-single-flight-jwt");
  });

  it("resets single-flight refresh lock cleanly on refresh failure without leaking in-flight state", async () => {
    registerDefaultAccessTokenProvider(() => "expired-jwt-2");
    const refreshedHandler = vi.fn();
    registerDefaultAccessTokenRefreshedHandler(refreshedHandler);

    let refreshAttempts = 0;
    const mockFetch = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith("/api/v1/auth/refresh")) {
        refreshAttempts += 1;
        if (refreshAttempts === 1) {
          return Promise.resolve(
            makeProblemResponse(401, "ERR_REFRESH_INVALID", "Refresh échoué", "/api/v1/auth/refresh"),
          );
        }
        return Promise.resolve(
          new Response(JSON.stringify({ access_token: "recovered-jwt-3" }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      return Promise.resolve(
        makeProblemResponse(401, "ERR_AUTH_REQUIRED", "Session expirée", url),
      );
    });

    const clientOptions = {
      baseUrl: "http://api.test",
      fetchImpl: mockFetch as unknown as typeof fetch,
    };
    const requestSse = createRequestSse(clientOptions);
    const requestJson = createRequestJson(clientOptions);

    // Phase 1: concurrent SSE + JSON both fail cleanly after a single failed refresh
    const results = await Promise.allSettled([
      requestSse({ path: "/api/v1/events/stream?workspace_id=ws-1" }),
      requestJson("/api/v1/workspaces"),
    ]);
    expect(refreshAttempts).toBe(1);
    expect(refreshedHandler).not.toHaveBeenCalled();
    for (const r of results) {
      expect(r.status).toBe("rejected");
      if (r.status === "rejected") {
        expect(r.reason).toBeInstanceOf(OrciaProblemError);
        expect((r.reason as OrciaProblemError).problem.status).toBe(401);
      }
    }

    // Phase 2: lock is cleared (finally), so a subsequent 401 triggers a fresh refresh attempt
    await expect(
      requestJson("/api/v1/workspaces"),
    ).rejects.toBeInstanceOf(OrciaProblemError);
    expect(refreshAttempts).toBe(2);
    expect(refreshedHandler).toHaveBeenCalledWith("recovered-jwt-3");
  });
});
