import { createOrciaApiClient, type PermissionBrokerTicketItem } from "@orcia/api-client";
import type { UiBrokerConnectorScheme, UiPermissionBrokerTicketView } from "@orcia/ui";
import { useCallback, useEffect, useState } from "react";

const ALLOWED_BROKER_SCHEMES: ReadonlySet<UiBrokerConnectorScheme> = new Set([
  "git",
  "jira",
  "confluence",
  "db",
  "nexus",
  "mcp",
]);

function normalizeBrokerScheme(raw: string): UiBrokerConnectorScheme {
  const lower = raw.toLowerCase() as UiBrokerConnectorScheme;
  return ALLOWED_BROKER_SCHEMES.has(lower) ? lower : "git";
}

function mapBrokerTicket(item: PermissionBrokerTicketItem): UiPermissionBrokerTicketView {
  const reqUrl = item.request_url || item.jira_request_url;
  return {
    id: item.id,
    ticketKey: item.ticket_key,
    stepKey: item.step_key,
    stepNumber: item.step_number,
    stepState: item.step_state,
    status: item.status,
    targetUri: item.target_uri,
    connectorScheme: normalizeBrokerScheme(item.connector_scheme),
    executionIdentity: item.execution_identity,
    upstreamHttpStatus: item.upstream_http_status,
    requiredRole: item.required_role,
    approverTeam: item.approver_team,
    slaHours: item.sla_hours,
    jiraRequestUrl: reqUrl,
    permissionBrokerHint: item.permission_broker_hint,
    procedureMarkdown: item.procedure_markdown,
  };
}

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export function usePermissionBrokerTickets(params: {
  readonly workspaceId: string;
  readonly isFr: boolean;
  readonly onFeedback: (message: string) => void;
}) {
  const { workspaceId, isFr, onFeedback } = params;
  const [tickets, setTickets] = useState<readonly UiPermissionBrokerTicketView[]>([]);
  const [interactedTicketId, setInteractedTicketId] = useState<string | null>(null);

  const refreshTickets = useCallback(async () => {
    try {
      const client = createOrciaApiClient({ baseUrl: "" });
      const res = await client.getPermissionBrokerState(
        undefined,
        workspaceId ? workspaceId : undefined,
      );
      const rawTickets = Array.isArray(res?.tickets) ? res.tickets : [];
      setTickets(rawTickets.map(mapBrokerTicket));
    } catch (err: unknown) {
      onFeedback(
        isFr
          ? `⚠️ Impossible de charger les demandes d'accès (${errorMessage(err)}).`
          : `⚠️ Failed to load access requests (${errorMessage(err)}).`,
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId, isFr]);

  useEffect(() => {
    void refreshTickets();
  }, [refreshTickets]);

  const handleAction = useCallback(
    async (ticketId: string, action: "PAUSE" | "REPLAY") => {
      try {
        const client = createOrciaApiClient({ baseUrl: "" });
        const res = await client.applyPermissionTicketAction(ticketId, {
          action,
          ...(workspaceId ? { workspace_id: workspaceId } : {}),
        });
        if (res?.ticket) {
          const updated = mapBrokerTicket(res.ticket);
          setInteractedTicketId(updated.id);
          setTickets((prev) =>
            prev.some((t) => t.id === updated.id)
              ? prev.map((t) => (t.id === updated.id ? updated : t))
              : [updated, ...prev],
          );
        }
      } catch (err: unknown) {
        onFeedback(
          isFr
            ? `⚠️ Échec de l'action Permission Broker (${errorMessage(err)}).`
            : `⚠️ Permission Broker action failed (${errorMessage(err)}).`,
        );
      }
    },
    [workspaceId, isFr, onFeedback],
  );

  const waitingTicket =
    tickets.find(
      (t) =>
        t.status === "WAITING_FOR_PERMISSION" ||
        t.stepState === "PERMISSION_DENIED_STEP",
    ) ?? null;

  const activeTicket =
    waitingTicket ??
    (interactedTicketId
      ? tickets.find((t) => t.id === interactedTicketId) ?? null
      : null);

  return {
    tickets,
    activeTicket,
    refreshTickets,
    pauseTicket: (ticketId: string) => void handleAction(ticketId, "PAUSE"),
    replayTicket: (ticketId: string) => void handleAction(ticketId, "REPLAY"),
  };
}
