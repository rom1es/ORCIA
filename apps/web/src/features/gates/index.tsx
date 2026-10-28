import React from "react";
import { usePersonaContext } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";

export function GatesFeaturePanel() {
  const { dictionary } = useI18n();
  const {
    brokerActionBanner,
    triggerPermissionDeniedStep,
    triggerConfusedDeputyCheck,
  } = usePersonaContext();

  return (
    <section
      data-testid="permission-broker-simulator-panel"
      className="orcia-bento-card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "12px",
      }}
    >
      <div>
        <strong style={{ fontSize: "15px" }}>
          {dictionary.permissionBroker.simulatorTitle}
        </strong>
        <p
          style={{
            margin: "4px 0 0 0",
            color: "var(--color-muted-foreground)",
            fontSize: "var(--font-size-body)",
          }}
        >
          {dictionary.permissionBroker.simulatorSubtitle}
        </p>
      </div>

      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
        <button
          type="button"
          data-testid="simulate-permission-denied-git-btn"
          onClick={() => triggerPermissionDeniedStep("git")}
          style={{
            backgroundColor: "var(--color-arbitration-amber)",
            color: "var(--color-primary-foreground)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            padding: "7px 12px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {dictionary.permissionBroker.simulateGitDenialLabel}
        </button>

        <button
          type="button"
          data-testid="simulate-permission-denied-confluence-btn"
          onClick={() => triggerPermissionDeniedStep("confluence")}
          style={{
            backgroundColor: "var(--color-surface-hover)",
            color: "var(--color-foreground)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            padding: "7px 12px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {dictionary.permissionBroker.simulateConfluenceDenialLabel}
        </button>

        <button
          type="button"
          data-testid="simulate-permission-denied-jira-btn"
          onClick={() => triggerPermissionDeniedStep("jira")}
          style={{
            backgroundColor: "var(--color-surface-hover)",
            color: "var(--color-foreground)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            padding: "7px 12px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {dictionary.permissionBroker.simulateJiraDenialLabel}
        </button>

        <button
          type="button"
          data-testid="simulate-confused-deputy-btn"
          onClick={triggerConfusedDeputyCheck}
          style={{
            backgroundColor: "var(--color-stale-bg)",
            color: "var(--color-stale-crimson)",
            border: "1px solid var(--color-stale-crimson)",
            borderRadius: "var(--radius-sm)",
            padding: "7px 12px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {dictionary.permissionBroker.simulateConfusedDeputyLabel}
        </button>
      </div>

      {brokerActionBanner && (
        <div
          data-testid="permission-broker-action-banner"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--font-size-mono)",
            padding: "8px 10px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-arbitration-bg)",
            border: "1px solid var(--color-arbitration-amber)",
            wordBreak: "break-all",
          }}
        >
          {brokerActionBanner}
        </div>
      )}
    </section>
  );
}
