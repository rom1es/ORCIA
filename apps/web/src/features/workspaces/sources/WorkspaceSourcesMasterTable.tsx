import { OrciaIcon, StatusBadge } from "@orcia/ui";
import React, { useState } from "react";
import type {
  EnterpriseConnectorItemResponse,
  WorkspaceDatasourceItemResponse,
} from "@orcia/api-client";
import { useI18n } from "../../../i18n";
import { WorkspaceSourcesMasterRow } from "./WorkspaceSourcesMasterRow";

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
  readonly onReconcileStaleness?: () => Promise<void>;
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
  onReconcileStaleness,
}: WorkspaceSourcesMasterTableProps): React.ReactElement {
  const { dictionary } = useI18n();
  const copy = dictionary.epic18Sources;
  const sourcesCopy = dictionary.featureWorkspaces.sources;
  const [natureFilter, setNatureFilter] = useState<SourcesNatureFilter>("ALL");
  const [syncingDsId, setSyncingDsId] = useState<string | null>(null);
  const [isReconciling, setIsReconciling] = useState(false);

  const connectorMap = new Map(connectors.map((c) => [c.id, c.name]));
  const showFilterPills = datasources.length > 0 || natureFilter !== "ALL";
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

  const handleSyncRow = async (dsId: string) => {
    setSyncingDsId(dsId);
    try {
      await onTriggerSync(dsId);
    } finally {
      setSyncingDsId(null);
    }
  };

  return (
    <div data-testid="workspace-sources-master-table-root" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: showFilterPills ? "space-between" : "flex-end",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        {showFilterPills ? (
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
        ) : null}

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {onReconcileStaleness ? (
            <button
              type="button"
              data-testid="workspace-sources-reconcile-btn"
              disabled={isReadOnlyObserver || isReconciling}
              onClick={async () => {
                setIsReconciling(true);
                try {
                  await onReconcileStaleness();
                } finally {
                  setIsReconciling(false);
                }
              }}
              className="orcia-ds-btn orcia-ds-btn-secondary"
            >
              {isReconciling ? copy.actions.reconciling : copy.actions.reconcileBtn}
            </button>
          ) : null}
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
      </div>

      {filtered.length === 0 ? (
        <div data-testid="workspace-sources-empty-state" className="orcia-bento-card" style={{ textAlign: "center", padding: "28px" }}>
          <p style={{ margin: 0, color: "var(--color-muted-foreground)" }}>
            {datasources.length === 0 && natureFilter === "ALL"
              ? sourcesCopy.emptyWorkspaceMessage
              : sourcesCopy.emptyFilterMessage}
          </p>
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
              {filtered.map((ds) => (
                <WorkspaceSourcesMasterRow
                  key={ds.id}
                  ds={ds}
                  connName={ds.connector_id ? connectorMap.get(ds.connector_id) || ds.connector_id.slice(0, 8) : "—"}
                  isWorkspaceLead={isWorkspaceLead}
                  isReadOnlyObserver={isReadOnlyObserver}
                  isSyncing={syncingDsId === ds.id}
                  copy={copy}
                  sourcesCopy={sourcesCopy}
                  tdStyle={tdStyle}
                  getNatureIcon={getNatureIcon}
                  getFreshnessBadge={getFreshnessBadge}
                  onSync={handleSyncRow}
                  onEditDatasource={onEditDatasource}
                  onDeleteDatasource={onDeleteDatasource}
                  onToggleGitNexus={onToggleGitNexus}
                  {...(onRenewReferent ? { onRenewReferent } : {})}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
