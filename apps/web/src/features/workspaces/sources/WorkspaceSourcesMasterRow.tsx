import type { WorkspaceDatasourceItemResponse } from "@orcia/api-client";
import { OrciaIcon, OrciaSwitch, OrciaTooltip, StatusBadge } from "@orcia/ui";
import React from "react";
import type { Epic18SourcesLabels } from "../../../i18n/locales/epic18_sources_labels";
import type { FeatureWorkspacesDictionary } from "../../../i18n/locales/feature_workspaces_labels";

export interface WorkspaceSourcesMasterRowProps {
  readonly ds: WorkspaceDatasourceItemResponse;
  readonly connName: string;
  readonly isWorkspaceLead: boolean;
  readonly isReadOnlyObserver: boolean;
  readonly isSyncing: boolean;
  readonly copy: Epic18SourcesLabels;
  readonly sourcesCopy: FeatureWorkspacesDictionary["sources"];
  readonly tdStyle: React.CSSProperties;
  readonly getNatureIcon: (nature: string) => React.ReactNode;
  readonly getFreshnessBadge: (ds: WorkspaceDatasourceItemResponse) => React.ReactNode;
  readonly onSync: (datasourceId: string) => Promise<void>;
  readonly onEditDatasource: (datasource: WorkspaceDatasourceItemResponse) => void;
  readonly onDeleteDatasource: (datasourceId: string) => Promise<void>;
  readonly onToggleGitNexus: (
    datasource: WorkspaceDatasourceItemResponse,
    enabled: boolean,
  ) => Promise<void>;
  readonly onRenewReferent?: (datasourceId: string, currentReferent?: string) => void;
}

