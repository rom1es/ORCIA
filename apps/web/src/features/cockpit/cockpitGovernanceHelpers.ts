import type {
  ArbitrationTieBreakOptionView,
  UiTieBreakPolicy,
} from "@orcia/ui";
import type {
  RunBlackboardStateResponse,
  WorkflowAsCodeDefinitionSchemaItem,
} from "@orcia/api-client";

export interface PendingAnchorRequirement {
  readonly stepKey: string;
  readonly sectionKey: string;
  readonly sectionTitle: string;
}

export interface PendingArbitrationState {
  readonly arbitrationId: string;
  readonly stepKey: string;
  readonly questionTitle: string;
  readonly contextSummary: string;
  readonly tieBreakPolicy: UiTieBreakPolicy;
  readonly options: ArbitrationTieBreakOptionView[];
}

export interface DerivedGovernanceState {
  readonly runId: string;
  readonly stepStatus: string;
  readonly pendingAnchor: PendingAnchorRequirement | null;
  readonly pendingArbitration: PendingArbitrationState | null;
  readonly hasPendingAction: boolean;
  readonly committedSnapshotId: string | null;
  readonly hasStaleWarning: boolean;
}

export function formatStepStatusLabel(status: string, isFr: boolean): string {
  switch (status.toUpperCase()) {
    case "PENDING":
      return isFr ? "En attente" : "Pending";
    case "RUNNING":
      return isFr ? "En cours" : "Running";
    case "COMMITTED":
    case "COMPLETED":
      return isFr ? "Validé" : "Completed";
    case "STALE_NEEDS_REVIEW":
      return isFr ? "À revalider" : "Needs review";
    case "WAITING_FOR_HUMAN_ANCHOR":
      return isFr ? "Ancrage humain requis" : "Human anchor required";
    case "WAITING_FOR_HUMAN_ARBITRATION":
    case "PAUSED_ARBITRATION":
      return isFr ? "Arbitrage requis" : "Arbitration required";
    case "PAUSED_HUMAN_GATE":
      return isFr ? "Validation humaine requise" : "Human review required";
    default:
      return status;
  }
}

