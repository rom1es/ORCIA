import {
  ContextualInfoTriggerButton,
  OrciaIcon,
  type ControlCenterDatasourceItem,
  type ControlCenterWorkspaceGovItem,
} from "@orcia/ui";
import React, { useCallback, useEffect, useState } from "react";
import {
  createOrciaApiClient,
  type CreateWorkspaceDatasourceRequest,
  type EnterpriseConnectorItemResponse,
  type UpdateWorkspaceDatasourceRequest,
  type WorkspaceDatasourceItemResponse,
} from "@orcia/api-client";
import type { PlatformSetupContextValue } from "../../components/platformSetupStore";
import { useAuthSessionStore } from "../../stores/authSessionStore";
import { useI18n } from "../../i18n";
import { WorkspaceSourcesMasterTable } from "./sources/WorkspaceSourcesMasterTable";
import { WorkspaceSourceAttachModal } from "./sources/WorkspaceSourceAttachModal";
import { mapFallbackWorkspaceDatasources } from "./sources/WorkspaceSourcesFallbackHelper";

export interface WorkspaceSourcesRagTabProps {
  readonly isFr?: boolean;
  readonly activeWorkspace: ControlCenterWorkspaceGovItem;
  readonly fallbackDatasources?: readonly ControlCenterDatasourceItem[];
  readonly openHelpSection?: (sectionId: string) => void;
  readonly onRegisterDatasource?: PlatformSetupContextValue["registerDatasource"];
  readonly onFeedback?: (message: string) => void;
}

