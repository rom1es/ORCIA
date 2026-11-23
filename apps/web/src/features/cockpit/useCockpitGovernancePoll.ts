import {
  createOrciaApiClient,
  type RunBlackboardStateResponse,
  type WorkflowAsCodeDefinitionSchemaItem,
} from "@orcia/api-client";
import type { ControlCenterWorkspaceGovItem } from "@orcia/ui";
import { useEffect, useState } from "react";
import { derivePendingGovernanceFromBlackboard } from "./cockpitGovernanceHelpers";

const TERMINAL_RUN_STATUSES = new Set([
  "COMPLETED",
  "FAILED",
  "ROLLED_BACK",
  "KILL_SWITCH_STOPPED",
]);

export interface PendingGovernanceTarget {
  readonly runId: string;
  readonly workflow: WorkflowAsCodeDefinitionSchemaItem | null;
  readonly initialBlackboard: RunBlackboardStateResponse;
}

export interface ChallengeRunTarget {
  readonly runId: string;
  readonly hasStaleWarning: boolean;
}

export function useCockpitGovernancePoll(params: {
  readonly activeScopeId: string;
  readonly activeScopeLevel: string | undefined;
  readonly availableWorkspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly isAuthenticated: boolean;
  readonly isHydrating: boolean;
  readonly runRefreshSignal: number;
}) {
  const {
    activeScopeId,
    activeScopeLevel,
    availableWorkspaces,
    isAuthenticated,
    isHydrating,
    runRefreshSignal,
  } = params;
  const [pendingGovernance, setPendingGovernance] =
    useState<PendingGovernanceTarget | null>(null);
  const [challengeTarget, setChallengeTarget] = useState<ChallengeRunTarget | null>(null);

  useEffect(() => {
    if (isHydrating || !isAuthenticated) {
      setPendingGovernance(null);
      setChallengeTarget(null);
      return;
    }
    let cancelled = false;
    const apiClient = createOrciaApiClient({ baseUrl: "" });
    void apiClient
      .getOrchestrationState()
      .then(async (state) => {
        if (cancelled) return;
        const serverRuns = state.runs ?? [];
        const scopedServerRuns =
          activeScopeLevel === "WORKSPACE"
            ? serverRuns.filter((r) => r.workspace_id === activeScopeId)
            : activeScopeLevel === "TEAM"
              ? serverRuns.filter((r) =>
                  availableWorkspaces.some((ws) => ws.workspaceId === r.workspace_id),
                )
              : serverRuns;
        const activeRuns = scopedServerRuns.filter(
          (r) => !TERMINAL_RUN_STATUSES.has(r.status),
        );
        if (activeRuns.length === 0) {
          setPendingGovernance(null);
          setChallengeTarget(null);
          return;
        }
        const candidates = [...activeRuns].reverse();
        const checked = await Promise.all(
          candidates.map(async (run) => {
            try {
              const bb = await apiClient.getRunBlackboardState(run.id);
              const wf = (state.workflows ?? []).find((w) => w.uri === run.workflow_uri) ?? null;
              const derived = derivePendingGovernanceFromBlackboard(bb, wf);
              const hasSignedAnchor = (bb.human_anchors?.length ?? 0) > 0;
              return {
                pending: derived.hasPendingAction
                  ? { runId: run.id, workflow: wf, initialBlackboard: bb }
                  : null,
                challenge:
                  hasSignedAnchor || derived.hasStaleWarning
                    ? { runId: run.id, hasStaleWarning: derived.hasStaleWarning }
                    : null,
              };
            } catch (err: unknown) {
              console.warn("[orcia/cockpit] failed to inspect run blackboard:", err);
              return { pending: null, challenge: null };
            }
          }),
        );
        if (cancelled) return;
        setPendingGovernance(checked.find((item) => item.pending !== null)?.pending ?? null);
        setChallengeTarget(checked.find((item) => item.challenge !== null)?.challenge ?? null);
      })
      .catch((err: unknown) => {
        console.warn("[orcia/cockpit] failed to check orchestration state:", err);
        if (!cancelled) {
          setPendingGovernance(null);
          setChallengeTarget(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [
    activeScopeId,
    activeScopeLevel,
    availableWorkspaces,
    isAuthenticated,
    isHydrating,
    runRefreshSignal,
  ]);

  return { pendingGovernance, challengeTarget };
}
