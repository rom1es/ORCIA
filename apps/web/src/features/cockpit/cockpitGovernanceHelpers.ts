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
