import type {
  HitlSignalRequest,
  ProcessPendingRunItemResponse,
  WorkflowV2RunResponse,
} from "@orcia/api-client";
import type { UiAgentTraceEventItem } from "@orcia/ui";
import type { SupportedWebLocale } from "../../../i18n";
import { mapApiTraceEventToUi } from "../../shared/reflexiveTraceMappers";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";
import { createProcessesApiClient } from "../studio/studioLabelsAndMappers";
import {
  mapBackendRunStatusToDrawerStatus,
  simpleHashHex,
  type InteractiveProcessDrawerStatus,
} from "./interactiveRunFormatters";

type RunState = WorkflowV2RunResponse["run"];

export interface SyncRunFromBackendCallbacks {
  readonly actorSlug: string;
  readonly fallbackStatus: InteractiveProcessDrawerStatus;
  readonly refreshSnapshot: (execId: string) => Promise<unknown>;
  readonly setRunId: (id: string) => void;
  readonly setStatus: (status: InteractiveProcessDrawerStatus) => void;
  readonly setCurrentSubIndex: (idx: number) => void;
  readonly setIteration: (iter: number) => void;
  readonly setReentryMode: (mode: "initial" | "corrections") => void;
  readonly setInlineRunTraceEvents: (events: readonly UiAgentTraceEventItem[]) => void;
  readonly setArtifactMarkdown: (md: string) => void;
  readonly setArtifactSha256: (sha: string) => void;
  readonly markServerRunPersisted: () => void;
}

export async function applyBackendRunToController(
  run: RunState,
  cb: SyncRunFromBackendCallbacks,
  isCancelled: () => boolean,
): Promise<string> {
  const resolvedRunId = run.run_id;
  cb.setRunId(resolvedRunId);
  cb.markServerRunPersisted();
  cb.setStatus(mapBackendRunStatusToDrawerStatus(run.status, cb.fallbackStatus));
  if (typeof run.current_sub_step_index === "number") {
    cb.setCurrentSubIndex(run.current_sub_step_index);
  }
  if (typeof run.iteration === "number") {
    cb.setIteration(run.iteration);
  }
  cb.setReentryMode(run.reentry_mode === "corrections" ? "corrections" : "initial");

  if (run.reflexive_execution_id) {
    await cb.refreshSnapshot(run.reflexive_execution_id);
  } else if (Array.isArray(run.trace_events) && run.trace_events.length > 0 && !isCancelled()) {
    cb.setInlineRunTraceEvents(
      run.trace_events.map((ev) => mapApiTraceEventToUi(ev, cb.actorSlug)),
    );
  }

  if (!isCancelled() && run.final_artifact_pointer?.sha256) {
    cb.setArtifactSha256(run.final_artifact_pointer.sha256);
  }
  return resolvedRunId;
}

export async function hydrateOrStartWorkflowRun(params: {
  readonly locale: SupportedWebLocale;
  readonly workflow: WorkflowDefinitionV2Item;
  readonly workspaceId?: string;
  readonly initialPendingRun?: ProcessPendingRunItemResponse | null;
  readonly callbacks: SyncRunFromBackendCallbacks;
  readonly isCancelled: () => boolean;
}): Promise<string | null> {
  const { locale, workflow, workspaceId, initialPendingRun, callbacks, isCancelled } = params;
  const apiClient = createProcessesApiClient(locale);

  if (initialPendingRun) {
    if (initialPendingRun.source === "workflow_v2") {
      const res = await apiClient.getWorkflowV2Run(initialPendingRun.run_id);
      if (isCancelled() || !res?.run) return null;
      return applyBackendRunToController(res.run, callbacks, isCancelled);
    }

    callbacks.setRunId(initialPendingRun.run_id);
    callbacks.setStatus(
      mapBackendRunStatusToDrawerStatus(initialPendingRun.status, callbacks.fallbackStatus),
    );
    if (initialPendingRun.reflexive_execution_id) {
      await callbacks.refreshSnapshot(initialPendingRun.reflexive_execution_id);
    }
    return initialPendingRun.run_id;
  }

  const res = await apiClient.startWorkflowV2Run(workflow.id, {
    inputs: { objective: workflow.title },
    iteration: 1,
    reentry_mode: "initial",
    ...(workspaceId ? { workspace_id: workspaceId } : {}),
  });
  if (isCancelled() || !res?.run) return null;
  return applyBackendRunToController(res.run, callbacks, isCancelled);
}

export async function sendWorkflowHitlSignalAndSync(params: {
  readonly locale: SupportedWebLocale;
  readonly runId: string;
  readonly payload: HitlSignalRequest;
  readonly callbacks: SyncRunFromBackendCallbacks;
  readonly onRunStateChanged?: () => void;
}): Promise<RunState | null> {
  const res = await createProcessesApiClient(params.locale).sendWorkflowV2HitlSignal(
    params.runId,
    params.payload,
  );
  if (res?.run) {
    await applyBackendRunToController(res.run, params.callbacks, () => false);
    params.onRunStateChanged?.();
    return res.run;
  }
  return null;
}

export function applySnapshotContentUpdate(
  finalMarkdown: string | null | undefined,
  artifactSha256: string | null | undefined,
  setArtifactMarkdown: (md: string) => void,
  setArtifactSha256: (sha: string) => void,
): void {
  if (finalMarkdown) {
    setArtifactMarkdown(finalMarkdown);
    setArtifactSha256(artifactSha256 || simpleHashHex(finalMarkdown));
  }
}
