import { buildPersonaQuery, type createRequestJson } from "../helpers";
import type {
  AcquireResourceLeasesRequest,
  AcquireResourceLeasesResponse,
  AssistantSaveAndLaunchRequest,
  AssistantSaveAndLaunchResponse,
  ClaimTaskRequest,
  ClaimTaskResponse,
  CommandPaletteSearchResponse,
  CommitStagedJiraActionRequest,
  CommitStagedJiraActionResponse,
  ControlCenterOverviewResponse,
  HumanGateChunkDecideRequest,
  HumanGateChunkDecideResponse,
  HumanGateEvaluateRequest,
  HumanGateEvaluateResponse,
  HumanGateEvaluationListResponse,
  HumanGateFinalizeRequest,
  HumanGateFinalizeResponse,
  InboxNotificationListResponse,
  JiraJqlSearchRequest,
  JiraJqlSearchResponse,
  McpToolCallRequest,
  McpToolCallResponse,
  McpToolsListResponse,
  ReleaseTaskClaimRequest,
  RunMutationGuardCheckRequest,
  RunMutationGuardCheckResponse,
  StagedJiraActionListResponse,
  StageJiraActionRequest,
  StageJiraActionResponse,
  UpdateWorkspaceLifecycleRequest,
  ValidateFencedWriteRequest,
  ValidateFencedWriteResponse,
  WorkspaceGovernanceItemResponse,
} from "./_epics1To7Types";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export function createEpics4To7TailOperations(requestJson: RequestJsonFn) {
  return {
    assistantSaveAndLaunchWorkflow(
      payload: AssistantSaveAndLaunchRequest,
      personaKey?: string,
    ): Promise<AssistantSaveAndLaunchResponse> {
      return requestJson<AssistantSaveAndLaunchResponse>(
        `/api/v1/assistant/workflows/save-and-launch${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    listHumanGateEvaluations(
      workspaceId?: string,
      personaKey?: string,
    ): Promise<HumanGateEvaluationListResponse> {
      const params = new URLSearchParams();
      if (workspaceId && workspaceId.trim()) {
        params.set("workspace_id", workspaceId.trim());
      }
      if (personaKey && personaKey.trim()) {
        params.set("persona_key", personaKey.trim());
      }
      const qs = params.toString();
      return requestJson<HumanGateEvaluationListResponse>(
        `/api/v1/gates/human/evaluations${qs ? `?${qs}` : ""}`,
      );
    },
    evaluateHumanGate(
      payload: HumanGateEvaluateRequest,
      personaKey?: string,
    ): Promise<HumanGateEvaluateResponse> {
      return requestJson<HumanGateEvaluateResponse>(
        `/api/v1/gates/human/evaluate${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    inspectHumanGateHypotheses(
      gateEvaluationId: string,
      personaKey?: string,
    ): Promise<HumanGateEvaluateResponse> {
      return requestJson<HumanGateEvaluateResponse>(
        `/api/v1/gates/human/${encodeURIComponent(gateEvaluationId)}/inspect-hypotheses${buildPersonaQuery(personaKey)}`,
        "POST",
      );
    },
    decideHumanGateChunk(
      gateEvaluationId: string,
      chunkKey: string,
      payload: HumanGateChunkDecideRequest,
      personaKey?: string,
    ): Promise<HumanGateChunkDecideResponse> {
      return requestJson<HumanGateChunkDecideResponse>(
        `/api/v1/gates/human/${encodeURIComponent(gateEvaluationId)}/chunks/${encodeURIComponent(chunkKey)}/decide${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    finalizeHumanGate(
      gateEvaluationId: string,
      payload: HumanGateFinalizeRequest,
      personaKey?: string,
    ): Promise<HumanGateFinalizeResponse> {
      return requestJson<HumanGateFinalizeResponse>(
        `/api/v1/gates/human/${encodeURIComponent(gateEvaluationId)}/finalize${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    searchWorkspaceJiraJql(
      payload: JiraJqlSearchRequest,
      personaKey?: string,
    ): Promise<JiraJqlSearchResponse> {
      return requestJson<JiraJqlSearchResponse>(
        `/api/v1/jira/jql/search${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    listStagedJiraActions(
      workspaceId?: string,
      personaKey?: string,
    ): Promise<StagedJiraActionListResponse> {
      const params = new URLSearchParams();
      if (workspaceId && workspaceId.trim()) {
        params.set("workspace_id", workspaceId.trim());
      }
      if (personaKey && personaKey.trim()) {
        params.set("persona_key", personaKey.trim());
      }
      const qs = params.toString();
      return requestJson<StagedJiraActionListResponse>(
        `/api/v1/jira/actions/staged${qs ? `?${qs}` : ""}`,
      );
    },
    stageJiraWorkflowAction(
      payload: StageJiraActionRequest,
      personaKey?: string,
    ): Promise<StageJiraActionResponse> {
      return requestJson<StageJiraActionResponse>(
        `/api/v1/jira/actions/stage${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    commitStagedJiraAction(
      payload: CommitStagedJiraActionRequest,
      personaKey?: string,
    ): Promise<CommitStagedJiraActionResponse> {
      return requestJson<CommitStagedJiraActionResponse>(
        `/api/v1/jira/actions/commit${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    listGovernedMcpTools(personaKey?: string): Promise<McpToolsListResponse> {
      return requestJson<McpToolsListResponse>(
        `/api/v1/mcp/tools${buildPersonaQuery(personaKey)}`,
      );
    },
    callGovernedMcpTool(
      payload: McpToolCallRequest,
      personaKey?: string,
    ): Promise<McpToolCallResponse> {
      return requestJson<McpToolCallResponse>(
        `/api/v1/mcp/call${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    listInboxNotifications(options?: {
      workspaceId?: string;
      scopeFilter?: "ALL" | "PERSONAL" | "TEAM";
      personaKey?: string;
    }): Promise<InboxNotificationListResponse> {
      const params = new URLSearchParams();
      if (options?.workspaceId) params.set("workspace_id", options.workspaceId);
      if (options?.scopeFilter) params.set("scope_filter", options.scopeFilter);
      if (options?.personaKey) params.set("persona_key", options.personaKey);
      const qs = params.toString();
      return requestJson<InboxNotificationListResponse>(
        `/api/v1/inbox/notifications${qs ? `?${qs}` : ""}`,
      );
    },
    claimTaskNotification(
      taskId: string,
      payload: ClaimTaskRequest,
      personaKey?: string,
    ): Promise<ClaimTaskResponse> {
      return requestJson<ClaimTaskResponse>(
        `/api/v1/tasks/${encodeURIComponent(taskId)}/claim${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    releaseTaskNotificationClaim(
      taskId: string,
      payload: ReleaseTaskClaimRequest,
      personaKey?: string,
    ): Promise<ClaimTaskResponse> {
      return requestJson<ClaimTaskResponse>(
        `/api/v1/tasks/${encodeURIComponent(taskId)}/release${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    claimStepExecution(
      runId: string,
      stepId: string,
      payload: ClaimTaskRequest,
      personaKey?: string,
    ): Promise<ClaimTaskResponse> {
      return requestJson<ClaimTaskResponse>(
        `/api/v1/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepId)}/claim${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    acquireResourceLeases(
      payload: AcquireResourceLeasesRequest,
      personaKey?: string,
    ): Promise<AcquireResourceLeasesResponse> {
      return requestJson<AcquireResourceLeasesResponse>(
        `/api/v1/resource-leases/acquire${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    executeFencedResourceWrite(
      payload: ValidateFencedWriteRequest,
      personaKey?: string,
    ): Promise<ValidateFencedWriteResponse> {
      return requestJson<ValidateFencedWriteResponse>(
        `/api/v1/resource-leases/fenced-write${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    getControlCenterOverview(options?: {
      scopeType?: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
      scopeId?: string;
      personaKey?: string;
    }): Promise<ControlCenterOverviewResponse> {
      const params = new URLSearchParams();
      if (options?.scopeType) params.set("scope_type", options.scopeType);
      if (options?.scopeId) params.set("scope_id", options.scopeId);
      if (options?.personaKey) params.set("persona_key", options.personaKey);
      const qs = params.toString();
      return requestJson<ControlCenterOverviewResponse>(
        `/api/v1/control-center/overview${qs ? `?${qs}` : ""}`,
      );
    },
    updateWorkspaceLifecycle(
      workspaceId: string,
      payload: UpdateWorkspaceLifecycleRequest,
      personaKey?: string,
    ): Promise<WorkspaceGovernanceItemResponse> {
      return requestJson<WorkspaceGovernanceItemResponse>(
        `/api/v1/control-center/workspaces/${encodeURIComponent(workspaceId)}/lifecycle${buildPersonaQuery(personaKey)}`,
        "PATCH",
        payload,
      );
    },
    checkRunStepMutationGuard(
      runId: string,
      stepId: string,
      payload: RunMutationGuardCheckRequest,
      personaKey?: string,
    ): Promise<RunMutationGuardCheckResponse> {
      return requestJson<RunMutationGuardCheckResponse>(
        `/api/v1/control-center/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepId)}/mutate-check${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    searchCommandPalette(
      query: string,
      personaKey?: string,
    ): Promise<CommandPaletteSearchResponse> {
      const params = new URLSearchParams({ q: query });
      if (personaKey) params.set("persona_key", personaKey);
      return requestJson<CommandPaletteSearchResponse>(
        `/api/v1/control-center/command-palette?${params.toString()}`,
      );
    },
  };
}
