import type {
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

export function createReflexiveExecutionDomainClient(requestJson: RequestJsonFn) {
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
  };
}
