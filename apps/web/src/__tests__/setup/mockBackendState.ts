import type { ApiWorkflowDefinitionV2 } from "@orcia/api-client";
import { writeCachedPlatformAdmin } from "../../components/platformSetupStorageHelpers";
import { INITIAL_WORKFLOWS_V2 } from "../../features/processes/processStudioV2Data";
import { mapUiItemToApiWorkflowV2 } from "../../features/processes/studio/studioLabelsAndMappers";
import { resetAuthSessionStore } from "../../stores/authSessionStore";
import { resetVitestAuthPolicyMockState, seedVitestPlatformAuthPolicy } from "../vitestAuthPolicyMockHandlers";
import { resetVitestAutonomousSupervisionMockState } from "../vitestAutonomousSupervisionMockHandlers";
import { resetVitestConnectorsMockState } from "../vitestConnectorsMockHandlers";
import { resetVitestIamMockState } from "../vitestIamMockHandlers";
import { resetVitestOntologyMockState } from "../vitestOntologyMockHandlers";
import { resetVitestPacksAndWizardsMockState } from "../vitestPacksAndWizardsMockHandlers";
import { resetVitestReflexiveBackend } from "../vitestReflexiveBackend";
import { hydrateMockOrgUnitsFromSetup } from "./orgUnitsScopeHelpers";

export interface RecordedVitestApiCall {
  readonly method: string;
  readonly path: string;
  readonly body: unknown;
  readonly headers?: Record<string, string>;
}

export interface MockOrganizationalUnit {
  id: string;
  slug: string;
  name: string;
  kind: "BU" | "TEAM";
  parent_id: string | null;
  billing_enabled: boolean;
  lead_user_id: string | null;
  lead_user_ids?: string[];
  ontology_lead_user_ids?: string[];
  member_user_ids: string[];
  can_edit?: boolean;
  can_create_child?: boolean;
  can_delete?: boolean;
  can_manage_members?: boolean;
  can_manage_ontology_leads?: boolean;
  can_invite_users?: boolean;
}

export interface MockBackendState {
  firstAdmin: {
    email: string;
    displayName: string;
    roles?: string[];
  } | null;
  platformSetupState: Record<string, unknown> | null;
  orgUnits: MockOrganizationalUnit[];
  orgUnitSeq: number;
  workspaces: Array<Record<string, unknown>>;
  workspaceSeq: number;
  workspaceWaivers: Array<Record<string, unknown>>;
  waiverSeq: number;
  dnaMechanisms: Array<Record<string, unknown>>;
  dnaMechanismSeq: number;
  agents: Array<Record<string, unknown>>;
  skills: Array<Record<string, unknown>>;
  assistantFolders: Array<Record<string, unknown>>;
  assistantThreads: Array<Record<string, unknown>>;
  assistantThreadMessages: Array<Record<string, unknown>>;
  assistantGovernance: {
    userPreferences: Record<string, unknown>;
    workspaceSettings: Record<string, unknown>;
    workspaceSettingsByWs?: Record<string, Record<string, unknown>>;
    canEditWorkspaceLayer: boolean;
  };
  inboxNotifications: Array<Record<string, unknown>>;
  permissionBrokerPolicies: Array<Record<string, unknown>>;
  permissionBrokerTickets: Array<Record<string, unknown>>;
  orchestrationRuns: Array<{
    id: string;
    workspace_id: string;
    workflow_uri?: string;
    status: string;
    step_status: string;
    draft_artifact: Record<string, unknown>;
    committed_snapshot_id: string | null;
    human_anchors?: Array<Record<string, unknown>>;
    pending_arbitrations?: Array<Record<string, unknown>>;
  }>;
  aiModelMappings: Array<Record<string, unknown>>;
  autonomyContracts: Array<Record<string, unknown>>;
  workflowTriggers: Array<Record<string, unknown>>;
  mockReindexStatus: Record<string, unknown>;
  workflowsV2: Map<string, ApiWorkflowDefinitionV2>;
  recordedCalls: RecordedVitestApiCall[];
}

export function buildInitialWorkflowsV2Map(): Map<string, ApiWorkflowDefinitionV2> {
  const map = new Map<string, ApiWorkflowDefinitionV2>();
  for (const wf of INITIAL_WORKFLOWS_V2) {
    const apiWf = mapUiItemToApiWorkflowV2(wf);
    map.set(apiWf.id, apiWf);
  }
  return map;
}

