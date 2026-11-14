import type {
  CodegraphToolsListResponse,
  InvokeCodegraphToolRequest,
  InvokeCodegraphToolResponse,
} from "../generated/codegraph_mcp";
import { buildPersonaQuery, type createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export function createCodegraphMcpDomainClient(requestJson: RequestJsonFn) {
  return {
    listCodegraphTools(
      workspaceId: string,
      personaKey?: string,
    ): Promise<CodegraphToolsListResponse> {
      return requestJson<CodegraphToolsListResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/codegraph/tools${buildPersonaQuery(personaKey)}`,
      );
    },
    invokeCodegraphTool(
      workspaceId: string,
      payload: InvokeCodegraphToolRequest,
      personaKey?: string,
    ): Promise<InvokeCodegraphToolResponse> {
      return requestJson<InvokeCodegraphToolResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/codegraph/invoke${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
  };
}
