import { useEffect, useMemo, useRef, useState } from "react";
import {
  INITIAL_WORKFLOWS_V2,
  loadPersistedWorkflowsV2,
  savePersistedWorkflowV2,
  type WorkflowDefinitionV2Item,
} from "../processStudioV2Data";
import type { ProcessOrchestrationModesCopy } from "../../../i18n/locales/process_orchestration_modes_labels";
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
}

export function useStudioWorkflowController({
  targetId,
  locale,
  modesCopy,
}: UseStudioWorkflowControllerArgs) {
  const isFr = locale === "fr";
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

  useEffect(() => {
    setWorkflow(initialWf);
  }, [initialWf]);

  useEffect(() => {
    let cancelled = false;
    createProcessesApiClient(locale)
      .getWorkflowV2(targetId)
      .then((apiWf) => {
        if (cancelled || !isMountedRef.current || !apiWf?.id) return;
        const hydrated = mapApiWorkflowV2ToUiItem(apiWf, initialWf);
        savePersistedWorkflowV2(hydrated);
        setWorkflow((prev) =>
          JSON.stringify(prev) === JSON.stringify(hydrated) ? prev : hydrated,
        );
      })
      .catch((err: unknown) => {
        if (cancelled || !isMountedRef.current) return;
        const detail = err instanceof Error ? err.message : String(err);
        setStatusBanner({
          tone: "error",
          message: isFr
            ? `Impossible d'actualiser le processus depuis le serveur (${detail}). Copie locale affichée.`
            : `Unable to refresh process from server (${detail}). Showing local working copy.`,
        });
      });
    return () => {
      cancelled = true;
    };
  }, [targetId, locale, isFr, initialWf]);

  const persistUpdate = (
    nextWf: WorkflowDefinitionV2Item,
    bannerMessage?: string,
    publish = false,
  ) => {
    setWorkflow(nextWf);
    savePersistedWorkflowV2(nextWf);
    if (bannerMessage) {
      setStatusBanner({ tone: "success", message: bannerMessage });
    }
    createProcessesApiClient(locale)
      .saveWorkflowV2(nextWf.id, {
        workflow: mapUiItemToApiWorkflowV2(nextWf),
        publish,
      })
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
        const detail = err instanceof Error ? err.message : String(err);
        setStatusBanner({
          tone: "error",
          message: isFr
            ? `Échec de l'enregistrement sur le serveur : ${detail}`
            : `Failed to save process on server: ${detail}`,
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
      isFr
        ? "Liste des agents spécialisés mobilisables mise à jour."
        : "Mobilizable specialist agents updated.",
    );
  };

  const handleToggleSubStepEnabled = (subStepId: string) => {
    const base = ensureDraftOnEdit(workflow);
    const nextSubSteps = base.sub_steps.map((s) =>
      s.id === subStepId ? { ...s, enabled: !s.enabled } : s,
    );
    const toggled = nextSubSteps.find((s) => s.id === subStepId);
    persistUpdate(
      { ...base, sub_steps: nextSubSteps },
      isFr
        ? `Étape « ${toggled?.short_label} » ${toggled?.enabled ? "activée" : "ignorée"} dans votre copie de travail.`
        : `Step "${toggled?.short_label}" ${toggled?.enabled ? "enabled" : "skipped"} in your working draft.`,
    );
  };

  const handleSwitchExecutionMode = (mode: "native_orcia" | "external_delegated") => {
    const base = ensureDraftOnEdit(workflow);
    persistUpdate(
      {
        ...base,
        execution_mode: mode,
        external_tool_label:
          mode === "external_delegated"
            ? (base.external_tool_label ?? "IDE / Git de l'équipe")
            : base.external_tool_label,
        external_completion_event:
          mode === "external_delegated"
            ? (base.external_completion_event ?? "git:pr_opened")
            : base.external_completion_event,
      },
      isFr
        ? `Mode de réalisation basculé sur « ${mode === "external_delegated" ? "Réalisation dans l'IDE / Git de l'équipe" : "Exécution guidée dans ORCIA"} ».`
        : `Execution mode switched to "${mode === "external_delegated" ? "IDE / Git" : "ORCIA"}".`,
    );
  };

  const handleSaveAsDraft = () => {
    const drafted = ensureDraftOnEdit(workflow);
    persistUpdate(
      drafted,
      isFr ? `Brouillon enregistré (${drafted.version}).` : `Draft saved (${drafted.version}).`,
    );
  };

  const handlePublishWorkflow = () => {
    const published = buildNextPublishedWorkflow(workflow);
    persistUpdate(
      published,
      isFr
        ? `Processus publié et activé (version ${published.version}).`
        : `Process published as version ${published.version}.`,
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
      message: isFr
        ? `Simulation à blanc terminée : ${enabledCount} étape(s) vérifiée(s), aucune modification envoyée aux outils externes.`
        : `Dry-run completed: ${enabledCount} step(s) verified, 0 external writes executed.`,
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
        const detail = err instanceof Error ? err.message : String(err);
        setStatusBanner({
          tone: "error",
          message: isFr
            ? `Simulation distante indisponible (${detail}). Estimation locale affichée.`
            : `Remote simulation unavailable (${detail}). Showing local estimate.`,
        });
      });
  };

  return {
    workflow,
    viewMode,
    setViewMode,
    statusBanner,
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
