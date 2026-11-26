import type { ProcessPendingRunItemResponse } from "@orcia/api-client";
import { OrciaAlertBanner, OrciaPageHeader } from "@orcia/ui";
import React, { useCallback, useEffect, useState } from "react";
import { CreateProcessFormDialog } from "../../components/CreateProcessFormDialog";
import { useOptionalPlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { resolveEffectiveWorkspaceId } from "../../components/shellScopeOptions";
import { useI18n } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import { useAuthSessionStore } from "../../stores/authSessionStore";
import { AutonomousRunsSupervisionPanel } from "./AutonomousRunsSupervisionPanel";
import {
  ProcessCatalogCardGrid,
  type WorkflowHubFilter,
} from "./ProcessCatalogCardGrid";
import {
  ProcessesActiveDossiersCard,
  resolveWorkflowForPendingRun,
} from "./ProcessesActiveDossiersCard";
import {
  loadPersistedWorkflowsV2,
  savePersistedWorkflowV2,
  type WorkflowDefinitionV2Item,
} from "./processStudioV2Data";
import { ProcessesValueStreamOverviewCard } from "./ProcessesValueStreamOverviewCard";
import {
  createProcessesApiClient,
  mapApiWorkflowV2ToUiItem,
} from "./studio/studioLabelsAndMappers";

export type { WorkflowHubFilter };

export function ProcessesHubPage() {
  const { locale, isFr, dictionary } = useI18n();
  const { activeScopeId, navigateToRoute, openHelpSection } = useShellNavigation();
  const setupCtx = useOptionalPlatformSetup();
  const authEmail = useAuthSessionStore((s) => s.email);
  const activeWorkspaceId = resolveEffectiveWorkspaceId(
    activeScopeId,
    setupCtx?.workspaces ?? [],
    authEmail,
  );
  const effectivePendingScopeParam =
    activeScopeId === "scope-global" || !activeWorkspaceId
      ? "scope-global"
      : activeWorkspaceId;

  const modesCopy = dictionary.processOrchestrationModes;
  const hubCopy = dictionary.processStudioUi.hub;
  const [isCreateProcessOpen, setIsCreateProcessOpen] = useState(false);

  const [workflows, setWorkflows] = useState<WorkflowDefinitionV2Item[]>(() =>
    loadPersistedWorkflowsV2(locale),
  );
  const [pendingRuns, setPendingRuns] = useState<ProcessPendingRunItemResponse[]>([]);
  const [isLoadingPendingRuns, setIsLoadingPendingRuns] = useState<boolean>(true);
  const [filter, setFilter] = useState<WorkflowHubFilter>("all");
  const [activeRunWorkflow, setActiveRunWorkflow] = useState<WorkflowDefinitionV2Item | null>(null);
  const [activePendingRun, setActivePendingRun] = useState<ProcessPendingRunItemResponse | null>(
    null,
  );
  const [hubErrorBanner, setHubErrorBanner] = useState<string | null>(null);
  const [vsmSummary, setVsmSummary] = useState<{
    id: string;
    title: string;
    subtitle: string;
  } | null>(null);

  const refreshPendingRuns = useCallback(() => {
    const apiClient = createProcessesApiClient(locale);
    setIsLoadingPendingRuns(true);
    return apiClient
      .listProcessPendingRuns({ workspaceId: effectivePendingScopeParam })
      .then((res) => {
        setPendingRuns(Array.isArray(res?.items) ? res.items : []);
      })
      .catch((err: unknown) => {
        const formatted = formatRfc9457ErrorToBanner(
          err,
          locale,
          hubCopy.pendingRunsResourceLabel,
        );
        setHubErrorBanner(formatted.fullText);
      })
      .finally(() => {
        setIsLoadingPendingRuns(false);
      });
  }, [locale, effectivePendingScopeParam, hubCopy.pendingRunsResourceLabel]);

  useEffect(() => {
    let cancelled = false;
    const apiClient = createProcessesApiClient(locale);
    setIsLoadingPendingRuns(true);

    Promise.all([
      apiClient.listWorkflowsV2(),
      apiClient.listValueStreamMaps(),
      apiClient.listProcessPendingRuns({ workspaceId: effectivePendingScopeParam }),
    ])
      .then(([wfRes, vsmRes, pendingRes]) => {
        if (cancelled) return;
        const firstVsm = Array.isArray(vsmRes?.items) ? vsmRes.items[0] : undefined;
        if (firstVsm?.id) {
          setVsmSummary({
            id: firstVsm.id,
            title: firstVsm.title,
            subtitle: firstVsm.subtitle,
          });
        }
        setPendingRuns(Array.isArray(pendingRes?.items) ? pendingRes.items : []);
        if (!Array.isArray(wfRes?.items) || wfRes.items.length === 0) return;
        setWorkflows((prev) =>
          wfRes.items.map((apiWf) => {
            const existing = prev.find((p) => p.id === apiWf.id || p.slug === apiWf.slug);
            const uiItem = mapApiWorkflowV2ToUiItem(apiWf, existing, locale);
            savePersistedWorkflowV2(uiItem);
            return uiItem;
          }),
        );
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const formatted = formatRfc9457ErrorToBanner(
          err,
          locale,
          hubCopy.catalogResourceLabel,
        );
        setHubErrorBanner(formatted.fullText);
      })
      .finally(() => {
        if (!cancelled) setIsLoadingPendingRuns(false);
      });

    return () => {
      cancelled = true;
    };
  }, [locale, effectivePendingScopeParam, hubCopy.catalogResourceLabel]);

  return (
    <section
      data-testid="processes-hub-v2-page"
      style={{ display: "flex", flexDirection: "column", gap: "18px" }}
    >
      <OrciaPageHeader
        testId="processes-page-header"
        icon="processes"
        title={dictionary.fourZoneShell.menuEntries.processes}
        subtitle={dictionary.modulePages.gates.subtitle}
        primaryAction={
          <button
            type="button"
            data-testid="open-create-process-modal-btn"
            onClick={() => setIsCreateProcessOpen(true)}
            className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm orcia-ds-nowrap"
          >
            {hubCopy.newProcessBtn}
          </button>
        }
        alertSlot={
          hubErrorBanner ? (
            <OrciaAlertBanner tone="crimson" role="alert" testId="processes-hub-error-banner">
              {hubErrorBanner}
            </OrciaAlertBanner>
          ) : null
        }
      />

      <ProcessesActiveDossiersCard
        pendingRuns={pendingRuns}
        workflows={workflows}
        isLoadingPendingRuns={isLoadingPendingRuns}
        activeRunWorkflow={activeRunWorkflow}
        activePendingRun={activePendingRun}
        activeWorkspaceId={activeWorkspaceId}
        onOpenPendingRun={(run) => {
          setActivePendingRun(run);
          setActiveRunWorkflow(resolveWorkflowForPendingRun(run, workflows));
        }}
        onCloseRunDrawer={() => {
          setActiveRunWorkflow(null);
          setActivePendingRun(null);
          void refreshPendingRuns();
        }}
        onRunStateChanged={() => {
          void refreshPendingRuns();
        }}
      />

      <ProcessCatalogCardGrid
        workflows={workflows}
        filter={filter}
        modesCopy={modesCopy}
        isFr={isFr}
        onChangeFilter={setFilter}
        onExecuteWorkflow={(wfId) => {
          const matched = workflows.find((w) => w.id === wfId) ?? null;
          setActivePendingRun(null);
          setActiveRunWorkflow(matched);
        }}
        onOpenStudio={(wfId) => navigateToRoute(`/processes/studio/${wfId}`)}
      />

      <CreateProcessFormDialog
        open={isCreateProcessOpen}
        onOpenChange={setIsCreateProcessOpen}
        isFr={isFr}
        openHelpSection={openHelpSection}
        upsertWorkflow={(item) => {
          setupCtx?.upsertWorkflow(item);
          const createdV2: WorkflowDefinitionV2Item = {
            id: item.workflowKey,
            slug: item.workflowKey,
            title: item.title,
            pack_id: "orcia-pack-custom",
            vsm_step_num: null,
            version: item.version,
            status: item.status === "PUBLISHED" ? "published" : "draft",
            orchestration_type: "deterministic_dbos",
            reflexive_objective: item.prePrompt || item.title,
            execution_mode: "native_orcia",
            agent_ref: "@assistant",
            skills_refs: [],
            knowledge_base_refs: [],
            triggers: [],
            contract: { inputs: [], outputs: [], exit_criteria: [] },
            sub_steps: [],
            controls: { deterministic_gates: [], probabilistic_evaluations: [] },
            guardrails: [],
          };
          savePersistedWorkflowV2(createdV2);
          setWorkflows((prev) => [
            createdV2,
            ...prev.filter((p) => p.id !== createdV2.id),
          ]);
        }}
      />

      <AutonomousRunsSupervisionPanel />

      <ProcessesValueStreamOverviewCard
        isFr={isFr}
        vsmId={vsmSummary?.id}
        vsmTitle={vsmSummary?.title}
        vsmSubtitle={vsmSummary?.subtitle}
        onOpenInteractiveVsm={(vsmId) => navigateToRoute(`/processes/vsm/${vsmId}`)}
      />
    </section>
  );
}
