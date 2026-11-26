import type {
  GuardedEntityDeleteResponse,
  PackDeleteResponse,
  PackImportRequest,
  PackImportResponse,
} from "../generated/packs";
import type {
  DeclarativePacksListResponse,
  DeclarativePackSummaryResponse,
  HitlSignalRequest,
  PacksConnectorHealthResponse,
  ProcessPendingRunItemResponse,
  ProcessPendingRunsListResponse,
  SaveWorkflowV2Request,
  SaveWorkflowV2Response,
  StartWorkflowV2RunRequest,
  VsmListResponse,
  WhatIfSimulationRequest,
  WorkflowV2RunResponse,
  WorkflowsV2ListResponse,
} from "../generated/process_studio_v2";
import type { components } from "../generated/schema";
import {
  buildPersonaQuery,
  OrciaClientError,
  type BinaryDownloadResult,
  type createRequestBinary,
  type createRequestJson,
} from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;
type RequestBinaryFn = ReturnType<typeof createRequestBinary>;

export type ApiWorkflowDefinitionV2 = components["schemas"]["WorkflowDefinitionV2-Output"];
export type ApiValueStreamMapSpec = components["schemas"]["ValueStreamMapSpec"];
export type ApiImpactAssessmentResult = components["schemas"]["ImpactAssessmentResult"];
export type {
  DeclarativePacksListResponse,
  DeclarativePackSummaryResponse,
  GuardedEntityDeleteResponse,
  PackDeleteResponse,
  PackImportRequest,
  PackImportResponse,
  PacksConnectorHealthResponse,
  ProcessPendingRunItemResponse,
  ProcessPendingRunsListResponse,
};

export interface GuardedWorkflowDeleteOptions {
  readonly unlinkFromDraftPacks?: boolean;
  readonly personaKey?: string;
}

function buildWorkflowDeleteQuery(options?: GuardedWorkflowDeleteOptions): string {
  if (!options) return "";
  const qs = new URLSearchParams();
  if (options.unlinkFromDraftPacks) qs.set("unlink_from_draft_packs", "true");
  if (options.personaKey) qs.set("persona_key", options.personaKey);
  const encoded = qs.toString();
  return encoded ? `?${encoded}` : "";
}

export interface SaveWorkflowV2Options {
  readonly workspaceId?: string;
  readonly personaKey?: string;
}

export interface ListProcessPendingRunsParams {
  readonly workspaceId?: string;
  readonly scopeType?: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
  readonly scopeId?: string;
  readonly includeCompleted?: boolean;
  readonly limit?: number;
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
    getPacksHealth(): Promise<PacksConnectorHealthResponse> {
      return requestJson<PacksConnectorHealthResponse>("/api/v1/packs/health");
    },
    importPackArchive(payload: PackImportRequest): Promise<PackImportResponse> {
      return requestJson<PackImportResponse>("/api/v1/packs/import", "POST", payload);
    },
    deletePackBundle(bundleId: string): Promise<PackDeleteResponse> {
      return requestJson<PackDeleteResponse>(
        `/api/v1/packs/${encodeURIComponent(bundleId)}`,
        "DELETE",
      );
    },
    exportWorkspacePackZip(
      workspaceId: string,
      packId = "orcia-pack-sdlc",
    ): Promise<BinaryDownloadResult> {
      const encodedWs = encodeURIComponent(workspaceId);
      const qs = new URLSearchParams({ pack_id: packId }).toString();
      const path = `/api/v1/packs/export/${encodedWs}?${qs}`;
      if (!requestBinary) {
        throw new OrciaClientError("ERR_CLIENT_NOT_CONFIGURED", {
          detail: "workflowsV2.requestBinary",
        });
      }
      return requestBinary(path, "POST");
    },
    listWorkflowsV2(): Promise<WorkflowsV2ListResponse> {
      return requestJson<WorkflowsV2ListResponse>("/api/v1/workflows/v2");
    },
    listProcessPendingRuns(
      params: ListProcessPendingRunsParams = {},
    ): Promise<ProcessPendingRunsListResponse> {
      const search = new URLSearchParams();
      if (params.workspaceId) search.set("workspace_id", params.workspaceId);
      if (params.scopeType) search.set("scope_type", params.scopeType);
      if (params.scopeId) search.set("scope_id", params.scopeId);
      if (params.includeCompleted !== undefined) {
        search.set("include_completed", String(params.includeCompleted));
      }
      if (params.limit !== undefined) search.set("limit", String(params.limit));
      if (params.personaKey) search.set("persona_key", params.personaKey);
      const qs = search.toString();
      return requestJson<ProcessPendingRunsListResponse>(
        `/api/v1/workflows/v2/runs${qs ? `?${qs}` : ""}`,
      );
    },
    listValueStreamMaps(): Promise<VsmListResponse> {
      return requestJson<VsmListResponse>("/api/v1/vsm");
    },
    getValueStreamMap(vsmId: string): Promise<ApiValueStreamMapSpec> {
      const encoded = encodeURIComponent(vsmId);
      return requestJson<ApiValueStreamMapSpec>(`/api/v1/vsm/${encoded}`);
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
    deleteWorkflowV2(
      workflowId: string,
      options?: GuardedWorkflowDeleteOptions,
    ): Promise<GuardedEntityDeleteResponse> {
      const encoded = encodeURIComponent(workflowId);
      return requestJson<GuardedEntityDeleteResponse>(
        `/api/v1/workflows/v2/${encoded}${buildWorkflowDeleteQuery(options)}`,
        "DELETE",
      );
    },
    deleteVsmV2(
      vsmId: string,
      options?: GuardedWorkflowDeleteOptions,
    ): Promise<GuardedEntityDeleteResponse> {
      const encoded = encodeURIComponent(vsmId);
      return requestJson<GuardedEntityDeleteResponse>(
        `/api/v1/vsm/${encoded}${buildWorkflowDeleteQuery(options)}`,
        "DELETE",
      );
    },
  };
}
