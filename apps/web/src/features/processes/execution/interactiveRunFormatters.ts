import {
  DICTIONARIES,
  formatI18nTemplate,
  resolveDictionaryForFlag,
  type SupportedWebLocale,
} from "../../../i18n";

export function formatAgentHumanLabel(
  agentRef: string,
  locale: SupportedWebLocale = "fr",
): string {
  const labels = DICTIONARIES[locale].processVsmExecutionUi.execution.agentHumanLabels;
  return (
    labels[agentRef] ??
    agentRef.replace(/^pack:\/\/[^/]+\/agents\//, "").replace(/\.md$/, "")
  );
}

export function extractAgentSlugFromRef(agentRef: string): string {
  return (
    agentRef
      .replace(/^pack:\/\/[^/]+\/agents\//, "")
      .replace(/\.md$/, "")
      .trim() || "assistant"
  );
}

export function simpleHashHex(text: string): string {
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  const hex = (h >>> 0).toString(16).padStart(8, "0");
  return `${hex}${hex}${hex}${hex}${hex}${hex}${hex}${hex}`;
}

export type InteractiveProcessDrawerStatus =
  | "RUNNING"
  | "WAITING_EXTERNAL_GATE"
  | "WAITING_SUBSTEP_HITL"
  | "WAITING_WRITE_PREVIEW"
  | "WAITING_FINAL_ANCHOR"
  | "COMPLETED_APPROVED"
  | "RETURN_LOOP_TRIGGERED"
  | "SLA_SUSPENDED"
  | "FAILED_GATES";

export function mapBackendRunStatusToDrawerStatus(
  rawStatus: string | undefined,
  fallback: InteractiveProcessDrawerStatus,
): InteractiveProcessDrawerStatus {
  const upper = (rawStatus ?? "").trim().toUpperCase();
  if (upper === "COMPLETED" || upper === "COMPLETED_APPROVED") {
    return "COMPLETED_APPROVED";
  }
  if (upper === "PAUSED" || upper === "SLA_SUSPENDED") {
    return "SLA_SUSPENDED";
  }
  if (upper === "INITIALIZED" || upper === "RUNNING") {
    return "RUNNING";
  }
  if (
    upper === "WAITING_EXTERNAL_GATE" ||
    upper === "WAITING_SUBSTEP_HITL" ||
    upper === "WAITING_WRITE_PREVIEW" ||
    upper === "WAITING_FINAL_ANCHOR" ||
    upper === "RETURN_LOOP_TRIGGERED" ||
    upper === "FAILED_GATES"
  ) {
    return upper as InteractiveProcessDrawerStatus;
  }
  return fallback;
}

export function buildInitialArtifactMarkdown(
  workflowTitle: string,
  stepName: string,
  agentLabel: string,
  locale: SupportedWebLocale = "fr",
): string {
  const tpl =
    DICTIONARIES[locale].processVsmExecutionUi.execution.initialArtifactMarkdownTemplate;
  return formatI18nTemplate(tpl, {
    title: workflowTitle,
    step: stepName,
    agent: agentLabel,
  });
}

export function buildSubStepAdvanceMarkdown(
  workflowTitle: string,
  stepName: string,
  outputDescription: string,
  locale: SupportedWebLocale = "fr",
): string {
  const tpl =
    DICTIONARIES[locale].processVsmExecutionUi.execution.substepAdvanceMarkdownTemplate;
  return formatI18nTemplate(tpl, {
    title: workflowTitle,
    step: stepName,
    output: outputDescription,
  });
}

export function buildWritePreviewExecutionPayload(
  actorSlug: string,
  workflowId: string,
  workflowTitle: string,
  reflexiveObjective: string | null | undefined,
  isFr: boolean,
  workspaceId?: string,
) {
  const tpl =
    resolveDictionaryForFlag(isFr).processVsmExecutionUi.execution
      .writePreviewActionSummaryTemplate;
  return {
    actor_slug: actorSlug,
    objective: reflexiveObjective || workflowTitle,
    effort_level: "high" as const,
    effort_mode: "approfondi" as const,
    allow_sub_agent_delegation: true,
    available_delegate_agents: ["analyste-metier"],
    initial_resources: [],
    ...(workspaceId ? { workspace_id: workspaceId } : {}),
    requested_write_preview: {
      connector_type: "confluence",
      action: "publish_page",
      target_resource_uri: "confluence://Architecture/Documentation-ORCIA",
      action_summary: formatI18nTemplate(tpl, { title: workflowTitle }),
      payload: { workflow_id: workflowId, title: workflowTitle },
    },
  };
}

export function buildStatusHumanLabelMap(
  execCopy: ReturnType<typeof resolveDictionaryForFlag>["processVsmExecutionUi"]["execution"],
  iteration: number,
): Record<InteractiveProcessDrawerStatus, string> {
  return {
    RUNNING: execCopy.statusRunning,
    WAITING_EXTERNAL_GATE: execCopy.statusWaitingExternal,
    WAITING_SUBSTEP_HITL: execCopy.statusWaitingSubstepHitl,
    WAITING_WRITE_PREVIEW: execCopy.statusWaitingWritePreview,
    WAITING_FINAL_ANCHOR: execCopy.statusWaitingFinalAnchor,
    COMPLETED_APPROVED: execCopy.statusCompletedApproved,
    RETURN_LOOP_TRIGGERED: formatI18nTemplate(execCopy.statusReturnLoopTemplate, { iteration }),
    SLA_SUSPENDED: execCopy.statusSlaSuspended,
    FAILED_GATES: execCopy.statusFailedGates,
  };
}

export function buildFallbackFocusWorkflow(runId: string, defaultTitle: string) {
  return {
    id: runId,
    slug: runId,
    title: defaultTitle,
    pack_id: "orcia-pack-custom",
    vsm_step_num: null,
    version: "1.0.0",
    status: "published" as const,
    orchestration_type: "deterministic_dbos" as const,
    reflexive_objective: null,
    execution_mode: "native_orcia" as const,
    agent_ref: "@assistant",
    skills_refs: [],
    knowledge_base_refs: [],
    triggers: [],
    contract: { inputs: [], outputs: [], exit_criteria: [] },
    sub_steps: [],
    controls: { deterministic_gates: [], probabilistic_evaluations: [] },
    guardrails: [],
  };
}
