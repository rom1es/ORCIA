import type {
  DeclarativePacksListResponse,
  DeclarativePackSummaryResponse,
  HitlSignalRequest,
  SaveWorkflowV2Request,
  SaveWorkflowV2Response,
  StartWorkflowV2RunRequest,
  WhatIfSimulationRequest,
  WorkflowV2RunResponse,
  WorkflowsV2ListResponse,
} from "../generated/process_studio_v2";
import type { components } from "../generated/schema";
import {
  buildPersonaQuery,
  type BinaryDownloadResult,
  type createRequestBinary,
  type createRequestJson,
} from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;
type RequestBinaryFn = ReturnType<typeof createRequestBinary>;

export type ApiWorkflowDefinitionV2 = components["schemas"]["WorkflowDefinitionV2-Output"];
export type ApiImpactAssessmentResult = components["schemas"]["ImpactAssessmentResult"];
export type { DeclarativePacksListResponse, DeclarativePackSummaryResponse };

export interface SaveWorkflowV2Options {
  readonly workspaceId?: string;
  readonly personaKey?: string;
}

export function createWorkflowsV2DomainClient(
  requestJson: RequestJsonFn,
  requestBinary?: RequestBinaryFn,
) {
  return {
    listDeclarativePacks(): Promise<DeclarativePacksListResponse> {
      return requestJson<DeclarativePacksListResponse>("/api/v1/packs");
    },
    exportWorkspacePackZip(
      workspaceId: string,
      packId = "orcia-pack-sdlc",
    ): Promise<BinaryDownloadResult> {
      const encodedWs = encodeURIComponent(workspaceId);
      const qs = new URLSearchParams({ pack_id: packId }).toString();
      const path = `/api/v1/packs/export/${encodedWs}?${qs}`;
      if (!requestBinary) {
        throw new Error("Binary download helper not configured on workflowsV2 client.");
      }
      return requestBinary(path, "POST");
    },
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
      workspaceIdOrOptions?: string | SaveWorkflowV2Options,
    ): Promise<SaveWorkflowV2Response> {
      const opts: SaveWorkflowV2Options =
        typeof workspaceIdOrOptions === "string"
          ? { workspaceId: workspaceIdOrOptions }
          : (workspaceIdOrOptions ?? {});
      const extraHeaders: Record<string, string> | undefined = opts.workspaceId
        ? { "X-Orcia-Workspace-Id": opts.workspaceId }
        : undefined;
      const encoded = encodeURIComponent(workflowId);
      return requestJson<SaveWorkflowV2Response>(
        `/api/v1/workflows/v2/${encoded}${buildPersonaQuery(opts.personaKey)}`,
        "PUT",
        payload,
        extraHeaders,
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
