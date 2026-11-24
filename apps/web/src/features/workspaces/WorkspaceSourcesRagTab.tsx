import type {
  ControlCenterDatasourceItem,
  ControlCenterWorkspaceGovItem,
} from "@orcia/ui";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createOrciaApiClient,
  type CreateWorkspaceDatasourceRequest,
  type EnterpriseConnectorItemResponse,
  type UpdateWorkspaceDatasourceRequest,
  type WorkspaceDatasourceItemResponse,
} from "@orcia/api-client";
import { useShellNavigation } from "../../components/ShellContainer";
import { useAuthSessionStore } from "../../stores/authSessionStore";
import { useI18n } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import { useActiveEmbeddingModelStatus } from "../shared/useActiveEmbeddingModelStatus";
import { WorkspaceSourcesMasterTable } from "./sources/WorkspaceSourcesMasterTable";
import { WorkspaceSourceAttachModal } from "./sources/WorkspaceSourceAttachModal";
import { mapFallbackWorkspaceDatasources } from "./sources/WorkspaceSourcesFallbackHelper";
import { WorkspaceSourcesColdStartBanner } from "./sources/WorkspaceSourcesColdStartBanner";
import { WorkspaceSourcesRenewReferentForm } from "./sources/WorkspaceSourcesRenewReferentForm";

export interface WorkspaceSourcesRagTabProps {
  readonly isFr?: boolean;
  readonly activeWorkspace: ControlCenterWorkspaceGovItem;
  readonly initialDatasources?: readonly WorkspaceDatasourceItemResponse[];
  readonly fallbackDatasources?: readonly ControlCenterDatasourceItem[];
  readonly openHelpSection?: (sectionId: string) => void;
  readonly onSourcesChanged?: (items: readonly WorkspaceDatasourceItemResponse[]) => void;
  readonly onFeedback?: (message: string) => void;
}

const EMPTY_FALLBACK_DATASOURCES: readonly ControlCenterDatasourceItem[] = [];
const EMPTY_INITIAL_DATASOURCES: readonly WorkspaceDatasourceItemResponse[] = [];
const LEAD_ROLES = new Set(["TEAM_LEAD", "BU_LEAD", "PLATFORM_ADMIN", "SECOPS"]);

