// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { OrciaRootErrorBoundary } from "../components/OrciaRootErrorBoundary";
import { useWorkspaceEventsSse } from "../components/useWorkspaceEventsSse";
import {
  classifyAssistantStreamError,
  resetBackgroundAssistantStreamForTests,
} from "../features/inbox/assistantBackgroundStreamStore";
import { clearSavedAssistantConversationsStorage } from "../features/inbox/savedConversationsStore";
import { useReflexiveExecutionController } from "../features/shared/useReflexiveExecutionController";
import { ASSISTANT_EN_LABELS, ASSISTANT_FR_LABELS } from "../i18n/locales/assistant_labels";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";
import { OrciaProblemError } from "@orcia/api-client";
import {
  getRecordedVitestApiCalls,
  resetVitestApiBackend,
  seedVitestPlatformSetupState,
  vitestFetchTransport,
} from "./vitest.setup";

function seedAssistantReadyState(accessToken = "jwt-story-23-2-token"): void {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: "0192c4e0-0000-7000-8000-000000000201",
          name: "Direction Produit",
          slug: "direction-produit",
          level: "BU",
          parentId: null,
          billingEnabled: true,
        },
      ],
      llm_tiers: [
        {
          tier: "medium",
          primaryModel: "qwen3-32b",
          model_name: "qwen3-32b",
          endpoint_url: "http://127.0.0.1:11434",
          usage: "chat",
          is_active: true,
        },
        {
          tier: "fast",
          primaryModel: "nomic-embed-text",
          model_name: "nomic-embed-text",
          endpoint_url: "http://127.0.0.1:11434",
          usage: "embedding",
          is_active: true,
        },
      ],
      ai_model_mappings: [
        {
          id: "chat-23-2",
          scope_level: "GLOBAL",
          scope_id: null,
          inference_tier: "medium",
          usage: "chat",
          is_active: true,
          provider_slug: "ollama",
          model_family: "Ollama",
          model_name: "qwen3-32b",
          endpoint_uri: "http://127.0.0.1:11434/v1",
        },
        {
          id: "emb-23-2",
          scope_level: "GLOBAL",
          scope_id: null,
          inference_tier: "simple",
          usage: "embedding",
          is_active: true,
          provider_slug: "ollama",
          model_family: "Ollama",
          model_name: "nomic-embed-text",
          endpoint_uri: "http://127.0.0.1:11434/v1",
        },
      ],
      workspaces: [
        {
          workspaceId: "0195f000-0000-7000-8000-000000000301",
          name: "Espace Test 23.2",
          visibilityMode: "STANDARD",
          ownerOrgUnitName: "Direction Produit",
          lifecyclePhase: "BUILD",
          suggestedWorkflows: [],
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
    },
    {
      email: "admin.232@orcia.fr",
      displayName: "Admin 23.2",
      roles: ["PLATFORM_ADMIN"],
    },
  );
  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken,
    email: "admin.232@orcia.fr",
    displayName: "Admin 23.2",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "PLATFORM_ADMIN",
    readOnlyObserver: false,
    mustChangePassword: false,
  });
}

function makeProblemDetailsResponse(
  status: number,
  errorCode: string,
  detail: string,
  instance: string,
): Response {
  return new Response(
    JSON.stringify({
      type: "https://orcia.io/problems/error",
      title: "Erreur",
      status,
      detail,
      instance,
      error_code: errorCode,
      trace_id: "0195f000000070008000000000000232",
    }),
    {
      status,
      headers: { "Content-Type": "application/problem+json" },
    },
  );
}

