import type {
  BackgroundAuditRunRequest,
  BackgroundAuditRunResponse,
  HumanAnchorSignRequest,
  HumanAnchorSignResponse,
  HumanArbitrationCreateRequest,
  HumanArbitrationCreateResponse,
  HumanArbitrationResolveRequest,
  HumanArbitrationResolveResponse,
  RunBlackboardStateResponse,
  StepExecuteRequest,
  StepExecuteResponse,
  StepHumanResumeRequest,
  StepHydrateRequest,
  StepHydrateResponse,
} from "../generated/blackboard";
import type {
  ArtifactTemplateCompileRequest,
  ArtifactTemplateCompileResponse,
  OrchestrationSetupStateResponse,
  WorkflowManifestRegisterRequest,
  WorkflowManifestRegisterResponse,
  WorkflowManifestValidateRequest,
  WorkflowManifestValidateResponse,
  WorkflowRunInstantiateRequest,
  WorkflowRunInstantiateResponse,
} from "../generated/orchestration";
import type { components } from "../generated/schema";
import { buildPersonaQuery, type createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export type UpstreamChallengePreviewRequest =
  components["schemas"]["UpstreamChallengePreviewRequest"];
export type UpstreamChallengePreviewResponse =
  components["schemas"]["UpstreamChallengePreviewResponse"];
export type UpstreamChallengeSubmitRequest =
  components["schemas"]["UpstreamChallengeSubmitRequest"];
export type UpstreamChallengeSubmitResponse =
  components["schemas"]["UpstreamChallengeSubmitResponse"];
export type StepReplayRequest = components["schemas"]["StepReplayRequest"];
export type StepReplayResponse = components["schemas"]["StepReplayResponse"];

export type AssistantChatRequest = components["schemas"]["AssistantChatRequest"];
export type AssistantChatResponse = components["schemas"]["AssistantChatResponse"];
export type AssistantSaveAndLaunchRequest =
  components["schemas"]["AssistantSaveAndLaunchRequest"];
export type AssistantSaveAndLaunchResponse =
  components["schemas"]["AssistantSaveAndLaunchResponse"];

export type DeterministicGateEvaluateRequest =
  components["schemas"]["DeterministicGateEvaluateRequest"];
export type DeterministicGateEvaluateResponse =
  components["schemas"]["DeterministicGateEvaluateResponse"];
export type GateEvaluationsListResponse = components["schemas"]["GateEvaluationsListResponse"];
export type InitExistingProjectRequest = components["schemas"]["InitExistingProjectRequest"];
export type InitExistingProjectResponse = components["schemas"]["InitExistingProjectResponse"];
export type InitSkillRequest = components["schemas"]["InitSkillRequest"];
export type InitSkillResponse = components["schemas"]["InitSkillResponse"];
export type Tier2TddVerifyRequest = components["schemas"]["Tier2TddVerifyRequest"];
export type Tier2TddVerifyResponse = components["schemas"]["Tier2TddVerifyResponse"];
export type DeploymentRolesListResponse = components["schemas"]["DeploymentRolesListResponse"];
export type AgenticGateEvaluateRequest = components["schemas"]["AgenticGateEvaluateRequest"];
export type AgenticGateEvaluateResponse = components["schemas"]["AgenticGateEvaluateResponse"];

export type HumanGateEvaluateRequest = components["schemas"]["HumanGateEvaluateRequest"];
export type HumanGateEvaluateResponse = components["schemas"]["HumanGateEvaluateResponse"];
export type HumanGateEvaluationListResponse =
  components["schemas"]["HumanGateEvaluationListResponse"];
export type HumanGateEvaluationSchemaItem =
  components["schemas"]["HumanGateEvaluationSchemaItem"];
export type HumanGateChunkDecideRequest = components["schemas"]["HumanGateChunkDecideRequest"];
export type HumanGateChunkDecideResponse = components["schemas"]["HumanGateChunkDecideResponse"];
export type HumanGateFinalizeRequest = components["schemas"]["HumanGateFinalizeRequest"];
export type HumanGateFinalizeResponse = components["schemas"]["HumanGateFinalizeResponse"];

export type JiraJqlSearchRequest = components["schemas"]["JiraJqlSearchRequest"];
export type JiraJqlSearchResponse = components["schemas"]["JiraJqlSearchResponse"];
export type StageJiraActionRequest = components["schemas"]["StageJiraActionRequest"];
export type StageJiraActionResponse = components["schemas"]["StageJiraActionResponse"];
export type StagedJiraActionListResponse = components["schemas"]["StagedJiraActionListResponse"];
export type StagedJiraActionItemSchema = components["schemas"]["StagedJiraActionItemSchema"];
export type CommitStagedJiraActionRequest =
  components["schemas"]["CommitStagedJiraActionRequest"];
export type CommitStagedJiraActionResponse =
  components["schemas"]["CommitStagedJiraActionResponse"];
export type JiraIssueUpdatedWebhookRequest =
  components["schemas"]["JiraIssueUpdatedWebhookRequest"];
export type JiraIssueUpdatedWebhookResponse =
  components["schemas"]["JiraIssueUpdatedWebhookResponse"];
export type McpToolsListResponse = components["schemas"]["McpToolsListResponse"];
export type McpToolCallRequest = components["schemas"]["McpToolCallRequest"];
export type McpToolCallResponse = components["schemas"]["McpToolCallResponse"];

export type InboxNotificationListResponse =
  components["schemas"]["InboxNotificationListResponse"];
export type ClaimTaskRequest = components["schemas"]["ClaimTaskRequest"];
export type ClaimTaskResponse = components["schemas"]["ClaimTaskResponse"];
export type ReleaseTaskClaimRequest = components["schemas"]["ReleaseTaskClaimRequest"];
export type AcquireResourceLeasesRequest = components["schemas"]["AcquireResourceLeasesRequest"];
export type AcquireResourceLeasesResponse =
  components["schemas"]["AcquireResourceLeasesResponse"];
export type ValidateFencedWriteRequest = components["schemas"]["ValidateFencedWriteRequest"];
export type ValidateFencedWriteResponse = components["schemas"]["ValidateFencedWriteResponse"];

export type ControlCenterOverviewResponse =
  components["schemas"]["ControlCenterOverviewResponse"];
export type UpdateWorkspaceLifecycleRequest =
  components["schemas"]["UpdateWorkspaceLifecycleRequest"];
export type WorkspaceGovernanceItemResponse =
  components["schemas"]["WorkspaceGovernanceItemResponse"];
export type RunMutationGuardCheckRequest = components["schemas"]["RunMutationGuardCheckRequest"];
export type RunMutationGuardCheckResponse =
  components["schemas"]["RunMutationGuardCheckResponse"];
export type CommandPaletteSearchResponse = components["schemas"]["CommandPaletteSearchResponse"];

export function createEpics1To7OperationsDomainClient(requestJson: RequestJsonFn) {
  return {
    // Epic 3 — Workflow-as-Code, Durable Orchestration, Blackboard, Anchors, Arbitration, Challenge & Replay
    getOrchestrationState(personaKey?: string): Promise<OrchestrationSetupStateResponse> {
      return requestJson<OrchestrationSetupStateResponse>(
        `/api/v1/orchestration/state${buildPersonaQuery(personaKey)}`,
      );
    },
    validateWorkflowManifest(
      payload: WorkflowManifestValidateRequest,
      personaKey?: string,
    ): Promise<WorkflowManifestValidateResponse> {
      return requestJson<WorkflowManifestValidateResponse>(
        `/api/v1/orchestration/workflows/validate${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    registerWorkflowManifest(
      payload: WorkflowManifestRegisterRequest,
      personaKey?: string,
    ): Promise<WorkflowManifestRegisterResponse> {
      return requestJson<WorkflowManifestRegisterResponse>(
        `/api/v1/orchestration/workflows/register${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    compileArtifactTemplate(
      payload: ArtifactTemplateCompileRequest,
      personaKey?: string,
    ): Promise<ArtifactTemplateCompileResponse> {
      return requestJson<ArtifactTemplateCompileResponse>(
        `/api/v1/orchestration/templates/compile${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    instantiateWorkflowRun(
      payload: WorkflowRunInstantiateRequest,
      personaKey?: string,
    ): Promise<WorkflowRunInstantiateResponse> {
      return requestJson<WorkflowRunInstantiateResponse>(
        `/api/v1/orchestration/runs/instantiate${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    getRunBlackboardState(
      runId: string,
      personaKey?: string,
    ): Promise<RunBlackboardStateResponse> {
      return requestJson<RunBlackboardStateResponse>(
        `/api/v1/orchestration/runs/${encodeURIComponent(runId)}/blackboard${buildPersonaQuery(personaKey)}`,
      );
    },
    hydrateStepContext(
      payload: StepHydrateRequest,
      personaKey?: string,
    ): Promise<StepHydrateResponse> {
      return requestJson<StepHydrateResponse>(
        `/api/v1/orchestration/runs/steps/hydrate${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    executeWorkflowStep(
      payload: StepExecuteRequest,
      personaKey?: string,
    ): Promise<StepExecuteResponse> {
      return requestJson<StepExecuteResponse>(
        `/api/v1/orchestration/runs/steps/execute${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    signHumanAnchor(
      payload: HumanAnchorSignRequest,
      personaKey?: string,
    ): Promise<HumanAnchorSignResponse> {
      return requestJson<HumanAnchorSignResponse>(
        `/api/v1/orchestration/runs/anchors/sign${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    requestHumanArbitration(
      runId: string,
      stepKey: string,
      payload: HumanArbitrationCreateRequest,
      personaKey?: string,
    ): Promise<HumanArbitrationCreateResponse> {
      return requestJson<HumanArbitrationCreateResponse>(
        `/api/v1/orchestration/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepKey)}/arbitration${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    resolveHumanArbitration(
      runId: string,
      stepKey: string,
      payload: HumanArbitrationResolveRequest,
      personaKey?: string,
    ): Promise<HumanArbitrationResolveResponse> {
      return requestJson<HumanArbitrationResolveResponse>(
        `/api/v1/orchestration/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepKey)}/arbitration/resolve${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    resumeHumanWorkflowStep(
      runId: string,
      stepKey: string,
      payload: StepHumanResumeRequest,
      personaKey?: string,
    ): Promise<StepExecuteResponse> {
      return requestJson<StepExecuteResponse>(
        `/api/v1/orchestration/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepKey)}/resume${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    executeBackgroundFastPathAudit(
      payload: BackgroundAuditRunRequest,
      personaKey?: string,
    ): Promise<BackgroundAuditRunResponse> {
      return requestJson<BackgroundAuditRunResponse>(
        `/api/v1/orchestration/runs/fast-path-audit${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    previewUpstreamChallenge(
      runId: string,
      stepKey: string,
      payload: UpstreamChallengePreviewRequest,
      personaKey?: string,
    ): Promise<UpstreamChallengePreviewResponse> {
      return requestJson<UpstreamChallengePreviewResponse>(
        `/api/v1/orchestration/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepKey)}/challenge/preview${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    submitUpstreamChallenge(
      runId: string,
      stepKey: string,
      payload: UpstreamChallengeSubmitRequest,
      personaKey?: string,
    ): Promise<UpstreamChallengeSubmitResponse> {
      return requestJson<UpstreamChallengeSubmitResponse>(
        `/api/v1/orchestration/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepKey)}/challenge${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    replayWorkflowFromStep(
      runId: string,
      stepKey: string,
      payload?: StepReplayRequest,
      personaKey?: string,
    ): Promise<StepReplayResponse> {
      return requestJson<StepReplayResponse>(
        `/api/v1/orchestration/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepKey)}/replay${buildPersonaQuery(personaKey)}`,
        "POST",
        payload ?? {},
      );
    },
    assistantChatTurn(
      payload: AssistantChatRequest,
      personaKey?: string,
    ): Promise<AssistantChatResponse> {
      return requestJson<AssistantChatResponse>(
        `/api/v1/assistant/chat${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
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

    // Epic 4 — Tier 1/2 Sandboxes, Agentic Gates, Adaptive Human Gates, Jira & Governed MCP
    evaluateDeterministicGate(
      payload: DeterministicGateEvaluateRequest,
      personaKey?: string,
    ): Promise<DeterministicGateEvaluateResponse> {
      return requestJson<DeterministicGateEvaluateResponse>(
        `/api/v1/gates/deterministic/evaluate${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    listGateEvaluations(runId?: string, personaKey?: string): Promise<GateEvaluationsListResponse> {
      const params = new URLSearchParams();
      if (runId) params.set("run_id", runId);
      if (personaKey) params.set("persona_key", personaKey);
      const qs = params.toString();
      return requestJson<GateEvaluationsListResponse>(
        `/api/v1/gates/evaluations${qs ? `?${qs}` : ""}`,
      );
    },
    executeInitExistingProject(
      payload: InitExistingProjectRequest,
      personaKey?: string,
    ): Promise<InitExistingProjectResponse> {
      return requestJson<InitExistingProjectResponse>(
        `/api/v1/bootstrap/init-existing-project${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    executeInitSkill(
      payload: InitSkillRequest,
      personaKey?: string,
    ): Promise<InitSkillResponse> {
      return requestJson<InitSkillResponse>(
        `/api/v1/bootstrap/init-skill${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    verifyTier2Tdd(
      payload: Tier2TddVerifyRequest,
      personaKey?: string,
    ): Promise<Tier2TddVerifyResponse> {
      return requestJson<Tier2TddVerifyResponse>(
        `/api/v1/gates/sandbox/tier2/tdd-verify${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    listDeploymentRoles(personaKey?: string): Promise<DeploymentRolesListResponse> {
      return requestJson<DeploymentRolesListResponse>(
        `/api/v1/gates/sandbox/deployment-roles${buildPersonaQuery(personaKey)}`,
      );
    },
    evaluateAgenticGate(
      payload: AgenticGateEvaluateRequest,
      personaKey?: string,
    ): Promise<AgenticGateEvaluateResponse> {
      return requestJson<AgenticGateEvaluateResponse>(
        `/api/v1/gates/agentic/evaluate${buildPersonaQuery(personaKey)}`,
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

    // Epics 5, 6 & 7 — Unified Inbox, Atomic Claim, Resource Leases, Control Center & FinOps Roll-Up
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
