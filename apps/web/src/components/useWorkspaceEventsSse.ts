import { createOrciaApiClient, OrciaProblemError } from "@orcia/api-client";
import { useEffect, useState } from "react";
import { useAuthSessionStore } from "../stores/authSessionStore";

export interface WorkspaceSseClaimEvent {
  readonly eventId: string;
  readonly eventName: string;
  readonly workspaceId: string;
  readonly runId: string;
  readonly stepExecutionId: string;
  readonly dispatchLatencyMs: number;
  readonly payload: Record<string, unknown>;
}

const TRACKED_WORKSPACE_EVENTS = new Set<string>([
  "task.claim.locked",
  "task.claim.released",
  "autonomous.run.killed",
  "autonomous.artifact.rolled_back",
  "TriggerFired",
  "TriggerCircuitOpened",
  "AutonomousEscalated",
  "PostHocSampleSelected",
]);

/**
 * Consommateur SSE temps réel authentifié (`GET /api/v1/events/stream`, `AD-4`, `< 500 ms`).
 * Utilise `createRequestSse` (Bearer JWT + RFC 9457) et reste inactif tant qu'aucune session valide n'est présente.
 */
export function useWorkspaceEventsSse(
  workspaceId: string | undefined,
  options?: { readonly enabled?: boolean },
): {
  readonly connected: boolean;
  readonly lastClaimEvent: WorkspaceSseClaimEvent | null;
} {
  const isAuthenticated = useAuthSessionStore((s) => s.isAuthenticated);
  const [connected, setConnected] = useState(false);
  const [lastClaimEvent, setLastClaimEvent] = useState<WorkspaceSseClaimEvent | null>(null);

  useEffect(() => {
    const trimmed = workspaceId?.trim() ?? "";
    const currentToken = useAuthSessionStore.getState().accessToken;
    if (!trimmed || !isAuthenticated || !currentToken || options?.enabled === false) {
      setConnected(false);
      return;
    }

    let disposed = false;
    let activeController: AbortController | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let retryAttempt = 0;

    const scheduleReconnect = () => {
      if (disposed) return;
      const delayMs = Math.min(30_000, 1_500 * 2 ** retryAttempt);
      retryAttempt += 1;
      retryTimer = setTimeout(() => {
        if (!disposed) {
          void connect();
        }
      }, delayMs);
    };

    const connect = async (): Promise<void> => {
      if (disposed) return;
      const controller = new AbortController();
      activeController = controller;
      const client = createOrciaApiClient({ baseUrl: "" });
      try {
        await client.streamWorkspaceEventsSse(trimmed, {
          signal: controller.signal,
          onOpen: () => {
            if (!disposed && !controller.signal.aborted) {
              retryAttempt = 0;
              setConnected(true);
            }
          },
          onEvent: (eventName, parsed) => {
            if (disposed || controller.signal.aborted) return;
            if (eventName === "connected") {
              retryAttempt = 0;
              setConnected(true);
              return;
            }
            if (!TRACKED_WORKSPACE_EVENTS.has(eventName)) return;
            const eventId = typeof parsed.event_id === "string" ? parsed.event_id : "";
            const resolvedName =
              typeof parsed.event_name === "string" ? parsed.event_name : eventName;
            if (eventId && resolvedName) {
              setLastClaimEvent({
                eventId,
                eventName: resolvedName,
                workspaceId:
                  typeof parsed.workspace_id === "string" ? parsed.workspace_id : trimmed,
                runId: typeof parsed.run_id === "string" ? parsed.run_id : "",
                stepExecutionId:
                  typeof parsed.step_execution_id === "string" ? parsed.step_execution_id : "",
                dispatchLatencyMs:
                  typeof parsed.dispatch_latency_ms === "number"
                    ? parsed.dispatch_latency_ms
                    : 0,
                payload:
                  parsed.payload && typeof parsed.payload === "object"
                    ? (parsed.payload as Record<string, unknown>)
                    : {},
              });
            }
          },
        });
        if (!disposed && !controller.signal.aborted) {
          setConnected(false);
          scheduleReconnect();
        }
      } catch (err: unknown) {
        if (disposed || controller.signal.aborted) return;
        setConnected(false);
        if (
          err instanceof OrciaProblemError &&
          (err.problem.status === 401 || err.problem.status === 403)
        ) {
          console.warn(
            "[useWorkspaceEventsSse] SSE connection stopped by auth/scope guard:",
            err.problem.status,
            err.problem.error_code,
          );
          return;
        }
        console.warn("[useWorkspaceEventsSse] Transient SSE error, scheduling reconnect:", err);
        scheduleReconnect();
      }
    };

    void connect();

    return () => {
      disposed = true;
      activeController?.abort();
      if (retryTimer !== null) {
        clearTimeout(retryTimer);
      }
      setConnected(false);
    };
  }, [workspaceId, isAuthenticated, options?.enabled]);

  return { connected, lastClaimEvent };
}