export function formatStepKeyLabel(stepKey: string, isFr: boolean): string {
  const mapFr: Record<string, string> = {
    "frame-architecture-intent": "Cadrage de l'intention d'architecture",
    "delegate-remediation-subworkflow": "Sous-processus de correction",
    "post-deploy-verification": "Vérification post-déploiement",
    "step-architecture-gate": "Validation d'architecture",
    "inbox-review-step": "Relecture en boîte de réception",
  };
  const mapEn: Record<string, string> = {
    "frame-architecture-intent": "Architecture intent framing",
    "delegate-remediation-subworkflow": "Remediation sub-process",
    "post-deploy-verification": "Post-deployment verification",
    "step-architecture-gate": "Architecture review gate",
    "inbox-review-step": "Inbox review step",
  };
  const dict = isFr ? mapFr : mapEn;
  if (dict[stepKey]) return dict[stepKey];
  return stepKey
    .replace(/[-_]+/g, " ")
    .replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function mapRawArbitrationOptions(rawOptions: unknown): ArbitrationTieBreakOptionView[] {
  if (!Array.isArray(rawOptions)) {
    return [];
  }
  const out: ArbitrationTieBreakOptionView[] = [];
  for (const item of rawOptions) {
    if (!item || typeof item !== "object") continue;
    const rec = item as Record<string, unknown>;
    const optionKey = typeof rec.option_key === "string" ? rec.option_key.trim() : "";
    const title = typeof rec.title === "string" ? rec.title.trim() : "";
    if (!optionKey || !title) continue;
    out.push({
      optionKey,
      title,
      pros: Array.isArray(rec.pros) ? rec.pros.map(String) : [],
      cons: Array.isArray(rec.cons) ? rec.cons.map(String) : [],
      siImpact: typeof rec.si_impact === "string" ? rec.si_impact : "",
      finopsImpact: typeof rec.finops_impact === "string" ? rec.finops_impact : "",
      recommended: Boolean(rec.recommended),
    });
  }
  return out;
}

function resolveTieBreakPolicy(raw: unknown): UiTieBreakPolicy {
  if (
    raw === "ONTOLOGY_AXIOM_FIRST" ||
    raw === "DEFER_AND_CONTINUE_WITH_ASSUMPTION" ||
    raw === "PAUSE_AND_ESCALATE"
  ) {
    return raw;
  }
  return "PAUSE_AND_ESCALATE";
}

export function derivePendingGovernanceFromBlackboard(
  bb: RunBlackboardStateResponse,
  workflow?: WorkflowAsCodeDefinitionSchemaItem | null,
): DerivedGovernanceState {
  const stepExecs = bb.step_executions ?? [];
  const humanAnchors = bb.human_anchors ?? [];

  const anchorCandidates: Array<{
    stepKey: string;
    title: string;
    templateKey: string | null;
  }> = [];
  const seenSteps = new Set<string>();

  for (const wfStep of workflow?.steps ?? []) {
    if (wfStep.human_authored_required && !seenSteps.has(wfStep.step_key)) {
      seenSteps.add(wfStep.step_key);
      anchorCandidates.push({
        stepKey: wfStep.step_key,
        title: wfStep.title,
        templateKey: wfStep.template_key ?? null,
      });
    }
  }
  for (const exec of stepExecs) {
    if (exec.status === "WAITING_FOR_HUMAN_ANCHOR" && !seenSteps.has(exec.step_key)) {
      seenSteps.add(exec.step_key);
      anchorCandidates.push({
        stepKey: exec.step_key,
        title: exec.step_key,
        templateKey: null,
      });
    }
  }

  let pendingAnchor: PendingAnchorRequirement | null = null;
  for (const candidate of anchorCandidates) {
    const exec = stepExecs.find((s) => s.step_key === candidate.stepKey);
    if (exec && exec.status === "COMMITTED") {
      continue;
    }
    const signedInAnchors = humanAnchors.some(
      (a) => a.step_key === candidate.stepKey && Boolean(a.content_sha256),
    );
    const draftAnchors = (exec?.draft_artifact?.human_anchors ?? {}) as Record<
      string,
      { content_sha256?: string }
    >;
    const signedInDraft = Object.values(draftAnchors).some((entry) =>
      Boolean(entry?.content_sha256),
    );
    if (!signedInAnchors && !signedInDraft) {
      const sectionKey =
        candidate.templateKey === "tpl-architecture-decision-record" ||
        candidate.stepKey === "frame-architecture-intent"
          ? "human_architecture_intent"
          : "primary-anchor";
      pendingAnchor = {
        stepKey: candidate.stepKey,
        sectionKey,
        sectionTitle: candidate.title,
      };
      break;
    }
  }

  let pendingArbitration: PendingArbitrationState | null = null;
  const serverArb = (bb.pending_arbitrations ?? []).find(
    (a) => a.status === "PENDING" && (a.options_matrix?.length ?? 0) >= 2,
  );
  if (serverArb) {
    const opts = mapRawArbitrationOptions(serverArb.options_matrix);
    if (opts.length >= 2) {
      pendingArbitration = {
        arbitrationId: serverArb.id,
        stepKey: serverArb.step_key,
        questionTitle: serverArb.question_title,
        contextSummary: serverArb.context_summary,
        tieBreakPolicy: resolveTieBreakPolicy(serverArb.tie_break_policy),
        options: opts,
      };
    }
  } else {
    const waitingStep = stepExecs.find((s) => s.status === "WAITING_FOR_HUMAN_ARBITRATION");
    if (waitingStep) {
      const draft = (waitingStep.draft_artifact ?? {}) as Record<string, unknown>;
      const arbId =
        typeof draft.pending_arbitration_id === "string" ? draft.pending_arbitration_id : "";
      const opts = mapRawArbitrationOptions(draft.options_matrix);
      if (arbId && opts.length >= 2 && !draft.arbitration_resolution) {
        pendingArbitration = {
          arbitrationId: arbId,
          stepKey: waitingStep.step_key,
          questionTitle:
            typeof draft.arbitration_question_title === "string"
              ? draft.arbitration_question_title
              : waitingStep.step_key,
          contextSummary:
            typeof draft.arbitration_context_summary === "string"
              ? draft.arbitration_context_summary
              : "",
          tieBreakPolicy: resolveTieBreakPolicy(draft.arbitration_tie_break_policy),
          options: opts,
        };
      }
    }
  }

  const firstSnap = (bb.active_snapshots ?? [])[0];
  const anchorExec = pendingAnchor
    ? stepExecs.find((s) => s.step_key === pendingAnchor.stepKey)
    : undefined;
  const stepStatus = pendingArbitration
    ? "WAITING_FOR_HUMAN_ARBITRATION"
    : pendingAnchor
      ? (anchorExec?.status ?? "WAITING_FOR_HUMAN_ANCHOR")
      : (stepExecs[0]?.status ?? bb.run_status ?? "PENDING");
  const hasStaleWarning =
    stepExecs.some((s) => (s.status as string) === "STALE_NEEDS_REVIEW") ||
    (bb.active_snapshots ?? []).some((s) => (s.superseded_snapshot_ids?.length ?? 0) > 0);

  return {
    runId: bb.run_id,
    stepStatus,
    pendingAnchor,
    pendingArbitration,
    hasPendingAction: pendingAnchor !== null || pendingArbitration !== null,
    committedSnapshotId: firstSnap?.id ?? stepExecs[0]?.committed_snapshot_id ?? null,
    hasStaleWarning,
  };
}
