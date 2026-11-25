import { OrciaAlertBanner, OrciaPageHeader } from "@orcia/ui";
import React, { useEffect, useState } from "react";
import { CreateProcessFormDialog } from "../../components/CreateProcessFormDialog";
import { useOptionalPlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { resolveEffectiveWorkspaceId } from "../../components/shellScopeOptions";
import { useI18n } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import { useAuthSessionStore } from "../../stores/authSessionStore";
import {
  readPersistedReflexiveId,
  writePersistedReflexiveId,
} from "../shared/reflexiveTraceMappers";
import { AutonomousRunsSupervisionPanel } from "./AutonomousRunsSupervisionPanel";
import {
  ProcessCatalogCardGrid,
  type WorkflowHubFilter,
} from "./ProcessCatalogCardGrid";
import { ProcessesActiveDossiersCard } from "./ProcessesActiveDossiersCard";
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

export const ACTIVE_PROCESS_RUN_WORKFLOW_STORAGE_KEY =
  "orcia.processes.active_run_workflow_id.v1";

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
  const modesCopy = dictionary.processOrchestrationModes;
  const hubCopy = dictionary.processStudioUi.hub;
  const [isCreateProcessOpen, setIsCreateProcessOpen] = useState(false);

  const [workflows, setWorkflows] = useState<WorkflowDefinitionV2Item[]>(() =>
    loadPersistedWorkflowsV2(locale),
  );
  const [filter, setFilter] = useState<WorkflowHubFilter>("all");
  const [activeRunWorkflowId, setActiveRunWorkflowIdState] = useState<
    string | null
  >(() => readPersistedReflexiveId(ACTIVE_PROCESS_RUN_WORKFLOW_STORAGE_KEY));
  const setActiveRunWorkflowId = (nextId: string | null) => {
    setActiveRunWorkflowIdState(nextId);
    writePersistedReflexiveId(ACTIVE_PROCESS_RUN_WORKFLOW_STORAGE_KEY, nextId);
  };
  const [hubErrorBanner, setHubErrorBanner] = useState<string | null>(null);
  const [vsmSummary, setVsmSummary] = useState<{
    id: string;
    title: string;
    subtitle: string;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    const apiClient = createProcessesApiClient(locale);
    Promise.all([apiClient.listWorkflowsV2(), apiClient.listValueStreamMaps()])
      .then(([wfRes, vsmRes]) => {
        if (cancelled) {
          return;
        }
        const firstVsm = Array.isArray(vsmRes?.items) ? vsmRes.items[0] : undefined;
        if (firstVsm?.id) {
          setVsmSummary({
            id: firstVsm.id,
            title: firstVsm.title,
            subtitle: firstVsm.subtitle,
          });
        }
        if (!Array.isArray(wfRes?.items) || wfRes.items.length === 0) {
          return;
        }
        setWorkflows((prev) => {
          const mapped = wfRes.items.map((apiWf) => {
            const existing = prev.find((p) => p.id === apiWf.id || p.slug === apiWf.slug);
            const uiItem = mapApiWorkflowV2ToUiItem(apiWf, existing, locale);
            savePersistedWorkflowV2(uiItem);
            return uiItem;
          });
          return mapped;
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const formatted = formatRfc9457ErrorToBanner(
          err,
          locale,
          hubCopy.catalogResourceLabel,
        );
        setHubErrorBanner(formatted.fullText);
      });
    return () => {
      cancelled = true;
    };
  }, [locale, hubCopy.catalogResourceLabel]);

  const activeRunWorkflow =
    workflows.find((w) => w.id === activeRunWorkflowId) ?? null;
  const featuredPendingWorkflow = workflows[0] ?? null;

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
        featuredPendingWorkflow={featuredPendingWorkflow}
        activeRunWorkflow={activeRunWorkflow}
        activeWorkspaceId={activeWorkspaceId}
        onSelectWorkflowRun={setActiveRunWorkflowId}
      />

      <ProcessCatalogCardGrid
        workflows={workflows}
        filter={filter}
        modesCopy={modesCopy}
        isFr={isFr}
        onChangeFilter={setFilter}
        onExecuteWorkflow={(wfId) => setActiveRunWorkflowId(wfId)}
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
            contract: {
              inputs: [],
              outputs: [],
              exit_criteria: [],
            },
            sub_steps: [],
            controls: {
              deterministic_gates: [],
              probabilistic_evaluations: [],
            },
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
