import type {
  ApproveReflexiveWriteRequest,
  ReflexiveExecutionSnapshotResponse,
  StartReflexiveExecutionRequest,
  SurgicalExploreRequest,
  SurgicalExploreResponse,
  SurgicalInspectLinesResponse,
} from "../generated/reflexive_execution";
import { buildPersonaQuery, type createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export interface InspectSourceLinesParams {
  uri: string;
  startLine?: number;
  endLine?: number;
  workspaceId?: string;
  personaKey?: string;
}

export function createReflexiveExecutionDomainClient(
  requestJson: RequestJsonFn,
  baseUrl = "",
) {
  const normalizedBase = baseUrl.replace(/\/+$/, "");

  return {
    inspectSourceLines(params: InspectSourceLinesParams): Promise<SurgicalInspectLinesResponse> {
      const search = new URLSearchParams();
      search.set("uri", params.uri);
      if (params.startLine !== undefined) {
        search.set("start_line", String(params.startLine));
      }
      if (params.endLine !== undefined) {
        search.set("end_line", String(params.endLine));
      }
      if (params.workspaceId) {
        search.set("workspace_id", params.workspaceId);
      }
      if (params.personaKey) {
        search.set("persona_key", params.personaKey);
      }
      return requestJson<SurgicalInspectLinesResponse>(
        `/api/v1/sources/inspect-lines?${search.toString()}`,
      );
    },
    executeSurgicalExplore(
      payload: SurgicalExploreRequest,
      personaKey?: string,
    ): Promise<SurgicalExploreResponse> {
      return requestJson<SurgicalExploreResponse>(
        `/api/v1/sources/surgical-explore${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    startReflexiveExecution(
      payload: StartReflexiveExecutionRequest,
      personaKey?: string,
    ): Promise<ReflexiveExecutionSnapshotResponse> {
      return requestJson<ReflexiveExecutionSnapshotResponse>(
        `/api/v1/executions/reflexive${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    getReflexiveExecutionSnapshot(
      executionId: string,
      personaKey?: string,
    ): Promise<ReflexiveExecutionSnapshotResponse> {
      const encoded = encodeURIComponent(executionId);
      return requestJson<ReflexiveExecutionSnapshotResponse>(
        `/api/v1/executions/${encoded}${buildPersonaQuery(personaKey)}`,
      );
    },
    buildReflexiveTraceStreamUrl(executionId: string, personaKey?: string): string {
      const encoded = encodeURIComponent(executionId);
      return `${normalizedBase}/api/v1/executions/${encoded}/trace-stream${buildPersonaQuery(personaKey)}`;
    },
    synthesizeReflexiveExecutionNow(
      executionId: string,
      personaKey?: string,
    ): Promise<ReflexiveExecutionSnapshotResponse> {
      const encoded = encodeURIComponent(executionId);
      return requestJson<ReflexiveExecutionSnapshotResponse>(
        `/api/v1/executions/${encoded}/synthesize-now${buildPersonaQuery(personaKey)}`,
        "POST",
      );
    },
    cancelReflexiveExecution(
      executionId: string,
      personaKey?: string,
    ): Promise<ReflexiveExecutionSnapshotResponse> {
      const encoded = encodeURIComponent(executionId);
      return requestJson<ReflexiveExecutionSnapshotResponse>(
        `/api/v1/executions/${encoded}/cancel${buildPersonaQuery(personaKey)}`,
        "POST",
      );
    },
    approveReflexiveWrite(
      executionId: string,
      payload: ApproveReflexiveWriteRequest,
      personaKey?: string,
    ): Promise<ReflexiveExecutionSnapshotResponse> {
      const encoded = encodeURIComponent(executionId);
      return requestJson<ReflexiveExecutionSnapshotResponse>(
        `/api/v1/executions/${encoded}/approve-write${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
  };
}