export const backendState: MockBackendState = {
  firstAdmin: null,
  platformSetupState: null,
  orgUnits: [],
  orgUnitSeq: 0,
  workspaces: [],
  workspaceSeq: 0,
  workspaceWaivers: [],
  waiverSeq: 0,
  dnaMechanisms: [],
  dnaMechanismSeq: 0,
  agents: [],
  skills: [],
  assistantFolders: [],
  assistantThreads: [],
  assistantThreadMessages: [],
  assistantGovernance: {
    userPreferences: {
      response_tone: "BALANCED",
      favorite_format: "STRUCTURED_SECTIONS",
      default_hat: "PM",
      personal_instructions: "Privilégier des réponses claires.",
      sha256: "sha-user-default",
    },
    workspaceSettings: {
      workspace_instructions: "S'appuyer sur les documents de référence de l'espace.",
      mcp_expose_assistant: true,
      mcp_frozen_by_upper_layer: false,
      mcp_frozen_origin: null,
      mcp_ide_config_json: "{\"mcpServers\":{\"orcia\":{}}}",
      mcp_endpoint_url: "https://orcia.local/mcp",
      mcp_tool_name: "orcia_assistant",
      arbitration_policy: "PAUSE_AND_ESCALATE",
      default_checked_sources: [],
      recommended_agents: [],
      welcome_suggestions: [],
      sha256: "sha-ws-default",
    },
    workspaceSettingsByWs: {},
    canEditWorkspaceLayer: true,
  },
  inboxNotifications: [],
  permissionBrokerPolicies: [],
  permissionBrokerTickets: [],
  orchestrationRuns: [],
  aiModelMappings: [],
  autonomyContracts: [],
  workflowTriggers: [],
  mockReindexStatus: {
    status: "IDLE",
    progress_percentage: 0,
    indexed_chunks_count: 0,
    indexed_documents_count: 0,
  },
  workflowsV2: buildInitialWorkflowsV2Map(),
  recordedCalls: [],
};

export function problemResponse(
  status: number,
  errorCode: string,
  title: string,
  detail: string,
  instance: string,
): Response {
  return new Response(
    JSON.stringify({
      type: `https://orcia.io/problems/${errorCode.toLowerCase().replace(/_/g, "-")}`,
      title,
      status,
      detail,
      instance,
      trace_id: "0195f000000070008000000000000999",
      error_code: errorCode,
    }),
    {
      status,
      headers: { "Content-Type": "application/problem+json" },
    },
  );
}

export function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function parseJsonBody(init?: RequestInit): { body: Record<string, unknown>; hasRawBody: boolean; isMultipart: boolean } {
  if (!init?.body) {
    return { body: {}, hasRawBody: false, isMultipart: false };
  }
  if (typeof FormData !== "undefined" && init.body instanceof FormData) {
    return { body: {}, hasRawBody: true, isMultipart: true };
  }
  if (typeof init.body !== "string") {
    return { body: {}, hasRawBody: true, isMultipart: false };
  }
  try {
    return { body: JSON.parse(init.body) as Record<string, unknown>, hasRawBody: true, isMultipart: false };
  } catch {
    return { body: {}, hasRawBody: true, isMultipart: false };
  }
}

