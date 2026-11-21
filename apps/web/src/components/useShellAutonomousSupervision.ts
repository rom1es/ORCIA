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
  currentUserEmail,
}: {
  isAuthenticated: boolean;
  selectedScope: { id: string; level: string };
  workspaces: readonly { workspaceId: string; ownerUserId?: string }[];
  currentUserEmail?: string | null;
}) {
  const activeWsUuid = useMemo(() => {
    const callerEmail = currentUserEmail?.trim().toLowerCase() ?? "";
    const eligibleWorkspaces = workspaces.filter(
      (w) =>
        isValidWorkspaceKey(w.workspaceId) &&
        (!w.ownerUserId || !callerEmail || w.ownerUserId.toLowerCase() === callerEmail),
    );
    const scopeWs = selectedScope.id.startsWith("scope-ws-")
      ? selectedScope.id.slice("scope-ws-".length)
      : selectedScope.id;
    const effectiveWsId = eligibleWorkspaces.find((w) => w.workspaceId === scopeWs)?.workspaceId;
    if (effectiveWsId) return effectiveWsId;
    return eligibleWorkspaces[0]?.workspaceId ?? null;
  }, [selectedScope, workspaces, currentUserEmail]);

  const { lastClaimEvent } = useWorkspaceEventsSse(
    isAuthenticated ? (activeWsUuid ?? undefined) : undefined,
  );
  const [autonomousRuns, setAutonomousRuns] = useState<AutonomousRunSupervisionItemSchema[]>([]);
  const [inboxNotifications, setInboxNotifications] = useState<TaskNotificationItemResponse[]>([]);
  const shellApiClient = useMemo(() => createOrciaApiClient({ baseUrl: "" }), []);

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
      } catch (err: unknown) {
        console.warn(
          "[orcia:shell.autonomousSupervision]",
          err instanceof Error ? err.message : String(err),
        );
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