export function WorkspaceSourcesRagTab({
  activeWorkspace,
  initialDatasources = EMPTY_INITIAL_DATASOURCES,
  fallbackDatasources = EMPTY_FALLBACK_DATASOURCES,
  onSourcesChanged,
  onFeedback = () => {},
}: WorkspaceSourcesRagTabProps): React.ReactElement {
  const { dictionary, locale } = useI18n();
  const sourcesCopy = dictionary.categoryAControllers.workspaceSources;
  const openUserSettingsModalAtTab = useAuthSessionStore((s) => s.openUserSettingsModalAtTab);
  const sessionRoles = useAuthSessionStore((s) => s.roles);
  const sessionActiveHat = useAuthSessionStore((s) => s.activeHat);
  const sessionReadOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const { navigateToRoute } = useShellNavigation();
  const { hasActiveEmbeddingModel } = useActiveEmbeddingModelStatus();

  const wsId = activeWorkspace.workspaceId || "";
  const [datasources, setDatasources] = useState<readonly WorkspaceDatasourceItemResponse[]>(() =>
    initialDatasources.length > 0
      ? initialDatasources
      : mapFallbackWorkspaceDatasources(fallbackDatasources, activeWorkspace.name, wsId),
  );
  const onSourcesChangedRef = useRef(onSourcesChanged);
  onSourcesChangedRef.current = onSourcesChanged;
  const onFeedbackRef = useRef(onFeedback);
  onFeedbackRef.current = onFeedback;
  const fallbackRef = useRef(fallbackDatasources);
  fallbackRef.current = fallbackDatasources;
  const prevWsIdRef = useRef(wsId);
  const [connectors, setConnectors] = useState<readonly EnterpriseConnectorItemResponse[]>([]);
  const [isAttachModalOpen, setIsAttachModalOpen] = useState(false);
  const [editingDatasource, setEditingDatasource] = useState<WorkspaceDatasourceItemResponse | null>(null);
  const [renewingDsId, setRenewingDsId] = useState<string | null>(null);
  const [newReferentInput, setNewReferentInput] = useState<string>("");
  const [feedbackBanner, setFeedbackBanner] = useState<string | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const client = useMemo(() => createOrciaApiClient({ baseUrl: "", locale }), [locale]);
  const wsEffectiveRole = (activeWorkspace as { effectiveRole?: string }).effectiveRole;
  const normalizedRoles = sessionRoles.map((r) => String(r).toUpperCase());
  const effectiveRole =
    wsEffectiveRole ||
    (sessionActiveHat ? String(sessionActiveHat).toUpperCase() : "") ||
    normalizedRoles[0] ||
    "CONTRIBUTOR";
  const isWorkspaceLead =
    LEAD_ROLES.has(effectiveRole) ||
    (!wsEffectiveRole && normalizedRoles.some((r) => LEAD_ROLES.has(r)));
  const isReadOnlyObserver =
    activeWorkspace.accessMode === "READ_ONLY_OBSERVER" ||
    sessionReadOnlyObserver ||
    effectiveRole === "OBSERVER" ||
    effectiveRole === "READ_ONLY_OBSERVER";

  const showFeedback = (msg: string) => {
    setErrorBanner(null);
    setFeedbackBanner(msg);
    onFeedbackRef.current(msg);
  };

  const showApiError = useCallback(
    (err: unknown) => {
      const formatted = formatRfc9457ErrorToBanner(err, locale);
      setFeedbackBanner(null);
      setErrorBanner(formatted.fullText);
      onFeedbackRef.current(`⚠️ ${formatted.fullText}`);
    },
    [locale],
  );

  const loadData = useCallback(async () => {
    if (!wsId) return;
    try {
      const [dsRes, connRes] = await Promise.all([
        client.listWorkspaceDatasources(wsId),
        client.listEnterpriseConnectors(),
      ]);
      setDatasources(dsRes.items);
      setConnectors(connRes.items);
      onSourcesChangedRef.current?.(dsRes.items);
    } catch (err: unknown) {
      showApiError(err);
      if (fallbackRef.current.length > 0) {
        const mapped = mapFallbackWorkspaceDatasources(fallbackRef.current, activeWorkspace.name, wsId);
        setDatasources(mapped);
        onSourcesChangedRef.current?.(mapped);
      }
    }
  }, [wsId, activeWorkspace.name, client, showApiError]);

  useEffect(() => {
    if (prevWsIdRef.current !== wsId) {
      prevWsIdRef.current = wsId;
      setDatasources(mapFallbackWorkspaceDatasources(fallbackRef.current, activeWorkspace.name, wsId));
    }
    void loadData();
  }, [wsId, activeWorkspace.name, loadData]);

  const handleAttachOrUpdate = async (
    payload: CreateWorkspaceDatasourceRequest | UpdateWorkspaceDatasourceRequest,
    isEdit: boolean,
  ) => {
    if (!wsId) return;
    try {
      if (isEdit && editingDatasource) {
        await client.updateWorkspaceDatasource(wsId, editingDatasource.id, payload as UpdateWorkspaceDatasourceRequest);
        showFeedback(sourcesCopy.updated);
      } else {
        await client.createWorkspaceDatasource(wsId, payload as CreateWorkspaceDatasourceRequest);
        showFeedback(sourcesCopy.attached);
      }
      setIsAttachModalOpen(false);
      setEditingDatasource(null);
      await loadData();
    } catch (err: unknown) {
      showApiError(err);
      throw err;
    }
  };

  const handleTriggerSync = async (datasourceId: string) => {
    if (!wsId) return;
    try {
      const res = await client.triggerWorkspaceDatasourceSync(wsId, datasourceId);
      showFeedback(
        sourcesCopy.syncTriggered.replace("{status}", res.datasource.freshness_status ?? ""),
      );
      await loadData();
    } catch (err: unknown) {
      showApiError(err);
    }
  };

  const handleDeleteDatasource = async (datasourceId: string) => {
    if (!wsId) return;
    try {
      await client.deleteWorkspaceDatasource(wsId, datasourceId);
      showFeedback(sourcesCopy.deleted);
      await loadData();
    } catch (err: unknown) {
      showApiError(err);
    }
  };

  const handleToggleGitNexus = async (datasource: WorkspaceDatasourceItemResponse, enabled: boolean) => {
    if (!wsId) return;
    try {
      await client.updateWorkspaceDatasource(wsId, datasource.id, {
        codegraph_enabled: enabled,
      });
      showFeedback(enabled ? sourcesCopy.gitNexusEnabled : sourcesCopy.gitNexusDisabled);
      await loadData();
    } catch (err: unknown) {
      showApiError(err);
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
      showFeedback(sourcesCopy.referentRenewed);
      await loadData();
    } catch (err: unknown) {
      showApiError(err);
    }
  };

  const handleReconcileStaleness = async () => {
    if (!wsId) return;
    try {
      const res = await client.reconcileWorkspaceStaleness(wsId);
      showFeedback(
        sourcesCopy.reconciled
          .replace("{evaluated}", String(res.evaluated_count))
          .replace("{stale}", String(res.stale_count)),
      );
      await loadData();
    } catch (err: unknown) {
      showApiError(err);
    }
  };

  return (
    <div data-testid="workspace-detail-sources-content" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      <WorkspaceSourcesColdStartBanner
        bannerText={sourcesCopy.coldStartBanner}
        ctaLabel={sourcesCopy.myAccountCta}
        onOpenMyAccount={() => openUserSettingsModalAtTab("PASSTHROUGH_SOURCES")}
      />

      {errorBanner ? (
        <div role="alert" data-testid="sources-error-alert" className="rounded-lg border border-status-danger/40 bg-status-danger/10 px-3 py-2 text-xs text-status-danger">
          {errorBanner}
        </div>
      ) : null}

      {feedbackBanner ? (
        <div data-testid="sources-feedback-banner" style={{ padding: "8px 12px", borderRadius: "var(--radius-sm)", backgroundColor: "var(--color-bg-elevated)", border: "1px solid var(--color-border)", fontSize: "12px" }}>
          {feedbackBanner}
        </div>
      ) : null}

      <strong style={{ fontSize: "14px" }}>
        {sourcesCopy.sourcesTitle.replace("{name}", activeWorkspace.name)}
      </strong>

      {renewingDsId ? (
        <WorkspaceSourcesRenewReferentForm
          datasourceId={renewingDsId}
          value={newReferentInput}
          placeholder={sourcesCopy.newReferentPlaceholder}
          confirmLabel={sourcesCopy.confirmRenewalCta}
          cancelLabel={sourcesCopy.cancelCta}
          onChange={setNewReferentInput}
          onSubmit={() => void handleRenewReferent(renewingDsId)}
          onCancel={() => setRenewingDsId(null)}
        />
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
        hasActiveEmbeddingModel={hasActiveEmbeddingModel}
        onNavigateToAiModels={() => navigateToRoute("/settings/ai-models")}
        onClose={() => { setIsAttachModalOpen(false); setEditingDatasource(null); }}
        onSubmit={handleAttachOrUpdate}
      />
    </div>
  );
}
