import type { components } from "../generated/schema";
import {
  buildPersonaQuery,
  type createRequestJson,
  type createRequestSse,
  type SseEventHandler,
} from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;
type RequestSseFn = ReturnType<typeof createRequestSse>;

export type ThreeSpeedTurnRequest = components["schemas"]["ThreeSpeedTurnRequest"];
export type ThreeSpeedTurnResponse = components["schemas"]["ThreeSpeedTurnResponse"];
export type ActiveBackgroundTurnStatusResponse =
  components["schemas"]["ActiveBackgroundTurnStatusResponse"];
export type StopActiveBackgroundTurnRequest =
  components["schemas"]["StopActiveBackgroundTurnRequest"];
export type RecordAssistantTurnFeedbackRequest =
  components["schemas"]["RecordAssistantTurnFeedbackRequest"];
export type AssistantWorkspaceOverviewResponse =
  components["schemas"]["AssistantWorkspaceOverviewResponse"];
export type CreateAssistantFolderRequest =
  components["schemas"]["CreateOrUpdateAssistantFolderRequest"];
export type AssistantFolderResponse = components["schemas"]["AssistantFolderSchemaItem"];
export type ConfigureAssistantFolderSharingRequest =
  components["schemas"]["ConfigureFolderSharingRequest"];
export type ConfigureAssistantFolderSharingResponse =
  components["schemas"]["ConfigureFolderSharingResponse"];
export type CreateAssistantThreadRequest =
  components["schemas"]["CreateAssistantThreadRequest"];
export type AssistantThreadResponse = components["schemas"]["AssistantThreadSchemaItem"];
export type SendCollaborativeThreadTurnRequest =
  components["schemas"]["SendCollaborativeThreadTurnRequest"];
export type SendCollaborativeThreadTurnResponse =
  components["schemas"]["SendCollaborativeThreadTurnResponse"];

export interface AssistantTurnSseOptions {
  readonly signal?: AbortSignal;
  readonly accessToken?: string;
  readonly onOpen?: (response: Response) => void;
  readonly onEvent?: SseEventHandler;
}

export interface ReflexiveTraceSseOptions {
  readonly personaKey?: string;
  readonly signal?: AbortSignal;
  readonly accessToken?: string;
  readonly onOpen?: (response: Response) => void;
  readonly onEvent?: SseEventHandler;
}

export interface WorkspaceEventsSseOptions {
  readonly live?: boolean;
  readonly personaKey?: string;
  readonly signal?: AbortSignal;
  readonly accessToken?: string;
  readonly onOpen?: (response: Response) => void;
  readonly onEvent?: SseEventHandler;
}

export function streamAssistantTurnSse(
  requestSse: RequestSseFn,
  payload: ThreeSpeedTurnRequest,
  options?: AssistantTurnSseOptions,
): Promise<void> {
  return requestSse({
    path: "/api/v1/assistant/three-speed/stream",
    method: "POST",
    body: payload,
    ...(options?.signal ? { signal: options.signal } : {}),
    ...(options?.accessToken !== undefined ? { accessToken: options.accessToken } : {}),
    ...(options?.onOpen ? { onOpen: options.onOpen } : {}),
    ...(options?.onEvent ? { onEvent: options.onEvent } : {}),
  });
}

export function streamReflexiveExecutionTraceSse(
  requestSse: RequestSseFn,
  executionId: string,
  options?: ReflexiveTraceSseOptions,
): Promise<void> {
  const encoded = encodeURIComponent(executionId);
  return requestSse({
    path: `/api/v1/executions/${encoded}/trace-stream${buildPersonaQuery(options?.personaKey)}`,
    method: "GET",
    ...(options?.signal ? { signal: options.signal } : {}),
    ...(options?.accessToken !== undefined ? { accessToken: options.accessToken } : {}),
    ...(options?.onOpen ? { onOpen: options.onOpen } : {}),
    ...(options?.onEvent ? { onEvent: options.onEvent } : {}),
  });
}