export function buildSseStreamResponse(chunks: readonly string[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

export function resetVitestApiBackend(): void {
  delete (globalThis as Record<string, unknown>).__ORCIA_MOCK_REFRESH_FAILS__;
  delete (globalThis as Record<string, unknown>).__VITEST_AUTH_MODE__;
  backendState.firstAdmin = null;
  writeCachedPlatformAdmin(null);
  backendState.platformSetupState = null;
  backendState.orgUnits = [];
  backendState.orgUnitSeq = 0;
  backendState.workspaces = [];
  backendState.workspaceSeq = 0;
  backendState.workspaceWaivers = [];
  backendState.waiverSeq = 0;
  backendState.dnaMechanisms = [];
  backendState.dnaMechanismSeq = 0;
  backendState.agents = [];
  backendState.skills = [];
  backendState.assistantFolders = [];
  backendState.assistantThreads = [];
  backendState.assistantThreadMessages = [];
  backendState.assistantGovernance = {
    userPreferences: {
      response_tone: "BALANCED",
      favorite_format: "STRUCTURED_SECTIONS",
      default_hat: "PM",
      personal_instructions: "Privilégier des réponses claires.",
      sha256: "sha-user-default",
    },
    workspaceSettings: {
      workspace_instructions: "S'appuyer sur les documents de référence de l'espace.",
      mcp_expose_assistant: true,
      mcp_frozen_by_upper_layer: false,
      mcp_frozen_origin: null,
      mcp_ide_config_json: "{\"mcpServers\":{\"orcia\":{}}}",
      mcp_endpoint_url: "https://orcia.local/mcp",
      mcp_tool_name: "orcia_assistant",
      arbitration_policy: "PAUSE_AND_ESCALATE",
      default_checked_sources: [],
      recommended_agents: [],
      welcome_suggestions: [],
      sha256: "sha-ws-default",
    },
    workspaceSettingsByWs: {},
    canEditWorkspaceLayer: true,
  };
  backendState.inboxNotifications = [];
  backendState.permissionBrokerPolicies = [];
  backendState.permissionBrokerTickets = [];
  backendState.orchestrationRuns = [];
  backendState.aiModelMappings = [];
  backendState.autonomyContracts = [];
  backendState.workflowTriggers = [];
  backendState.mockReindexStatus = {
    status: "IDLE",
    progress_percentage: 0,
    indexed_chunks_count: 0,
    indexed_documents_count: 0,
  };
  backendState.workflowsV2 = buildInitialWorkflowsV2Map();
  backendState.recordedCalls = [];
  resetVitestIamMockState();
  resetVitestConnectorsMockState();
  resetVitestAutonomousSupervisionMockState();
  resetVitestOntologyMockState();
  resetVitestPacksAndWizardsMockState();
  resetVitestAuthPolicyMockState();
  resetVitestReflexiveBackend();
  resetAuthSessionStore();
}

export function setVitestPublicAuthMode(mode: "LOCAL" | "SSO"): void {
  seedVitestPlatformAuthPolicy({ authMode: mode });
}

export function setVitestMockRefreshFails(fails: boolean): void {
  if (fails) {
    (globalThis as Record<string, unknown>).__ORCIA_MOCK_REFRESH_FAILS__ = true;
  } else {
    delete (globalThis as Record<string, unknown>).__ORCIA_MOCK_REFRESH_FAILS__;
  }
}

export function setVitestMockReindexStatus(statusRecord: Record<string, unknown>): void {
  backendState.mockReindexStatus = { ...statusRecord };
}

export function seedVitestPlatformSetupState(
  state: Record<string, unknown>,
  firstAdmin: { email: string; displayName: string; roles?: string[] } | null = { email: "admin@orcia.test", displayName: "Admin Test" },
): void {
  backendState.firstAdmin = firstAdmin;
  writeCachedPlatformAdmin(
    firstAdmin
      ? { displayName: firstAdmin.displayName, email: firstAdmin.email, role: "PLATFORM_ADMIN" }
      : null,
  );
  backendState.platformSetupState = state;
  backendState.orgUnits = hydrateMockOrgUnitsFromSetup(state.org_units);
  backendState.orgUnitSeq = backendState.orgUnits.length;
  if (state.ai_model_mappings !== undefined) {
    backendState.aiModelMappings = Array.isArray(state.ai_model_mappings)
      ? (state.ai_model_mappings as Array<Record<string, unknown>>)
      : [];
  } else if (firstAdmin !== null) {
    backendState.aiModelMappings = [
      {
        id: "01930000-0000-7000-8000-000000000099",
        scope_level: "GLOBAL",
        scope_id: null,
        inference_tier: "light",
        usage: "embedding",
        is_active: true,
        provider: "ollama",
        model_name: "bge-m3:latest",
      },
    ];
  } else {
    backendState.aiModelMappings = [];
  }
  if (Array.isArray(state.runs)) {
    backendState.orchestrationRuns = (state.runs as Array<Record<string, unknown>>).map((r) => ({
      id: String(r.runId ?? r.id ?? "0195f000-0000-7000-8000-000000000701"),
      workspace_id: String(r.workspaceId ?? r.workspace_id ?? "0192c4e0-0000-7000-8000-000000000201"),
      workflow_uri: "orcia://workflows/claims-engineering-delivery",
      status: String(r.status ?? "RUNNING"),
      step_status: "WAITING_FOR_HUMAN_ANCHOR",
      draft_artifact: {},
      committed_snapshot_id: null,
      human_anchors: [],
      pending_arbitrations: [],
    }));
  }
}

export function getRecordedVitestApiCalls(): readonly RecordedVitestApiCall[] {
  return backendState.recordedCalls;
}

export function seedVitestInboxNotifications(items: Array<Record<string, unknown>>): void {
  backendState.inboxNotifications = items.map((item) => ({ ...item }));
}

export function seedVitestPermissionBrokerTickets(tickets: Array<Record<string, unknown>>): void {
  backendState.permissionBrokerTickets = tickets.map((ticket) => ({ ...ticket }));
}
