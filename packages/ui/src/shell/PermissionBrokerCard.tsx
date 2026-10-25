import React from "react";
import { StatusBadge } from "../primitives/StatusBadge";
import type {
  UiPermissionBrokerLabels,
  UiPermissionBrokerTicketView,
} from "./types";

export interface PermissionBrokerCardProps {
  ticket: UiPermissionBrokerTicketView;
  labels: UiPermissionBrokerLabels;
  onPauseStep?: (ticketId: string) => void;
  onReplayStep?: (ticketId: string) => void;
}

export function PermissionBrokerCard({
  ticket,
  labels,
  onPauseStep,
  onReplayStep,
}: PermissionBrokerCardProps) {
  const isReplayed = ticket.status === "REPLAYED" || ticket.status === "GRANTED";
  const isPaused = ticket.status === "PAUSED";
  const identityBadgeLabel =
    ticket.executionIdentity === "passthrough"
      ? labels.passthroughBadgeLabel
      : labels.servicePrincipalBadgeLabel;

  return (
    <section
      data-testid="permission-broker-card"
      data-ticket-id={ticket.id}
      data-step-state={ticket.stepState}
      data-ticket-status={ticket.status}
      data-execution-identity={ticket.executionIdentity}
      aria-label={labels.cardBadgeTitle}
      style={{
        backgroundColor: "var(--color-arbitration-bg)",
        border: "2px solid var(--color-arbitration-amber)",
        borderRadius: "var(--radius-md)",
        padding: "12px",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "6px",
          flexWrap: "wrap",
        }}
      >
        <StatusBadge
          testId="permission-broker-card-badge"
          label={`${labels.cardBadgeTitle} • HTTP ${ticket.upstreamHttpStatus}`}
          tone={isReplayed ? "emerald" : "amber"}
        />
        <StatusBadge
          testId="permission-broker-identity-badge"
          label={identityBadgeLabel}
          tone="cobalt"
          monospace
        />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <span
          style={{
            fontSize: "var(--font-size-mono)",
            color: "var(--color-muted-foreground)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {labels.targetUriLabel} (Step {ticket.stepNumber} • {ticket.stepKey})
        </span>
        <code
          data-testid="permission-broker-target-uri"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--font-size-mono)",
            backgroundColor: "var(--color-surface-card)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            padding: "4px 6px",
            wordBreak: "break-all",
          }}
        >
          {ticket.targetUri}
        </code>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr",
          gap: "6px",
          backgroundColor: "var(--color-surface-card)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-sm)",
          padding: "8px",
        }}
      >
        <div>
          <span
            style={{
              display: "block",
              fontSize: "var(--font-size-mono)",
              color: "var(--color-muted-foreground)",
            }}
          >
            {labels.requiredRoleLabel}
          </span>
          <strong
            data-testid="permission-broker-required-role"
            style={{ fontFamily: "var(--font-mono)", fontSize: "var(--font-size-mono)" }}
          >
            {ticket.requiredRole}
          </strong>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", flexWrap: "wrap" }}>
          <div>
            <span
              style={{
                display: "block",
                fontSize: "var(--font-size-mono)",
                color: "var(--color-muted-foreground)",
              }}
            >
              {labels.approverTeamLabel}
            </span>
            <span data-testid="permission-broker-approver-team" style={{ fontWeight: 600 }}>
              {ticket.approverTeam}
            </span>
          </div>

          <StatusBadge
            testId="permission-broker-sla"
            label={`${labels.slaHoursPrefix}: ${ticket.slaHours}h`}
            tone="amber"
            monospace
          />
        </div>

        <div>
          <span
            style={{
              display: "block",
              fontSize: "var(--font-size-mono)",
              color: "var(--color-muted-foreground)",
            }}
          >
            {labels.rfcHintLabel}
          </span>
          <code
            data-testid="permission-broker-hint"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "var(--font-size-mono)",
              wordBreak: "break-all",
            }}
          >
            {ticket.permissionBrokerHint}
          </code>
        </div>

        {ticket.procedureMarkdown && (
          <div
            data-testid="permission-broker-card-procedure"
            style={{
              fontSize: "var(--font-size-mono)",
              color: "var(--color-muted-foreground)",
              borderTop: "1px dashed var(--color-border)",
              paddingTop: "6px",
              whiteSpace: "pre-wrap",
            }}
          >
            {ticket.procedureMarkdown}
          </div>
        )}
      </div>

      <a
        data-testid="permission-broker-jira-link"
        href={ticket.jiraRequestUrl}
        target="_blank"
        rel="noopener noreferrer"
        style={{
          display: "inline-block",
          textAlign: "center",
          textDecoration: "none",
          backgroundColor: "var(--color-arbitration-amber)",
          color: "var(--color-primary-foreground)",
          borderRadius: "var(--radius-sm)",
          padding: "8px 10px",
          fontWeight: 700,
          fontSize: "var(--font-size-body)",
        }}
      >
        {labels.jiraRequestButtonLabel}
      </a>

      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
        <button
          type="button"
          data-testid="permission-broker-pause-btn"
          onClick={() => onPauseStep?.(ticket.id)}
          style={{
            flex: "1 1 120px",
            backgroundColor: "var(--color-surface-card)",
            color: "var(--color-foreground)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            padding: "6px 8px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {labels.pauseStepButtonLabel}
        </button>
        <button
          type="button"
          data-testid="permission-broker-replay-btn"
          onClick={() => onReplayStep?.(ticket.id)}
          style={{
            flex: "1 1 140px",
            backgroundColor: "var(--color-gate-emerald)",
            color: "var(--color-primary-foreground)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            padding: "6px 8px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {labels.replayStepButtonLabel} (Step {ticket.stepNumber})
        </button>
      </div>

      {(isPaused || isReplayed) && (
        <div
          data-testid="permission-broker-card-state-banner"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--font-size-mono)",
            padding: "6px 8px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: isReplayed
              ? "var(--color-gate-emerald-bg)"
              : "var(--color-surface-card)",
            color: isReplayed
              ? "var(--color-gate-emerald)"
              : "var(--color-arbitration-amber)",
            border: "1px solid var(--color-border)",
          }}
        >
          {isReplayed ? labels.replayedStateBanner : labels.pausedStateBanner}
        </div>
      )}
    </section>
  );
}
