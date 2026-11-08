import { useEffect, useState } from "react";

export interface WorkspaceSseClaimEvent {
  readonly eventId: string;
  readonly eventName: string;
  readonly workspaceId: string;
  readonly runId: string;
  readonly stepExecutionId: string;
  readonly dispatchLatencyMs: number;
  readonly payload: Record<string, unknown>;
}

/**
 * Consommateur SSE temps réel (`GET /api/v1/events/stream`, `AD-4`, `< 500 ms`).
 * Écoute les événements `task.claim.locked` et `task.claim.released` publiés sur le canal du workspace actif.
 */
export function useWorkspaceEventsSse(workspaceId: string | undefined): {
  readonly connected: boolean;
  readonly lastClaimEvent: WorkspaceSseClaimEvent | null;
} {
  const [connected, setConnected] = useState(false);
  const [lastClaimEvent, setLastClaimEvent] = useState<WorkspaceSseClaimEvent | null>(null);

  useEffect(() => {
    const trimmed = workspaceId?.trim() ?? "";
    if (!trimmed || typeof EventSource === "undefined") {
      setConnected(false);
      return;
    }

    const url = `/api/v1/events/stream?workspace_id=${encodeURIComponent(trimmed)}`;
    const source = new EventSource(url);

    const handleClaimFrame = (rawEvent: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(rawEvent.data) as {
          event_id?: string;
          event_name?: string;
          workspace_id?: string;
          run_id?: string;
          step_execution_id?: string;
          dispatch_latency_ms?: number;
          payload?: Record<string, unknown>;
        };
        if (parsed.event_id && parsed.event_name) {
          setLastClaimEvent({
            eventId: parsed.event_id,
            eventName: parsed.event_name,
            workspaceId: parsed.workspace_id ?? trimmed,
            runId: parsed.run_id ?? "",
            stepExecutionId: parsed.step_execution_id ?? "",
            dispatchLatencyMs: parsed.dispatch_latency_ms ?? 0,
            payload: parsed.payload ?? {},
          });
        }
      } catch {
        // Ignore malformed frame
      }
    };

    source.addEventListener("connected", () => setConnected(true));
    source.addEventListener("task.claim.locked", handleClaimFrame as EventListener);
    source.addEventListener("task.claim.released", handleClaimFrame as EventListener);
    source.onerror = () => setConnected(false);

    return () => {
      source.close();
      setConnected(false);
    };
  }, [workspaceId]);

  return { connected, lastClaimEvent };
}
