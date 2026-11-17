import type {
  SaveWorkflowV2Request,
  SaveWorkflowV2Response,
  WorkflowDefinitionV2_Output,
} from "../generated/schema";

type RequestJsonFn = <T>(
  path: string,
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
  body?: unknown,
  extraHeaders?: Record<string, string>,
) => Promise<T>;

export function createWorkflowsV2DomainClient(requestJson: RequestJsonFn) {
  return {
    getWorkflowV2(workflowId: string): Promise<WorkflowDefinitionV2_Output> {
      return requestJson<WorkflowDefinitionV2_Output>(
        `/api/v1/workflows/v2/${encodeURIComponent(workflowId)}`,
      );
    },
    saveWorkflowV2(
      workflowId: string,
      payload: SaveWorkflowV2Request,
      workspaceId?: string,
    ): Promise<SaveWorkflowV2Response> {
      const extraHeaders: Record<string, string> | undefined = workspaceId
        ? { "X-Orcia-Workspace-Id": workspaceId }
        : undefined;
      return requestJson<SaveWorkflowV2Response>(
        `/api/v1/workflows/v2/${encodeURIComponent(workflowId)}`,
        "PUT",
        payload,
        extraHeaders,
      );
    },
  };
}
