import { backendState, jsonResponse } from "./mockBackendState";

function buildAssembledLayers(workspaceId: string) {
  const userPrefs = backendState.assistantGovernance.userPreferences;
  const wsSettings = backendState.assistantGovernance.workspaceSettings;
  return [
    {
      layer_number: 1,
      layer_code: "1_CONSTITUTION",
      label: "Socle constitutionnel ORCIA",
      immutable: true,
      origin_badge: "SOCLE",
      content: "Respecter les bornes de sécurité et tracer chaque décision.",
      sha256: "sha-layer-1",
    },
    {
      layer_number: 4,
      layer_code: "4_ESPACE",
      label: `Consignes de l'Espace (${workspaceId.slice(0, 8)})`,
      immutable: false,
      origin_badge: "ESPACE",
      content: String(wsSettings.workspace_instructions ?? ""),
      sha256: String(wsSettings.sha256 ?? "sha-layer-4"),
    },
    {
      layer_number: 5,
      layer_code: "5_UTILISATEUR",
      label: "Préférences personnelles",
      immutable: false,
      origin_badge: "UTILISATEUR",
      content: String(userPrefs.personal_instructions ?? ""),
      sha256: String(userPrefs.sha256 ?? "sha-layer-5"),
    },
  ];
}

export function handleAssistantGovernanceAndThreadsRoute(params: {
  path: string;
  method: string;
  parsedUrl: URL;
  body: Record<string, unknown>;
}): Response | null {
  const { path, method, parsedUrl, body } = params;

  const threadMessagesMatch = /^\/api\/v1\/assistant\/threads\/([^/]+)\/messages$/.exec(path);
  if (threadMessagesMatch && method === "GET") {
    const threadId = decodeURIComponent(threadMessagesMatch[1] ?? "");
    const wsId = parsedUrl.searchParams.get("workspace_id") ?? "0195f000-0000-7000-8000-000000000301";
    const msgs = backendState.assistantThreadMessages.filter((m) => m.thread_id === threadId);
    return jsonResponse({
      thread_id: threadId,
      workspace_id: wsId,
      messages: msgs,
    });
  }

  if (path === "/api/v1/assistant/threads" && method === "POST") {
    const threadId = `thread-${Date.now()}-${backendState.recordedCalls.length}`;
    const wsId = String(body.workspace_id ?? "0195f000-0000-7000-8000-000000000301");
    const rec = {
      thread_id: threadId,
      workspace_id: wsId,
      folder_id: body.folder_id ?? null,
      creator_user_id: "0195f000-0000-7000-8000-000000000001",
      last_author_user_id: "0195f000-0000-7000-8000-000000000001",
      title: String(body.title ?? "Discussion"),
      thread_summary: String(body.initial_summary ?? ""),
      turn_count: 0,
    };
    backendState.assistantThreads = [rec, ...backendState.assistantThreads];
    return jsonResponse(rec);
  }

  const overviewMatch = /^\/api\/v1\/assistant\/workspaces\/([^/]+)\/overview$/.exec(path);
  if (overviewMatch && method === "GET") {
    const workspaceId = decodeURIComponent(overviewMatch[1] ?? "");
    const wsFolders = backendState.assistantFolders.filter((f) => f.workspace_id === workspaceId);
    const wsThreads = backendState.assistantThreads.filter((t) => t.workspace_id === workspaceId);
    return jsonResponse({
      workspace_id: workspaceId,
      tabs: ["ACTIVE_DISCUSSION", "FOLDERS", "HISTORY_SEARCH"],
      active_folder_pill_label: null,
      folders_count: wsFolders.length,
      folders: wsFolders,
      threads: wsThreads,
      history_hits: [],
    });
  }

  if (path === "/api/v1/assistant/governance" && method === "GET") {
    const wsId = parsedUrl.searchParams.get("workspace_id") ?? "0195f000-0000-7000-8000-000000000301";
    return jsonResponse({
      workspace_id: wsId,
      can_edit_workspace_layer: backendState.assistantGovernance.canEditWorkspaceLayer,
      user_preferences: {
        ...backendState.assistantGovernance.userPreferences,
        user_id: "0195f000-0000-7000-8000-000000000001",
        workspace_id: wsId,
      },
      workspace_settings: {
        ...backendState.assistantGovernance.workspaceSettings,
        workspace_id: wsId,
      },
      assembled_layers: buildAssembledLayers(wsId),
    });
  }

  if (path === "/api/v1/assistant/governance/mode-a/user" && method === "PUT") {
    const wsId = String(body.workspace_id ?? "0195f000-0000-7000-8000-000000000301");
    backendState.assistantGovernance.userPreferences = {
      ...backendState.assistantGovernance.userPreferences,
      response_tone: body.response_tone ?? "BALANCED",
      favorite_format: body.favorite_format ?? "STRUCTURED_SECTIONS",
      default_hat: body.default_hat ?? "PM",
      personal_instructions: body.personal_instructions ?? "",
      sha256: `sha-user-${backendState.recordedCalls.length}`,
    };
    return jsonResponse({
      ...backendState.assistantGovernance.userPreferences,
      user_id: "0195f000-0000-7000-8000-000000000001",
      workspace_id: wsId,
    });
  }

  if (path === "/api/v1/assistant/governance/mode-a/workspace" && method === "PUT") {
    const wsId = String(body.workspace_id ?? "0195f000-0000-7000-8000-000000000301");
    backendState.assistantGovernance.workspaceSettings = {
      ...backendState.assistantGovernance.workspaceSettings,
      workspace_instructions: body.workspace_instructions ?? "",
      mcp_expose_assistant: Boolean(body.mcp_expose_assistant ?? true),
      sha256: `sha-ws-${backendState.recordedCalls.length}`,
    };
    return jsonResponse({
      ...backendState.assistantGovernance.workspaceSettings,
      workspace_id: wsId,
    });
  }

  return null;
}