export function streamWorkspaceEventsSse(
  requestSse: RequestSseFn,
  workspaceId: string,
  options?: WorkspaceEventsSseOptions,
): Promise<void> {
  const params = new URLSearchParams({ workspace_id: workspaceId });
  if (options?.live !== undefined) {
    params.set("live", options.live ? "true" : "false");
  }
  if (options?.personaKey) {
    params.set("persona_key", options.personaKey);
  }
  return requestSse({
    path: `/api/v1/events/stream?${params.toString()}`,
    method: "GET",
    ...(options?.signal ? { signal: options.signal } : {}),
    ...(options?.accessToken !== undefined ? { accessToken: options.accessToken } : {}),
    ...(options?.onOpen ? { onOpen: options.onOpen } : {}),
    ...(options?.onEvent ? { onEvent: options.onEvent } : {}),
  });
}

export function createAssistantStreamingDomainClient(
  requestSse: RequestSseFn,
  requestJson: RequestJsonFn,
) {
  return {
    executeAssistantTurn(payload: ThreeSpeedTurnRequest): Promise<ThreeSpeedTurnResponse> {
      return requestJson<ThreeSpeedTurnResponse>("/api/v1/assistant/three-speed/turn", "POST", payload);
    },
    getActiveAssistantTurnStatus(workspaceId: string): Promise<ActiveBackgroundTurnStatusResponse> {
      return requestJson<ActiveBackgroundTurnStatusResponse>(
        `/api/v1/assistant/three-speed/active-turn?workspace_id=${encodeURIComponent(workspaceId)}`,
      );
    },
    stopActiveAssistantTurn(payload: StopActiveBackgroundTurnRequest): Promise<ActiveBackgroundTurnStatusResponse> {
      return requestJson<ActiveBackgroundTurnStatusResponse>(
        "/api/v1/assistant/three-speed/stop",
        "POST",
        payload,
      );
    },
    recordAssistantTurnFeedback(payload: RecordAssistantTurnFeedbackRequest): Promise<Record<string, unknown>> {
      return requestJson<Record<string, unknown>>(
        "/api/v1/assistant/three-speed/feedback",
        "POST",
        payload,
      );
    },
    streamAssistantTurnSse(
      payload: ThreeSpeedTurnRequest,
      options?: AssistantTurnSseOptions,
    ): Promise<void> {
      return streamAssistantTurnSse(requestSse, payload, options);
    },
    streamReflexiveExecutionTraceSse(
      executionId: string,
      options?: ReflexiveTraceSseOptions,
    ): Promise<void> {
      return streamReflexiveExecutionTraceSse(requestSse, executionId, options);
    },
    streamWorkspaceEventsSse(
      workspaceId: string,
      options?: WorkspaceEventsSseOptions,
    ): Promise<void> {
      return streamWorkspaceEventsSse(requestSse, workspaceId, options);
    },
    listAssistantFolders(workspaceId: string): Promise<AssistantWorkspaceOverviewResponse> {
      return requestJson<AssistantWorkspaceOverviewResponse>(
        `/api/v1/assistant/workspaces/${encodeURIComponent(workspaceId)}/overview`,
      );
    },
    createAssistantFolder(payload: CreateAssistantFolderRequest): Promise<AssistantFolderResponse> {
      return requestJson<AssistantFolderResponse>("/api/v1/assistant/folders", "POST", payload);
    },
    configureAssistantFolderSharing(
      folderId: string,
      payload: ConfigureAssistantFolderSharingRequest,
    ): Promise<ConfigureAssistantFolderSharingResponse> {
      return requestJson<ConfigureAssistantFolderSharingResponse>(
        `/api/v1/assistant/folders/${encodeURIComponent(folderId)}/share`,
        "POST",
        payload,
      );
    },
    createAssistantThread(payload: CreateAssistantThreadRequest): Promise<AssistantThreadResponse> {
      return requestJson<AssistantThreadResponse>("/api/v1/assistant/threads", "POST", payload);
    },
    sendCollaborativeThreadTurn(
      threadId: string,
      payload: SendCollaborativeThreadTurnRequest,
    ): Promise<SendCollaborativeThreadTurnResponse> {
      return requestJson<SendCollaborativeThreadTurnResponse>(
        `/api/v1/assistant/threads/${encodeURIComponent(threadId)}/turns`,
        "POST",
        payload,
      );
    },
  };
}