export function WorkspaceSourcesMasterRow({
  ds,
  connName,
  isWorkspaceLead,
  isReadOnlyObserver,
  isSyncing,
  copy,
  sourcesCopy,
  tdStyle,
  getNatureIcon,
  getFreshnessBadge,
  onSync,
  onEditDatasource,
  onDeleteDatasource,
  onToggleGitNexus,
  onRenewReferent,
}: WorkspaceSourcesMasterRowProps): React.ReactElement {
  const isCode = ds.source_nature === "SOURCE_CODE";
  const dsExtra = ds as unknown as { sync_status?: string; referent_user_id?: string };
  const isSyncPaused =
    dsExtra.sync_status === "PAUSED_REFERENT_RENEWAL_REQUIRED" ||
    ds.codegraph_status === "PAUSED_REFERENT_RENEWAL_REQUIRED" ||
    dsExtra.sync_status === "PAUSED";

  return (
    <tr
      data-testid={`workspace-detail-source-row-${ds.id}`}
      style={{ borderBottom: "1px solid var(--color-border-subtle)" }}
    >
      <td style={tdStyle}>
        <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
          {getNatureIcon(ds.source_nature ?? "DOCUMENT_KB")}
          <span>{ds.source_nature ?? "DOCUMENT_KB"}</span>
        </span>
      </td>
      <td style={tdStyle}>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <strong>{ds.alias}</strong>
          <span style={{ color: "var(--color-muted-foreground)", fontFamily: "var(--font-mono)" }}>
            {ds.uri}
          </span>
          {isSyncPaused && (
            <div style={{ marginTop: "4px", display: "flex", alignItems: "center", gap: "6px" }}>
              <span
                data-testid={`rag-sync-paused-badge-${ds.id}`}
                style={{
                  padding: "2px 6px",
                  borderRadius: "4px",
                  fontSize: "11px",
                  fontWeight: 600,
                  backgroundColor: "rgba(245, 158, 11, 0.15)",
                  color: "var(--color-status-warning)",
                  border: "1px solid rgba(245, 158, 11, 0.3)",
                }}
              >
                {sourcesCopy.syncPausedBanner}
              </span>
              {onRenewReferent ? (
                <button
                  type="button"
                  data-testid={`renew-referent-btn-${ds.id}`}
                  onClick={() => onRenewReferent(ds.id, dsExtra.referent_user_id || "")}
                  className="orcia-ds-btn orcia-ds-btn-secondary"
                  style={{ padding: "2px 6px", fontSize: "10px" }}
                >
                  {sourcesCopy.renewReferentBtn}
                </button>
              ) : null}
            </div>
          )}
        </div>
      </td>
      <td style={tdStyle}>{connName}</td>
      <td style={tdStyle}>
        {ds.target_scope || ds.target_ref
          ? `${ds.target_scope ?? ""}${ds.target_ref ? ` (${ds.target_ref})` : ""}`
          : "—"}
      </td>
      <td style={tdStyle}>
        <StatusBadge
          label={ds.sync_mode === "WEBHOOK_PUSH" ? copy.syncModes.webhook : copy.syncModes.polling24h}
          tone={ds.sync_mode === "WEBHOOK_PUSH" ? "cobalt" : "neutral"}
        />
      </td>
      <td style={tdStyle}>{getFreshnessBadge(ds)}</td>
      <td style={tdStyle}>
        {isCode ? (
          <div data-testid={`gitnexus-governance-cell-${ds.id}`} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {!isWorkspaceLead ? (
              <OrciaTooltip content={copy.codegraph.leadRequiredTooltip}>
                <span>
                  <OrciaSwitch checked={Boolean(ds.codegraph_enabled)} disabled={true} ariaLabel={copy.codegraph.switchLabel} testId={`gitnexus-toggle-${ds.id}`} onCheckedChange={() => {}} />
                </span>
              </OrciaTooltip>
            ) : (
              <OrciaSwitch
                checked={Boolean(ds.codegraph_enabled)}
                disabled={isReadOnlyObserver}
                ariaLabel={copy.codegraph.switchLabel}
                testId={`gitnexus-toggle-${ds.id}`}
                onCheckedChange={(checked) => onToggleGitNexus(ds, checked)}
              />
            )}
            <div style={{ display: "flex", flexDirection: "column" }}>
              <StatusBadge
                label={
                  ds.codegraph_status === "READY"
                    ? copy.codegraph.readyBadge
                    : ds.codegraph_status === "INDEXING"
                      ? copy.codegraph.indexingBadge
                      : ds.codegraph_status === "PAUSED_REFERENT_RENEWAL_REQUIRED"
                        ? copy.codegraph.pausedBadge
                        : copy.codegraph.disabledBadge
                }
                tone={
                  ds.codegraph_status === "READY"
                    ? "emerald"
                    : ds.codegraph_status === "INDEXING"
                      ? "cobalt"
                      : ds.codegraph_status === "PAUSED_REFERENT_RENEWAL_REQUIRED"
                        ? "amber"
                        : "neutral"
                }
              />
              {ds.codegraph_enabled ? (
                <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>
                  {ds.codegraph_auth_mode === "WORKSPACE_LEAD_TOKEN"
                    ? copy.codegraph.leadTokenLabel
                    : copy.codegraph.serviceAccountLabel}
                </span>
              ) : null}
            </div>
          </div>
        ) : (
          <span style={{ color: "var(--color-muted-foreground)" }}>—</span>
        )}
      </td>
      <td style={{ ...tdStyle, textAlign: "right" }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
          <button
            type="button"
            data-testid={`sync-datasource-btn-${ds.id}`}
            disabled={isReadOnlyObserver || isSyncing}
            className="orcia-ds-btn orcia-ds-btn-secondary"
            onClick={() => void onSync(ds.id)}
          >
            {copy.actions.syncBtn}
          </button>
          <button
            type="button"
            data-testid={`edit-datasource-btn-${ds.id}`}
            disabled={isReadOnlyObserver}
            className="orcia-ds-btn orcia-ds-btn-secondary"
            onClick={() => onEditDatasource(ds)}
          >
            {copy.actions.editSourceBtn}
          </button>
          <button
            type="button"
            data-testid={`delete-datasource-btn-${ds.id}`}
            disabled={isReadOnlyObserver}
            className="orcia-ds-btn orcia-ds-btn-danger"
            onClick={() => onDeleteDatasource(ds.id)}
          >
            {copy.actions.deleteSourceBtn}
          </button>
        </div>
      </td>
    </tr>
  );
}
