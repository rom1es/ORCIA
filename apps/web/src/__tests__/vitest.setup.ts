import type { ApiWorkflowDefinitionV2 } from "@orcia/api-client";
import type { UiAssistantSpeedMode, UiInferenceEffort } from "@orcia/ui";
import { beforeEach } from "vitest";
import {
  evaluateVitestLocalLoginPolicy,
  getVitestBootEpoch,
  handleVitestAuthPolicyRoute,
  resetVitestAuthPolicyMockState,
  seedVitestPlatformAuthPolicy,
} from "./vitestAuthPolicyMockHandlers";
import {
  detectAdaptiveThinkingStepsForQuestion,
  shouldUseProgressiveStepThinking,
} from "../features/inbox/assistantBackgroundStreamStore";
import { writeCachedPlatformAdmin } from "../components/platformSetupStorageHelpers";
import { INITIAL_WORKFLOWS_V2 } from "../features/processes/processStudioV2Data";
import { mapUiItemToApiWorkflowV2 } from "../features/processes/studio/studioLabelsAndMappers";
import {
  resetVitestReflexiveBackend,
  tryHandleVitestReflexiveEndpoint,
} from "./vitestReflexiveBackend";

export interface RecordedVitestApiCall {
  readonly method: string;
  readonly path: string;
  readonly body: unknown;
  readonly headers?: Record<string, string>;
}

interface MockOrganizationalUnit {
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

interface MockBackendState {
  firstAdmin: {
    email: string;
    displayName: string;
    roles?: string[];
  } | null;
  platformSetupState: Record<string, unknown> | null;
  orgUnits: MockOrganizationalUnit[];
  orgUnitSeq: number;
  agents: Array<Record<string, unknown>>;
  skills: Array<Record<string, unknown>>;
  assistantFolders: Array<Record<string, unknown>>;
  orchestrationRuns: Array<{
    id: string;
    workspace_id: string;
    status: string;
    step_status: string;
    draft_artifact: Record<string, unknown>;
    committed_snapshot_id: string | null;
  }>;
  aiModelMappings: Array<Record<string, unknown>>;
  autonomyContracts: Array<Record<string, unknown>>;
  workflowTriggers: Array<Record<string, unknown>>;
  mockReindexStatus: Record<string, unknown>;
  workflowsV2: Map<string, ApiWorkflowDefinitionV2>;
  recordedCalls: RecordedVitestApiCall[];
}

class VitestResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = VitestResizeObserverMock as unknown as typeof ResizeObserver;
}

function buildInitialWorkflowsV2Map(): Map<string, ApiWorkflowDefinitionV2> {
  const map = new Map<string, ApiWorkflowDefinitionV2>();
  for (const wf of INITIAL_WORKFLOWS_V2) {
    const apiWf = mapUiItemToApiWorkflowV2(wf);
    map.set(apiWf.id, apiWf);
  }
  return map;
}

const backendState: MockBackendState = {
  firstAdmin: null,
  platformSetupState: null,
  orgUnits: [],
  orgUnitSeq: 0,
  agents: [],
  skills: [],
  assistantFolders: [],
  orchestrationRuns: [],
  aiModelMappings: [],
  autonomyContracts: [],
  workflowTriggers: [],
  mockReindexStatus: { status: "IDLE", progress_percentage: 0 },
  workflowsV2: buildInitialWorkflowsV2Map(),
  recordedCalls: [],
};

import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";
import {
  getVitestIamAccounts,
  handleVitestIamRoute,
  resetVitestIamMockState,
  syncVitestIamRolesWithOrgUnits,
  upsertVitestIamOrgInvitedUser,
} from "./vitestIamMockHandlers";
import {
  handleVitestConnectorsRoute,
  resetVitestConnectorsMockState,
} from "./vitestConnectorsMockHandlers";
import {
  handleVitestAutonomousSupervisionRoute,
  resetVitestAutonomousSupervisionMockState,
} from "./vitestAutonomousSupervisionMockHandlers";
import {
  handleVitestOntologyRoute,
  resetVitestOntologyMockState,
} from "./vitestOntologyMockHandlers";

function hydrateMockOrgUnitsFromSetup(rawUnits: unknown): MockOrganizationalUnit[] {
  if (!Array.isArray(rawUnits)) return [];
  return rawUnits.map((raw, index) => {
    const item = raw as Record<string, unknown>;
    const id = String(item.id ?? `org-${index + 1}`);
    const name = String(item.name ?? id);
    const slug = String(
      item.slug ?? name.toLowerCase().replace(/[^a-z0-9-]+/g, "-").replace(/^-|-$/g, ""),
    );
    const rawLevel = String(item.level ?? item.kind ?? "BU").toUpperCase();
    const kind: "BU" | "TEAM" = rawLevel === "TEAM" ? "TEAM" : "BU";
    const rawParent = item.parentId ?? item.parent_id ?? null;
    const parent_id =
      typeof rawParent === "string" && rawParent.trim() && rawParent !== "scope-global"
        ? rawParent.trim()
        : null;
    const billing_enabled =
      item.billingEnabled !== undefined
        ? Boolean(item.billingEnabled)
        : item.billing_enabled !== undefined
          ? Boolean(item.billing_enabled)
          : true;
    const rawLead = item.leadUserId ?? item.lead_user_id ?? null;
    const lead_user_id =
      typeof rawLead === "string" && rawLead.trim() ? rawLead.trim() : null;
    const rawLeadIds = item.leadUserIds ?? item.lead_user_ids ?? [];
    const lead_user_ids = Array.isArray(rawLeadIds) && rawLeadIds.length > 0
      ? rawLeadIds.map((l) => String(l).trim()).filter(Boolean)
      : (lead_user_id ? [lead_user_id] : []);
    const rawOntologyLeads = item.ontologyLeadUserIds ?? item.ontology_lead_user_ids ?? [];
    const ontology_lead_user_ids =
      kind === "BU" && Array.isArray(rawOntologyLeads)
        ? rawOntologyLeads.map((l) => String(l).trim()).filter(Boolean)
        : [];
    const rawMembers = item.memberUserIds ?? item.member_user_ids ?? [];
    const member_user_ids = Array.isArray(rawMembers)
      ? rawMembers.map((m) => String(m).trim()).filter(Boolean)
      : [];
    return {
      id,
      slug,
      name,
      kind,
      parent_id,
      billing_enabled,
      lead_user_id: lead_user_ids[0] ?? lead_user_id,
      lead_user_ids,
      ontology_lead_user_ids,
      member_user_ids: kind === "BU" ? [] : member_user_ids,
    };
  });
}

function syncSetupOrgUnitsFromMock(): void {
  const mapped = backendState.orgUnits.map((u) => ({
    id: u.id,
    name: u.name,
    slug: u.slug,
    level: u.kind,
    parentId: u.parent_id ?? "scope-global",
    billingEnabled: u.billing_enabled,
    leadUserId: u.lead_user_id,
    leadUserIds: u.lead_user_ids ?? (u.lead_user_id ? [u.lead_user_id] : []),
    ontologyLeadUserIds: u.kind === "BU" ? (u.ontology_lead_user_ids ?? []) : [],
    memberUserIds: u.kind === "BU" ? [] : u.member_user_ids,
  }));
  if (backendState.platformSetupState) {
    backendState.platformSetupState = {
      ...backendState.platformSetupState,
      org_units: mapped,
    };
  } else if (mapped.length > 0) {
    backendState.platformSetupState = {
      org_units: mapped,
      rbac_grants: [],
      llm_tiers: [],
      workspaces: [],
      datasources: [],
      packs: [],
      workflows: [],
      runs: [],
      catalog_items: [],
      ontology_concepts: [],
      audit_events: [],
    };
  }
  syncVitestIamRolesWithOrgUnits(backendState.orgUnits);
}

function countAttachedWorkspacesForUnit(unitId: string): {
  readonly count: number;
  readonly names: readonly string[];
} {
  const rawWs = backendState.platformSetupState?.workspaces;
  if (!Array.isArray(rawWs)) return { count: 0, names: [] };
  const matched = rawWs
    .map((w) => w as Record<string, unknown>)
    .filter((w) => String(w.ownerOrgUnitId ?? "") === unitId);
  return {
    count: matched.length,
    names: matched.map((w) => String(w.name ?? w.workspaceId ?? "")).filter(Boolean),
  };
}

