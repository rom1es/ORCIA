import type { SupportedWebLocale } from "../../../i18n";
import {
  extractLocalizedApiError,
  resolveLocalizedClientError,
} from "../../../lib/formatRfc9457ErrorToBanner";
import type { DeterministicSubStepItem } from "../processStudioV2Data";
import { createProcessesApiClient } from "../studio/studioLabelsAndMappers";
import {
  buildSubStepAdvanceMarkdown,
  mapBackendRunStatusToDrawerStatus,
  simpleHashHex,
  type InteractiveProcessDrawerStatus,
} from "./interactiveRunFormatters";

export async function executeApproveSubStep(params: {
  readonly locale: SupportedWebLocale;
  readonly runId: string;
  readonly actorSlug: string;
  readonly hasPersistedServerRun: boolean;
  readonly workflowTitle: string;
  readonly enabledSubSteps: readonly DeterministicSubStepItem[];
  readonly currentSubIndex: number;
  readonly currentSubStep: DeterministicSubStepItem | undefined;
  readonly status: InteractiveProcessDrawerStatus;
  readonly artifactSha256: string;
  readonly writePreviewPrompt: string;
  readonly stepApprovedAdvanceTpl: string;
  readonly readyForFinalSignoff: string;
  readonly setSignedTokenPreview: (tok: string) => void;
  readonly setCurrentSubIndex: (idx: number) => void;
  readonly setArtifactMarkdown: (md: string) => void;
  readonly setArtifactSha256: (sha: string) => void;
  readonly setStatus: (s: InteractiveProcessDrawerStatus) => void;
  readonly setHasError: (err: boolean) => void;
  readonly setStatusBanner: (msg: string | null) => void;
  readonly onRunStateChanged?: () => void;
}): Promise<void> {
  if (params.currentSubStep?.write_preview_required && params.status !== "WAITING_WRITE_PREVIEW") {
    params.setStatus("WAITING_WRITE_PREVIEW");
    params.setStatusBanner(params.writePreviewPrompt);
    return;
  }
  if (params.status === "WAITING_WRITE_PREVIEW") {
    params.setSignedTokenPreview(`sat_${params.artifactSha256.slice(0, 16)}_hmac_ok`);
  }
  if (params.hasPersistedServerRun) {
    try {
      const updated = await createProcessesApiClient(params.locale).sendWorkflowV2HitlSignal(
        params.runId,
        { action: "APPROVE", actor_id: params.actorSlug },
      );
      if (updated?.run) {
        const mappedStatus = mapBackendRunStatusToDrawerStatus(
          updated.run.status,
          "WAITING_FINAL_ANCHOR",
        );
        params.setStatus(mappedStatus);
        if (typeof updated.run.current_sub_step_index === "number") {
          params.setCurrentSubIndex(updated.run.current_sub_step_index);
        }
        if (mappedStatus === "WAITING_FINAL_ANCHOR") {
          params.setStatusBanner(params.readyForFinalSignoff);
        } else {
          const nextSub = params.enabledSubSteps[updated.run.current_sub_step_index ?? 0];
          params.setStatusBanner(
            params.stepApprovedAdvanceTpl
              .replace("{step}", params.currentSubStep?.short_label ?? "")
              .replace("{nextStep}", nextSub?.short_label ?? ""),
          );
        }
        params.onRunStateChanged?.();
        return;
      }
    } catch (err: unknown) {
      const extracted = extractLocalizedApiError(
        err,
        params.locale,
        "ERR_CLIENT_PROCESS_DELIVERABLE_APPROVE",
      );
      params.setHasError(true);
      params.setStatusBanner(extracted.errorMessage);
      return;
    }
  }
  if (params.currentSubIndex + 1 < params.enabledSubSteps.length) {
    const nextIdx = params.currentSubIndex + 1;
    const nextSub = params.enabledSubSteps[nextIdx];
    params.setCurrentSubIndex(nextIdx);
    const nextMd = buildSubStepAdvanceMarkdown(
      params.workflowTitle,
      nextSub?.name ?? "",
      nextSub?.output_description ?? "",
      params.locale,
    );
    params.setArtifactMarkdown(nextMd);
    params.setArtifactSha256(simpleHashHex(nextMd));
    params.setStatus(nextSub?.write_preview_required ? "WAITING_WRITE_PREVIEW" : "WAITING_SUBSTEP_HITL");
    params.setStatusBanner(
      params.stepApprovedAdvanceTpl
        .replace("{step}", params.currentSubStep?.short_label ?? "")
        .replace("{nextStep}", nextSub?.short_label ?? ""),
    );
  } else {
    params.setStatus("WAITING_FINAL_ANCHOR");
    params.setStatusBanner(params.readyForFinalSignoff);
  }
}

