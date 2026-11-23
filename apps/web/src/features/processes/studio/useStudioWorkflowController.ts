import { useEffect, useMemo, useRef, useState } from "react";
import {
  INITIAL_WORKFLOWS_V2,
  loadPersistedWorkflowsV2,
  savePersistedWorkflowV2,
  type WorkflowDefinitionV2Item,
} from "../processStudioV2Data";
import type { ProcessOrchestrationModesCopy } from "../../../i18n/locales/process_orchestration_modes_labels";
import { CATEGORY_A_CONTROLLER_BY_LOCALE } from "../../../i18n/locales/category_a_controller_labels";
import {
  extractLocalizedApiError,
  formatRfc9457ErrorToBanner,
  resolveLocalizedClientError,
} from "../../../lib/formatRfc9457ErrorToBanner";
import {
  buildNextPublishedWorkflow,
  createProcessesApiClient,
  ensureDraftOnEdit,
  mapApiWorkflowV2ToUiItem,
  mapUiItemToApiWorkflowV2,
} from "./studioLabelsAndMappers";
import type { WhatIfSummaryState } from "./WorkflowBlocks1345Sections";
import type { UiProcessOrchestrationType } from "./WorkflowOrchestrationModeSelector";
import type { StudioStatusBannerState, StudioViewMode } from "./WorkflowStudioHeaderBar";

interface UseStudioWorkflowControllerArgs {
  targetId: string;
  locale: "fr" | "en";
  modesCopy: ProcessOrchestrationModesCopy;
  workspaceId?: string;
}

