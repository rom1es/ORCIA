import {
  createOrciaApiClient,
  type AutonomousRunSupervisionItemSchema,
  type TaskNotificationItemResponse,
} from "@orcia/api-client";
import { useEffect, useMemo, useState } from "react";
import { useWorkspaceEventsSse } from "./useWorkspaceEventsSse";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const SETUP_WS_RE = /^ws-\d+$/;

function isValidWorkspaceKey(id: string): boolean {
  return UUID_RE.test(id) || SETUP_WS_RE.test(id);
}

export function useShellAutonomousSupervision({
  isAuthenticated,
  selectedScope,
  workspaces,
}: {
  isAuthenticated: boolean;
  selectedScope: { id: string; level: string };
  workspaces: readonly { workspaceId: string }[];
}) {
  const { lastClaimEvent } = useWorkspaceEventsSse(workspaces[0]?.workspaceId);
  const [autonomousRuns, setAutonomousRuns] = useState<AutonomousRunSupervisionItemSchema[]>([]);
  const [inboxNotifications, setInboxNotifications] = useState<TaskNotificationItemResponse[]>([]);
  const shellApiClient = useMemo(() => createOrciaApiClient({ baseUrl: "" }), []);

  const activeWsUuid = useMemo(() => {
    const scopeWs = selectedScope.id.startsWith("scope-ws-")
      ? selectedScope.id.slice("scope-ws-".length)
      : selectedScope.id;
    if (selectedScope.level === "WORKSPACE" && isValidWorkspaceKey(scopeWs)) {
      return scopeWs;
    }
    return workspaces.find((w) => isValidWorkspaceKey(w.workspaceId))?.workspaceId ?? null;
  }, [selectedScope, workspaces]);

  useEffect(() => {
    if (!isAuthenticated || !activeWsUuid) {
      setAutonomousRuns([]);
      setInboxNotifications([]);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const [autoRes, inboxRes] = await Promise.all([
          shellApiClient.listWorkspaceAutonomousRuns(activeWsUuid),
          shellApiClient.listInboxNotifications({ workspaceId: activeWsUuid }),
        ]);
        if (!cancelled) {
          setAutonomousRuns(Array.isArray(autoRes?.runs) ? autoRes.runs : []);
          setInboxNotifications(Array.isArray(inboxRes?.items) ? inboxRes.items : []);
        }
      } catch {
        if (!cancelled) {
          setAutonomousRuns([]);
          setInboxNotifications([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeWsUuid, isAuthenticated, lastClaimEvent?.eventId, shellApiClient]);

  return { lastClaimEvent, autonomousRuns, inboxNotifications };
}
