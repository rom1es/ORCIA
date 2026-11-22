import type { components } from "../generated/schema";
import type { createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export type AssistantGovernanceViewResponse =
  components["schemas"]["AssistantGovernanceViewResponse"];
export type UpdateUserLayerPreferencesRequest =
  components["schemas"]["UpdateUserLayerPreferencesRequest"];
export type UserLayerPreferencesSchemaItem =
  components["schemas"]["UserLayerPreferencesSchemaItem"];
export type UpdateWorkspaceLayerSettingsRequest =
  components["schemas"]["UpdateWorkspaceLayerSettingsRequest"];
export type WorkspaceLayerSettingsSchemaItem =
  components["schemas"]["WorkspaceLayerSettingsSchemaItem"];
export type AssembledLayerPreviewSchemaItem =
  components["schemas"]["AssembledLayerPreviewSchemaItem"];
export type AssistantThreadMessagesListResponse =
  components["schemas"]["AssistantThreadMessagesListResponse"];
export type AssistantThreadMessageSchemaItem =
  components["schemas"]["AssistantThreadMessageSchemaItem"];

export function createAssistantGovernanceAndThreadsDomainClient(requestJson: RequestJsonFn) {
  return {
    listAssistantThreadMessages(
      threadId: string,
      workspaceId: string,
      limit = 200,
    ): Promise<AssistantThreadMessagesListResponse> {
      const qs = new URLSearchParams({
        workspace_id: workspaceId,
        limit: String(limit),
      }).toString();
      return requestJson<AssistantThreadMessagesListResponse>(
        `/api/v1/assistant/threads/${encodeURIComponent(threadId)}/messages?${qs}`,
      );
    },
    getAssistantGovernance(
      workspaceId: string,
      packKey?: string,
    ): Promise<AssistantGovernanceViewResponse> {
      const params = new URLSearchParams({ workspace_id: workspaceId });
      if (packKey) params.set("pack_key", packKey);
      return requestJson<AssistantGovernanceViewResponse>(
        `/api/v1/assistant/governance?${params.toString()}`,
      );
    },
    updateAssistantUserPreferences(
      payload: UpdateUserLayerPreferencesRequest,
    ): Promise<UserLayerPreferencesSchemaItem> {
      return requestJson<UserLayerPreferencesSchemaItem>(
        "/api/v1/assistant/governance/mode-a/user",
        "PUT",
        payload,
      );
    },
    updateAssistantWorkspaceSettings(
      payload: UpdateWorkspaceLayerSettingsRequest,
    ): Promise<WorkspaceLayerSettingsSchemaItem> {
      return requestJson<WorkspaceLayerSettingsSchemaItem>(
        "/api/v1/assistant/governance/mode-a/workspace",
        "PUT",
        payload,
      );
    },
  };
}