export function WorkspaceSourcesRagTab({
  isFr = true,
  activeWorkspace,
  fallbackDatasources = [],
  openHelpSection = () => {},
  onRegisterDatasource,
  onFeedback = () => {},
}: WorkspaceSourcesRagTabProps): React.ReactElement {
  const { dictionary } = useI18n();
  const copy = dictionary.epic18Sources;
  const openUserSettingsModalAtTab = useAuthSessionStore((s) => s.openUserSettingsModalAtTab);

  const wsId = activeWorkspace.workspaceId || "";
  const [datasources, setDatasources] = useState<readonly WorkspaceDatasourceItemResponse[]>(() =>
    mapFallbackWorkspaceDatasources(fallbackDatasources, activeWorkspace.name, wsId),
  );
  const [connectors, setConnectors] = useState<readonly EnterpriseConnectorItemResponse[]>([]);
  const [isAttachModalOpen, setIsAttachModalOpen] = useState(false);
  const [editingDatasource, setEditingDatasource] = useState<WorkspaceDatasourceItemResponse | null>(null);
  const [renewingDsId, setRenewingDsId] = useState<string | null>(null);
  const [newReferentInput, setNewReferentInput] = useState<string>("");
  const [feedbackBanner, setFeedbackBanner] = useState<string | null>(null);

  const client = createOrciaApiClient({ baseUrl: "" });
  const effectiveRole =
    (activeWorkspace as unknown as { effectiveRole?: string }).effectiveRole || "PLATFORM_ADMIN";
  const isWorkspaceLead = ["TEAM_LEAD", "BU_LEAD", "PLATFORM_ADMIN", "SECOPS"].includes(effectiveRole);
  const isReadOnlyObserver =
    activeWorkspace.accessMode === "READ_ONLY_OBSERVER" ||
    effectiveRole === "OBSERVER" ||
    effectiveRole === "READ_ONLY_OBSERVER";

  const showFeedback = (msg: string) => {
    setFeedbackBanner(msg);
    onFeedback(msg);
  };

  const loadData = useCallback(async () => {
    if (!wsId) return;
    try {
      const [dsRes, connRes] = await Promise.all([
        client.listWorkspaceDatasources(wsId),
        client.listEnterpriseConnectors(),
      ]);
      setDatasources(dsRes.items);
      setConnectors(connRes.items);
    } catch (err: unknown) {
      console.warn(
        "[orcia:workspaceSources.loadData]",
        err instanceof Error ? err.message : String(err),
      );
      if (fallbackDatasources.length > 0) {
        setDatasources(
          fallbackDatasources
            .filter((d) => d.workspaceName === activeWorkspace.name)
            .map((d) => ({
              id: d.id,
              workspace_id: wsId,
              alias: d.alias,
              scheme: d.scheme,
              uri: d.uri,
              connector_id: null,
              sync_identity_mode: d.executionIdentity === "service_account" ? "SERVICE_ACCOUNT" : "TEAM_REFERENT_USER",
              service_account_id: null,
              referent_user_id: null,
              sync_status: "ACTIVE",
              sync_status_reason: null,
              source_nature: "DOCUMENT_KB",
              sync_mode: "POLLING_24H",
              target_scope: null,
              target_ref: null,
              last_sync_at_iso: null,
              last_probe_at_iso: null,
              fingerprint_hash: null,
              freshness_status: "PENDING_INITIAL_SYNC",
              codegraph_enabled: false,
              codegraph_auth_mode: "SERVICE_ACCOUNT",
              codegraph_owner_user_id: null,
              codegraph_status: "DISABLED",
              codegraph_last_indexed_at_iso: null,
              codegraph_head_sha: null,
              created_at_iso: "",
            })),
        );
      }
    }
  }, [wsId, activeWorkspace.name, fallbackDatasources]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleAttachOrUpdate = async (
    payload: CreateWorkspaceDatasourceRequest | UpdateWorkspaceDatasourceRequest,
    isEdit: boolean,
  ) => {
    if (!wsId) return;
    try {
      if (isEdit && editingDatasource) {
        await client.updateWorkspaceDatasource(wsId, editingDatasource.id, payload as UpdateWorkspaceDatasourceRequest);
        showFeedback(isFr ? `Source modifiée.` : `Source updated.`);
      } else {
        const createPayload = payload as CreateWorkspaceDatasourceRequest;
        await client.createWorkspaceDatasource(wsId, createPayload);
        onRegisterDatasource?.({
          workspaceName: activeWorkspace.name,
          alias: createPayload.alias,
          scheme: (createPayload.scheme as "git" | "confluence" | "jira" | "db") || "confluence",
          uri: createPayload.uri,
          executionIdentity: createPayload.sync_identity_mode === "SERVICE_ACCOUNT" ? "service_account" : "passthrough",
          freshnessTtlDays: 1,
        });
        showFeedback(isFr ? `Source rattachée.` : `Source attached.`);
      }
      setIsAttachModalOpen(false);
      setEditingDatasource(null);
      await loadData();
    } catch (err: unknown) {
      showFeedback(`⚠️ ${err instanceof Error ? err.message : "Erreur"}`);
    }
  };

  const handleTriggerSync = async (datasourceId: string) => {
    if (!wsId) return;
    try {
      const res = await client.triggerWorkspaceDatasourceSync(wsId, datasourceId);
      showFeedback(
        isFr
          ? `✅ Synchronisation déclenchée (${res.datasource.freshness_status}).`
          : `✅ Sync triggered (${res.datasource.freshness_status}).`,
      );
      await loadData();
    } catch (err: unknown) {
      showFeedback(`⚠️ ${err instanceof Error ? err.message : "Erreur"}`);
    }
  };

  const handleDeleteDatasource = async (datasourceId: string) => {
    if (!wsId) return;
    try {
      await client.deleteWorkspaceDatasource(wsId, datasourceId);
      showFeedback(isFr ? "✅ Source détachée." : "✅ Source deleted.");
      await loadData();
    } catch (err: unknown) {
      showFeedback(`⚠️ ${err instanceof Error ? err.message : "Erreur"}`);
    }
  };

  const handleToggleGitNexus = async (datasource: WorkspaceDatasourceItemResponse, enabled: boolean) => {
    if (!wsId) return;
    try {
      await client.updateWorkspaceDatasource(wsId, datasource.id, {
        codegraph_enabled: enabled,
      });
      showFeedback(enabled ? (isFr ? "✅ GitNexus activé." : "✅ GitNexus active.") : (isFr ? "GitNexus désactivé." : "GitNexus disabled."));
      await loadData();
    } catch (err: unknown) {
      showFeedback(`⚠️ ${err instanceof Error ? err.message : "Erreur GitNexus"}`);
    }
  };

  const handleRenewReferent = async (datasourceId: string) => {
    if (!newReferentInput.trim() || !wsId) return;
    try {
      await client.updateWorkspaceDatasource(wsId, datasourceId, {
        referent_user_id: newReferentInput.trim(),
        sync_identity_mode: "TEAM_REFERENT_USER",
      });
      setRenewingDsId(null);
      setNewReferentInput("");
      showFeedback(isFr ? "Référent renouvelé." : "Referent renewed.");
      await loadData();
    } catch (err: unknown) {
      showFeedback(`⚠️ ${err instanceof Error ? err.message : isFr ? "Erreur de renouvellement." : "Renewal error."}`);
    }
  };

  const handleReconcileStaleness = async () => {
    if (!wsId) return;
    try {
      const res = await client.reconcileWorkspaceStaleness(wsId);
      showFeedback(
        isFr
          ? `✅ Fraîcheur réconciliée (${res.evaluated_count} évaluées, ${res.stale_count} désynchronisées).`
          : `✅ Freshness reconciled (${res.evaluated_count} evaluated, ${res.stale_count} stale).`,
      );
      await loadData();
    } catch (err: unknown) {
      showFeedback(`⚠️ ${err instanceof Error ? err.message : "Erreur réconciliation"}`);
    }
  };

  return (
    <div data-testid="workspace-detail-sources-content" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      <div
        data-testid="rag-passthrough-cold-start-banner"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 14px",
          borderRadius: "var(--radius-sm)",
          backgroundColor: "rgba(59, 130, 246, 0.08)",
          border: "1px solid rgba(59, 130, 246, 0.2)",
          fontSize: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <OrciaIcon name="plug" size={16} />
          <span>{isFr ? "Attribution nominative : vos droits Jira / GitLab s'appliquent." : "Nominative attribution: Jira / GitLab rights apply."}</span>
        </div>
        <button
          type="button"
          data-testid="open-my-account-passthrough-cta"
          onClick={() => openUserSettingsModalAtTab("PASSTHROUGH_SOURCES")}
          className="orcia-ds-btn-secondary"
          style={{ padding: "4px 10px", fontSize: "11px", whiteSpace: "nowrap" }}
        >
          {isFr ? "👤 Mon Compte › Mes Connexions" : "👤 My Account › Connections"}
        </button>
      </div>

      {feedbackBanner ? (
        <div data-testid="sources-feedback-banner" style={{ padding: "8px 12px", borderRadius: "var(--radius-sm)", backgroundColor: "var(--color-bg-elevated)", border: "1px solid var(--color-border)", fontSize: "12px" }}>
          {feedbackBanner}
        </div>
      ) : null}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <strong style={{ fontSize: "14px" }}>{isFr ? `Sources de « ${activeWorkspace.name} »` : `Sources for "${activeWorkspace.name}"`}</strong>
          <ContextualInfoTriggerButton sectionId="workspace-sources" label={isFr ? "Aide sources" : "Help sources"} onOpenHelpSection={openHelpSection} />
        </div>
      </div>

      {renewingDsId ? (
        <form
          autoComplete="off"
          data-lpignore="true"
          data-form-type="other"
          data-testid={`renew-referent-form-${renewingDsId}`}
          onSubmit={(e) => { e.preventDefault(); void handleRenewReferent(renewingDsId); }}
          style={{ display: "flex", alignItems: "center", gap: "8px", padding: "8px 12px", borderRadius: "var(--radius-sm)", backgroundColor: "var(--color-bg-elevated)", border: "1px solid var(--color-border)" }}
        >
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid={`renew-referent-input-${renewingDsId}`}
            value={newReferentInput}
            onChange={(e) => setNewReferentInput(e.target.value)}
            placeholder={isFr ? "Nouveau référent (email)..." : "New referent email..."}
            style={{ flex: 1, padding: "6px 10px", fontSize: "12px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)" }}
          />
          <button type="submit" data-testid={`renew-referent-submit-btn-${renewingDsId}`} disabled={!newReferentInput.trim()} className="orcia-ds-btn orcia-ds-btn-primary" style={{ padding: "5px 10px", fontSize: "11px" }}>
            {isFr ? "Valider le renouvellement" : "Confirm renewal"}
          </button>
          <button type="button" onClick={() => setRenewingDsId(null)} className="orcia-ds-btn orcia-ds-btn-secondary" style={{ padding: "5px 10px", fontSize: "11px" }}>
            {isFr ? "Annuler" : "Cancel"}
          </button>
        </form>
      ) : null}

      <WorkspaceSourcesMasterTable
        datasources={datasources}
        connectors={connectors}
        isWorkspaceLead={isWorkspaceLead}
        isReadOnlyObserver={isReadOnlyObserver}
        onTriggerSync={handleTriggerSync}
        onOpenAttachModal={() => { setEditingDatasource(null); setIsAttachModalOpen(true); }}
        onEditDatasource={(ds) => { setEditingDatasource(ds); setIsAttachModalOpen(true); }}
        onDeleteDatasource={handleDeleteDatasource}
        onToggleGitNexus={handleToggleGitNexus}
        onRenewReferent={(dsId, curRef) => { setRenewingDsId(dsId); setNewReferentInput(curRef || ""); }}
        onReconcileStaleness={handleReconcileStaleness}
      />

      <WorkspaceSourceAttachModal
        isOpen={isAttachModalOpen}
        editingDatasource={editingDatasource}
        connectors={connectors}
        isWorkspaceLead={isWorkspaceLead}
        onClose={() => { setIsAttachModalOpen(false); setEditingDatasource(null); }}
        onSubmit={handleAttachOrUpdate}
      />
    </div>
  );
}
