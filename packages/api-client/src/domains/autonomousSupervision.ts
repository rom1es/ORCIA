import type {
  AutonomousRunSupervisionItemSchema,
  AutonomousRunsListResponse,
  EmergencyStopRequest,
  EmergencyStopResponse,
  InvalidateAndRestoreRequest,
  InvalidateAndRestoreResponse,
  PostHocReviewRequest,
  PostHocReviewResponse,
} from "../generated/autonomous_supervision";
import type { createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export type {
  AutonomousRunSupervisionItemSchema,
  AutonomousRunsListResponse,
  EmergencyStopRequest,
  EmergencyStopResponse,
  InvalidateAndRestoreRequest,
  InvalidateAndRestoreResponse,
  PostHocReviewRequest,
  PostHocReviewResponse,
};

export function createAutonomousSupervisionDomainClient(requestJson: RequestJsonFn) {
  return {
    listAutonomousRuns(params?: { scopeId?: string | null }): Promise<AutonomousRunsListResponse> {
      const qs = params?.scopeId ? `?scope_id=${encodeURIComponent(params.scopeId)}` : "";
      return requestJson<AutonomousRunsListResponse>(`/api/v1/autonomous-runs${qs}`);
    },

    listWorkspaceAutonomousRuns(workspaceId: string): Promise<AutonomousRunsListResponse> {
      const ws = encodeURIComponent(workspaceId);
      return requestJson<AutonomousRunsListResponse>(
        `/api/v1/workspaces/${ws}/autonomous-runs`,
      );
    },

    emergencyStopAutonomousRun(
      runId: string,
      payload?: EmergencyStopRequest,
    ): Promise<EmergencyStopResponse> {
      const id = encodeURIComponent(runId);
      return requestJson<EmergencyStopResponse>(
        `/api/v1/runs/${id}/emergency-stop`,
        "POST",
        payload ?? { reason: "", suspend_trigger: true },
      );
    },

    invalidateAndRestoreAutonomousRun(
      runId: string,
      payload?: InvalidateAndRestoreRequest,
    ): Promise<InvalidateAndRestoreResponse> {
      const id = encodeURIComponent(runId);
      return requestJson<InvalidateAndRestoreResponse>(
        `/api/v1/runs/${id}/invalidate-and-restore`,
        "POST",
        payload ?? { comment: "" },
      );
    },

    reviewPostHocAutonomousRun(
      runId: string,
      payload: PostHocReviewRequest,
    ): Promise<PostHocReviewResponse> {
      const id = encodeURIComponent(runId);
      return requestJson<PostHocReviewResponse>(
        `/api/v1/runs/${id}/post-hoc-review`,
        "POST",
        payload,
      );
    },
  };
}
