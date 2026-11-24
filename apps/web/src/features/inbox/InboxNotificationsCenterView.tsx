import { createOrciaApiClient, type TaskNotificationItemResponse } from "@orcia/api-client";
import { PresenceClaimPill } from "@orcia/ui";
import React, { useCallback, useEffect, useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { resolveEffectiveWorkspaceId } from "../../components/shellScopeOptions";
import { useWorkspaceEventsSse } from "../../components/useWorkspaceEventsSse";
import { formatI18nTemplate, useI18n } from "../../i18n";
import type { FeatureInboxAssistantDictionary } from "../../i18n/locales/feature_inbox_assistant_labels";
import { useAuthSessionStore } from "../../stores/authSessionStore";

const DEFAULT_INBOX_WORKSPACE_ID = "0195f000-0000-7000-8000-000000000301";

function errorDetail(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

function formatNotificationTitle(
  rawTitle: string,
  notifCopy: FeatureInboxAssistantDictionary["notificationsCenter"],
): string {
  const prefix = "Prise en charge directe de l'étape '";
  if (rawTitle.startsWith(prefix) && rawTitle.endsWith("'")) {
    const slug = rawTitle.slice(prefix.length, -1);
    const known: Record<string, string> = {
      "inbox-review-step": notifCopy.inboxReviewStepLabel,
    };
    const clean =
      known[slug] ??
      slug.replace(/[-_]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    return formatI18nTemplate(notifCopy.directClaimPrefix, { label: clean });
  }
  return rawTitle;
}

export function InboxNotificationsCenterView(): React.JSX.Element {
  const { dictionary } = useI18n();
  const notifCopy = dictionary.featureInboxAssistant.notificationsCenter;
  const { workspaces } = usePlatformSetup();
  const { activeScopeId } = useShellNavigation();
  const { readOnlyObserver, email: authEmail } = useAuthSessionStore();

  const activeWorkspaceId =
    resolveEffectiveWorkspaceId(activeScopeId, workspaces, authEmail) ||
    DEFAULT_INBOX_WORKSPACE_ID;
  const [scopeFilter, setScopeFilter] = useState<"ALL" | "PERSONAL" | "TEAM">("ALL");
  const [items, setItems] = useState<readonly TaskNotificationItemResponse[]>([]);
  const [amberBadgeCount, setAmberBadgeCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [feedback, setFeedback] = useState<string | null>(null);

  const { connected, lastClaimEvent } = useWorkspaceEventsSse(activeWorkspaceId);

  const loadNotifications = useCallback(async () => {
    try {
      const client = createOrciaApiClient({ baseUrl: "" });
      const res = await client.listInboxNotifications({
        workspaceId: activeWorkspaceId,
        scopeFilter,
      });
      setItems(Array.isArray(res?.items) ? res.items : []);
      setAmberBadgeCount(typeof res?.amber_badge_count === "number" ? res.amber_badge_count : 0);
      setFeedback(null);
    } catch (err: unknown) {
      setFeedback(
        formatI18nTemplate(notifCopy.loadErrorTemplate, { detail: errorDetail(err) }),
      );
    } finally {
      setLoading(false);
    }
  }, [activeWorkspaceId, notifCopy.loadErrorTemplate, scopeFilter]);

  useEffect(() => {
    void loadNotifications();
  }, [loadNotifications, lastClaimEvent?.eventId]);

  const handleClaim = useCallback(
    async (taskId: string) => {
      try {
        const client = createOrciaApiClient({ baseUrl: "" });
        await client.claimTaskNotification(taskId, {
          workspace_id: activeWorkspaceId,
          ttl_seconds: 900,
          force: false,
        });
        await loadNotifications();
      } catch (err: unknown) {
        setFeedback(
          formatI18nTemplate(notifCopy.claimErrorTemplate, { detail: errorDetail(err) }),
        );
      }
    },
    [activeWorkspaceId, loadNotifications, notifCopy.claimErrorTemplate],
  );

  const handleRelease = useCallback(
    async (taskId: string, force: boolean) => {
      try {
        const client = createOrciaApiClient({ baseUrl: "" });
        await client.releaseTaskNotificationClaim(taskId, { force });
        await loadNotifications();
      } catch (err: unknown) {
        setFeedback(
          formatI18nTemplate(notifCopy.releaseErrorTemplate, { detail: errorDetail(err) }),
        );
      }
    },
    [loadNotifications, notifCopy.releaseErrorTemplate],
  );

  const scopeLabels: Record<"ALL" | "PERSONAL" | "TEAM", string> = {
    ALL: notifCopy.filterAll,
    PERSONAL: notifCopy.filterPersonal,
    TEAM: notifCopy.filterTeam,
  };

  return (
    <div className="space-y-4" data-testid="inbox-feature-panel">
      <section
        data-testid="inbox-notifications-center"
        className="orcia-bento-card space-y-3"
      >
        <header className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold">{notifCopy.title}</h2>
            <span
              data-testid="inbox-amber-badge-count"
              className="rounded-full px-2 py-0.5 text-xs font-semibold"
              style={{
                backgroundColor: "var(--color-arbitration-bg)",
                color: "var(--color-arbitration-amber)",
                border: "1px solid var(--color-arbitration-amber)",
              }}
            >
              {amberBadgeCount}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span
              data-testid="inbox-sse-status-badge"
              className="text-xs font-mono"
              style={{ color: "var(--color-text-secondary)" }}
            >
              {connected ? notifCopy.liveStreamBadge : notifCopy.restSyncBadge}
            </span>
            {(["ALL", "PERSONAL", "TEAM"] as const).map((scope) => (
              <button
                key={scope}
                type="button"
                data-testid={`inbox-scope-filter-${scope}`}
                onClick={() => setScopeFilter(scope)}
                className="rounded border px-2.5 py-1 text-xs font-semibold"
                style={{
                  borderColor: "var(--color-border-subtle)",
                  backgroundColor:
                    scopeFilter === scope
                      ? "var(--color-action-primary)"
                      : "var(--color-surface-card)",
                  color:
                    scopeFilter === scope
                      ? "var(--color-primary-foreground)"
                      : "var(--color-text-primary)",
                }}
              >
                {scopeLabels[scope]}
              </button>
            ))}
          </div>
        </header>

        {feedback ? (
          <div
            role="status"
            data-testid="inbox-notifications-feedback"
            className="rounded border px-3 py-2 text-xs font-medium"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-primary)",
            }}
          >
            {feedback}
          </div>
        ) : null}

        {loading ? (
          <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>
            {notifCopy.loadingText}
          </p>
        ) : items.length === 0 ? (
          <p
            data-testid="inbox-notifications-empty"
            className="text-xs"
            style={{ color: "var(--color-text-secondary)" }}
          >
            {notifCopy.emptyText}
          </p>
        ) : (
          <ul
            data-testid="inbox-notifications-list"
            className="space-y-2"
            style={{ listStyle: "none", margin: 0, padding: 0 }}
          >
            {items.map((item) => (
              <li
                key={item.id}
                data-testid={`inbox-notification-card-${item.id}`}
                className="rounded-lg border p-3 space-y-2"
                style={{
                  backgroundColor: "var(--color-surface-card)",
                  borderColor: "var(--color-border-subtle)",
                  opacity: item.presence_state === "CLAIMED_BY_PEER" ? 0.85 : 1,
                }}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <strong className="text-xs font-semibold">
                      {formatNotificationTitle(item.title, notifCopy)}
                    </strong>
                    <p className="text-xs mt-0.5" style={{ color: "var(--color-text-secondary)" }}>
                      {item.summary}
                    </p>
                  </div>
                  <PresenceClaimPill
                    taskId={item.id}
                    stepExecutionId={item.step_execution_id}
                    presenceState={item.presence_state}
                    claimedByDisplayName={item.claimed_by_display_name}
                    canForceUnclaim={item.can_force_unclaim}
                    readOnlyObserver={readOnlyObserver}
                    sseLatencyMs={lastClaimEvent?.dispatchLatencyMs}
                    labels={dictionary.inboxAndClaims.presencePill}
                    onClaim={(tid) => void handleClaim(tid)}
                    onRelease={(tid, force) => void handleRelease(tid, force)}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
