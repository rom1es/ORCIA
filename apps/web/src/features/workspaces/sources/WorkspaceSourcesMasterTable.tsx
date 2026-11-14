import {
  OrciaIcon,
  OrciaSwitch,
  OrciaTooltip,
  StatusBadge,
} from "@orcia/ui";
import React, { useState } from "react";
import type {
  EnterpriseConnectorItemResponse,
  WorkspaceDatasourceItemResponse,
} from "@orcia/api-client";
import { useI18n } from "../../../i18n";

export type SourcesNatureFilter =
  | "ALL"
  | "DOCUMENT_KB"
  | "WORK_TRACKER"
  | "SOURCE_CODE"
  | "RELATIONAL_SCHEMA";

export interface WorkspaceSourcesMasterTableProps {
  readonly datasources: readonly WorkspaceDatasourceItemResponse[];
  readonly connectors: readonly EnterpriseConnectorItemResponse[];
  readonly isWorkspaceLead: boolean;
  readonly isReadOnlyObserver: boolean;
  readonly onTriggerSync: (datasourceId: string) => Promise<void>;
  readonly onOpenAttachModal: () => void;
  readonly onEditDatasource: (datasource: WorkspaceDatasourceItemResponse) => void;
  readonly onDeleteDatasource: (datasourceId: string) => Promise<void>;
  readonly onToggleGitNexus: (
    datasource: WorkspaceDatasourceItemResponse,
    enabled: boolean,
  ) => Promise<void>;
  readonly onRenewReferent?: (datasourceId: string, currentReferent?: string) => void;
}

const tdStyle: React.CSSProperties = { padding: "8px" };

