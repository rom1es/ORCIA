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
import { buildPersonaQuery, type createRequestJson } from "../helpers";
import type {
  AgenticGateEvaluateRequest,
  AgenticGateEvaluateResponse,
  DeploymentRolesListResponse,
  DeterministicGateEvaluateRequest,
  DeterministicGateEvaluateResponse,
  GateEvaluationsListResponse,
  InitExistingProjectRequest,
  InitExistingProjectResponse,
  InitSkillRequest,
  InitSkillResponse,
  StepReplayRequest,
  StepReplayResponse,
  Tier2TddVerifyRequest,
  Tier2TddVerifyResponse,
  UpstreamChallengePreviewRequest,
  UpstreamChallengePreviewResponse,
  UpstreamChallengeSubmitRequest,
  UpstreamChallengeSubmitResponse,
} from "./_epics1To7Types";
import { createEpics4To7TailOperations } from "./_epics4To7Operations";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export * from "./_epics1To7Types";

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
    ...createEpics4To7TailOperations(requestJson),
  };
}