function problemResponse(
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

export function resetVitestApiBackend(): void {
  delete (globalThis as Record<string, unknown>).__ORCIA_MOCK_REFRESH_FAILS__;
  delete (globalThis as Record<string, unknown>).__VITEST_AUTH_MODE__;
  backendState.firstAdmin = null;
  writeCachedPlatformAdmin(null);
  backendState.platformSetupState = null;
  backendState.orgUnits = [];
  backendState.orgUnitSeq = 0;
  backendState.agents = [];
  backendState.skills = [];
  backendState.assistantFolders = [];
  backendState.orchestrationRuns = [];
  backendState.aiModelMappings = [];
  backendState.autonomyContracts = [];
  backendState.workflowTriggers = [];
  backendState.mockReindexStatus = { status: "IDLE", progress_percentage: 0 };
  backendState.workflowsV2 = buildInitialWorkflowsV2Map();
  backendState.recordedCalls = [];
  resetVitestIamMockState();
  resetVitestConnectorsMockState();
  resetVitestAutonomousSupervisionMockState();
  resetVitestOntologyMockState();
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

/** Pré-remplit le 1er administrateur et l'état de plateforme servis par le backend simulé. */
export function seedVitestPlatformSetupState(
  state: Record<string, unknown>,
  firstAdmin: { email: string; displayName: string; roles?: string[] } | null = { email: "admin@orcia.test", displayName: "Admin Test" },
): void {
  backendState.firstAdmin = firstAdmin;
  writeCachedPlatformAdmin(
    firstAdmin
      ? {
          displayName: firstAdmin.displayName,
          email: firstAdmin.email,
          role: "PLATFORM_ADMIN",
        }
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
}

export function getRecordedVitestApiCalls(): readonly RecordedVitestApiCall[] {
  return backendState.recordedCalls;
}

(globalThis as Record<string, unknown>).__ORCIA_RESET_VITEST_BACKEND__ = resetVitestApiBackend;

if (typeof window !== "undefined") {
  window.scrollTo = () => undefined;
}

beforeEach(() => {
  resetVitestApiBackend();
});

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function parseJsonBody(init?: RequestInit): Record<string, unknown> {
  if (!init?.body || typeof init.body !== "string") {
    return {};
  }
  try {
    return JSON.parse(init.body) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function buildSseStreamResponse(chunks: readonly string[]): Response {
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

async function vitestFetchTransport(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const rawUrl =
    typeof input === "string"
      ? input
      : input instanceof URL
        ? input.toString()
        : input.url;
  const parsedUrl = new URL(rawUrl, "http://127.0.0.1:8000");
  const path = parsedUrl.pathname;
  const method = (init?.method ?? "GET").toUpperCase();
  const body = parseJsonBody(init);
  const reqHeaders = new Headers(init?.headers);
  const capturedHeadersObj: Record<string, string> = {};
  reqHeaders.forEach((v, k) => {
    capturedHeadersObj[k.toLowerCase()] = v;
  });

  backendState.recordedCalls.push({
    method,
    path,
    body,
    headers: capturedHeadersObj,
  });

  // 1. Accostage & Platform Setup State
  if (path === "/api/v1/bootstrap/accostage-status" && method === "GET") {
    if (backendState.firstAdmin) {
      return jsonResponse({
        first_admin_initialized: true,
        first_admin_email: backendState.firstAdmin.email,
        first_admin_display_name: backendState.firstAdmin.displayName,
        boot_epoch: getVitestBootEpoch(),
      });
    }
    return jsonResponse({
      first_admin_initialized: false,
      first_admin_email: null,
      first_admin_display_name: null,
      boot_epoch: getVitestBootEpoch(),
    });
  }

  if (
    (path === "/api/v1/bootstrap/welcome-setup/first-admin" ||
      path === "/api/v1/bootstrap/welcome-setup") &&
    method === "POST"
  ) {
    const email = String(body.email ?? "admin@orcia.local");
    const displayName = String(body.display_name ?? email);
    backendState.firstAdmin = { email, displayName };
    return jsonResponse({
      first_admin_initialized: true,
      first_admin_email: email,
      first_admin_display_name: displayName,
      access_token: "mock-first-admin-access-token",
      token_type: "bearer",
    });
  }

  // 1b. Authentification & Sessions
  if (path === "/api/v1/auth/login/local" && method === "POST") {
    const email = String(body.email ?? "admin@orcia.local").toLowerCase();
    const isMockFirstAdmin =
      backendState.firstAdmin && backendState.firstAdmin.email.toLowerCase() === email;
    const iamAccounts = getVitestIamAccounts();
    const iamUser = iamAccounts.find(
      (a) => a.principal_id.toLowerCase() === email || a.email?.toLowerCase() === email,
    );
    const displayName =
      iamUser?.display_name ??
      (isMockFirstAdmin ? backendState.firstAdmin!.displayName : "Romain Admin");
    const roles = iamUser?.roles ?? ["PLATFORM_ADMIN"];
    const policyGate = evaluateVitestLocalLoginPolicy({
      email,
      displayName,
      roles,
      path,
      jsonResponse,
      problemResponse,
    });
    if (policyGate !== null) {
      return policyGate;
    }
    return jsonResponse({
      access_token: "mock-access-token",
      token_type: "bearer",
      roles,
      user_id: iamUser?.id ?? "usr-vitest-1",
      email,
      display_name: displayName,
      platform_role: roles[0] ?? "PLATFORM_ADMIN",
      requires_two_factor: false,
      must_change_password: false,
      issued_at_iso: "2026-11-14T12:00:00Z",
    });
  }

  if (path === "/api/v1/auth/me" && method === "GET") {
    const targetEmail =
      backendState.firstAdmin?.email ??
      useAuthSessionStore.getState().email ??
      "admin@orcia.local";
    const targetDisplayName =
      backendState.firstAdmin?.displayName ??
      useAuthSessionStore.getState().displayName ??
      "Administrateur Plateforme";
    const matchedAccount = getVitestIamAccounts().find(
      (a) =>
        a.principal_id.toLowerCase() === targetEmail.toLowerCase() ||
        (a.email && a.email.toLowerCase() === targetEmail.toLowerCase()),
    );
    const storeRoles = useAuthSessionStore.getState().roles;
    const resolvedRoles =
      matchedAccount?.roles ?? (storeRoles.length > 0 ? storeRoles : ["PLATFORM_ADMIN"]);
    const activeHat =
      useAuthSessionStore.getState().activeHat ||
      (resolvedRoles.includes("PLATFORM_ADMIN") ? "PLATFORM_ADMIN" : resolvedRoles[0] || "CONTRIBUTOR");

    return jsonResponse({
      user_id: "usr-vitest-1",
      email: targetEmail,
      display_name: targetDisplayName,
      roles: resolvedRoles,
      active_hat: activeHat,
      access_mode: "READ_WRITE",
      must_change_password: false,
      workspaces: [],
    });
  }

  if (path === "/api/v1/auth/session" && method === "GET") {
    if ((globalThis as Record<string, unknown>).__ORCIA_MOCK_REFRESH_FAILS__) {
      return jsonResponse({
        authenticated: false,
        session: null,
        trace_id: "01a1dead000000000000000000000001",
      });
    }
    const targetEmail =
      backendState.firstAdmin?.email ??
      useAuthSessionStore.getState().email ??
      "admin@orcia.local";
    const targetDisplayName =
      backendState.firstAdmin?.displayName ??
      useAuthSessionStore.getState().displayName ??
      "Administrateur Plateforme";
    const matchedAccount = getVitestIamAccounts().find(
      (a) =>
        a.principal_id.toLowerCase() === targetEmail.toLowerCase() ||
        (a.email && a.email.toLowerCase() === targetEmail.toLowerCase()),
    );
    const storeRoles = useAuthSessionStore.getState().roles;
    const resolvedRoles =
      matchedAccount?.roles ?? (storeRoles.length > 0 ? storeRoles : ["PLATFORM_ADMIN"]);
    const platformRole = resolvedRoles.includes("PLATFORM_ADMIN")
      ? "PLATFORM_ADMIN"
      : resolvedRoles[0] || "CONTRIBUTOR";

    return jsonResponse({
      authenticated: true,
      session: {
        access_token: "mock-refreshed-token",
        token_type: "Bearer",
        expires_in_seconds: 900,
        roles: resolvedRoles,
        platform_role: platformRole,
        human_profile_archetype: "Tech Lead",
        primary_org_unit_id: "org-root",
        user_id: "usr-vitest-1",
        email: targetEmail,
        display_name: targetDisplayName,
        must_change_password: false,
        requires_two_factor: false,
        trace_id: "01a1dead000000000000000000000002",
      },
      trace_id: "01a1dead000000000000000000000002",
    });
  }

  if (path === "/api/v1/auth/refresh" && method === "POST") {
    if ((globalThis as Record<string, unknown>).__ORCIA_MOCK_REFRESH_FAILS__) {
      return problemResponse(
        401,
        "ERR_AUTH_TOKEN_EXPIRED",
        "Session expirée",
        "Le jeton de rafraîchissement est absent ou invalide.",
        path,
      );
    }
    return jsonResponse({
      access_token: "mock-refreshed-token",
      token_type: "bearer",
      roles: ["PLATFORM_ADMIN"],
      user_id: "usr-vitest-1",
      email: backendState.firstAdmin?.email ?? "admin@orcia.local",
      display_name: backendState.firstAdmin?.displayName ?? "Administrateur Plateforme",
      must_change_password: false,
      issued_at_iso: "2026-11-14T12:00:00Z",
    });
  }

  if (path === "/api/v1/auth/logout" && method === "POST") {
    return jsonResponse({ message: "Successfully logged out" });
  }

  if (path === "/api/v1/auth/change-password" && method === "POST") {
    if (body?.current_password === "WrongCurrentPassword123" || body?.current_password === "wrong") { // pragma: allowlist secret
      return jsonResponse(
        {
          type: "https://orcia.fr/errors/auth-current-password-invalid",
          title: "Mot de passe actuel incorrect",
          status: 422,
          detail: "Le mot de passe actuel saisi est incorrect. Vérifiez votre saisie puis réessayez.",
          error_code: "ERR_AUTH_CURRENT_PASSWORD_INVALID",
        },
        422,
      );
    }
    return jsonResponse({ message: "Password updated successfully" });
  }

  if (path === "/api/v1/bootstrap/platform-setup-state" && method === "PUT") {
    backendState.platformSetupState = body;
    if (Array.isArray(body.org_units) && (body.org_units.length > 0 || backendState.orgUnits.length === 0)) {
      backendState.orgUnits = hydrateMockOrgUnitsFromSetup(body.org_units);
      backendState.orgUnitSeq = Math.max(backendState.orgUnitSeq, backendState.orgUnits.length);
    }
    return jsonResponse(body);
  }

  if (path === "/api/v1/bootstrap/platform-setup-state" && method === "GET") {
    return jsonResponse(
      backendState.platformSetupState ?? {
        org_units: [],
        rbac_grants: [],
        llm_tiers: [],
        workspaces: [],
        datasources: [],
        packs: [],
        workflows: [],
        runs: [],
        catalog_items: [],
        ontology_concepts: [],
        audit_events: [],
      },
    );
  }

  // 1c. Audit Ledger & Run Provenance (Story 6.1)
  if (path.startsWith("/api/v1/audit/ledger") && method === "GET") {
    if (path.includes("/provenance")) {
      const parts = path.split("/");
      const runId = parts[5] ?? "run-1";
      return jsonResponse({
        run_id: runId,
        root_run_id: null,
        total_events: 1,
        total_input_tokens: 1000,
        total_output_tokens: 500,
        total_cost_usd: 0.002,
        models_invoked: ["qwen2.5-coder"],
        actors_involved: ["Admin"],
        run_lock_sha256: "sha256-verified-lock",
        workflow_contract_sha256: "sha256-contract",
        cas_references: ["seaweedfs://blobs/sha-1"],
        is_run_lock_aligned: true,
        first_event_at: new Date().toISOString(),
        last_event_at: new Date().toISOString(),
      });
    }
    if (path.includes("/export")) {
      const parts = path.split("/");
      const runId = parts[5] ?? "run-1";
      const isMd = (parsedUrl.searchParams.get("format") ?? "json") === "md";
      return jsonResponse({
        run_id: runId,
        format: isMd ? "md" : "json",
        content: isMd ? "# Dossier Certifié" : "{}",
        exported_at: new Date().toISOString(),
        manifest_sha256: "sha256-verified-lock",
        entries_count: 1,
      });
    }

    const rawAudit = (backendState.platformSetupState?.audit_events as Array<Record<string, unknown>>) ?? [];
    const entries = rawAudit.map((e, idx) => ({
      id: String(e.id ?? `evt-${idx + 1}`),
      source_event_id: String(e.source_event_id ?? e.sourceEventId ?? `01933e7e-0000-7000-8000-${String(idx + 1).padStart(12, "0")}`),
      workspace_id: e.workspace_id ?? e.workspaceId ?? e.scopeId ?? null,
      scope_path: String(e.scope_path ?? e.scopePath ?? "GLOBAL"),
      run_id: e.run_id ?? e.runId ?? null,
      actor_type: String(e.actor_type ?? e.actorType ?? "USER"),
      actor_id: String(e.actor_id ?? e.actorId ?? e.actorEmail ?? "admin"),
      actor_display_name: String(e.actor_display_name ?? e.actorName ?? "Administrateur"),
      actor_email: e.actor_email ?? e.actorEmail ?? null,
      event_type: String(e.event_type ?? e.eventType ?? "RecordedAction"),
      summary: String(e.summary ?? ""),
      cost_usd: Number(e.cost_usd ?? e.costUsd ?? 0),
      input_tokens: Number(e.input_tokens ?? e.inputTokens ?? 0),
      output_tokens: Number(e.output_tokens ?? e.outputTokens ?? 0),
      created_at: String(e.created_at ?? e.timestampIso ?? new Date().toISOString()),
    }));

    return jsonResponse({
      entries,
      total: entries.length,
      limit: Number(parsedUrl.searchParams.get("limit") ?? 500),
      offset: Number(parsedUrl.searchParams.get("offset") ?? 0),
    });
  }

  // 1b. Hierarchical Organization Units CRUD (/api/v1/org-units — Story 17.2)
  const MOCK_KNOWN_ORG_USERS = [
    { principal_id: "claire.admin@orcia.fr", display_name: "Claire Admin", email: "claire.admin@orcia.fr" },
    { principal_id: "vp.produit@orcia.fr", display_name: "VP Produit", email: "vp.produit@orcia.fr" },
    { principal_id: "marc.lead@orcia.fr", display_name: "Marc Lead", email: "marc.lead@orcia.fr" },
    { principal_id: "alice@orcia.fr", display_name: "Alice Développeuse", email: "alice@orcia.fr" },
    { principal_id: "bob@orcia.fr", display_name: "Bob Ingénieur", email: "bob@orcia.fr" },
    { principal_id: "romain@orcia.fr", display_name: "Romain Esnault", email: "romain@orcia.fr" },
  ];

  const isMockUserKnown = (val: string) => {
    const needle = val.trim().toLowerCase();
    return getAllMockKnownOrgUsers().some(
      (u) =>
        u.principal_id.toLowerCase() === needle ||
        (u.email && u.email.toLowerCase() === needle),
    );
  };

  const getAllMockKnownOrgUsers = () => {
    const iamAccounts = getVitestIamAccounts()
      .filter((a) => a.account_kind === "HUMAN" && a.status !== "DISABLED")
      .map((a) => ({
        principal_id: a.principal_id,
        display_name: a.display_name,
        email: a.email,
      }));
    const byKey = new Map<string, { principal_id: string; display_name: string; email: string | null }>();
    for (const u of [...MOCK_KNOWN_ORG_USERS, ...iamAccounts]) {
      const k = u.principal_id.toLowerCase().trim();
      if (!byKey.has(k)) {
        byKey.set(k, u);
      }
    }
    return Array.from(byKey.values()).sort((a, b) =>
      a.display_name.localeCompare(b.display_name),
    );
  };

  if (path === "/api/v1/org-units/known-users" && method === "GET") {
    const qParam = parsedUrl.searchParams.get("q")?.trim()?.toLowerCase() ?? null;
    const limitParamRaw = parsedUrl.searchParams.get("limit");
    const limit = limitParamRaw ? parseInt(limitParamRaw, 10) : 10;

    let users = getAllMockKnownOrgUsers();
    if (qParam) {
      users = users.filter(
        (u) =>
          u.display_name.toLowerCase().includes(qParam) ||
          u.principal_id.toLowerCase().includes(qParam) ||
          (u.email && u.email.toLowerCase().includes(qParam)),
      );
    }
    const hasMore = users.length > limit;
    return jsonResponse({
      items: users.slice(0, limit),
      has_more: hasMore,
    });
  }

  const resolveMockOrgActor = () => {
    const session = useAuthSessionStore.getState();
    const headerHat = reqHeaders.get("x-orcia-active-hat")?.trim().toUpperCase();
    const activeHat =
      headerHat ||
      (session.activeHat ? String(session.activeHat).toUpperCase() : "") ||
      (session.roles?.[0] ? String(session.roles[0]).toUpperCase() : "") ||
      "PLATFORM_ADMIN";
    const candidates = new Set<string>();
    if (session.email) candidates.add(session.email.toLowerCase());
    if (session.displayName) candidates.add(session.displayName.toLowerCase());
    const hasSessionUser = Boolean(
      session.email || session.activeHat || (session.roles && session.roles.length > 0),
    );
    return { activeHat, candidates, hasSessionUser };
  };

  const computeOrgSubtreeAndAncestors = (actorCandidates: Set<string>, activeHat: string) => {
    const byId = new Map(backendState.orgUnits.map((u) => [u.id, u]));
    const isLead = (u: MockOrganizationalUnit) => {
      const leads = u.lead_user_ids ?? (u.lead_user_id ? [u.lead_user_id] : []);
      return leads.some((id) => actorCandidates.has(id.toLowerCase()));
    };
    const isOntologyLead = (u: MockOrganizationalUnit) =>
      (u.ontology_lead_user_ids ?? []).some((id) => actorCandidates.has(id.toLowerCase()));
    const isMember = (u: MockOrganizationalUnit) =>
      u.member_user_ids.some((id) => actorCandidates.has(id.toLowerCase()));

    const collectDescendants = (seeds: Set<string>) => {
      const result = new Set(seeds);
      let changed = true;
      while (changed) {
        changed = false;
        for (const u of backendState.orgUnits) {
          if (u.parent_id && result.has(u.parent_id) && !result.has(u.id)) {
            result.add(u.id);
            changed = true;
          }
        }
      }
      return result;
    };
    const collectAncestors = (seeds: Set<string>) => {
      const result = new Set<string>();
      for (const id of seeds) {
        let cur = byId.get(id)?.parent_id ?? null;
        const guard = new Set<string>([id]);
        while (cur && !guard.has(cur)) {
          guard.add(cur);
          result.add(cur);
          cur = byId.get(cur)?.parent_id ?? null;
        }
      }
      return result;
    };

    if (activeHat === "BU_LEAD" || activeHat === "BU_DIRECTOR") {
      const directBus = new Set(
        backendState.orgUnits.filter((u) => u.kind === "BU" && isLead(u)).map((u) => u.id),
      );
      const managed = collectDescendants(directBus);
      const rootLedBus = new Set(
        Array.from(directBus).filter((id) => {
          const p = byId.get(id)?.parent_id;
          return !p || !managed.has(p);
        }),
      );
      const ancestors = collectAncestors(managed);
      const visible = new Set([...managed, ...ancestors]);
      return { managed, rootLedBus, visible };
    }
    if (activeHat === "TEAM_LEAD") {
      const managed = new Set(
        backendState.orgUnits.filter((u) => u.kind === "TEAM" && isLead(u)).map((u) => u.id),
      );
      const ancestors = collectAncestors(managed);
      const visible = new Set([...managed, ...ancestors]);
      return { managed, rootLedBus: new Set<string>(), visible };
    }
    if (activeHat === "ONTOLOGY_LEAD") {
      const ledBus = new Set(
        backendState.orgUnits.filter((u) => u.kind === "BU" && isOntologyLead(u)).map((u) => u.id),
      );
      const visible = new Set([...collectDescendants(ledBus), ...collectAncestors(ledBus)]);
      return { managed: new Set<string>(), rootLedBus: new Set<string>(), visible };
    }
    if (activeHat === "CONTRIBUTOR") {
      const teams = new Set(
        backendState.orgUnits.filter((u) => u.kind === "TEAM" && isMember(u)).map((u) => u.id),
      );
      const visible = new Set([...teams, ...collectAncestors(teams)]);
      return { managed: new Set<string>(), rootLedBus: new Set<string>(), visible };
    }
    return {
      managed: new Set(backendState.orgUnits.map((u) => u.id)),
      rootLedBus: new Set<string>(),
      visible: new Set(backendState.orgUnits.map((u) => u.id)),
    };
  };

  if (path === "/api/v1/org-units" && method === "GET") {
    const qParam = parsedUrl.searchParams.get("q")?.trim()?.toLowerCase() ?? null;
    const kindParam = parsedUrl.searchParams.get("kind")?.toUpperCase() ?? null;
    const limitParamRaw = parsedUrl.searchParams.get("limit");
    const limitParam = limitParamRaw ? parseInt(limitParamRaw, 10) : null;

    const { activeHat, candidates, hasSessionUser } = resolveMockOrgActor();
    const scopeInfo = hasSessionUser
      ? computeOrgSubtreeAndAncestors(candidates, activeHat)
      : null;

    let units = backendState.orgUnits
      .filter((u) => {
        if (!scopeInfo || activeHat === "PLATFORM_ADMIN" || activeHat === "SECOPS") {
          return true;
        }
        return scopeInfo.visible.has(u.id);
      })
      .map((u) => {
        const isBu = u.kind === "BU";
        let canEdit = true;
        let canCreateChild = isBu;
        let canDelete = true;
        let canManageMembers = !isBu;
        let canManageOntologyLeads = isBu;
        let canInviteUsers = true;

        if (hasSessionUser) {
          if (activeHat === "PLATFORM_ADMIN") {
            // full access
          } else if ((activeHat === "BU_LEAD" || activeHat === "BU_DIRECTOR") && scopeInfo) {
            const inManaged = scopeInfo.managed.has(u.id);
            canEdit = inManaged;
            canCreateChild = inManaged && isBu;
            canDelete = inManaged && !scopeInfo.rootLedBus.has(u.id);
            canManageMembers = inManaged && !isBu;
            canManageOntologyLeads = inManaged && isBu;
            canInviteUsers = inManaged;
          } else if (activeHat === "TEAM_LEAD" && scopeInfo) {
            const inManaged = scopeInfo.managed.has(u.id);
            canEdit = inManaged;
            canCreateChild = false;
            canDelete = false;
            canManageMembers = inManaged && !isBu;
            canManageOntologyLeads = false;
            canInviteUsers = false;
          } else {
            canEdit = false;
            canCreateChild = false;
            canDelete = false;
            canManageMembers = false;
            canManageOntologyLeads = false;
            canInviteUsers = false;
          }
        }

        return {
          ...u,
          lead_user_id: u.lead_user_id ?? (u.lead_user_ids?.[0] ?? null),
          lead_user_ids: u.lead_user_ids ?? (u.lead_user_id ? [u.lead_user_id] : []),
          ontology_lead_user_ids: isBu ? (u.ontology_lead_user_ids ?? []) : [],
          attached_workspaces_count: countAttachedWorkspacesForUnit(u.id).count,
          can_edit: u.can_edit ?? canEdit,
          can_create_child: u.can_create_child ?? canCreateChild,
          can_delete: u.can_delete ?? canDelete,
          can_manage_members: u.can_manage_members ?? canManageMembers,
          can_manage_ontology_leads: u.can_manage_ontology_leads ?? canManageOntologyLeads,
          can_invite_users: u.can_invite_users ?? canInviteUsers,
        };
      });

    if (kindParam) {
      units = units.filter(
        (u) => ((u as unknown as { level?: string }).level || u.kind) === kindParam,
      );
    }
    if (qParam) {
      units = units.filter(
        (u) =>
          u.name.toLowerCase().includes(qParam) ||
          (u.slug ? u.slug.toLowerCase().includes(qParam) : false),
      );
    }
    if (limitParam && limitParam > 0) {
      units = units.slice(0, limitParam);
    }

    return jsonResponse({
      org_units: units,
      known_users: getAllMockKnownOrgUsers(),
      trace_id: "0195f000000070008000000000000999",
    });
  }

  if (path === "/api/v1/org-units/invite-user" && method === "POST") {
    const accessMode = (reqHeaders.get("x-orcia-access-mode") ?? "").toUpperCase();
    const { activeHat, candidates, hasSessionUser } = resolveMockOrgActor();
    if (accessMode === "READ_ONLY_OBSERVER" || activeHat === "OBSERVER") {
      return problemResponse(
        403,
        "ERR_OBSERVER_MODE_READ_ONLY",
        "Mode observateur en lecture seule",
        "Les mutations sont refusées en mode observateur lecture seule.",
        path,
      );
    }
    if (!["PLATFORM_ADMIN", "BU_LEAD", "BU_DIRECTOR"].includes(activeHat)) {
      return problemResponse(
        403,
        "ERR_SCOPE_ACCESS_DENIED",
        "Accès au périmètre refusé",
        "Seul un Administrateur Plateforme ou un Responsable de BU peut inviter dans son périmètre.",
        path,
      );
    }
    const requestedRole = String(body.assignment_role ?? body.role ?? "").trim().toUpperCase();
    if (requestedRole === "PLATFORM_ADMIN" || requestedRole === "SECOPS") {
      return problemResponse(
        403,
        "ERR_PRIVILEGE_ESCALATION_FORBIDDEN",
        "Escalade de privilèges interdite",
        "L'attribution de PLATFORM_ADMIN ou SECOPS est interdite depuis Mon Organisation.",
        path,
      );
    }
    const targetUnitId = String(body.target_org_unit_id ?? "").trim();
    const targetUnit = backendState.orgUnits.find((u) => u.id === targetUnitId);
    if (!targetUnit) {
      return problemResponse(
        404,
        "ERR_RESOURCE_NOT_FOUND",
        "Unité introuvable",
        `Unité organisationnelle introuvable : '${targetUnitId}'.`,
        path,
      );
    }
    if (hasSessionUser && (activeHat === "BU_LEAD" || activeHat === "BU_DIRECTOR")) {
      const scopeInfo = computeOrgSubtreeAndAncestors(candidates, activeHat);
      if (!scopeInfo.managed.has(targetUnit.id)) {
        return problemResponse(
          403,
          "ERR_SCOPE_ACCESS_DENIED",
          "Hors périmètre de délégation",
          "Cette unité n'appartient pas à votre périmètre BU.",
          path,
        );
      }
    }
    const email = String(body.email ?? "").trim().toLowerCase();
    const displayName = String(body.display_name ?? email).trim();
    const account = upsertVitestIamOrgInvitedUser({
      email,
      displayName,
      role: requestedRole,
      targetUnitId: targetUnit.id,
      targetUnitKind: targetUnit.kind,
    });
    if (requestedRole === "TEAM_MEMBER") {
      if (!targetUnit.member_user_ids.includes(email)) {
        targetUnit.member_user_ids = [...targetUnit.member_user_ids, email];
      }
    } else if (requestedRole === "TEAM_LEAD" || requestedRole === "BU_LEAD") {
      const leads = targetUnit.lead_user_ids ?? (targetUnit.lead_user_id ? [targetUnit.lead_user_id] : []);
      if (!leads.includes(email)) {
        targetUnit.lead_user_ids = [...leads, email];
        targetUnit.lead_user_id = targetUnit.lead_user_ids[0] ?? null;
      }
    } else if (requestedRole === "ONTOLOGY_LEAD") {
      const ontoLeads = targetUnit.ontology_lead_user_ids ?? [];
      if (!ontoLeads.includes(email)) {
        targetUnit.ontology_lead_user_ids = [...ontoLeads, email];
      }
    }
    syncSetupOrgUnitsFromMock();
    return jsonResponse({
      account_id: account.id,
      user_id: account.id,
      principal_id: account.principal_id,
      email: account.email ?? email,
      display_name: account.display_name,
      assignment_role: requestedRole,
      role: requestedRole,
      target_org_unit_id: targetUnit.id,
      temporary_password: "OrciaMock!2026", // pragma: allowlist secret
      auth_mode: "LOCAL",
      org_unit: {
        ...targetUnit,
        lead_user_id: targetUnit.lead_user_id ?? (targetUnit.lead_user_ids?.[0] ?? null),
        lead_user_ids: targetUnit.lead_user_ids ?? (targetUnit.lead_user_id ? [targetUnit.lead_user_id] : []),
        ontology_lead_user_ids: targetUnit.kind === "BU" ? (targetUnit.ontology_lead_user_ids ?? []) : [],
        attached_workspaces_count: countAttachedWorkspacesForUnit(targetUnit.id).count,
        can_edit: true,
        can_create_child: targetUnit.kind === "BU",
        can_delete: activeHat === "PLATFORM_ADMIN",
        can_manage_members: targetUnit.kind === "TEAM",
        can_manage_ontology_leads: targetUnit.kind === "BU",
        can_invite_users: true,
      },
      trace_id: "0195f000000070008000000000000999",
    });
  }

  if (
    (path === "/api/v1/org-units" && method === "POST") ||
    (/^\/api\/v1\/org-units\/([^/]+)$/.test(path) && (method === "PATCH" || method === "DELETE"))
  ) {
    const accessMode = (reqHeaders.get("x-orcia-access-mode") ?? "").toUpperCase();
    const activeHat = (reqHeaders.get("x-orcia-active-hat") ?? "PLATFORM_ADMIN").toUpperCase();
    if (accessMode === "READ_ONLY_OBSERVER" || activeHat === "OBSERVER") {
      return problemResponse(
        403,
        "ERR_OBSERVER_MODE_READ_ONLY",
        "Mode observateur en lecture seule",
        "Les mutations sont refusées en mode observateur lecture seule.",
        path,
      );
    }
    if (!["PLATFORM_ADMIN", "SECOPS", "BU_LEAD", "TEAM_LEAD"].includes(activeHat)) {
      return problemResponse(
        403,
        "ERR_SCOPE_ACCESS_DENIED",
        "Accès au périmètre refusé",
        "Votre rôle ne permet pas de modifier l'organigramme.",
        path,
      );
    }

    if (path === "/api/v1/org-units" && method === "POST") {
      const name = String(body.name ?? "").trim();
      const kind: "BU" | "TEAM" = String(body.kind ?? "BU").toUpperCase() === "TEAM" ? "TEAM" : "BU";
      const rawSlug = typeof body.slug === "string" ? body.slug.trim().toLowerCase() : "";
      const slug = (rawSlug || name.toLowerCase())
        .replace(/[^a-z0-9-]+/g, "-")
        .replace(/^-|-$/g, "");
      if (backendState.orgUnits.some((u) => u.slug === slug)) {
        return problemResponse(
          409,
          "ERR_ORG_UNIT_DUPLICATE_SLUG",
          "Identifiant court d'unité déjà utilisé",
          `L'identifiant court '${slug}' est déjà utilisé.`,
          path,
        );
      }
      const rawParent =
        typeof body.parent_id === "string" &&
        body.parent_id.trim() &&
        body.parent_id.trim() !== "scope-global"
          ? body.parent_id.trim()
          : null;
      if (rawParent) {
        const parentUnit = backendState.orgUnits.find((u) => u.id === rawParent);
        if (!parentUnit) {
          return problemResponse(
            404,
            "ERR_RESOURCE_NOT_FOUND",
            "Ressource introuvable",
            `Unité parente introuvable : '${rawParent}'.`,
            path,
          );
        }
        if (kind === "BU" && parentUnit.kind === "TEAM") {
          return problemResponse(
            422,
            "ERR_ORG_UNIT_INVALID_PARENT_KIND",
            "Rattachement hiérarchique invalide",
            "Une Direction ou un Pôle (BU) ne peut pas être rattaché sous une Équipe.",
            path,
          );
        }
      }
      const rawMembers = Array.isArray(body.member_user_ids)
        ? body.member_user_ids.map((m) => String(m).trim()).filter(Boolean)
        : [];
      if (kind === "BU" && rawMembers.length > 0) {
        return problemResponse(
          422,
          "ERR_ORG_UNIT_BU_MEMBERS_FORBIDDEN",
          "Membres interdits sur une Direction (BU)",
          "Une Direction (BU) ou un Pôle (Sous-BU) ne peut pas comporter de membres directs. Les membres doivent être rattachés à une Équipe.",
          path,
        );
      }
      for (const m of rawMembers) {
        if (!isMockUserKnown(m)) {
          return problemResponse(
            422,
            "ERR_ORG_UNIT_UNKNOWN_USER",
            "Utilisateur inconnu",
            `L'utilisateur '${m}' n'est pas un compte connu et actif de la plateforme.`,
            path,
          );
        }
      }

      const rawLead =
        typeof body.lead_user_id === "string" && body.lead_user_id.trim()
          ? body.lead_user_id.trim()
          : null;
      const rawLeadIds = Array.isArray(body.lead_user_ids)
        ? body.lead_user_ids.map((l) => String(l).trim()).filter(Boolean)
        : (rawLead ? [rawLead] : []);
      for (const l of rawLeadIds) {
        if (!isMockUserKnown(l)) {
          return problemResponse(
            422,
            "ERR_ORG_UNIT_UNKNOWN_USER",
            "Utilisateur inconnu",
            `L'utilisateur '${l}' n'est pas un compte connu et actif de la plateforme.`,
            path,
          );
        }
      }

      const rawOntologyLeads = Array.isArray(body.ontology_lead_user_ids)
        ? body.ontology_lead_user_ids.map((l) => String(l).trim()).filter(Boolean)
        : [];
      if (kind === "TEAM" && rawOntologyLeads.length > 0) {
        return problemResponse(
          422,
          "ERR_ORG_UNIT_ONTOLOGY_LEAD_ONLY_BU",
          "Référents Glossaire réservés aux Directions (BU)",
          "Seule une Direction ou Sous-BU (BU) peut désigner des Référents Glossaire.",
          path,
        );
      }

      backendState.orgUnitSeq += 1;
      const id = `org-${backendState.orgUnitSeq}`;
      const created: MockOrganizationalUnit = {
        id,
        slug,
        name,
        kind,
        parent_id: rawParent,
        billing_enabled: body.billing_enabled !== undefined ? Boolean(body.billing_enabled) : true,
        lead_user_id: rawLeadIds[0] ?? null,
        lead_user_ids: rawLeadIds,
        ontology_lead_user_ids: kind === "BU" ? rawOntologyLeads : [],
        member_user_ids: kind === "BU" ? [] : rawMembers,
      };
      backendState.orgUnits = [...backendState.orgUnits, created];
      syncSetupOrgUnitsFromMock();
      return jsonResponse({
        ...created,
        attached_workspaces_count: 0,
        can_edit: true,
        can_create_child: created.kind === "BU",
        can_delete: true,
        can_manage_members: created.kind === "TEAM",
        can_manage_ontology_leads: created.kind === "BU",
        can_invite_users: true,
      });
    }

    const orgIdMatch = /^\/api\/v1\/org-units\/([^/]+)$/.exec(path);
    const targetId = decodeURIComponent(orgIdMatch?.[1] ?? "");
    const target = backendState.orgUnits.find((u) => u.id === targetId);
    if (!target) {
      return problemResponse(
        404,
        "ERR_RESOURCE_NOT_FOUND",
        "Ressource introuvable",
        `Unité introuvable : '${targetId}'.`,
        path,
      );
    }

    if (method === "PATCH") {
      const nextName =
        typeof body.name === "string" && body.name.trim() ? body.name.trim() : target.name;
      let nextParentId = target.parent_id;
      if ("parent_id" in body) {
        const candidate =
          typeof body.parent_id === "string" &&
          body.parent_id.trim() &&
          body.parent_id.trim() !== "scope-global"
            ? body.parent_id.trim()
            : null;
        if (candidate === target.id) {
          return problemResponse(
            422,
            "ERR_ORG_UNIT_HIERARCHY_CYCLE",
            "Cycle hiérarchique détecté",
            "Une unité ne peut pas être rattachée à elle-même ou à l'une de ses sous-unités.",
            path,
          );
        }
        if (candidate) {
          const parentUnit = backendState.orgUnits.find((u) => u.id === candidate);
          if (!parentUnit) {
            return problemResponse(
              404,
              "ERR_RESOURCE_NOT_FOUND",
              "Ressource introuvable",
              `Unité parente introuvable : '${candidate}'.`,
              path,
            );
          }
          if (target.kind === "BU" && parentUnit.kind === "TEAM") {
            return problemResponse(
              422,
              "ERR_ORG_UNIT_INVALID_PARENT_KIND",
              "Rattachement hiérarchique invalide",
              "Une Direction ou un Pôle (BU) ne peut pas être rattaché sous une Équipe.",
              path,
            );
          }
          let cursor: MockOrganizationalUnit | undefined = parentUnit;
          const seen = new Set<string>([target.id]);
          while (cursor) {
            if (seen.has(cursor.id)) {
              return problemResponse(
                422,
                "ERR_ORG_UNIT_HIERARCHY_CYCLE",
                "Cycle hiérarchique détecté",
                "Une unité ne peut pas être rattachée à elle-même ou à l'une de ses sous-unités.",
                path,
              );
            }
            seen.add(cursor.id);
            cursor = cursor.parent_id
              ? backendState.orgUnits.find((u) => u.id === cursor?.parent_id)
              : undefined;
          }
        }
        nextParentId = candidate;
      }
      let nextLeadUserId = target.lead_user_id;
      let nextLeadUserIds = target.lead_user_ids ?? (target.lead_user_id ? [target.lead_user_id] : []);
      if ("lead_user_ids" in body && Array.isArray(body.lead_user_ids)) {
        const rawLeads = body.lead_user_ids.map((l) => String(l).trim()).filter(Boolean);
        for (const l of rawLeads) {
          if (!isMockUserKnown(l)) {
            return problemResponse(
              422,
              "ERR_ORG_UNIT_UNKNOWN_USER",
              "Utilisateur inconnu",
              `L'utilisateur '${l}' n'est pas un compte connu et actif de la plateforme.`,
              path,
            );
          }
        }
        nextLeadUserIds = rawLeads;
        nextLeadUserId = rawLeads[0] ?? null;
      } else if ("lead_user_id" in body) {
        const rawLead =
          typeof body.lead_user_id === "string" && body.lead_user_id.trim()
            ? body.lead_user_id.trim()
            : null;
        if (rawLead && !isMockUserKnown(rawLead)) {
          return problemResponse(
            422,
            "ERR_ORG_UNIT_UNKNOWN_USER",
            "Utilisateur inconnu",
            `L'utilisateur '${rawLead}' n'est pas un compte connu et actif de la plateforme.`,
            path,
          );
        }
        nextLeadUserId = rawLead;
        nextLeadUserIds = rawLead ? [rawLead] : [];
      }

      let nextMemberUserIds = target.kind === "BU" ? [] : target.member_user_ids;
      if ("member_user_ids" in body && Array.isArray(body.member_user_ids)) {
        const rawMembers = body.member_user_ids.map((m) => String(m).trim()).filter(Boolean);
        if (target.kind === "BU" && rawMembers.length > 0) {
          return problemResponse(
            422,
            "ERR_ORG_UNIT_BU_MEMBERS_FORBIDDEN",
            "Membres interdits sur une Direction (BU)",
            "Une Direction (BU) ou un Pôle (Sous-BU) ne peut pas comporter de membres directs. Les membres doivent être rattachés à une Équipe.",
            path,
          );
        }
        for (const m of rawMembers) {
          if (!isMockUserKnown(m)) {
            return problemResponse(
              422,
              "ERR_ORG_UNIT_UNKNOWN_USER",
              "Utilisateur inconnu",
              `L'utilisateur '${m}' n'est pas un compte connu et actif de la plateforme.`,
              path,
            );
          }
        }
        nextMemberUserIds = rawMembers;
      }

      let nextOntologyLeadUserIds = target.kind === "BU" ? (target.ontology_lead_user_ids ?? []) : [];
      if ("ontology_lead_user_ids" in body && Array.isArray(body.ontology_lead_user_ids)) {
        const rawOnto = body.ontology_lead_user_ids.map((l) => String(l).trim()).filter(Boolean);
        if (target.kind === "TEAM" && rawOnto.length > 0) {
          return problemResponse(
            422,
            "ERR_ORG_UNIT_ONTOLOGY_LEAD_ONLY_BU",
            "Référents Glossaire réservés aux Directions (BU)",
            "Seule une Direction ou Sous-BU (BU) peut désigner des Référents Glossaire.",
            path,
          );
        }
        nextOntologyLeadUserIds = target.kind === "BU" ? rawOnto : [];
      }

      const { activeHat: patchHat, candidates: patchCandidates, hasSessionUser: patchHasUser } =
        resolveMockOrgActor();
      if (patchHasUser && (patchHat === "BU_LEAD" || patchHat === "BU_DIRECTOR" || patchHat === "TEAM_LEAD")) {
        const patchScope = computeOrgSubtreeAndAncestors(patchCandidates, patchHat);
        if (!patchScope.managed.has(target.id)) {
          return problemResponse(
            403,
            "ERR_SCOPE_ACCESS_DENIED",
            "Hors périmètre de délégation",
            "Cette unité n'appartient pas à votre périmètre de délégation.",
            path,
          );
        }
        if (nextLeadUserIds.length === 0) {
          return problemResponse(
            422,
            "ERR_ORG_UNIT_LAST_LEAD_REMOVAL_FORBIDDEN",
            "Dernier responsable requis",
            "Impossible de retirer le dernier responsable de cette unité.",
            path,
          );
        }
      }

      const updated: MockOrganizationalUnit = {
        ...target,
        name: nextName,
        parent_id: nextParentId,
        billing_enabled:
          body.billing_enabled !== undefined
            ? Boolean(body.billing_enabled)
            : target.billing_enabled,
        lead_user_id: nextLeadUserId,
        lead_user_ids: nextLeadUserIds,
        ontology_lead_user_ids: target.kind === "BU" ? nextOntologyLeadUserIds : [],
        member_user_ids: target.kind === "BU" ? [] : nextMemberUserIds,
      };
      backendState.orgUnits = backendState.orgUnits.map((u) =>
        u.id === target.id ? updated : u,
      );
      syncSetupOrgUnitsFromMock();
      return jsonResponse({
        ...updated,
        attached_workspaces_count: countAttachedWorkspacesForUnit(updated.id).count,
      });
    }

    if (method === "DELETE") {
      const children = backendState.orgUnits.filter((u) => u.parent_id === target.id);
      const wsInfo = countAttachedWorkspacesForUnit(target.id);
      if (children.length > 0 || wsInfo.count > 0) {
        const parts: string[] = [];
        if (children.length > 0) {
          parts.push(
            children.length > 1
              ? `${children.length} sous-unités sont rattachées`
              : "1 sous-unité est rattachée",
          );
        }
        if (wsInfo.count > 0) {
          parts.push(
            wsInfo.count > 1
              ? `${wsInfo.count} Espaces de Travail sont rattachés`
              : "1 Espace de Travail est rattaché",
          );
        }
        const detail = `Suppression refusée : ${parts.join(" et ")} à « ${target.name} ». Supprimez ou déplacez d'abord ces éléments.`;
        return problemResponse(
          409,
          "ERR_ORG_UNIT_NOT_EMPTY",
          "Unité organisationnelle non vide",
          detail,
          path,
        );
      }
      backendState.orgUnits = backendState.orgUnits.filter((u) => u.id !== target.id);
      syncSetupOrgUnitsFromMock();
      return jsonResponse({
        deleted_id: target.id,
        deleted: true,
        trace_id: "0195f000000070008000000000000999",
      });
    }
  }

  const authPolicyResp = handleVitestAuthPolicyRoute({
    method,
    path,
    body,
    reqHeaders,
    jsonResponse,
    problemResponse,
  });
  if (authPolicyResp !== null) {
    return authPolicyResp;
  }

  // 1c. Story 17.3 IAM Accounts Directory, Native 6-Role Matrix & SecOps Exceptions
  const iamResp = handleVitestIamRoute({
    method,
    path,
    parsedUrl,
    body,
    reqHeaders,
    firstAdmin: backendState.firstAdmin,
    orgUnits: backendState.orgUnits,
    syncSetupOrgUnits: syncSetupOrgUnitsFromMock,
    jsonResponse,
    problemResponse,
  });
  if (iamResp !== null) {
    return iamResp;
  }

  // 1d. Story 17.4 Enterprise Connectors, User Passthrough Tokens & Workspace Datasources
  const connResp = handleVitestConnectorsRoute({
    method,
    path,
    parsedUrl,
    body,
    reqHeaders,
    firstAdmin: backendState.firstAdmin,
    orgUnits: backendState.orgUnits,
    jsonResponse,
    problemResponse: (status, title, detail, errorCode) =>
      problemResponse(status, errorCode, title, detail, path),
  });
  if (connResp !== null) {
    return connResp;
  }

  // 2. Mon Assistant SSE Stream & Turn Actions
  if (path === "/api/v1/assistant/three-speed/stream" && method === "POST") {
    if ((globalThis as Record<string, unknown>).__ORCIA_TEST_KEEP_STREAM_PENDING__) {
      return new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      });
    }
    const hat = String(body.hat ?? "PM");
    const requestedSpeed = String(
      body.requested_speed ?? "SPEED_1_FAST",
    ) as UiAssistantSpeedMode;
    const thinkingEffort = String(
      body.thinking_effort ?? "balanced",
    ) as UiInferenceEffort;
    const locale = String(body.locale ?? "fr");
    const isFr = locale !== "en";
    const fullUserPrompt = String(body.user_prompt ?? "");
    const cleanPrompt = fullUserPrompt.split("\n\n[Pièces jointes")[0] ?? fullUserPrompt;
    const replyText = `[${requestedSpeed}] ${cleanPrompt}`;
    const personalInstructions = body.personal_instructions
      ? String(body.personal_instructions)
      : "";
    const folderPinnedNotes = body.folder_pinned_notes
      ? String(body.folder_pinned_notes)
      : "";
    const assembledSystemPrompt = [
      `[ROLE=${hat}] [SPEED=${requestedSpeed}] [EFFORT=${thinkingEffort}]`,
      personalInstructions ? `[LAYER_5_USER_PREFERENCES] ${personalInstructions}` : "",
      folderPinnedNotes ? `[LAYER_5_ACTIVE_FOLDER_PINNED_NOTES] ${folderPinnedNotes}` : "",
    ]
      .filter(Boolean)
      .join("\n");

    const useSteps = shouldUseProgressiveStepThinking({
      userPrompt: cleanPrompt,
      requestedSpeed,
      deepAuditPillActive: Boolean(body.deep_audit_pill_active),
      thinkingEffort,
    });
    const plannedSteps = useSteps
      ? detectAdaptiveThinkingStepsForQuestion(cleanPrompt, isFr)
      : [];
    const thinkingText = plannedSteps
      .map((s) => `${s.label}: ${s.intermediateOutput ?? ""}`)
      .join(" · ");

    return buildSseStreamResponse([
      `event: cache_status\ndata: ${JSON.stringify({ cache_hit: false, cache_lookup_ms: 1 })}\n\n`,
      `event: token_delta\ndata: ${JSON.stringify({ accumulated_text: replyText })}\n\n`,
      `event: turn_completed\ndata: ${JSON.stringify({
        turn_id: `turn-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        response_text: replyText,
        thinking_text: thinkingText,
        assembled_system_prompt: assembledSystemPrompt,
        latency_ms: plannedSteps.length > 0 ? 3000 : 1000,
      })}\n\n`,
    ]);
  }

  if (path === "/api/v1/assistant/three-speed/stop" && method === "POST") {
    return jsonResponse({ status: "STOPPED", streamed_text: "", thinking_text: "" });
  }

  if (path === "/api/v1/assistant/three-speed/feedback" && method === "POST") {
    return jsonResponse({ status: "recorded" });
  }

  if (path === "/api/v1/assistant/folders" && method === "POST") {
    const title = String(body.title ?? "Dossier");
    const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, "-");
    const folderId = typeof body.folder_id === "string" && body.folder_id ? body.folder_id : `folder-${slug}-${backendState.recordedCalls.length}`;
    const existing = backendState.assistantFolders.find((f) => f.folder_id === folderId);
    const record: Record<string, unknown> = {
      folder_id: folderId,
      workspace_id: String(body.workspace_id ?? ""),
      owner_user_id: "user-vitest",
      title,
      pinned_notes_markdown: String(body.pinned_notes_markdown ?? ""),
      working_attachments_uris: [],
      consolidated_summary: String(body.consolidated_summary ?? ""),
      evidence_tags: ["S1"],
      has_restricted_sources: Boolean(body.has_restricted_sources ?? false),
      visibility_mode: existing?.visibility_mode ?? "PRIVATE",
      shares: [],
      assembled_layer5_prompt_block: `Dossier actif : ${title}`,
    };
    backendState.assistantFolders = existing
      ? backendState.assistantFolders.map((f) => (f.folder_id === folderId ? record : f))
      : [...backendState.assistantFolders, record];
    return jsonResponse(record);
  }

  const shareMatch = /^\/api\/v1\/assistant\/folders\/([^/]+)\/share$/.exec(path);
  if (shareMatch && method === "POST") {
    const folderId = decodeURIComponent(shareMatch[1] ?? "");
    const folder = backendState.assistantFolders.find((f) => f.folder_id === folderId);
    if (!folder) return jsonResponse({ error_code: "ERR_RESOURCE_NOT_FOUND" }, 404);
    folder.visibility_mode = body.visibility_mode;
    return jsonResponse({
      folder_id: folderId,
      workspace_id: folder.workspace_id,
      visibility_mode: body.visibility_mode,
      shares: [],
      has_restricted_sources: folder.has_restricted_sources,
    });
  }

  const overviewMatch = /^\/api\/v1\/assistant\/workspaces\/([^/]+)\/overview$/.exec(path);
  if (overviewMatch && method === "GET") {
    const workspaceId = decodeURIComponent(overviewMatch[1] ?? "");
    const wsFolders = backendState.assistantFolders.filter((f) => f.workspace_id === workspaceId);
    return jsonResponse({
      workspace_id: workspaceId,
      tabs: ["ACTIVE_DISCUSSION", "FOLDERS", "HISTORY_SEARCH"],
      active_folder_pill_label: null,
      folders_count: wsFolders.length,
      folders: wsFolders,
      threads: [],
      history_hits: [],
    });
  }

  if (path === "/api/v1/assistant/threads" && method === "POST") {
    return jsonResponse({
      thread_id: `thread-${backendState.recordedCalls.length}`,
      workspace_id: String(body.workspace_id ?? "ws-1"),
      title: String(body.title ?? "Discussion"),
    });
  }

  // 3. Agents & Skills Studio
  if (path === "/api/v1/agents-and-skills" && method === "GET") {
    return jsonResponse({
      agents: backendState.agents,
      skills: backendState.skills,
    });
  }

  if (path === "/api/v1/skills" && method === "POST") {
    const skillId = String(body.skill_id ?? "skill-custom");
    const slug = skillId.replace(/^skill-/, "") || "custom";
    const entry = {
      skill_id: skillId,
      slug,
      command_handle: `/${slug}`,
      name: String(body.name ?? "Compétence"),
      objective: String(body.objective ?? ""),
      input_parameters: Array.isArray(body.input_parameters) ? body.input_parameters : [],
      instructions: String(body.instructions ?? ""),
      expected_output_format: String(body.expected_output_format ?? "Synthèse structurée"),
      visibility_scope: String(body.visibility_scope ?? "TEAM"),
      source_pack_key: null,
    };
    backendState.skills = [
      ...backendState.skills.filter((s) => s.skill_id !== skillId),
      entry,
    ];
    return jsonResponse(entry);
  }

  if (path.startsWith("/api/v1/skills/") && method === "DELETE") {
    const skillId = decodeURIComponent(path.slice("/api/v1/skills/".length));
    backendState.skills = backendState.skills.filter((s) => s.skill_id !== skillId);
    return jsonResponse({ deleted: true, skill_id: skillId });
  }

  if (path.startsWith("/api/v1/skills/") && path.endsWith("/execute") && method === "POST") {
    const skillId = decodeURIComponent(
      path.slice("/api/v1/skills/".length, -"/execute".length),
    );
    const inputText = String(body.input_text ?? "");
    const existing = backendState.skills.find((s) => s.skill_id === skillId);
    const name = String(existing?.name ?? skillId);
    const handle = String(existing?.command_handle ?? `/${skillId.replace(/^skill-/, "")}`);
    return jsonResponse({
      skill_id: skillId,
      output_text: [
        `### ✅ Exécution de la compétence **${name}** (\`${handle}\`)`,
        `- **Entrée analysée** : ${inputText.trim()}`,
        `- **Livrable** : Analyse structurée prête pour validation métier.`,
      ].join("\n"),
    });
  }

  if (path === "/api/v1/agents" && method === "POST") {
    const agentId = String(body.agent_id ?? "agent-custom");
    const slug = agentId.replace(/^agent-/, "") || "custom";
    const entry = {
      agent_id: agentId,
      slug,
      handle: `@${slug}`,
      name: String(body.name ?? "Agent"),
      role_mission: String(body.role_mission ?? ""),
      instructions: String(body.instructions ?? ""),
      thinking_level: String(body.thinking_level ?? "medium"),
      skill_ids: Array.isArray(body.skill_ids) ? body.skill_ids : [],
      visibility_scope: String(body.visibility_scope ?? "TEAM"),
      source_pack_key: null,
      enabled_in_workspace: true,
      mcp_exposed: Boolean(body.mcp_exposed ?? false),
    };
    backendState.agents = [
      ...backendState.agents.filter((a) => a.agent_id !== agentId),
      entry,
    ];
    return jsonResponse(entry);
  }

  if (path.startsWith("/api/v1/agents/") && path.endsWith("/duplicate") && method === "POST") {
    const newName = String(body.new_name ?? "Agent (Copie)");
    return jsonResponse({
      agent_id: `agent-copie-${backendState.recordedCalls.length}`,
      name: newName,
    });
  }

  if (path.startsWith("/api/v1/agents/") && path.endsWith("/governance") && method === "PATCH") {
    const agentId = decodeURIComponent(
      path.slice("/api/v1/agents/".length, -"/governance".length),
    );
    backendState.agents = backendState.agents.map((a) =>
      a.agent_id === agentId ? { ...a, ...body } : a,
    );
    return jsonResponse({ agent_id: agentId, ...body });
  }

  if (path.startsWith("/api/v1/agents/") && path.endsWith("/skills") && method === "PUT") {
    const agentId = decodeURIComponent(
      path.slice("/api/v1/agents/".length, -"/skills".length),
    );
    const skillIds = Array.isArray(body.skill_ids) ? body.skill_ids : [];
    backendState.agents = backendState.agents.map((a) =>
      a.agent_id === agentId ? { ...a, skill_ids: skillIds } : a,
    );
    return jsonResponse({ agent_id: agentId, skill_ids: skillIds });
  }

  if (path.startsWith("/api/v1/agents/") && path.endsWith("/execute") && method === "POST") {
    const agentId = decodeURIComponent(
      path.slice("/api/v1/agents/".length, -"/execute".length),
    );
    const prompt = String(body.prompt ?? "");
    const existing = backendState.agents.find((a) => a.agent_id === agentId);
    const name = String(existing?.name ?? agentId);
    const roleMission = String(existing?.role_mission ?? "Mission spécialisée");
    const thinkingLevel = String(existing?.thinking_level ?? "medium");
    return jsonResponse({
      agent_id: agentId,
      response_text: [
        `### ✅ Agent **${name}** (${roleMission}) — Réflexion : \`${thinkingLevel}\``,
        `- **Demande traitée** : ${prompt.trim()}`,
        "- **Synthèse de l'Agent** : Réponse structurée produite.",
      ].join("\n"),
    });
  }

  if (path.startsWith("/api/v1/agents/") && method === "DELETE") {
    const agentId = decodeURIComponent(path.slice("/api/v1/agents/".length));
    backendState.agents = backendState.agents.filter((a) => a.agent_id !== agentId);
    return jsonResponse({ deleted: true, agent_id: agentId });
  }

  // 4. LLM Provider Connection Test & Registration
  if (
    (path === "/api/v1/bootstrap/welcome-setup/llm-test" ||
      path === "/api/v1/assistant/llm-providers/test-connection") &&
    method === "POST"
  ) {
    const provider = String(body.provider_slug ?? "Anthropic");
    const model = String(body.model_name ?? "");
    const uri = String(body.endpoint_uri ?? "");
    const isGeminiNative = uri.includes("/v1beta") && !uri.includes("/openai");
    const modeLabel = isGeminiNative ? " - Mode B" : "";
    return jsonResponse({
      ok: true,
      provider_slug: provider,
      model_name: model,
      endpoint_uri: uri,
      auth_mode: String(body.auth_mode ?? "api_key"),
      protocol_mode: isGeminiNative ? "google_gemini_native" : "openai_compatible",
      latency_ms: 24,
      message_fr: `✅ Connexion réussie au modèle « ${model} » (${provider}${modeLabel}) sur ${uri} — Réponse reçue en 24 ms.`,
      message_en: `✅ Successfully connected to model '${model}' (${provider}${modeLabel}) at ${uri} — Response received in 24 ms.`,
    });
  }

  if (
    (path === "/api/v1/bootstrap/welcome-setup/progressive-llm" ||
      path === "/api/v1/settings/llm/endpoints") &&
    method === "POST"
  ) {
    return jsonResponse({ status: "registered", endpoint_key: body.endpoint_key ?? "medium" });
  }

  if (path === "/api/v1/settings/ai-models/mappings" && method === "GET") {
    let items = backendState.aiModelMappings;
    const usage = parsedUrl.searchParams.get("usage");
    const isActive = parsedUrl.searchParams.get("is_active");
    if (usage) {
      items = items.filter((m) => m.usage === usage);
    }
    if (isActive !== null) {
      items = items.filter((m) => String(m.is_active) === isActive);
    }
    return jsonResponse({ items, total: items.length });
  }

  if (path === "/api/v1/settings/ai-models/reindex-status" && method === "GET") {
    return jsonResponse(backendState.mockReindexStatus);
  }

  if (path === "/api/v1/settings/ai-models/reindex-embeddings" && method === "POST") {
    backendState.mockReindexStatus = {
      status: "PENDING",
      progress_percentage: 0,
      total_chunks: 50,
      processed_chunks: 0,
    };
    return jsonResponse({
      job_id: "mock-reindex-job-1",
      status: "PENDING",
      target_model_id: "mod-1",
      target_model_name: "text-embedding-3-small",
      message: "Réindexation globale lancée",
    });
  }

  // 5. MCP Test Bench, Help Validation, Starlark Compiler, Federated Search & Packs
  if (path === "/api/v1/mcp/test-bench" && method === "POST") {
    return jsonResponse({ steps: [], discovered_capabilities: [], can_activate: true });
  }

  if (path === "/api/v1/help/validate" && method === "POST") {
    return jsonResponse({
      article_id: "help-processes-guide",
      lang: String(body.lang ?? "fr"),
      passed: true,
      bound_routes_valid: true,
      ui_components_and_sections_valid: true,
      glossary_and_zero_secret_valid: true,
      elapsed_ms: 2.1,
      violations: [],
    });
  }

  if (path.includes("/dna-mechanisms/compile") && method === "POST") {
    const ruleId = String(body.rule_id ?? "RULE-01");
    return jsonResponse({
      mechanism_id: `mech-${ruleId.toLowerCase()}`,
      rule_id: ruleId,
      script_name: `${ruleId.toLowerCase().replace(/[^a-z0-9_]/g, "_")}.star`,
      starlark_code: `def check(ctx):\n    val = ctx.payload.get("reference_code", "")\n    if not val:\n        orcia_sys.emit_verdict("${ruleId}", "FAIL", "Champ reference_code obligatoire")\n        return False\n    orcia_sys.emit_verdict("${ruleId}", "PASS", "Conforme")\n    return True`,
      sha256: `sha256:${ruleId.toLowerCase()}`,
      explanation_fr: `Vérifie automatiquement la conformité de la règle « ${ruleId} » avant chaque validation.`,
      verified_badge_fr: "✓ Vérifié automatiquement (cas valide + cas rejeté)",
      causal_breadcrumb: `Orientation ➔ Règle (${ruleId}) ➔ Contrôle automatique`,
      self_corrected: false,
      signed_and_active: false,
    });
  }

  if (path === "/api/v1/search" && method === "GET") {
    return jsonResponse({ hits: [] });
  }

  if (path === "/api/v1/settings/packs/installed" && method === "GET") {
    return jsonResponse({ packs: [] });
  }

  // 6. Orchestration Human-Led Anchor & Arbitration (Story 3.4 / BUG-E2E-02)
  if (path === "/api/v1/orchestration/state" && method === "GET") {
    return jsonResponse({
      workflows: [],
      runs: backendState.orchestrationRuns.map((r) => ({
        id: r.id,
        run_key: `run-${r.id}`,
        workspace_id: r.workspace_id,
        workflow_def_id: "wf-claims",
        workflow_uri: "orcia://workflows/claims-engineering-delivery",
        parent_run_id: null,
        parent_step_execution_id: null,
        root_run_id: r.id,
        nesting_depth: 0,
        execution_regime: "HUMAN_LED",
        criticality: "HIGH_CRITICAL",
        trigger_id: null,
        trigger_idempotency_key: null,
        status: r.status,
        initiated_by_user_id: "user-vitest",
        execution_identity_mode: "PASSTHROUGH",
        budget_max_usd: 15,
        run_lock: {
          workflow_uri: "orcia://workflows/claims-engineering-delivery",
          workflow_version: "1.0.0",
          workflow_sha256: "sha256:wf",
          sources: [],
          sub_workflow_locks: [],
          manifest_sha256: "sha256:lock",
        },
      })),
      compiled_default_template: {
        template_key: "tpl-architecture-decision-record",
        uri: "orcia://templates/adr",
        version: "1.0.0",
        human_markdown_view: "",
        cognitive_chunks: [],
        agent_json_schema: {},
        bound_ontology_terms: [],
        sha256: "sha256:tpl",
      },
      trace_id: "0195f000000070008000000000000999",
    });
  }

  if (path === "/api/v1/orchestration/runs/instantiate" && method === "POST") {
    const runId = `0195f000-0000-7000-8000-00000000900${backendState.orchestrationRuns.length + 1}`;
    const wsId = String(body.workspace_id ?? "0192c4e0-0000-7000-8000-000000000201");
    const runEntry = {
      id: runId,
      workspace_id: wsId,
      status: "RUNNING",
      step_status: "PENDING",
      draft_artifact: {},
      committed_snapshot_id: null,
    };
    backendState.orchestrationRuns.push(runEntry);
    return jsonResponse({
      run: {
        id: runId,
        run_key: `run-${runId}`,
        workspace_id: wsId,
        workflow_def_id: "wf-claims",
        workflow_uri: String(body.workflow_uri ?? "orcia://workflows/claims-engineering-delivery"),
        parent_run_id: null,
        parent_step_execution_id: null,
        root_run_id: runId,
        nesting_depth: 0,
        execution_regime: "HUMAN_LED",
        criticality: "HIGH_CRITICAL",
        trigger_id: null,
        trigger_idempotency_key: null,
        status: "RUNNING",
        initiated_by_user_id: "user-vitest",
        execution_identity_mode: "PASSTHROUGH",
        budget_max_usd: 15,
        run_lock: {
          workflow_uri: "orcia://workflows/claims-engineering-delivery",
          workflow_version: "1.0.0",
          workflow_sha256: "sha256:wf",
          sources: [],
          sub_workflow_locks: [],
          manifest_sha256: "sha256:lock",
        },
      },
      trace_id: "0195f000000070008000000000000999",
    });
  }

  const bbMatch = /^\/api\/v1\/orchestration\/runs\/([^/]+)\/blackboard$/.exec(path);
  if (bbMatch && method === "GET") {
    const runId = decodeURIComponent(bbMatch[1] ?? "");
    const run = backendState.orchestrationRuns.find((r) => r.id === runId);
    if (!run) {
      return jsonResponse({ error_code: "ERR_RESOURCE_NOT_FOUND" }, 404);
    }
    return jsonResponse({
      run_id: run.id,
      root_run_id: run.id,
      run_status: run.status,
      accumulated_root_cost_usd: 0.02,
      step_executions: [
        {
          id: `step-${run.id}`,
          step_execution_key: `${run.id}:frame-architecture-intent`,
          run_id: run.id,
          step_key: "frame-architecture-intent",
          step_index: 0,
          step_type: "HUMAN_TASK",
          execution_mode: "COACHING",
          status: run.step_status,
          attempt_count: 1,
          max_agent_retries: 2,
          draft_artifact: run.draft_artifact,
          draft_cas_key: null,
          step_memlog: [],
          hydrated_input_uris: [],
          child_run_id: null,
          committed_snapshot_id: run.committed_snapshot_id,
          cost_usd: 0,
        },
      ],
      active_snapshots: run.committed_snapshot_id
        ? [
            {
              id: run.committed_snapshot_id,
              snapshot_key: `snap-${run.id}`,
              run_id: run.id,
              step_execution_id: `step-${run.id}`,
              parent_snapshot_id: null,
              step_key: "frame-architecture-intent",
              branch_status: "ACTIVE",
              artifact_payload: run.draft_artifact,
              artifact_cas_key: "cas://snap",
              artifact_sha256: "a".repeat(64),
              memlog_summary: [],
              superseded_snapshot_ids: [],
            },
          ]
        : [],
      trace_id: "0195f000000070008000000000000999",
    });
  }

  if (path === "/api/v1/orchestration/runs/anchors/sign" && method === "POST") {
    const runId = String(body.run_id ?? "");
    const contentText = String(body.content_text ?? "").trim();
    const authorType = String(body.author_type ?? "HUMAN");
    if (authorType !== "HUMAN" || contentText.length < 30) {
      return jsonResponse({ error_code: "ERR_HUMAN_ANCHOR_REQUIRED" }, 422);
    }
    const run = backendState.orchestrationRuns.find((r) => r.id === runId);
    const sha = "b".repeat(64);
    const sectionKey = String(body.section_key ?? "human_architecture_intent");
    if (run) {
      const prevAnchors = (run.draft_artifact.human_anchors ?? {}) as Record<string, unknown>;
      run.draft_artifact = {
        ...run.draft_artifact,
        human_anchors: {
          ...prevAnchors,
          [sectionKey]: {
            content_text: contentText,
            content_sha256: sha,
            char_length: contentText.length,
            authored_by_user_id: "user-vitest",
          },
        },
      };
    }
    return jsonResponse({
      signature: {
        id: "sig-1",
        signature_key: `anchor-${sectionKey}`,
        workspace_id: run?.workspace_id ?? "ws-1",
        run_id: runId,
        step_execution_id: `step-${runId}`,
        step_key: String(body.step_key ?? "frame-architecture-intent"),
        section_key: sectionKey,
        content_text: contentText,
        content_sha256: sha,
        char_length: contentText.length,
        authored_by_user_id: "user-vitest",
        author_display_name: String(body.signature_text ?? "Admin Test"),
        signature_hash: "c".repeat(64),
      },
      step_execution: {
        id: `step-${runId}`,
        step_execution_key: `${runId}:frame-architecture-intent`,
        run_id: runId,
        step_key: String(body.step_key ?? "frame-architecture-intent"),
        step_index: 0,
        step_type: "HUMAN_TASK",
        execution_mode: "COACHING",
        status: run?.step_status ?? "PENDING",
        attempt_count: 1,
        max_agent_retries: 2,
        draft_artifact: run?.draft_artifact ?? {},
        draft_cas_key: null,
        step_memlog: [],
        hydrated_input_uris: [],
        child_run_id: null,
        committed_snapshot_id: run?.committed_snapshot_id ?? null,
        cost_usd: 0,
      },
      trace_id: "0195f000000070008000000000000999",
    });
  }

  const arbReqMatch = /^\/api\/v1\/orchestration\/runs\/([^/]+)\/steps\/([^/]+)\/arbitration$/.exec(
    path,
  );
  if (arbReqMatch && method === "POST") {
    const runId = decodeURIComponent(arbReqMatch[1] ?? "");
    const stepKey = decodeURIComponent(arbReqMatch[2] ?? "");
    const arbId = `arb-${runId}`;
    const run = backendState.orchestrationRuns.find((r) => r.id === runId);
    if (run) {
      run.status = "WAITING_FOR_HUMAN_ARBITRATION";
      run.step_status = "WAITING_FOR_HUMAN_ARBITRATION";
      run.draft_artifact = {
        ...run.draft_artifact,
        pending_arbitration_id: arbId,
      };
    }
    return jsonResponse({
      arbitration: {
        id: arbId,
        arbitration_key: arbId,
        workspace_id: run?.workspace_id ?? "ws-1",
        run_id: runId,
        step_execution_id: `step-${runId}`,
        step_key: stepKey,
        tie_break_policy: String(body.tie_break_policy ?? "PAUSE_AND_ESCALATE"),
        status: "PENDING",
        question_title: String(body.question_title ?? ""),
        context_summary: String(body.context_summary ?? ""),
        options_matrix: Array.isArray(body.options_matrix) ? body.options_matrix : [],
        selected_option_key: null,
        human_justification: null,
        resolved_by_user_id: null,
        resolved_by_axiom_key: null,
        outbox_event_id: "evt-arb-1",
      },
      step_execution: {
        id: `step-${runId}`,
        step_execution_key: `${runId}:${stepKey}`,
        run_id: runId,
        step_key: stepKey,
        step_index: 0,
        step_type: "HUMAN_TASK",
        execution_mode: "COACHING",
        status: "WAITING_FOR_HUMAN_ARBITRATION",
        attempt_count: 1,
        max_agent_retries: 2,
        draft_artifact: run?.draft_artifact ?? {},
        draft_cas_key: null,
        step_memlog: [],
        hydrated_input_uris: [],
        child_run_id: null,
        committed_snapshot_id: null,
        cost_usd: 0,
      },
      trace_id: "0195f000000070008000000000000999",
    });
  }

  const arbResMatch =
    /^\/api\/v1\/orchestration\/runs\/([^/]+)\/steps\/([^/]+)\/arbitration\/resolve$/.exec(path);
  if (arbResMatch && method === "POST") {
    const runId = decodeURIComponent(arbResMatch[1] ?? "");
    const stepKey = decodeURIComponent(arbResMatch[2] ?? "");
    const selectedOptionKey = String(body.selected_option_key ?? "OPT_A_SPOT_15M");
    const humanJustification = String(body.human_justification ?? "");
    const snapId = `snap-committed-${runId}`;
    const run = backendState.orchestrationRuns.find((r) => r.id === runId);
    if (run) {
      run.status = "RUNNING";
      run.step_status = "COMMITTED";
      run.committed_snapshot_id = snapId;
      run.draft_artifact = {
        ...run.draft_artifact,
        arbitration_resolution: {
          arbitration_id: String(body.arbitration_id ?? `arb-${runId}`),
          status: "RESOLVED_BY_HUMAN",
          selected_option_key: selectedOptionKey,
          human_justification: humanJustification,
        },
      };
    }
    return jsonResponse({
      arbitration: {
        id: String(body.arbitration_id ?? `arb-${runId}`),
        arbitration_key: `arb-${runId}`,
        workspace_id: run?.workspace_id ?? "ws-1",
        run_id: runId,
        step_execution_id: `step-${runId}`,
        step_key: stepKey,
        tie_break_policy: "PAUSE_AND_ESCALATE",
        status: "RESOLVED_BY_HUMAN",
        question_title: "Arbitrage",
        context_summary: "",
        options_matrix: [],
        selected_option_key: selectedOptionKey,
        human_justification: humanJustification,
        resolved_by_user_id: "user-vitest",
        resolved_by_axiom_key: null,
        outbox_event_id: "evt-arb-1",
      },
      step_execution: {
        id: `step-${runId}`,
        step_execution_key: `${runId}:${stepKey}`,
        run_id: runId,
        step_key: stepKey,
        step_index: 0,
        step_type: "HUMAN_TASK",
        execution_mode: "COACHING",
        status: "COMMITTED",
        attempt_count: 1,
        max_agent_retries: 2,
        draft_artifact: run?.draft_artifact ?? {},
        draft_cas_key: null,
        step_memlog: [],
        hydrated_input_uris: [],
        child_run_id: null,
        committed_snapshot_id: snapId,
        cost_usd: 0,
      },
      committed_snapshot: {
        id: snapId,
        snapshot_key: `snap-${runId}`,
        run_id: runId,
        step_execution_id: `step-${runId}`,
        parent_snapshot_id: null,
        step_key: stepKey,
        branch_status: "ACTIVE",
        artifact_payload: run?.draft_artifact ?? {},
        artifact_cas_key: "cas://snap",
        artifact_sha256: "a".repeat(64),
        memlog_summary: [],
        superseded_snapshot_ids: [],
      },
      trace_id: "0195f000000070008000000000000999",
    });
  }

  const autonomyContractMatch =
    /^\/api\/v1\/workspaces\/([^/]+)\/workflows\/([^/]+)\/autonomy-contract(\/revoke)?$/.exec(
      path,
    );
  if (autonomyContractMatch) {
    const wsId = decodeURIComponent(autonomyContractMatch[1] ?? "");
    const wfId = decodeURIComponent(autonomyContractMatch[2] ?? "");
    const isRevoke = autonomyContractMatch[3] === "/revoke";
    const defaultSp = {
      id: "0195f000-0000-7000-8000-000000007101",
      principal_id: "sp-docs-automation",
      display_name: "Robot Documentation Espace",
      roles: ["TEAM_LEAD"],
      team_ids: [wsId],
      status: "ACTIVE",
    };
    if (method === "GET" && !isRevoke) {
      const history = backendState.autonomyContracts.filter(
        (c) => c.workspace_id === wsId && c.workflow_id === wfId,
      );
      const active = history.find((c) => c.status === "ACTIVE") ?? null;
      return jsonResponse({
        workspace_id: wsId,
        workflow_id: wfId,
        active_contract: active,
        history,
        eligible_service_principals: [defaultSp],
        trace_id: "0195f000000070008000000000000711",
      });
    }
    if (method === "POST" && !isRevoke) {
      if (String(body.criticality ?? "STANDARD") === "HIGH_CRITICAL") {
        return jsonResponse(
          {
            error_code: "ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE",
            detail: "Ce workflow critique exige une Gate Humaine.",
          },
          422,
        );
      }
      for (const existing of backendState.autonomyContracts) {
        if (existing.workspace_id === wsId && existing.workflow_id === wfId && existing.status === "ACTIVE") {
          existing.status = "SUPERSEDED";
        }
      }
      const created = {
        id: `0195f000-0000-7000-8000-00000000720${backendState.autonomyContracts.length + 1}`,
        workspace_id: wsId,
        workflow_id: wfId,
        workflow_version: String(body.workflow_version ?? "1.0.0"),
        workflow_sha256: String(body.workflow_sha256 ?? "sha256-mock"),
        criticality: String(body.criticality ?? "STANDARD"),
        service_principal_id: String(body.service_principal_id ?? defaultSp.id),
        allowed_read_sources: Array.isArray(body.allowed_read_sources) ? body.allowed_read_sources : [],
        allowed_write_actions: Array.isArray(body.allowed_write_actions) ? body.allowed_write_actions : [],
        max_cost_per_run_usd: Number(body.max_cost_per_run_usd ?? 5),
        tie_break_policy: String(body.tie_break_policy ?? "ONTOLOGY_AXIOM_FIRST"),
        post_hoc_sampling_rate: Number(body.post_hoc_sampling_rate ?? 0.15),
        status: "ACTIVE",
        signed_by_user_id: "0195f000-0000-7000-8000-000000000203",
        signed_by_role: "TEAM_LEAD",
        signature_sha256: "a".repeat(64),
        signed_at_iso: "2026-11-17T10:00:00Z",
        revoked_at_iso: null,
        revoked_by_user_id: null,
      };
      backendState.autonomyContracts.unshift(created);
      return jsonResponse(created, 201);
    }
    if (method === "POST" && isRevoke) {
      const active = backendState.autonomyContracts.find(
        (c) => c.workspace_id === wsId && c.workflow_id === wfId && c.status === "ACTIVE",
      );
      if (!active) {
        return jsonResponse({ error_code: "ERR_AUTONOMY_CONTRACT_NOT_FOUND" }, 404);
      }
      active.status = "REVOKED";
      active.revoked_at_iso = "2026-11-17T10:05:00Z";
      active.revoked_by_user_id = "0195f000-0000-7000-8000-000000000203";
      return jsonResponse(active);
    }
  }

  const triggerMatch = path.match(
    /^\/api\/v1\/workspaces\/([^/]+)\/workflows\/(.+?)\/triggers(?:\/([^/]+)(?:\/(fire|reset-circuit))?)?$/,
  );
  if (triggerMatch) {
    const wsId = decodeURIComponent(triggerMatch[1] ?? "");
    const wfId = decodeURIComponent(triggerMatch[2] ?? "");
    const trigId = triggerMatch[3] ? decodeURIComponent(triggerMatch[3]) : null;
    const action = triggerMatch[4] ?? null;

    if (method === "GET" && !trigId) {
      const items = backendState.workflowTriggers.filter(
        (t) => t.workspace_id === wsId && t.workflow_id === wfId,
      );
      return jsonResponse({
        workspace_id: wsId,
        workflow_id: wfId,
        items,
        trace_id: "0195f000000070008000000000000720",
      });
    }
    if (method === "POST" && !trigId) {
      const activeContract = backendState.autonomyContracts.find(
        (c) => c.workspace_id === wsId && c.workflow_id === wfId && c.status === "ACTIVE",
      );
      if (!activeContract) {
        return jsonResponse({ error_code: "ERR_AUTONOMY_CONTRACT_REQUIRED" }, 422);
      }
      const nextIdx = backendState.workflowTriggers.length + 1;
      const newId = `0195f000-0000-7000-8000-00000000730${nextIdx}`;
      const secInput = (body.webhook_secret ?? null) as {
        action?: string;
        plaintext_value?: string;
      } | null;
      const hasSecret = Boolean(secInput?.action === "set" && secInput.plaintext_value);
      const created = {
        id: newId,
        trigger_key: `trg-${nextIdx}`,
        workspace_id: wsId,
        workflow_id: wfId,
        trigger_type: String(body.trigger_type ?? "MANUAL_AUTONOMOUS"),
        contract_id: String(activeContract.id),
        cron_expr: body.cron_expr ? String(body.cron_expr) : null,
        cooldown_window_seconds: Number(body.cooldown_window_seconds ?? 300),
        service_principal_id: String(activeContract.service_principal_id),
        max_runs_per_hour: Number(body.max_runs_per_hour ?? 10),
        max_daily_cost_usd: Number(body.max_daily_cost_usd ?? 25),
        max_consecutive_failures: 3,
        consecutive_failures: 0,
        status: "ACTIVE",
        auto_help_on_publish: Boolean(body.auto_help_on_publish ?? false),
        last_fired_at_iso: null,
        log_sink_service: body.log_sink_service ? String(body.log_sink_service) : null,
        log_sink_query_text: null,
        outbox_event_filter: null,
        webhook_secret_status: {
          configured: hasSecret,
          fingerprint: hasSecret ? "sha256:mockfp01" : null,
          masked_hint: hasSecret ? "••••••••cret" : null,
          updated_at: hasSecret ? "2026-11-17T10:10:00Z" : "",
          updated_by: hasSecret ? "0195f000-0000-7000-8000-000000000203" : "",
        },
      };
      backendState.workflowTriggers.unshift(created);
      return jsonResponse(created, 201);
    }
    if (method === "PATCH" && trigId) {
      const target = backendState.workflowTriggers.find(
        (t) => t.id === trigId && t.workspace_id === wsId,
      );
      if (!target) {
        return jsonResponse({ error_code: "ERR_TRIGGER_NOT_FOUND" }, 404);
      }
      if (typeof body.status === "string") target.status = body.status;
      if (typeof body.auto_help_on_publish === "boolean") {
        target.auto_help_on_publish = body.auto_help_on_publish;
      }
      const secInput = (body.webhook_secret ?? null) as { action?: string } | null;
      if (secInput?.action === "set") {
        target.webhook_secret_status = {
          configured: true,
          fingerprint: "sha256:mockfp02",
          masked_hint: "••••••••updated",
          updated_at: "2026-11-17T10:12:00Z",
          updated_by: "0195f000-0000-7000-8000-000000000203",
        };
      } else if (secInput?.action === "clear") {
        target.webhook_secret_status = {
          configured: false,
          fingerprint: null,
          masked_hint: null,
          updated_at: "2026-11-17T10:12:00Z",
          updated_by: "0195f000-0000-7000-8000-000000000203",
        };
      }
      return jsonResponse(target);
    }
    if (method === "DELETE" && trigId) {
      backendState.workflowTriggers = backendState.workflowTriggers.filter(
        (t) => !(t.id === trigId && t.workspace_id === wsId),
      );
      return jsonResponse({ deleted_id: trigId, trace_id: "0195f000000070008000000000000721" });
    }
    if (method === "POST" && trigId && action === "fire") {
      const target = backendState.workflowTriggers.find(
        (t) => t.id === trigId && t.workspace_id === wsId,
      );
      if (!target) {
        return jsonResponse({ error_code: "ERR_TRIGGER_NOT_FOUND" }, 404);
      }
      target.last_fired_at_iso = "2026-11-17T10:15:00Z";
      return jsonResponse(
        {
          dispatched: true,
          outcome: "DISPATCHED",
          trigger_id: trigId,
          idempotency_key: "manual:mock",
          dbos_workflow_id: `${trigId}:manual:mock`,
          run_id: "0195f000-0000-7000-8000-000000007401",
          attempts: 1,
          reason: null,
          trace_id: "0195f000000070008000000000000722",
        },
        201,
      );
    }
    if (method === "POST" && trigId && action === "reset-circuit") {
      const target = backendState.workflowTriggers.find(
        (t) => t.id === trigId && t.workspace_id === wsId,
      );
      if (!target) {
        return jsonResponse({ error_code: "ERR_TRIGGER_NOT_FOUND" }, 404);
      }
      target.status = "ACTIVE";
      target.consecutive_failures = 0;
      return jsonResponse(target);
    }
  }

  // Process Studio v2 & Dual-Mode Orchestration (Story 16.3)
  if (path === "/api/v1/workflows/v2" && method === "GET") {
    const items = Array.from(backendState.workflowsV2.values());
    return jsonResponse({ items });
  }

  const wfV2WhatIfMatch = /^\/api\/v1\/workflows\/v2\/([^/]+)\/what-if$/.exec(path);
  if (wfV2WhatIfMatch && method === "POST") {
    const wfId = decodeURIComponent(wfV2WhatIfMatch[1] ?? "");
    return jsonResponse({
      workflow_id: wfId,
      version: "1.0.0",
      sandbox_isolated: true,
      external_writes_executed: 0,
      sub_steps_evaluated: 2,
      deterministic_gates_passed: true,
      probabilistic_gates_passed: true,
      estimated_tokens: 2900,
      estimated_cost_usd: 0.03,
      findings: [],
    });
  }

  const wfV2RunsMatch = /^\/api\/v1\/workflows\/v2\/([^/]+)\/runs$/.exec(path);
  if (wfV2RunsMatch && method === "POST") {
    const wfId = decodeURIComponent(wfV2RunsMatch[1] ?? "");
    const existing = backendState.workflowsV2.get(wfId);
    const orchType = existing?.orchestration_type ?? "deterministic_dbos";
    return jsonResponse({
      run: {
        run_id: `run-${wfId}-01`,
        workflow_id: wfId,
        workflow_slug: existing?.slug ?? wfId,
        workflow_version: existing?.version ?? "1.0.0",
        orchestration_type: orchType,
        execution_mode: existing?.execution_mode ?? "native_orcia",
        status: "WAITING_FINAL_ANCHOR",
        iteration: 1,
        reentry_mode: "initial",
        current_sub_step_index: 0,
        inputs: {},
        mcp_context_bundle: null,
        sub_step_records: [],
        gate_report: null,
        final_artifact_pointer: null,
        reflexive_execution_id: `reflx-${wfId}-01`,
        trace_events: [],
        return_loop_target_step_num: null,
        return_loop_remarks: null,
        audit_trail: [],
      },
    });
  }

  const wfV2ItemMatch = /^\/api\/v1\/workflows\/v2\/([^/]+)$/.exec(path);
  if (wfV2ItemMatch && method === "GET") {
    const wfId = decodeURIComponent(wfV2ItemMatch[1] ?? "");
    const found =
      backendState.workflowsV2.get(wfId) ??
      Array.from(backendState.workflowsV2.values()).find((w) => w.slug === wfId);
    if (!found) {
      return jsonResponse({ detail: `Workflow '${wfId}' introuvable.` }, 404);
    }
    return jsonResponse(found);
  }

  if (wfV2ItemMatch && method === "PUT") {
    const wfId = decodeURIComponent(wfV2ItemMatch[1] ?? "");
    const incoming = (body.workflow ?? {}) as ApiWorkflowDefinitionV2;
    const saved: ApiWorkflowDefinitionV2 = {
      ...incoming,
      id: incoming.id || wfId,
    };
    backendState.workflowsV2.set(saved.id, saved);
    return jsonResponse({
      workflow: saved,
      forked_as_draft: false,
    });
  }

  const setupWorkspaces = Array.isArray(
    (backendState.platformSetupState as Record<string, unknown> | null)?.workspaces,
  )
    ? ((backendState.platformSetupState as Record<string, unknown>).workspaces as Array<
        Record<string, unknown>
      >)
    : [];
  const ontologyResponse = handleVitestOntologyRoute({
    path,
    method,
    body,
    orgUnits: backendState.orgUnits,
    workspaces: setupWorkspaces,
    jsonResponse,
    problemResponse,
  });
  if (ontologyResponse) {
    return ontologyResponse;
  }

  const supervisionResponse = handleVitestAutonomousSupervisionRoute(
    path,
    method,
    body,
    jsonResponse,
    parsedUrl.searchParams,
  );
  if (supervisionResponse) {
    return supervisionResponse;
  }

  const reflexiveResp = await tryHandleVitestReflexiveEndpoint({
    path,
    parsedUrl,
    method,
    body,
    ...(init ? { init } : {}),
  });
  if (reflexiveResp) {
    return reflexiveResp;
  }

  return jsonResponse({});
}

globalThis.fetch = vitestFetchTransport as typeof fetch;