export async function executeAcceptAndSignHitl(params: {
  readonly locale: SupportedWebLocale;
  readonly runId: string;
  readonly actorSlug: string;
  readonly startRunPromise: Promise<string | null> | null;
  readonly hasPersistedServerRun: boolean;
  readonly deliveredBanner: string;
  readonly setStatus: (s: InteractiveProcessDrawerStatus) => void;
  readonly setHasError: (err: boolean) => void;
  readonly setStatusBanner: (msg: string | null) => void;
  readonly onRunStateChanged?: () => void;
}): Promise<void> {
  try {
    let resolvedRunId = params.runId;
    if (params.startRunPromise) {
      const awaitedRunId = await params.startRunPromise;
      if (awaitedRunId) resolvedRunId = awaitedRunId;
    }
    if (params.hasPersistedServerRun) {
      const updated = await createProcessesApiClient(params.locale).sendWorkflowV2HitlSignal(
        resolvedRunId,
        { action: "APPROVE", actor_id: params.actorSlug },
      );
      params.setStatus(
        mapBackendRunStatusToDrawerStatus(updated?.run?.status, "COMPLETED_APPROVED"),
      );
      params.onRunStateChanged?.();
    } else {
      params.setStatus("COMPLETED_APPROVED");
    }
    params.setStatusBanner(params.deliveredBanner);
  } catch (err: unknown) {
    const extracted = extractLocalizedApiError(
      err,
      params.locale,
      "ERR_CLIENT_PROCESS_DELIVERABLE_APPROVE",
    );
    params.setHasError(true);
    params.setStatusBanner(
      resolveLocalizedClientError("ERR_CLIENT_PROCESS_DELIVERABLE_APPROVE", params.locale, {
        detail: extracted.errorMessage,
      }),
    );
  }
}

export async function executeRejectAndLoopHitl(params: {
  readonly locale: SupportedWebLocale;
  readonly runId: string;
  readonly actorSlug: string;
  readonly iteration: number;
  readonly targetStepNum: string;
  readonly correctionRemarks: string;
  readonly artifactMarkdown: string;
  readonly loopMarkdownTpl: string;
  readonly loopBannerTpl: string;
  readonly hasPersistedServerRun: boolean;
  readonly setIteration: (iter: number) => void;
  readonly setReentryMode: (mode: "initial" | "corrections") => void;
  readonly setCurrentSubIndex: (idx: number) => void;
  readonly setStatus: (s: InteractiveProcessDrawerStatus) => void;
  readonly setArtifactMarkdown: (md: string) => void;
  readonly setArtifactSha256: (sha: string) => void;
  readonly setHasError: (err: boolean) => void;
  readonly setStatusBanner: (msg: string | null) => void;
  readonly onRunStateChanged?: () => void;
}): Promise<void> {
  const nextIter = params.iteration + 1;
  params.setIteration(nextIter);
  params.setReentryMode("corrections");
  params.setCurrentSubIndex(0);
  params.setStatus("RETURN_LOOP_TRIGGERED");
  const loopSection = params.loopMarkdownTpl
    .replace("{cycle}", String(nextIter))
    .replace("{step}", params.targetStepNum)
    .replace("{remarks}", params.correctionRemarks);
  const revisedMd = `${params.artifactMarkdown}\n\n${loopSection}`;
  params.setArtifactMarkdown(revisedMd);
  params.setArtifactSha256(simpleHashHex(revisedMd));
  params.setStatusBanner(
    params.loopBannerTpl
      .replace("{step}", params.targetStepNum)
      .replace("{cycle}", String(nextIter)),
  );
  if (!params.hasPersistedServerRun) return;
  try {
    await createProcessesApiClient(params.locale).sendWorkflowV2HitlSignal(params.runId, {
      action: "REJECT_AND_LOOP",
      actor_id: params.actorSlug,
      target_step_num: params.targetStepNum,
      correction_remarks: params.correctionRemarks,
    });
    params.onRunStateChanged?.();
  } catch (err: unknown) {
    const extracted = extractLocalizedApiError(
      err,
      params.locale,
      "ERR_CLIENT_PROCESS_DELIVERABLE_APPROVE",
    );
    params.setHasError(true);
    params.setStatusBanner(extracted.errorMessage);
  }
}

export async function executeSuspendSlaHitl(params: {
  readonly locale: SupportedWebLocale;
  readonly runId: string;
  readonly actorSlug: string;
  readonly hasPersistedServerRun: boolean;
  readonly setHasError: (err: boolean) => void;
  readonly setStatusBanner: (msg: string | null) => void;
  readonly onRunStateChanged?: () => void;
}): Promise<void> {
  if (!params.hasPersistedServerRun) return;
  try {
    await createProcessesApiClient(params.locale).sendWorkflowV2HitlSignal(params.runId, {
      action: "SUSPEND_SLA",
      actor_id: params.actorSlug,
    });
    params.onRunStateChanged?.();
  } catch (err: unknown) {
    const extracted = extractLocalizedApiError(
      err,
      params.locale,
      "ERR_CLIENT_PROCESS_DELIVERABLE_APPROVE",
    );
    params.setHasError(true);
    params.setStatusBanner(extracted.errorMessage);
  }
}
