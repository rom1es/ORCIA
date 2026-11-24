import React, { useState } from "react";
import { OrciaIcon } from "../components/icons";
import type { FourZoneDirectionCShellLabels, UiNotificationCenterItem } from "./FourZoneDirectionCShell";

export interface FourZoneAutonomousNotificationsGroupProps {
  readonly items: readonly UiNotificationCenterItem[];
  readonly labels: FourZoneDirectionCShellLabels;
  readonly onSelectNotification?: (item: UiNotificationCenterItem) => void;
  readonly onCloseDrawer: () => void;
}

/**
 * Groups nominal autonomous runs by trigger in a collapsed-by-default accordion
 * inside `FourZoneNotificationsDrawer` (`Story 7.4`, Hick's Law).
 */
export function FourZoneAutonomousNotificationsGroup({
  items,
  labels,
  onSelectNotification,
  onCloseDrawer,
}: FourZoneAutonomousNotificationsGroupProps): React.ReactElement | null {
  const [expanded, setExpanded] = useState<boolean>(false);
  if (items.length === 0) {
    return null;
  }

  const groupedByTrigger = new Map<string, UiNotificationCenterItem[]>();
  for (const item of items) {
    const key = item.triggerLabel?.trim() || labels.autonomousDefaultTriggerLabel || item.id;
    const bucket = groupedByTrigger.get(key) ?? [];
    bucket.push(item);
    groupedByTrigger.set(key, bucket);
  }

  return (
    <div
      data-testid="notifications-autonomous-nominal-group"
      className="mt-3 rounded-lg border p-2.5 text-xs"
      style={{
        backgroundColor: "var(--color-autonomous-badge-bg)",
        borderColor: "var(--color-autonomous-badge-border)",
      }}
    >
      <button
        type="button"
        aria-expanded={expanded}
        data-testid="notifications-autonomous-nominal-toggle"
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center justify-between gap-2 text-left font-semibold"
        style={{ color: "var(--color-autonomous-badge-fg)" }}
      >
        <span className="inline-flex items-center gap-1.5">
          <OrciaIcon name="lightning" size={13} />
          <span>
            {labels.autonomousNominalGroupTitle ?? labels.notificationsDrawerTitle} ({items.length})
          </span>
        </span>
        <OrciaIcon name={expanded ? "caretDown" : "caretRight"} size={13} />
      </button>

      {expanded && (
        <div
          data-testid="notifications-autonomous-nominal-content"
          className="mt-2 flex flex-col gap-2"
        >
          {[...groupedByTrigger.entries()].map(([triggerName, bucket]) => (
            <div
              key={triggerName}
              data-testid={`notifications-autonomous-trigger-bucket-${triggerName}`}
              className="rounded border p-2"
              style={{
                backgroundColor: "var(--color-surface-card)",
                borderColor: "var(--color-autonomous-badge-border)",
              }}
            >
              <div className="flex items-center justify-between gap-2">
                <strong style={{ color: "var(--color-text-primary)" }}>{triggerName}</strong>
                <span
                  className="rounded px-1.5 py-0.5 text-[10px] font-semibold"
                  style={{
                    backgroundColor: "var(--color-autonomous-badge-bg)",
                    color: "var(--color-autonomous-badge-fg)",
                  }}
                >
                  {bucket.length}
                </span>
              </div>
              <ul className="mt-1.5 flex flex-col gap-1" style={{ listStyle: "none", margin: 0, padding: 0 }}>
                {bucket.map((item) => (
                  <li
                    key={item.id}
                    data-testid={`notification-center-item-${item.id}`}
                    className="flex items-center justify-between gap-2 text-[11px]"
                  >
                    <span style={{ color: "var(--color-text-secondary)" }}>{item.title}</span>
                    {item.targetRoute && item.ctaLabel && (
                      <button
                        type="button"
                        data-testid={`notification-center-cta-${item.id}`}
                        onClick={() => {
                          onSelectNotification?.(item);
                          onCloseDrawer();
                        }}
                        className="rounded px-1.5 py-0.5 font-semibold"
                        style={{
                          color: "var(--color-autonomous-badge-fg)",
                        }}
                      >
                        {item.ctaLabel}
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
