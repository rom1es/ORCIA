import React from "react";

export type UiClaimPresenceState = "UNCLAIMED" | "CLAIMED_BY_ME" | "CLAIMED_BY_PEER";

export interface PresenceClaimPillLabels {
  claimActionLabel: string;
  claimedByMeBadge: string;
  claimedByPeerPrefix: string;
  releaseActionLabel: string;
  forceUnclaimActionLabel: string;
  readOnlyObserverNotice: string;
  sseLatencyPrefix: string;
}

export interface PresenceClaimPillProps {
  taskId: string;
  stepExecutionId: string;
  presenceState: UiClaimPresenceState;
  claimedByDisplayName?: string | null;
  canForceUnclaim?: boolean;
  readOnlyObserver?: boolean;
  sseLatencyMs?: number;
  labels: PresenceClaimPillLabels;
  onClaim?: (taskId: string) => void;
  onRelease?: (taskId: string, force: boolean) => void;
}

export function PresenceClaimPill({
  taskId,
  stepExecutionId,
  presenceState,
  claimedByDisplayName,
  canForceUnclaim = false,
  readOnlyObserver = false,
  sseLatencyMs,
  labels,
  onClaim,
  onRelease,
}: PresenceClaimPillProps) {
  const isPeerLocked = presenceState === "CLAIMED_BY_PEER";

  return (
    <div
      data-testid={`presence-claim-pill-${taskId}`}
      data-presence-state={presenceState}
      data-step-execution-id={stepExecutionId}
      style={{
        display: "inline-flex",
        alignItems: "center",
        flexWrap: "wrap",
        gap: "8px",
        opacity: isPeerLocked ? 0.85 : 1,
      }}
    >
      {presenceState === "UNCLAIMED" ? (
        <button
          type="button"
          data-testid={`claim-task-btn-${taskId}`}
          disabled={readOnlyObserver}
          onClick={() => onClaim?.(taskId)}
          style={{
            padding: "5px 12px",
            borderRadius: "var(--radius-full)",
            border: "1px solid var(--color-primary-cobalt)",
            backgroundColor: readOnlyObserver
              ? "var(--color-surface-hover)"
              : "var(--color-primary-cobalt)",
            color: readOnlyObserver
              ? "var(--color-muted-foreground)"
              : "var(--color-primary-foreground)",
            fontFamily: "var(--font-sans)",
            fontSize: "var(--font-size-mono)",
            fontWeight: 600,
            cursor: readOnlyObserver ? "not-allowed" : "pointer",
          }}
        >
          {labels.claimActionLabel}
        </button>
      ) : null}

      {presenceState === "CLAIMED_BY_ME" ? (
        <>
          <span
            data-testid={`claimed-by-me-badge-${taskId}`}
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "4px 10px",
              borderRadius: "var(--radius-full)",
              backgroundColor: "var(--color-gate-emerald-bg)",
              color: "var(--color-gate-emerald)",
              border: "1px solid var(--color-gate-emerald)",
              fontFamily: "var(--font-sans)",
              fontSize: "var(--font-size-mono)",
              fontWeight: 600,
            }}
          >
            {labels.claimedByMeBadge}
          </span>
          <button
            type="button"
            data-testid={`release-claim-btn-${taskId}`}
            disabled={readOnlyObserver}
            onClick={() => onRelease?.(taskId, false)}
            style={{
              padding: "4px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-surface-card)",
              color: "var(--color-foreground)",
              fontFamily: "var(--font-sans)",
              fontSize: "var(--font-size-mono)",
              cursor: readOnlyObserver ? "not-allowed" : "pointer",
            }}
          >
            {labels.releaseActionLabel}
          </button>
        </>
      ) : null}

      {presenceState === "CLAIMED_BY_PEER" ? (
        <>
          <span
            data-testid={`claimed-by-peer-badge-${taskId}`}
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "4px 10px",
              borderRadius: "var(--radius-full)",
              backgroundColor: "var(--color-gate-emerald-bg)",
              color: "var(--color-gate-emerald)",
              border: "1px solid var(--color-gate-emerald)",
              fontFamily: "var(--font-sans)",
              fontSize: "var(--font-size-mono)",
              fontWeight: 600,
            }}
          >
            {`${labels.claimedByPeerPrefix} ${claimedByDisplayName ?? "Pair"}`}
          </span>
          {canForceUnclaim && !readOnlyObserver ? (
            <button
              type="button"
              data-testid={`force-unclaim-btn-${taskId}`}
              onClick={() => onRelease?.(taskId, true)}
              style={{
                padding: "4px 10px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-arbitration-amber)",
                backgroundColor: "var(--color-arbitration-bg)",
                color: "var(--color-arbitration-amber)",
                fontFamily: "var(--font-sans)",
                fontSize: "var(--font-size-mono)",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {labels.forceUnclaimActionLabel}
            </button>
          ) : null}
        </>
      ) : null}

      {typeof sseLatencyMs === "number" ? (
        <span
          data-testid={`sse-latency-badge-${taskId}`}
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--font-size-mono)",
            color: "var(--color-muted-foreground)",
          }}
        >
          {`${labels.sseLatencyPrefix} ${sseLatencyMs.toFixed(1)} ms`}
        </span>
      ) : null}
    </div>
  );
}
