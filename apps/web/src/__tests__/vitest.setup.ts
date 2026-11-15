import type { UiAssistantSpeedMode, UiInferenceEffort } from "@orcia/ui";
import { beforeEach } from "vitest";
import {
  detectAdaptiveThinkingStepsForQuestion,
  shouldUseProgressiveStepThinking,
} from "../features/inbox/assistantBackgroundStreamStore";
import { buildLocalLlmConnectionSuccessFeedback } from "../routes/settingsAiModelsPresets";

export interface RecordedVitestApiCall {
  readonly method: string;
  readonly path: string;
  readonly body: unknown;
}

interface MockOrganizationalUnit {
  id: string;
  slug: string;
  name: string;
  kind: "BU" | "TEAM";
  parent_id: string | null;
  billing_enabled: boolean;
  lead_user_id: string | null;
  member_user_ids: string[];
}

interface MockBackendState {
  firstAdmin: {
    email: string;
    displayName: string;
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

const backendState: MockBackendState = {
  firstAdmin: null,
  platformSetupState: null,
  orgUnits: [],
  orgUnitSeq: 0,
  agents: [],
  skills: [],
  assistantFolders: [],
  orchestrationRuns: [],
  recordedCalls: [],
};

import { resetAuthSessionStore } from "../stores/authSessionStore";
import {
  getVitestIamAccounts,
  handleVitestIamRoute,
  resetVitestIamMockState,
} from "./vitestIamMockHandlers";
import {
  handleVitestConnectorsRoute,
  resetVitestConnectorsMockState,
} from "./vitestConnectorsMockHandlers";

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
      lead_user_id,
      member_user_ids,
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
    memberUserIds: u.member_user_ids,
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
  backendState.firstAdmin = null;
  backendState.platformSetupState = null;
  backendState.orgUnits = [];
  backendState.orgUnitSeq = 0;
  backendState.agents = [];
  backendState.skills = [];
  backendState.assistantFolders = [];
  backendState.orchestrationRuns = [];
  backendState.recordedCalls = [];
  resetVitestIamMockState();
  resetVitestConnectorsMockState();
  resetAuthSessionStore();
}

export function setVitestMockRefreshFails(fails: boolean): void {
  if (fails) {
    (globalThis as Record<string, unknown>).__ORCIA_MOCK_REFRESH_FAILS__ = true;
  } else {
    delete (globalThis as Record<string, unknown>).__ORCIA_MOCK_REFRESH_FAILS__;
  }
}

/** Pré-remplit le 1er administrateur et l'état de plateforme servis par le backend simulé. */
export function seedVitestPlatformSetupState(
  state: Record<string, unknown>,
  firstAdmin: { email: string; displayName: string } = { email: "admin@orcia.test", displayName: "Admin Test" },
): void {
  backendState.firstAdmin = firstAdmin;
  backendState.platformSetupState = state;
  backendState.orgUnits = hydrateMockOrgUnitsFromSetup(state.org_units);
  backendState.orgUnitSeq = backendState.orgUnits.length;
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

  backendState.recordedCalls.push({ method, path, body });

  // 1. Accostage & Platform Setup State
  if (path === "/api/v1/bootstrap/accostage-status" && method === "GET") {
    if (backendState.firstAdmin) {
      return jsonResponse({
        first_admin_initialized: true,
        first_admin_email: backendState.firstAdmin.email,
        first_admin_display_name: backendState.firstAdmin.displayName,
      });
    }
    return jsonResponse({
      first_admin_initialized: false,
      first_admin_email: null,
      first_admin_display_name: null,
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
    return jsonResponse({
      access_token: "mock-access-token",
      token_type: "bearer",
      roles,
      user_id: iamUser?.id ?? "usr-vitest-1",
      email,
      display_name: displayName,
      must_change_password: false,
      issued_at_iso: "2026-11-14T12:00:00Z",
    });
  }

  if (path === "/api/v1/auth/me" && method === "GET") {
    return jsonResponse({
      user_id: "usr-vitest-1",
      email: backendState.firstAdmin?.email ?? "admin@orcia.local",
      display_name: backendState.firstAdmin?.displayName ?? "Administrateur Plateforme",
      roles: ["PLATFORM_ADMIN"],
      active_hat: "PLATFORM_ADMIN",
      access_mode: "READ_WRITE",
      must_change_password: false,
      workspaces: [],
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

  if (path === "/api/v1/org-units" && method === "GET") {
    const qParam = parsedUrl.searchParams.get("q")?.trim()?.toLowerCase() ?? null;
    const kindParam = parsedUrl.searchParams.get("kind")?.toUpperCase() ?? null;
    const limitParamRaw = parsedUrl.searchParams.get("limit");
    const limitParam = limitParamRaw ? parseInt(limitParamRaw, 10) : null;

    let units = backendState.orgUnits.map((u) => ({
      ...u,
      attached_workspaces_count: countAttachedWorkspacesForUnit(u.id).count,
    }));

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
      const rawMembers = Array.isArray(body.member_user_ids)
        ? body.member_user_ids.map((m) => String(m).trim()).filter(Boolean)
        : [];
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

      backendState.orgUnitSeq += 1;
      const id = `org-${backendState.orgUnitSeq}`;
      const created: MockOrganizationalUnit = {
        id,
        slug,
        name,
        kind,
        parent_id: rawParent,
        billing_enabled: body.billing_enabled !== undefined ? Boolean(body.billing_enabled) : true,
        lead_user_id: rawLead,
        member_user_ids: rawMembers,
      };
      backendState.orgUnits = [...backendState.orgUnits, created];
      syncSetupOrgUnitsFromMock();
      return jsonResponse({
        ...created,
        attached_workspaces_count: 0,
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
      if ("lead_user_id" in body) {
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
      }

      let nextMemberUserIds = target.member_user_ids;
      if ("member_user_ids" in body && Array.isArray(body.member_user_ids)) {
        const rawMembers = body.member_user_ids.map((m) => String(m).trim()).filter(Boolean);
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

      const updated: MockOrganizationalUnit = {
        ...target,
        name: nextName,
        parent_id: nextParentId,
        billing_enabled:
          body.billing_enabled !== undefined
            ? Boolean(body.billing_enabled)
            : target.billing_enabled,
        lead_user_id: nextLeadUserId,
        member_user_ids: nextMemberUserIds,
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
    const fr = buildLocalLlmConnectionSuccessFeedback({
      isFr: true,
      provider,
      model,
      uri,
    });
    const en = buildLocalLlmConnectionSuccessFeedback({
      isFr: false,
      provider,
      model,
      uri,
    });
    return jsonResponse({
      ok: fr.ok,
      provider_slug: provider,
      model_name: model,
      endpoint_uri: uri,
      auth_mode: String(body.auth_mode ?? "api_key"),
      protocol_mode: uri.includes("/v1beta") && !uri.includes("/openai") ? "google_gemini_native" : "openai_compatible",
      latency_ms: 18,
      message_fr: fr.message,
      message_en: en.message,
    });
  }

  if (
    (path === "/api/v1/bootstrap/welcome-setup/progressive-llm" ||
      path === "/api/v1/settings/llm/endpoints") &&
    method === "POST"
  ) {
    return jsonResponse({ status: "registered", endpoint_key: body.endpoint_key ?? "medium" });
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

  return jsonResponse({});
}

globalThis.fetch = vitestFetchTransport as typeof fetch;
