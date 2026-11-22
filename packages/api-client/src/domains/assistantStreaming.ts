import type { components } from "../generated/schema";
import {
  buildPersonaQuery,
  type createRequestJson,
  type createRequestSse,
  type SseEventHandler,
} from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;
type RequestSseFn = ReturnType<typeof createRequestSse>;

export type AssistantTurnCreateRequest = components["schemas"]["AssistantTurnCreateRequest"];
export type AssistantTurnAcceptedResponse =
  components["schemas"]["AssistantTurnAcceptedResponse"];
export type AssistantActiveTurnsListResponse =
  components["schemas"]["AssistantActiveTurnsListResponse"];
export type ActiveBackgroundTurnStatusResponse =
  components["schemas"]["ActiveBackgroundTurnStatusResponse"];
export type AssistantTurnSynthesizeNowResponse =
  components["schemas"]["AssistantTurnSynthesizeNowResponse"];
export type AssistantTurnApproveRequest = components["schemas"]["AssistantTurnApproveRequest"];
export type AssistantTurnApproveResponse = components["schemas"]["AssistantTurnApproveResponse"];
export type AssistantTurnFeedbackRequest = components["schemas"]["AssistantTurnFeedbackRequest"];
export type AssistantTurnFeedbackResponse = components["schemas"]["AssistantTurnFeedbackResponse"];
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
export type LaunchProcessFromFolderRequest =
  components["schemas"]["LaunchProcessFromFolderRequest"];
export type LaunchProcessFromFolderResponse =
  components["schemas"]["LaunchProcessFromFolderResponse"];

export interface AssistantTurnSseOptions {
  readonly after?: string;
  readonly signal?: AbortSignal;
  readonly accessToken?: string;
  readonly onTurnCreated?: (accepted: AssistantTurnAcceptedResponse) => void;
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

export function streamAssistantTurnByIdSse(
  requestSse: RequestSseFn,
  turnId: string,
  options?: AssistantTurnSseOptions,
): Promise<void> {
  const encoded = encodeURIComponent(turnId);
  const query = options?.after ? `?after=${encodeURIComponent(options.after)}` : "";
  return requestSse({
    path: `/api/v1/assistant/turns/${encoded}/stream${query}`,
    method: "GET",
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
  const createAssistantTurn = (
    payload: AssistantTurnCreateRequest,
  ): Promise<AssistantTurnAcceptedResponse> =>
    requestJson<AssistantTurnAcceptedResponse>("/api/v1/assistant/turns", "POST", payload);

  return {
    createAssistantTurn,
    listActiveAssistantTurns(workspaceId: string): Promise<AssistantActiveTurnsListResponse> {
      return requestJson<AssistantActiveTurnsListResponse>(
        `/api/v1/assistant/turns/active?workspace_id=${encodeURIComponent(workspaceId)}`,
      );
    },
    stopAssistantTurn(turnId: string): Promise<ActiveBackgroundTurnStatusResponse> {
      return requestJson<ActiveBackgroundTurnStatusResponse>(
        `/api/v1/assistant/turns/${encodeURIComponent(turnId)}/stop`,
        "POST",
        {},
      );
    },
    synthesizeAssistantTurnNow(turnId: string): Promise<AssistantTurnSynthesizeNowResponse> {
      return requestJson<AssistantTurnSynthesizeNowResponse>(
        `/api/v1/assistant/turns/${encodeURIComponent(turnId)}/synthesize-now`,
        "POST",
        {},
      );
    },
    approveAssistantTurnProposal(
      turnId: string,
      payload: AssistantTurnApproveRequest,
    ): Promise<AssistantTurnApproveResponse> {
      return requestJson<AssistantTurnApproveResponse>(
        `/api/v1/assistant/turns/${encodeURIComponent(turnId)}/approve`,
        "POST",
        payload,
      );
    },
    recordAssistantTurnFeedback(
      turnId: string,
      payload: AssistantTurnFeedbackRequest,
    ): Promise<AssistantTurnFeedbackResponse> {
      return requestJson<AssistantTurnFeedbackResponse>(
        `/api/v1/assistant/turns/${encodeURIComponent(turnId)}/feedback`,
        "POST",
        payload,
      );
    },
    streamAssistantTurnByIdSse(
      turnId: string,
      options?: AssistantTurnSseOptions,
    ): Promise<void> {
      return streamAssistantTurnByIdSse(requestSse, turnId, options);
    },
    async streamAssistantTurnSse(
      payload: AssistantTurnCreateRequest,
      options?: AssistantTurnSseOptions,
    ): Promise<AssistantTurnAcceptedResponse> {
      const accepted = await createAssistantTurn(payload);
      options?.onTurnCreated?.(accepted);
      await streamAssistantTurnByIdSse(requestSse, accepted.turn_id, options);
      return accepted;
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
    launchProcessFromFolder(
      folderId: string,
      payload: LaunchProcessFromFolderRequest,
    ): Promise<LaunchProcessFromFolderResponse> {
      return requestJson<LaunchProcessFromFolderResponse>(
        `/api/v1/assistant/folders/${encodeURIComponent(folderId)}/launch-process`,
        "POST",
        payload,
      );
    },
  };
}