export function useStudioWorkflowController({
  targetId,
  locale,
  modesCopy,
  workspaceId,
}: UseStudioWorkflowControllerArgs) {
  const processCopy = CATEGORY_A_CONTROLLER_BY_LOCALE[locale].processes;
  const isMountedRef = useRef<boolean>(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const initialWf = useMemo(() => {
    const list = loadPersistedWorkflowsV2();
    return (
      list.find((w) => w.id === targetId || w.slug === targetId) ??
      INITIAL_WORKFLOWS_V2[0]!
    );
  }, [targetId]);

  const [workflow, setWorkflow] = useState<WorkflowDefinitionV2Item>(initialWf);
  const [viewMode, setViewMode] = useState<StudioViewMode>("design");
  const [statusBanner, setStatusBanner] = useState<StudioStatusBannerState | null>(null);
  const [whatIfResult, setWhatIfResult] = useState<WhatIfSummaryState | null>(null);
  const hasUserEditedRef = useRef<boolean>(false);

  useEffect(() => {
    hasUserEditedRef.current = false;
    setWorkflow(initialWf);
  }, [initialWf]);

  useEffect(() => {
    let cancelled = false;
    createProcessesApiClient(locale)
      .getWorkflowV2(targetId)
      .then((apiWf) => {
        if (cancelled || !isMountedRef.current || hasUserEditedRef.current || !apiWf?.id) return;
        const hydrated = mapApiWorkflowV2ToUiItem(apiWf, initialWf);
        savePersistedWorkflowV2(hydrated);
        setWorkflow((prev) =>
          JSON.stringify(prev) === JSON.stringify(hydrated) ? prev : hydrated,
        );
      })
      .catch((err: unknown) => {
        if (cancelled || !isMountedRef.current) return;
        setStatusBanner({
          tone: "error",
          message: formatRfc9457ErrorToBanner(
            err,
            locale,
            processCopy.processResource,
          ).fullText,
        });
      });
    return () => {
      cancelled = true;
    };
  }, [targetId, locale, initialWf, processCopy.processResource]);

  const persistUpdate = (
    nextWf: WorkflowDefinitionV2Item,
    bannerMessage?: string,
    publish = false,
  ) => {
    hasUserEditedRef.current = true;
    setWorkflow(nextWf);
    savePersistedWorkflowV2(nextWf);
    if (bannerMessage) {
      setStatusBanner({ tone: "success", message: bannerMessage });
    }
    createProcessesApiClient(locale)
      .saveWorkflowV2(
        nextWf.id,
        {
          workflow: mapUiItemToApiWorkflowV2(nextWf),
          publish,
        },
        workspaceId ? { workspaceId } : undefined,
      )
      .then((res) => {
        if (!isMountedRef.current || !res?.workflow?.id) return;
        const synced = mapApiWorkflowV2ToUiItem(res.workflow, nextWf);
        savePersistedWorkflowV2(synced);
        if (synced.version !== nextWf.version || synced.status !== nextWf.status) {
          setWorkflow(synced);
        }
      })
      .catch((err: unknown) => {
        if (!isMountedRef.current) return;
        setStatusBanner({
          tone: "error",
          message: formatRfc9457ErrorToBanner(
            err,
            locale,
            processCopy.processSaveResource,
          ).fullText,
        });
      });
  };

  const handleSelectOrchestrationType = (nextType: UiProcessOrchestrationType) => {
    const currentType = workflow.orchestration_type ?? "deterministic_dbos";
    if (currentType === nextType) return;
    const base = ensureDraftOnEdit(workflow);
    persistUpdate(
      { ...base, orchestration_type: nextType },
      nextType === "non_deterministic"
        ? modesCopy.modeSwitchedToGoalBanner
        : modesCopy.modeSwitchedToMilestoneBanner,
    );
  };

  const handleChangeGoalObjective = (nextObjective: string) => {
    const updated: WorkflowDefinitionV2Item = {
      ...ensureDraftOnEdit(workflow),
      reflexive_objective: nextObjective,
    };
    setWorkflow(updated);
    savePersistedWorkflowV2(updated);
  };

  const handleToggleDelegateAgent = (agentSlug: string) => {
    const base = ensureDraftOnEdit(workflow);
    const current = base.allowed_delegate_agents ?? [];
    const nextAgents = current.includes(agentSlug)
      ? current.filter((slug) => slug !== agentSlug)
      : [...current, agentSlug];
    persistUpdate(
      { ...base, allowed_delegate_agents: nextAgents },
      processCopy.delegatedAgentsUpdated,
    );
  };

  const handleToggleSubStepEnabled = (subStepId: string) => {
    const base = ensureDraftOnEdit(workflow);
    const nextSubSteps = base.sub_steps.map((s) =>
      s.id === subStepId ? { ...s, enabled: !s.enabled } : s,
    );
    const toggled = nextSubSteps.find((s) => s.id === subStepId);
    const stateWord = toggled?.enabled
      ? processCopy.stepActivatedWord
      : processCopy.stepSkippedWord;
    persistUpdate(
      { ...base, sub_steps: nextSubSteps },
      processCopy.subStepDraftUpdated
        .replace("{step}", toggled?.short_label ?? "")
        .replace("{state}", stateWord),
    );
  };

  const handleSwitchExecutionMode = (mode: "native_orcia" | "external_delegated") => {
    const base = ensureDraftOnEdit(workflow);
    const modeLabel =
      mode === "external_delegated"
        ? processCopy.externalIdeLabel
        : processCopy.nativeOrciaLabel;
    persistUpdate(
      {
        ...base,
        execution_mode: mode,
        external_tool_label:
          mode === "external_delegated"
            ? (base.external_tool_label ?? processCopy.externalIdeLabel)
            : base.external_tool_label,
        external_completion_event:
          mode === "external_delegated"
            ? (base.external_completion_event ?? "git:pr_opened")
            : base.external_completion_event,
      },
      processCopy.executionModeSwitched.replace("{mode}", modeLabel),
    );
  };

  const handleSaveAsDraft = () => {
    const drafted = ensureDraftOnEdit(workflow);
    persistUpdate(
      drafted,
      processCopy.draftSavedBanner.replace("{version}", drafted.version),
    );
  };

  const handlePublishWorkflow = () => {
    const published = buildNextPublishedWorkflow(workflow);
    persistUpdate(
      published,
      processCopy.publishedBanner.replace("{version}", published.version),
      true,
    );
  };

  const handleRunWhatIfSimulation = () => {
    const enabledCount =
      workflow.orchestration_type === "non_deterministic"
        ? 1
        : workflow.sub_steps.filter((s) => s.enabled).length;
    setWhatIfResult({
      subStepsEvaluated: enabledCount,
      deterministicGatesPassed: true,
      externalWritesExecuted: 0,
      estimatedCostUsd: Number((enabledCount * 0.015).toFixed(3)),
    });
    setViewMode("what_if");
    setStatusBanner({
      tone: "success",
      message: processCopy.whatIfDoneBanner.replace("{count}", String(enabledCount)),
    });
    createProcessesApiClient(locale)
      .runWorkflowV2WhatIf(workflow.id, { sample_inputs: {} })
      .then((assessment) => {
        if (!isMountedRef.current || typeof assessment?.estimated_cost_usd !== "number") return;
        setWhatIfResult({
          subStepsEvaluated: assessment.sub_steps_evaluated ?? enabledCount,
          deterministicGatesPassed: assessment.deterministic_gates_passed ?? true,
          externalWritesExecuted: assessment.external_writes_executed ?? 0,
          estimatedCostUsd: assessment.estimated_cost_usd,
        });
      })
      .catch((err: unknown) => {
        if (!isMountedRef.current) return;
        const extracted = extractLocalizedApiError(err, locale);
        setStatusBanner({
          tone: "error",
          message: resolveLocalizedClientError(
            "ERR_CLIENT_PROCESS_SIMULATION_UNAVAILABLE",
            locale,
            { detail: extracted.errorMessage },
          ),
        });
      });
  };

  return {
    workflow,
    viewMode,
    setViewMode,
    statusBanner,
    setStatusBanner,
    whatIfResult,
    persistUpdate,
    handleSelectOrchestrationType,
    handleChangeGoalObjective,
    handleToggleDelegateAgent,
    handleToggleSubStepEnabled,
    handleSwitchExecutionMode,
    handleSaveAsDraft,
    handlePublishWorkflow,
    handleRunWhatIfSimulation,
  };
}
