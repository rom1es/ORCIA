import {
  OrciaAlertBanner,
  OrciaPageHeader,
  OrciaTabStrip,
  type OrciaTabStripItem,
} from "@orcia/ui";
import React, { useState } from "react";
import { CreateProcessFormDialog } from "../../components/CreateProcessFormDialog";
import { useOptionalPlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { resolveEffectiveWorkspaceId } from "../../components/shellScopeOptions";
import { useI18n } from "../../i18n";
import { useAuthSessionStore } from "../../stores/authSessionStore";
import { AutonomousRunsSupervisionPanel } from "./AutonomousRunsSupervisionPanel";
import {
  ProcessCatalogCardGrid,
  type WorkflowHubFilter,
} from "./ProcessCatalogCardGrid";
import { ProcessesActiveDossiersCard } from "./ProcessesActiveDossiersCard";
import {
  savePersistedWorkflowV2,
  type WorkflowDefinitionV2Item,
} from "./processStudioV2Data";
import { ProcessesValueStreamOverviewCard } from "./ProcessesValueStreamOverviewCard";
import { useProcessesHubData } from "./useProcessesHubData";

export type { WorkflowHubFilter };
export type ProcessesHubTabKey = "validations" | "catalog" | "value-stream";

function readInitialTabFromQuery(): ProcessesHubTabKey | null {
  if (typeof window === "undefined") return null;
  const raw = new URLSearchParams(window.location.search).get("tab")?.trim();
  if (raw === "validations" || raw === "catalog" || raw === "value-stream") {
    return raw;
  }
  return null;
}

export function ProcessesHubPage() {
  const { isFr, dictionary } = useI18n();
  const { activeScopeId, navigateToRoute, openHelpSection } = useShellNavigation();
  const setupCtx = useOptionalPlatformSetup();
  const authEmail = useAuthSessionStore((s) => s.email);
  const activeWorkspaceId = resolveEffectiveWorkspaceId(
    activeScopeId,
    setupCtx?.workspaces ?? [],
    authEmail,
  );

  const modesCopy = dictionary.processOrchestrationModes;
  const hubCopy = dictionary.processStudioUi.hub;
  const [isCreateProcessOpen, setIsCreateProcessOpen] = useState(false);
  const [filter, setFilter] = useState<WorkflowHubFilter>("all");
  const [userSelectedTab, setUserSelectedTab] = useState<ProcessesHubTabKey | null>(() =>
    readInitialTabFromQuery(),
  );

  const {
    workflows,
    setWorkflows,
    pendingRuns,
    autonomousCount,
    isLoadingPendingRuns,
    launchingWorkflowId,
    hubErrorBanner,
    vsmSummary,
    handleLaunchWorkflow,
  } = useProcessesHubData({
    activeScopeId,
    activeWorkspaceId,
    navigateToRoute,
  });

  const attentionCount = pendingRuns.length + autonomousCount;
  const activeTabId: ProcessesHubTabKey =
    userSelectedTab ?? (attentionCount > 0 ? "validations" : "catalog");

  const tabs: readonly OrciaTabStripItem<ProcessesHubTabKey>[] = [
    {
      key: "validations",
      label: hubCopy.tabValidationsAndRuns,
      icon: "clock",
      ...(attentionCount > 0 ? { count: attentionCount } : {}),
      testId: "processes-tab-validations",
      countTestId: "processes-tab-badge-validations",
    },
    {
      key: "catalog",
      label: hubCopy.tabBusinessProcesses,
      icon: "processes",
      testId: "processes-tab-catalog",
    },
    {
      key: "value-stream",
      label: hubCopy.tabValueStream,
      icon: "compass",
      testId: "processes-tab-value-stream",
    },
  ];

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
        tabs={
          <OrciaTabStrip<ProcessesHubTabKey>
            testId="processes-hub-tabs"
            ariaLabel={hubCopy.tabsAriaLabel}
            variant="underline"
            tabs={tabs}
            activeTabId={activeTabId}
            onSelectTab={setUserSelectedTab}
          />
        }
        alertSlot={
          hubErrorBanner ? (
            <OrciaAlertBanner tone="crimson" role="alert" testId="processes-hub-error-banner">
              {hubErrorBanner}
            </OrciaAlertBanner>
          ) : null
        }
      />

      {activeTabId === "validations" ? (
        <div data-testid="processes-tab-panel-validations" className="flex flex-col gap-4">
          <ProcessesActiveDossiersCard
            pendingRuns={pendingRuns}
            workflows={workflows}
            isLoadingPendingRuns={isLoadingPendingRuns}
            onOpenPendingRun={(run) => navigateToRoute(`/processes/runs/${run.run_id}`)}
          />
          <AutonomousRunsSupervisionPanel hideWhenEmptyOrUnauthorized={true} />
        </div>
      ) : null}

      {activeTabId === "catalog" ? (
        <div data-testid="processes-tab-panel-catalog">
          <ProcessCatalogCardGrid
            workflows={workflows}
            filter={filter}
            modesCopy={modesCopy}
            isFr={isFr}
            launchingWorkflowId={launchingWorkflowId}
            onChangeFilter={setFilter}
            onExecuteWorkflow={(wfId) => {
              void handleLaunchWorkflow(wfId);
            }}
            onOpenStudio={(wfId) => navigateToRoute(`/processes/studio/${wfId}`)}
          />
        </div>
      ) : null}

      {activeTabId === "value-stream" ? (
        <div data-testid="processes-tab-panel-value-stream">
          <ProcessesValueStreamOverviewCard
            isFr={isFr}
            vsmId={vsmSummary?.id}
            vsmTitle={vsmSummary?.title}
            vsmSubtitle={vsmSummary?.subtitle}
            onOpenInteractiveVsm={(vsmId) => navigateToRoute(`/processes/vsm/${vsmId}`)}
          />
        </div>
      ) : null}

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
    </section>
  );
}