export function WorkspaceSourcesMasterTable({
  datasources,
  connectors,
  isWorkspaceLead,
  isReadOnlyObserver,
  onTriggerSync,
  onOpenAttachModal,
  onEditDatasource,
  onDeleteDatasource,
  onToggleGitNexus,
  onRenewReferent,
}: WorkspaceSourcesMasterTableProps): React.ReactElement {
  const { dictionary } = useI18n();
  const copy = dictionary.epic18Sources;
  const [natureFilter, setNatureFilter] = useState<SourcesNatureFilter>("ALL");
  const [syncingDsId, setSyncingDsId] = useState<string | null>(null);

  const connectorMap = new Map(connectors.map((c) => [c.id, c.name]));
  const filtered = datasources.filter(
    (ds) => natureFilter === "ALL" || ds.source_nature === natureFilter,
  );

  const getNatureIcon = (nature: string) => {
    if (nature === "WORK_TRACKER") return <OrciaIcon name="target" />;
    if (nature === "SOURCE_CODE") return <OrciaIcon name="tools" />;
    if (nature === "RELATIONAL_SCHEMA") return <OrciaIcon name="dna" />;
    return <OrciaIcon name="books" />;
  };

  const getFreshnessBadge = (ds: WorkspaceDatasourceItemResponse) => {
    const s = ds.freshness_status || "PENDING_INITIAL_SYNC";
    const tone = s === "SYNCED" ? "emerald" : s === "STALE" ? "amber" : s === "SYNC_ERROR" ? "crimson" : "cobalt";
    const lbl = s === "SYNCED" ? copy.freshnessStatuses.synced : s === "STALE" ? copy.freshnessStatuses.stale : s === "SYNC_ERROR" ? copy.freshnessStatuses.syncError : copy.freshnessStatuses.pendingInitial;
    const shortHash = ds.fingerprint_hash ? ` • ${ds.fingerprint_hash.slice(0, 8)}` : "";

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
        <StatusBadge label={`${lbl}${shortHash}`} tone={tone} monospace />
        {ds.last_sync_at_iso ? (
          <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>
            {new Date(ds.last_sync_at_iso).toLocaleString()}
          </span>
        ) : null}
      </div>
    );
  };

  const filterTabs = [
    { key: "ALL" as const, label: copy.filters.all },
    { key: "DOCUMENT_KB" as const, label: copy.filters.docKb },
    { key: "WORK_TRACKER" as const, label: copy.filters.tracker },
    { key: "SOURCE_CODE" as const, label: copy.filters.code },
    { key: "RELATIONAL_SCHEMA" as const, label: copy.filters.schema },
  ];

  return (
    <div data-testid="workspace-sources-master-table-root" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
        <div role="radiogroup" aria-label={copy.columns.nature} style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          {filterTabs.map((item) => {
            const active = natureFilter === item.key;
            return (
              <button
                key={item.key}
                type="button"
                data-testid={`sources-filter-pill-${item.key.toLowerCase()}`}
                onClick={() => setNatureFilter(item.key)}
                className="orcia-ds-btn orcia-ds-btn-secondary"
                style={{
                  fontSize: "12px",
                  padding: "4px 10px",
                  fontWeight: active ? 700 : 500,
                  backgroundColor: active ? "var(--color-action-primary-subtle)" : "var(--color-bg-elevated)",
                  color: active ? "var(--color-action-primary)" : "var(--color-text-primary)",
                  borderColor: active ? "var(--color-action-primary)" : "var(--color-border)",
                }}
              >
                {item.label}
              </button>
            );
          })}
        </div>

        <button
          type="button"
          data-testid="open-attach-source-modal-btn"
          disabled={isReadOnlyObserver}
          onClick={onOpenAttachModal}
          className="orcia-ds-btn orcia-ds-btn-primary"
        >
          {copy.actions.attachSourceBtn}
        </button>
      </div>

      {filtered.length === 0 ? (
        <div data-testid="workspace-sources-empty-state" className="orcia-bento-card" style={{ textAlign: "center", padding: "28px" }}>
          <p style={{ margin: 0, color: "var(--color-muted-foreground)" }}>Aucune source ne correspond au filtre sélectionné.</p>
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table data-testid="workspace-sources-table" style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--color-border-subtle)", textAlign: "left", color: "var(--color-muted-foreground)" }}>
                <th style={tdStyle}>{copy.columns.nature}</th>
                <th style={tdStyle}>{copy.columns.alias}</th>
                <th style={tdStyle}>{copy.columns.connector}</th>
                <th style={tdStyle}>{copy.columns.target}</th>
                <th style={tdStyle}>{copy.columns.mode}</th>
                <th style={tdStyle}>{copy.columns.freshness}</th>
                <th style={tdStyle}>{copy.columns.gitnexus}</th>
                <th style={{ ...tdStyle, textAlign: "right" }}>{copy.columns.actions}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((ds) => {
                const connName = ds.connector_id ? connectorMap.get(ds.connector_id) || ds.connector_id.slice(0, 8) : "—";
                const isCode = ds.source_nature === "SOURCE_CODE";
                const isSyncing = syncingDsId === ds.id;

                return (
                  <tr key={ds.id} data-testid={`workspace-detail-source-row-${ds.id}`} style={{ borderBottom: "1px solid var(--color-border-subtle)" }}>
                    <td style={tdStyle}>
                      <span data-testid={`workspace-source-row-${ds.id}`} style={{ display: "none" }} />
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                        {getNatureIcon(ds.source_nature ?? "DOCUMENT_KB")}
                        <span>{ds.source_nature ?? "DOCUMENT_KB"}</span>
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <div style={{ display: "flex", flexDirection: "column" }}>
                        <strong>{ds.alias}</strong>
                        <span style={{ color: "var(--color-muted-foreground)", fontFamily: "var(--font-mono)" }}>{ds.uri}</span>
                        {((ds as unknown as { sync_status?: string }).sync_status === "PAUSED_REFERENT_RENEWAL_REQUIRED" ||
                          ds.codegraph_status === "PAUSED_REFERENT_RENEWAL_REQUIRED" ||
                          (ds as unknown as { sync_status?: string }).sync_status === "PAUSED") && (
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
                              ⚠️ Synchronisation en pause — Référent à renouveler
                            </span>
                            {onRenewReferent ? (
                              <button
                                type="button"
                                data-testid={`renew-referent-btn-${ds.id}`}
                                onClick={() => onRenewReferent(ds.id, (ds as unknown as { referent_user_id?: string }).referent_user_id || "")}
                                className="orcia-ds-btn orcia-ds-btn-secondary"
                                style={{ padding: "2px 6px", fontSize: "10px" }}
                              >
                                Renouveler le référent
                              </button>
                            ) : null}
                          </div>
                        )}
                        {(ds as unknown as { sync_status?: string }).sync_status === "ACTIVE" && (
                          <span data-testid={`rag-sync-active-badge-${ds.id}`} style={{ display: "none" }}>Synchronisation active</span>
                        )}
                      </div>
                    </td>
                    <td style={tdStyle}>{connName}</td>
                    <td style={tdStyle}>{ds.target_scope || ds.target_ref ? `${ds.target_scope ?? ""}${ds.target_ref ? ` (${ds.target_ref})` : ""}` : "—"}</td>
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
                              label={ds.codegraph_status === "READY" ? copy.codegraph.readyBadge : ds.codegraph_status === "INDEXING" ? copy.codegraph.indexingBadge : ds.codegraph_status === "PAUSED_REFERENT_RENEWAL_REQUIRED" ? copy.codegraph.pausedBadge : copy.codegraph.disabledBadge}
                              tone={ds.codegraph_status === "READY" ? "emerald" : ds.codegraph_status === "INDEXING" ? "cobalt" : ds.codegraph_status === "PAUSED_REFERENT_RENEWAL_REQUIRED" ? "amber" : "neutral"}
                            />
                            {ds.codegraph_enabled ? (
                              <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>
                                {ds.codegraph_auth_mode === "WORKSPACE_LEAD_TOKEN" ? copy.codegraph.leadTokenLabel : copy.codegraph.serviceAccountLabel}
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
                          onClick={async () => {
                            setSyncingDsId(ds.id);
                            try {
                              await onTriggerSync(ds.id);
                            } finally {
                              setSyncingDsId(null);
                            }
                          }}
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
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
