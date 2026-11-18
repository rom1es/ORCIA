import type { components } from "../generated/schema";
import type { createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export type ExceptionWaiverResponseItem = components["schemas"]["ExceptionWaiverResponse"];
export type RegisterExceptionWaiverInput = components["schemas"]["RegisterExceptionWaiverRequest"];
export type WorkspaceFiveTabsStatePayload =
  components["schemas"]["WorkspaceFiveTabsStateResponse"];

export function createWorkspaceGovernanceDomainClient(requestJson: RequestJsonFn) {
  return {
    getWorkspaceFiveTabsState(
      workspaceId: string,
      workspaceSlug = "default-ws",
    ): Promise<WorkspaceFiveTabsStatePayload> {
      const q = new URLSearchParams({ workspace_slug: workspaceSlug }).toString();
      return requestJson<WorkspaceFiveTabsStatePayload>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/five-tabs?${q}`,
      );
    },
    listWorkspaceExceptionWaivers(
      workspaceId: string,
      activeOnly = false,
    ): Promise<ExceptionWaiverResponseItem[]> {
      const q = activeOnly ? "?active_only=true" : "";
      return requestJson<ExceptionWaiverResponseItem[]>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/exception-waivers${q}`,
      );
    },
    registerWorkspaceExceptionWaiver(
      workspaceId: string,
      payload: RegisterExceptionWaiverInput,
    ): Promise<ExceptionWaiverResponseItem> {
      return requestJson<ExceptionWaiverResponseItem>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/exception-waivers`,
        "POST",
        payload,
      );
    },
  };
}
