import React, { useState } from "react";
import { OrciaIcon } from "../components/icons";
import { StatusBadge } from "../primitives/StatusBadge";
import type {
  UiOntologyExplorerLabels,
  UiStaleAlertView,
  UiTripartiteEdgeView,
} from "./types";

export interface TripartiteAuditDraft {
  readonly confluenceUri: string;
  readonly gitRepoUri: string;
  readonly gitSymbol: string;
  readonly jiraKey: string;
}

export interface OntologyTripartiteAndStaleSectionProps {
  readonly ragQuery: string;
  readonly onRagQueryChange: (val: string) => void;
  readonly filteredEdges: readonly UiTripartiteEdgeView[];
  readonly staleAlerts: readonly UiStaleAlertView[];
  readonly labels: UiOntologyExplorerLabels;
  readonly auditing?: boolean;
  readonly onAuditDocVsCode?: (draft: TripartiteAuditDraft) => Promise<void> | void;
  readonly onReplayAlert: (alert: UiStaleAlertView) => void;
}

export function OntologyTripartiteAndStaleSection({
  ragQuery,
  onRagQueryChange,
  filteredEdges,
  staleAlerts,
  labels,
  auditing = false,
  onAuditDocVsCode,
  onReplayAlert,
}: OntologyTripartiteAndStaleSectionProps): React.ReactElement {
  const [confluenceUri, setConfluenceUri] = useState("");
  const [gitRepoUri, setGitRepoUri] = useState("");
  const [jiraKey, setJiraKey] = useState("");

  const handleAuditSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!onAuditDocVsCode || auditing) return;
    const cleanConf = confluenceUri.trim();
    const cleanGit = gitRepoUri.trim();
    if (!cleanConf || !cleanGit) return;
    void Promise.resolve(
      onAuditDocVsCode({
        confluenceUri: cleanConf,
        gitRepoUri: cleanGit,
        gitSymbol: "main",
        jiraKey: jiraKey.trim(),
      }),
    ).then(() => {
      setConfluenceUri("");
      setGitRepoUri("");
      setJiraKey("");
    });
  };
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
        gap: "12px",
      }}
    >
      <div
        data-testid="tripartite-graph-section"
        style={{
          padding: "10px",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--color-border)",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        <strong>
          {labels.tripartiteTitle} · {labels.hybridRagTitle}
        </strong>
        <input
          type="search"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="hybrid-rag-search-input"
          value={ragQuery}
          onChange={(e) => onRagQueryChange(e.target.value)}
          placeholder={labels.hybridRagSearchPlaceholder}
          style={{
            padding: "6px 8px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-card)",
            color: "var(--color-foreground)",
          }}
        />
        {filteredEdges.map((edge) => (
          <div
            key={edge.edgeKey}
            data-testid={`tripartite-edge-${edge.edgeKey}`}
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "var(--font-size-mono)",
              color: "var(--color-muted-foreground)",
            }}
          >
            {edge.sourceUri} —[{edge.relationType}]→ {edge.targetUri}
          </div>
        ))}
        {onAuditDocVsCode ? (
          <form
            data-testid="tripartite-audit-form"
            autoComplete="off"
            data-lpignore="true"
            data-form-type="other"
            onSubmit={handleAuditSubmit}
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "6px",
              paddingTop: "6px",
              borderTop: "1px solid var(--color-border-subtle)",
            }}
          >
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="tripartite-confluence-uri-input"
              value={confluenceUri}
              onChange={(e) => setConfluenceUri(e.target.value)}
              placeholder={labels.auditConfluencePlaceholder ?? ""}
              style={{
                flex: "1 1 160px",
                padding: "5px 8px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                backgroundColor: "var(--color-surface-card)",
                color: "var(--color-foreground)",
                fontSize: "12px",
              }}
            />
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="tripartite-git-uri-input"
              value={gitRepoUri}
              onChange={(e) => setGitRepoUri(e.target.value)}
              placeholder={labels.auditGitPlaceholder ?? ""}
              style={{
                flex: "1 1 160px",
                padding: "5px 8px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                backgroundColor: "var(--color-surface-card)",
                color: "var(--color-foreground)",
                fontSize: "12px",
              }}
            />
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="tripartite-jira-key-input"
              value={jiraKey}
              onChange={(e) => setJiraKey(e.target.value)}
              placeholder={labels.auditJiraPlaceholder ?? ""}
              style={{
                flex: "0 1 110px",
                padding: "5px 8px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                backgroundColor: "var(--color-surface-card)",
                color: "var(--color-foreground)",
                fontSize: "12px",
              }}
            />
            <button
              type="submit"
              data-testid="tripartite-audit-submit-btn"
              disabled={auditing || !confluenceUri.trim() || !gitRepoUri.trim()}
              className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
            >
              {labels.auditSubmitLabel ?? labels.tripartiteTitle}
            </button>
          </form>
        ) : null}
      </div>

      <div
        data-testid="stale-alerts-section"
        style={{
          padding: "10px",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--color-stale-crimson)",
          backgroundColor: "var(--color-stale-bg)",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: "8px" }}>
          <strong>{labels.staleAlertsTitle}</strong>
          <StatusBadge label={labels.docObsoleteBadgeLabel} tone="crimson" monospace />
        </div>
        {staleAlerts.map((alert) => (
          <div
            key={alert.alertKey}
            data-testid={`stale-alert-${alert.alertKey}`}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "8px",
              fontFamily: "var(--font-mono)",
              fontSize: "var(--font-size-mono)",
              color: "var(--color-stale-crimson)",
            }}
          >
            <span>
              {`${alert.diagnosticMarker} ${alert.sourceUri} (${labels.staleJiraPrefix ?? "JIRA"}: ${alert.justifyingJiraKey ?? "TTL"}, ${labels.staleRunsPrefix ?? "RUNS"}: ${alert.impactedRunIds.join(", ")})`}
            </span>
            <button
              type="button"
              data-testid={`stale-alert-replay-btn-${alert.alertKey}`}
              onClick={() => onReplayAlert(alert)}
              style={{
                backgroundColor: "var(--color-surface-card)",
                color: "var(--color-stale-crimson)",
                border: "1px solid var(--color-stale-crimson)",
                borderRadius: "var(--radius-sm)",
                padding: "2px 6px",
                fontSize: "10px",
                cursor: "pointer",
              }}
            >
              <OrciaIcon name="regenerate" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
