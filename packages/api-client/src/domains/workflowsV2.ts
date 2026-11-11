import type {
  HitlSignalRequest,
  SaveWorkflowV2Request,
  SaveWorkflowV2Response,
  StartWorkflowV2RunRequest,
  WhatIfSimulationRequest,
  WorkflowV2RunResponse,
  WorkflowsV2ListResponse,
} from "../generated/process_studio_v2";
import type { components } from "../generated/schema";
import { buildPersonaQuery, type createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export type ApiWorkflowDefinitionV2 = components["schemas"]["WorkflowDefinitionV2-Output"];
export type ApiImpactAssessmentResult = components["schemas"]["ImpactAssessmentResult"];

export function createWorkflowsV2DomainClient(requestJson: RequestJsonFn) {
  return {
    listWorkflowsV2(): Promise<WorkflowsV2ListResponse> {
      return requestJson<WorkflowsV2ListResponse>("/api/v1/workflows/v2");
    },
    getWorkflowV2(workflowId: string): Promise<ApiWorkflowDefinitionV2> {
      const encoded = encodeURIComponent(workflowId);
      return requestJson<ApiWorkflowDefinitionV2>(`/api/v1/workflows/v2/${encoded}`);
    },
    saveWorkflowV2(
      workflowId: string,
      payload: SaveWorkflowV2Request,
      personaKey?: string,
    ): Promise<SaveWorkflowV2Response> {
      const encoded = encodeURIComponent(workflowId);
      return requestJson<SaveWorkflowV2Response>(
        `/api/v1/workflows/v2/${encoded}${buildPersonaQuery(personaKey)}`,
        "PUT",
        payload,
      );
    },
    runWorkflowV2WhatIf(
      workflowId: string,
      payload: WhatIfSimulationRequest,
    ): Promise<ApiImpactAssessmentResult> {
      const encoded = encodeURIComponent(workflowId);
      return requestJson<ApiImpactAssessmentResult>(
        `/api/v1/workflows/v2/${encoded}/what-if`,
        "POST",
        payload,
      );
    },
    startWorkflowV2Run(
      workflowId: string,
      payload: StartWorkflowV2RunRequest,
      personaKey?: string,
    ): Promise<WorkflowV2RunResponse> {
      const encoded = encodeURIComponent(workflowId);
      return requestJson<WorkflowV2RunResponse>(
        `/api/v1/workflows/v2/${encoded}/runs${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    getWorkflowV2Run(runId: string): Promise<WorkflowV2RunResponse> {
      const encoded = encodeURIComponent(runId);
      return requestJson<WorkflowV2RunResponse>(`/api/v1/runs/${encoded}`);
    },
    sendWorkflowV2HitlSignal(
      runId: string,
      payload: HitlSignalRequest,
      personaKey?: string,
    ): Promise<WorkflowV2RunResponse> {
      const encoded = encodeURIComponent(runId);
      return requestJson<WorkflowV2RunResponse>(
        `/api/v1/runs/${encoded}/hitl-signal${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
  };
}