function makeSseStream(frames: readonly string[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const frame of frames) {
        controller.enqueue(encoder.encode(frame));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

function WorkspaceEventsProbe({
  workspaceId,
  enabled = true,
}: {
  readonly workspaceId: string | undefined;
  readonly enabled?: boolean;
}) {
  const { connected, lastClaimEvent } = useWorkspaceEventsSse(workspaceId, { enabled });
  return (
    <div>
      <span data-testid="ws-sse-connected">{String(connected)}</span>
      <span data-testid="ws-sse-last-event">{lastClaimEvent?.eventName ?? "none"}</span>
    </div>
  );
}

function ReflexiveProbe() {
  const ctrl = useReflexiveExecutionController({
    storageKey: "orcia.reflexive_exec.test_23_2",
    locale: "fr",
  });
  return (
    <div>
      <button
        type="button"
        data-testid="probe-start-reflexive"
        onClick={() => {
          void ctrl.startExecution({
            actor_slug: "assistant-agent",
            objective: "Analyser capabilities.yaml",
          });
        }}
      >
        Start
      </button>
      <span data-testid="probe-reflexive-status">{ctrl.status ?? "IDLE"}</span>
      <span data-testid="probe-reflexive-events">{String(ctrl.events.length)}</span>
    </div>
  );
}

describe("Story 23.2 — Authenticated SSE hooks & 401 vs AI unavailable UX banner", () => {
  beforeEach(() => {
    resetVitestApiBackend();
    resetAuthSessionStore();
    resetBackgroundAssistantStreamForTests();
    clearSavedAssistantConversationsStorage();
    globalThis.fetch = vitestFetchTransport as typeof fetch;
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    resetBackgroundAssistantStreamForTests();
    resetAuthSessionStore();
    globalThis.fetch = vitestFetchTransport as typeof fetch;
  });

  it("classifies 401/403 as auth_expired (no HTTP 401, no AI blame) and 502/503/504/network as ai_unavailable in FR & EN", () => {
    for (const status of [401, 403]) {
      const err = new OrciaProblemError({
        type: "https://orcia.io/problems/auth-required",
        title: "Authentification requise",
        status,
        detail: `HTTP ${status} Unauthorized`,
        instance: "/api/v1/assistant/turns",
        error_code: status === 401 ? "ERR_AUTH_REQUIRED" : "ERR_FORBIDDEN_SCOPE",
        trace_id: "0195f000000070008000000000000001",
      });

      const frRes = classifyAssistantStreamError(err, true, ASSISTANT_FR_LABELS.assistantStreamErrors);
      expect(frRes.errorKind).toBe("auth_expired");
      expect(frRes.errorMessage).not.toContain("HTTP 401");
      expect(frRes.errorMessage).not.toContain("HTTP 403");
      expect(frRes.errorMessage).not.toContain("modèle IA");
      expect(frRes.errorMessage).toContain("session a expiré");

      const enRes = classifyAssistantStreamError(err, false, ASSISTANT_EN_LABELS.assistantStreamErrors);
      expect(enRes.errorKind).toBe("auth_expired");
      expect(enRes.errorMessage).not.toContain("HTTP 401");
      expect(enRes.errorMessage).not.toContain("AI model");
      expect(enRes.errorMessage).toContain("session has expired");
    }

    for (const status of [502, 503, 504]) {
      const err = new OrciaProblemError({
        type: "https://orcia.io/problems/ai-unavailable",
        title: "Service IA indisponible",
        status,
        detail: "Fournisseur LLM injoignable",
        instance: "/api/v1/assistant/turns",
        error_code: "ERR_AI_UNAVAILABLE",
        trace_id: "0195f000000070008000000000000002",
      });
      const frRes = classifyAssistantStreamError(err, true, ASSISTANT_FR_LABELS.assistantStreamErrors);
      expect(frRes.errorKind).toBe("ai_unavailable");
      expect(frRes.errorMessage).toContain("modèle IA configuré");
    }

    const networkRes = classifyAssistantStreamError(
      new TypeError("Failed to fetch"),
      true,
      ASSISTANT_FR_LABELS.assistantStreamErrors,
    );
    expect(networkRes.errorKind).toBe("ai_unavailable");
    expect(networkRes.errorMessage).toContain("modèle IA configuré");
  });

  it("displays critical role='alert' banner with reconnect button on 401 stream failure and resets session + navigates to /login", async () => {
    seedAssistantReadyState("expired-jwt-token");

    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const rawUrl = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const pathname = new URL(rawUrl, "http://127.0.0.1:8000").pathname;
      if (pathname === "/api/v1/assistant/turns") {
        return makeProblemDetailsResponse(
          401,
          "ERR_AUTH_REQUIRED",
          "Jeton expiré",
          "/api/v1/assistant/turns",
        );
      }
      if (pathname === "/api/v1/auth/refresh") {
        return makeProblemDetailsResponse(
          401,
          "ERR_REFRESH_INVALID",
          "Session expirée",
          "/api/v1/auth/refresh",
        );
      }
      return vitestFetchTransport(input, init);
    }) as typeof fetch;

    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/assistant"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    const input = await screen.findByTestId("assistant-three-speed-input");
    fireEvent.change(input, { target: { value: "Explique la gouvernance" } });
    fireEvent.click(screen.getByTestId("assistant-three-speed-send-btn"));

    const banner = await screen.findByTestId("assistant-error-banner");
    expect(banner.getAttribute("role")).toBe("alert");
    expect(banner.getAttribute("data-error-kind")).toBe("auth_expired");
    expect(banner.textContent).toContain("Votre session a expiré");
    expect(banner.textContent).not.toContain("HTTP 401");
    expect(banner.textContent).not.toContain("modèle IA");

    const reconnectBtn = screen.getByTestId("assistant-error-reconnect-btn");
    expect(reconnectBtn.textContent).toBe("Se reconnecter →");
    fireEvent.click(reconnectBtn);

    await waitFor(() => {
      expect(useAuthSessionStore.getState().isAuthenticated).toBe(false);
      expect(useAuthSessionStore.getState().accessToken).toBeNull();
      expect(router.state.location.pathname).toBe("/login");
    });
  });

  it("displays ai_unavailable diagnostic without reconnect button when assistant stream returns 503", async () => {
    seedAssistantReadyState("valid-jwt-token");

    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const rawUrl = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const pathname = new URL(rawUrl, "http://127.0.0.1:8000").pathname;
      if (pathname === "/api/v1/assistant/turns") {
        return makeProblemDetailsResponse(
          503,
          "ERR_AI_UNAVAILABLE",
          "Service LLM temporairement arrêté",
          "/api/v1/assistant/turns",
        );
      }
      if (pathname === "/api/v1/assistant/turns/active") {
        return new Response(
          JSON.stringify({ workspace_id: "ws-23-2", turns: [] }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return vitestFetchTransport(input, init);
    }) as typeof fetch;

    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/assistant"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    const input = await screen.findByTestId("assistant-three-speed-input");
    fireEvent.change(input, { target: { value: "Donne la météo projet" } });
    fireEvent.click(screen.getByTestId("assistant-three-speed-send-btn"));

    const banner = await screen.findByTestId("assistant-error-banner");
    expect(banner.getAttribute("role")).toBe("alert");
    expect(banner.getAttribute("data-error-kind")).toBe("ai_unavailable");
    expect(banner.textContent).toContain("Vérifiez que le modèle IA configuré est bien démarré");
    expect(screen.queryByTestId("assistant-error-reconnect-btn")).toBeNull();
  });

  it("keeps useWorkspaceEventsSse inactive without token, connects with Bearer when authenticated, and stops cleanly on 401/403 without loop", async () => {
    const fetchSpy = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
      const rawUrl = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      if (rawUrl.includes("/api/v1/events/stream")) {
        return makeSseStream([
          'event: connected\ndata: {"workspace_id":"ws-23-2"}\n\n',
          `id: ev-claim-1\nevent: task.claim.locked\ndata: ${JSON.stringify({
            event_id: "ev-claim-1",
            event_name: "task.claim.locked",
            workspace_id: "ws-23-2",
            run_id: "run-1",
            step_execution_id: "step-1",
            dispatch_latency_ms: 12,
            payload: { claimed_by: "user-1" },
          })}\n\n`,
        ]);
      }
      return makeProblemDetailsResponse(404, "ERR_NOT_FOUND", "Not found", rawUrl);
    });
    globalThis.fetch = fetchSpy as unknown as typeof fetch;

    // 1. Unauthenticated -> inactive (0 calls)
    useAuthSessionStore.setState({ isAuthenticated: false, accessToken: null });
    const { rerender } = render(<WorkspaceEventsProbe workspaceId="ws-23-2" />);
    expect(screen.getByTestId("ws-sse-connected").textContent).toBe("false");
    expect(fetchSpy).toHaveBeenCalledTimes(0);

    // 2. Authenticated -> sends Bearer and parses claim event
    useAuthSessionStore.setState({ isAuthenticated: true, accessToken: "jwt-ws-events-1" });
    rerender(<WorkspaceEventsProbe workspaceId="ws-23-2" />);

    await waitFor(() => {
      expect(screen.getByTestId("ws-sse-last-event").textContent).toBe("task.claim.locked");
    });
    const sseCallHeaders = (fetchSpy.mock.calls[0]?.[1] as RequestInit | undefined)?.headers as
      | Record<string, string>
      | undefined;
    expect(sseCallHeaders?.Authorization).toBe("Bearer jwt-ws-events-1");
    cleanup();

    // 3. 403 / 401 -> stops immediately without reconnect loop
    for (const status of [403, 401] as const) {
      const guardSpy = vi.fn(async (input: RequestInfo | URL) => {
        const rawUrl = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
        if (rawUrl.includes("/api/v1/auth/refresh")) {
          return makeProblemDetailsResponse(401, "ERR_REFRESH_INVALID", "Refresh invalid", "/api/v1/auth/refresh");
        }
        return makeProblemDetailsResponse(status, "ERR_GUARD", "Denied", "/api/v1/events/stream");
      });
      globalThis.fetch = guardSpy as unknown as typeof fetch;
      useAuthSessionStore.setState({ isAuthenticated: true, accessToken: "jwt-ws-guard" });
      render(<WorkspaceEventsProbe workspaceId="ws-23-2-guard" />);

      await waitFor(() => {
        expect(guardSpy.mock.calls.length).toBeGreaterThanOrEqual(status === 401 ? 2 : 1);
      });
      const countAfterStop = guardSpy.mock.calls.length;
      await new Promise((r) => setTimeout(r, 80));
      expect(guardSpy.mock.calls.length).toBe(countAfterStop);
      expect(screen.getByTestId("ws-sse-connected").textContent).toBe("false");
      cleanup();
    }
  });

  it("streams reflexive execution trace via streamReflexiveExecutionTraceSse with Authorization: Bearer", async () => {
    seedAssistantReadyState("jwt-reflexive-trace-23-2");

    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const rawUrl = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const pathname = new URL(rawUrl, "http://127.0.0.1:8000").pathname;
      if (pathname === "/api/v1/executions/reflexive" && (init?.method ?? "GET") === "POST") {
        // Record call via vitestFetchTransport or return RUNNING snapshot directly
        await vitestFetchTransport(input, init);
        return new Response(
          JSON.stringify({
            execution_id: "exec-23-2-stream",
            actor_slug: "assistant-agent",
            objective: "Analyser capabilities.yaml",
            status: "RUNNING",
            effort_mode: "equilibre",
            max_turns: 15,
            max_budget_tokens: 24000,
            turns_used: 1,
            tokens_used: 120,
            trace_events: [],
            pending_write_preview: null,
            final_markdown: null,
            artifact_pointer: null,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (pathname === "/api/v1/executions/exec-23-2-stream/trace-stream") {
        await vitestFetchTransport(input, init);
        return makeSseStream([
          `event: trace_event\ndata: ${JSON.stringify({
            event_id: "ev-232-1",
            execution_id: "exec-23-2-stream",
            sequence_index: 1,
            turn_index: 1,
            kind: "thought_completed",
            timestamp_utc: "2026-11-19T21:00:00Z",
            delta_text: "Trace SSE authentifiée reçue",
            metadata: { actor_slug: "assistant-agent" },
          })}\n\n`,
        ]);
      }
      if (pathname === "/api/v1/executions/exec-23-2-stream" && (init?.method ?? "GET") === "GET") {
        return new Response(
          JSON.stringify({
            execution_id: "exec-23-2-stream",
            actor_slug: "assistant-agent",
            objective: "Analyser capabilities.yaml",
            status: "COMPLETED",
            effort_mode: "equilibre",
            max_turns: 15,
            max_budget_tokens: 24000,
            turns_used: 1,
            tokens_used: 200,
            trace_events: [
              {
                event_id: "ev-232-1",
                execution_id: "exec-23-2-stream",
                sequence_index: 1,
                turn_index: 1,
                kind: "thought_completed",
                timestamp_utc: "2026-11-19T21:00:00Z",
                delta_text: "Trace SSE authentifiée reçue",
                metadata: { actor_slug: "assistant-agent" },
              },
            ],
            pending_write_preview: null,
            final_markdown: "OK",
            artifact_pointer: null,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return vitestFetchTransport(input, init);
    }) as typeof fetch;

    render(<ReflexiveProbe />);
    fireEvent.click(screen.getByTestId("probe-start-reflexive"));

    await waitFor(() => {
      expect(screen.getByTestId("probe-reflexive-status").textContent).toBe("COMPLETED");
      expect(Number(screen.getByTestId("probe-reflexive-events").textContent)).toBeGreaterThanOrEqual(1);
    });

    const traceCall = getRecordedVitestApiCalls().find((c) =>
      c.path.includes("/api/v1/executions/exec-23-2-stream/trace-stream"),
    );
    expect(traceCall).toBeDefined();
    expect(traceCall?.headers?.authorization).toBe("Bearer jwt-reflexive-trace-23-2");
  });

  it("does not abort an active useWorkspaceEventsSse stream when accessToken is refreshed in authSessionStore", async () => {
    let abortCount = 0;
    const controllerRef: { current: ReadableStreamDefaultController<Uint8Array> | null } = {
      current: null,
    };
    const encoder = new TextEncoder();

    const fetchSpy = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      init?.signal?.addEventListener("abort", () => {
        abortCount += 1;
      });
      const stream = new ReadableStream<Uint8Array>({
        start(controller) {
          controllerRef.current = controller;
          controller.enqueue(encoder.encode('event: connected\ndata: {"workspace_id":"ws-keepalive"}\n\n'));
        },
      });
      return Promise.resolve(
        new Response(stream, {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
      );
    });
    globalThis.fetch = fetchSpy as unknown as typeof fetch;

    useAuthSessionStore.setState({ isAuthenticated: true, accessToken: "jwt-initial-1" });
    render(<WorkspaceEventsProbe workspaceId="ws-keepalive" />);

    await waitFor(() => {
      expect(screen.getByTestId("ws-sse-connected").textContent).toBe("true");
    });
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(abortCount).toBe(0);

    // Simulate single-flight refresh updating accessToken while isAuthenticated stays true
    useAuthSessionStore.getState().setAuthSession({
      accessToken: "jwt-refreshed-2",
      isAuthenticated: true,
    });
    await new Promise((r) => setTimeout(r, 50));

    expect(abortCount).toBe(0);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("ws-sse-connected").textContent).toBe("true");

    controllerRef.current?.close();
    cleanup();
  });

  it("renders OrciaRootErrorBoundary fallback with role='alert' and data-testid='orcia-root-error-boundary' on render throw", () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);

    function ThrowingChild(): React.JSX.Element {
      throw new Error("Boom runtime UI");
    }

    render(
      <OrciaRootErrorBoundary>
        <ThrowingChild />
      </OrciaRootErrorBoundary>,
    );

    const boundary = screen.getByTestId("orcia-root-error-boundary");
    expect(boundary).toBeDefined();
    const alert = boundary.querySelector("[role='alert']");
    expect(alert).not.toBeNull();
    expect(alert?.textContent).toContain("Une erreur d'affichage inattendue est survenue.");
    expect(alert?.textContent).toContain("Boom runtime UI");
    expect(screen.getByTestId("orcia-root-error-reload-btn")).toBeDefined();
  });
});
