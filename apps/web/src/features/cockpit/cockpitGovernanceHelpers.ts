import type { ArbitrationTieBreakOptionView } from "@orcia/ui";
import { formatCurrency } from "../../lib/formatters";

export const DEFAULT_WORKFLOW_URI = "orcia://workflows/claims-engineering-delivery";
export const DEFAULT_STEP_KEY = "frame-architecture-intent";
export const DEFAULT_SECTION_KEY = "human_architecture_intent";
export const DEFAULT_FALLBACK_WORKSPACE_ID = "0192c4e0-0000-7000-8000-000000000201";

export const DEFAULT_ARBITRATION_OPTIONS: ArbitrationTieBreakOptionView[] = [
  {
    optionKey: "OPT_A_SPOT_15M",
    title: "Option A — Taux Spot 15 min",
    pros: ["Compatible API partenaire v3", "Latence minimale"],
    cons: ["Fenêtre client 15 min"],
    siImpact: "1 microservice impacté",
    finopsImpact: `${formatCurrency(0.02, "fr")} / exécution`,
    recommended: true,
  },
  {
    optionKey: "OPT_B_LOCK_48H",
    title: "Option B — Taux Bloqué 48h",
    pros: ["Confort client 48h"],
    cons: ["Incompatible API v3"],
    siImpact: "3 systèmes centraux impactés",
    finopsImpact: `${formatCurrency(0.18, "fr")} / exécution`,
    recommended: false,
  },
];

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

export function formatOptionTitle(optionKey: string, isFr: boolean): string {
  const matched = DEFAULT_ARBITRATION_OPTIONS.find((opt) => opt.optionKey === optionKey);
  if (matched) return matched.title;
  if (optionKey === "OPT_A_SPOT_15M") {
    return isFr ? "Option A — Taux Spot 15 min" : "Option A — 15-min Spot Rate";
  }
  if (optionKey === "OPT_B_LOCK_48H") {
    return isFr ? "Option B — Taux Bloqué 48h" : "Option B — 48h Locked Rate";
  }
  return optionKey;
}

export interface HydratedGovernanceState {
  readonly runId: string;
  readonly stepStatus: string;
  readonly anchorText: string | null;
  readonly signedSha256: string | null;
  readonly pendingArbitrationId: string | null;
  readonly resolvedOptionKey: string | null;
  readonly resolvedJustification: string | null;
  readonly committedSnapshotId: string | null;
  readonly hasStaleWarning: boolean;
}

export function extractGovernanceStateFromBlackboard(bb: {
  readonly run_id: string;
  readonly step_executions: ReadonlyArray<{
    readonly step_key: string;
    readonly status: string;
    readonly committed_snapshot_id?: string | null;
    readonly draft_artifact?: Record<string, unknown> | null;
  }>;
  readonly active_snapshots: ReadonlyArray<{
    readonly id: string;
    readonly superseded_snapshot_ids?: ReadonlyArray<string>;
  }>;
}): HydratedGovernanceState {
  const step =
    bb.step_executions.find((s) => s.step_key === DEFAULT_STEP_KEY) ??
    bb.step_executions[0];
  const draft = (step?.draft_artifact ?? {}) as Record<string, unknown>;
  const anchors = (draft.human_anchors ?? {}) as Record<
    string,
    { content_text?: string; content_sha256?: string }
  >;
  const anchorEntry = anchors[DEFAULT_SECTION_KEY];
  const resolution = draft.arbitration_resolution as
    | { selected_option_key?: string; human_justification?: string | null }
    | undefined;
  const firstSnap = bb.active_snapshots[0];
  const hasStaleWarning =
    bb.step_executions.some((s) => s.status === "STALE_NEEDS_REVIEW") ||
    bb.active_snapshots.some((s) => (s.superseded_snapshot_ids?.length ?? 0) > 0);
  return {
    runId: bb.run_id,
    stepStatus: step?.status ?? "PENDING",
    anchorText: anchorEntry?.content_text ?? null,
    signedSha256: anchorEntry?.content_sha256 ?? null,
    pendingArbitrationId:
      typeof draft.pending_arbitration_id === "string"
        ? draft.pending_arbitration_id
        : null,
    resolvedOptionKey: resolution?.selected_option_key ?? null,
    resolvedJustification: resolution?.human_justification ?? null,
    committedSnapshotId: firstSnap?.id ?? step?.committed_snapshot_id ?? null,
    hasStaleWarning,
  };
}
