import * as DialogPrimitive from "@radix-ui/react-dialog";
import React from "react";
import { OrciaIcon } from "../components/icons";
import { FourZoneAutonomousNotificationsGroup } from "./FourZoneAutonomousNotificationsGroup";
import type {
  EightFixedMenuKey,
  FourZoneDirectionCShellLabels,
  UiNotificationCenterItem,
} from "./FourZoneDirectionCShell";

export interface FourZoneNotificationsDrawerProps {
  readonly notifications: readonly UiNotificationCenterItem[];
  readonly labels: FourZoneDirectionCShellLabels;
  readonly onClose: () => void;
  readonly onSelectNotification?: (item: UiNotificationCenterItem) => void;
  readonly onSelectActivityMenu?: (route: string) => void;
  readonly onSelectMenu: (key: EightFixedMenuKey, route: string) => void;
}

export function FourZoneNotificationsDrawer({
  notifications,
  labels,
  onClose,
  onSelectNotification,
  onSelectActivityMenu,
  onSelectMenu,
}: FourZoneNotificationsDrawerProps): React.ReactElement {
  const nominalAutonomousItems = notifications.filter((n) => Boolean(n.isAutonomousNominal));
  const standardAndPriorityItems = notifications
    .filter((n) => !n.isAutonomousNominal)
    .sort((a, b) => Number(Boolean(b.isAutonomousPriority)) - Number(Boolean(a.isAutonomousPriority)));

  return (
    <DialogPrimitive.Root
      open={true}
      modal={false}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) onClose();
      }}
    >
      <DialogPrimitive.Portal>
        <DialogPrimitive.Content asChild aria-describedby={undefined}>
          <aside
            data-testid="topbar-notifications-drawer"
            aria-label={labels.notificationsDrawerTitle}
            className="fixed right-0 top-[52px] border-b border-l p-4 shadow-md"
            style={{
              zIndex: "var(--z-dialog)",
              width: "min(420px, 100vw)",
              maxHeight: "calc(100vh - 52px)",
              overflowY: "auto",
              backgroundColor: "var(--color-bg-surface)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <DialogPrimitive.Title className="sr-only">
              {labels.notificationsDrawerTitle}
            </DialogPrimitive.Title>
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold">{labels.notificationsDrawerTitle}</h2>
        <button
          type="button"
          data-testid="topbar-notifications-close"
          onClick={onClose}
          className="text-xs"
        >
          <OrciaIcon name="close" />
        </button>
      </div>

      {standardAndPriorityItems.length === 0 && nominalAutonomousItems.length === 0 ? (
        <p
          data-testid="topbar-notifications-empty-text"
          className="mt-2 text-xs"
          style={{ color: "var(--color-text-secondary)" }}
        >
          {labels.notificationsEmptyText}
        </p>
      ) : (
        <>
          {standardAndPriorityItems.length > 0 && (
            <ul
              data-testid="topbar-notifications-list"
              className="mt-3 flex flex-col gap-2"
              style={{ listStyle: "none", margin: 0, padding: 0 }}
            >
              {standardAndPriorityItems.map((item) => {
                const isAlert =
                  item.kind === "SETUP_PREREQUISITE" || item.kind === "ACTION_REQUIRED";
                const isAutonomousPriority = Boolean(item.isAutonomousPriority);
                return (
                  <li
                    key={item.id}
                    data-testid={`notification-center-item-${item.id}`}
                    className="rounded-lg border p-2.5 text-xs"
                    style={{
                      backgroundColor: isAlert
                        ? "var(--color-stale-bg)"
                        : isAutonomousPriority
                          ? "var(--color-autonomous-badge-bg)"
                          : "var(--color-bg-elevated)",
                      borderColor: isAlert
                        ? "var(--color-status-error)"
                        : isAutonomousPriority
                          ? "var(--color-autonomous-badge-border)"
                          : "var(--color-border-subtle)",
                    }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className="rounded px-1.5 py-0.5 text-[10px] font-bold"
                        style={{
                          backgroundColor: isAlert
                            ? "var(--color-status-error)"
                            : isAutonomousPriority
                              ? "var(--color-surface-card)"
                              : "var(--color-action-primary-subtle)",
                          color: isAlert
                            ? "var(--color-surface-card)"
                            : isAutonomousPriority
                              ? "var(--color-autonomous-badge-fg)"
                              : "var(--color-action-primary)",
                        }}
                      >
                        {item.badgeLabel}
                      </span>
                      {item.targetRoute && item.ctaLabel && (
                        <button
                          type="button"
                          data-testid={`notification-center-cta-${item.id}`}
                          onClick={() => {
                            onSelectNotification?.(item);
                            onClose();
                          }}
                          className="rounded px-2 py-0.5 text-[11px] font-semibold"
                          style={{
                            backgroundColor: "var(--color-action-primary)",
                            color: "var(--color-primary-foreground)",
                            border: "none",
                            cursor: "pointer",
                          }}
                        >
                          {item.ctaLabel}
                        </button>
                      )}
                    </div>
                    <strong
                      className="mt-1.5 block font-semibold"
                      style={{ color: "var(--color-text-primary)" }}
                    >
                      {item.title}
                    </strong>
                    <p
                      className="mt-0.5 text-[11px]"
                      style={{ color: "var(--color-text-secondary)", margin: 0 }}
                    >
                      {item.description}
                    </p>
                  </li>
                );
              })}
            </ul>
          )}

          <FourZoneAutonomousNotificationsGroup
            items={nominalAutonomousItems}
            labels={labels}
            onSelectNotification={onSelectNotification}
            onCloseDrawer={onClose}
          />
        </>
      )}

      <div
        data-testid="notifications-vs-activity-log-box"
        className="mt-3 rounded border p-2.5 text-[11px]"
        style={{
          backgroundColor: "var(--color-bg-elevated)",
          borderColor: "var(--color-border-subtle)",
          color: "var(--color-text-secondary)",
        }}
      >
        <p style={{ margin: 0 }}>
          {labels.notificationsVsActivityHint ?? ""}
        </p>
        <button
          type="button"
          data-testid="notifications-open-activity-log-btn"
          onClick={() => {
            onClose();
            if (onSelectActivityMenu) {
              onSelectActivityMenu("/activity");
            } else {
              onSelectMenu("finops", "/activity");
            }
          }}
          className="mt-1.5 inline-flex items-center gap-1.5 rounded border px-2 py-1 text-[11px] font-semibold"
          style={{
            backgroundColor: "var(--color-bg-surface)",
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-action-primary)",
            cursor: "pointer",
          }}
        >
          <OrciaIcon name="activity" size={14} />
          <span>{labels.notificationsOpenActivityCta ?? labels.activityMenuLabel ?? ""}</span>
        </button>
      </div>
          </aside>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
