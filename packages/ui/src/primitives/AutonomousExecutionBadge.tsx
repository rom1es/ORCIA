import React from "react";
import { ContextualInfoTriggerButton } from "../components/ContextualInfoTriggerButton";
import { OrciaIcon } from "../components/icons";

export interface AutonomousExecutionBadgeLabels {
  readonly badgeLabel: string;
  readonly triggerPrefix: string;
  readonly contractPrefix?: string;
  readonly emergencyStopButton: string;
  readonly invalidateAndRestoreButton: string;
  readonly helpButtonLabel?: string;
  readonly statusLabels?: Readonly<Record<string, string>>;
}

export interface AutonomousExecutionBadgeProps {
  readonly runId?: string | null;
  readonly triggerLabel?: string | null;
  readonly contractLabel?: string | null;
  readonly runStatus?: string | null;
  readonly canEmergencyStop?: boolean;
  readonly canInvalidateAndRestore?: boolean;
  readonly busy?: boolean;
  readonly compact?: boolean;
  readonly testId?: string;
  readonly labels: AutonomousExecutionBadgeLabels;
  readonly onEmergencyStop?: (runId: string) => void;
  readonly onInvalidateAndRestore?: (runId: string) => void;
  readonly onOpenHelpSection?: (sectionId: string) => void;
}

/**
 * UX-DR17 — Autonomous Execution Badge & Escape Hatch Bar.
 * Uses Cyan/Cobalt semantic tokens (`--color-autonomous-badge-*`), never human-led violet.
 */
export function AutonomousExecutionBadge({
  runId,
  triggerLabel,
  contractLabel,
  runStatus,
  canEmergencyStop = true,
  canInvalidateAndRestore = true,
  busy = false,
  compact = false,
  testId = "autonomous-execution-badge",
  labels,
  onEmergencyStop,
  onInvalidateAndRestore,
  onOpenHelpSection,
}: AutonomousExecutionBadgeProps): React.ReactElement {
  const statusDisplay =
    runStatus && labels.statusLabels?.[runStatus] ? labels.statusLabels[runStatus] : null;
  const isAlreadyStopped = runStatus === "KILL_SWITCH_STOPPED" || runStatus === "ROLLED_BACK";

  return (
    <div
      data-testid={testId}
      className="rounded-lg border px-2.5 py-2 text-xs"
      style={{
        backgroundColor: "var(--color-autonomous-badge-bg)",
        borderColor: "var(--color-autonomous-badge-border)",
        color: "var(--color-text-primary)",
        display: "flex",
        flexDirection: "column",
        gap: compact ? "6px" : "8px",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "6px",
        }}
      >
        <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
          <span
            data-testid={`${testId}-pill`}
            className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-bold"
            style={{
              backgroundColor: "var(--color-surface-card)",
              color: "var(--color-autonomous-badge-fg)",
              border: "1px solid var(--color-autonomous-badge-border)",
            }}
          >
            <OrciaIcon name="lightning" size={12} />
            <span>{labels.badgeLabel}</span>
          </span>

          {triggerLabel && (
            <span
              data-testid={`${testId}-trigger`}
              className="text-[11px] font-medium"
              style={{ color: "var(--color-text-secondary)" }}
            >
              {labels.triggerPrefix} {triggerLabel}
            </span>
          )}

          {contractLabel && (
            <span
              className="text-[11px]"
              style={{ color: "var(--color-text-muted)" }}
            >
              {labels.contractPrefix ? `${labels.contractPrefix} ${contractLabel}` : contractLabel}
            </span>
          )}

          {statusDisplay && (
            <span
              data-testid={`${testId}-status`}
              className="rounded px-1.5 py-0.5 text-[10px] font-semibold"
              style={{
                backgroundColor: isAlreadyStopped
                  ? "var(--color-stale-bg)"
                  : "var(--color-surface-card)",
                color: isAlreadyStopped
                  ? "var(--color-stale-crimson)"
                  : "var(--color-autonomous-badge-fg)",
              }}
            >
              {statusDisplay}
            </span>
          )}
        </div>

        {onOpenHelpSection && (
          <ContextualInfoTriggerButton
            sectionId="autonomous-supervision"
            label={labels.helpButtonLabel ?? labels.badgeLabel}
            onOpenHelpSection={onOpenHelpSection}
          />
        )}
      </div>

      {runId && (canEmergencyStop || canInvalidateAndRestore) && (onEmergencyStop || onInvalidateAndRestore) && (
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          {canEmergencyStop && onEmergencyStop && runStatus !== "KILL_SWITCH_STOPPED" && runStatus !== "ROLLED_BACK" && (
            <button
              type="button"
              disabled={busy}
              data-testid={`${testId}-emergency-stop-btn`}
              onClick={() => onEmergencyStop(runId)}
              className="orcia-ds-btn orcia-ds-btn-danger inline-flex items-center gap-1 rounded px-2.5 py-1 text-[11px] font-semibold"
              style={{
                backgroundColor: "var(--color-stale-bg)",
                color: "var(--color-stale-crimson)",
                border: "1px solid var(--color-stale-crimson)",
              }}
            >
              <OrciaIcon name="stopButton" size={12} />
              <span>{labels.emergencyStopButton}</span>
            </button>
          )}

          {canInvalidateAndRestore && onInvalidateAndRestore && runStatus !== "ROLLED_BACK" && (
            <button
              type="button"
              disabled={busy}
              data-testid={`${testId}-restore-btn`}
              onClick={() => onInvalidateAndRestore(runId)}
              className="orcia-ds-btn orcia-ds-btn-secondary inline-flex items-center gap-1 rounded px-2.5 py-1 text-[11px] font-semibold"
              style={{
                backgroundColor: "var(--color-surface-card)",
                color: "var(--color-autonomous-badge-fg)",
                border: "1px solid var(--color-autonomous-badge-border)",
              }}
            >
              <OrciaIcon name="rollback" size={12} />
              <span>{labels.invalidateAndRestoreButton}</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
