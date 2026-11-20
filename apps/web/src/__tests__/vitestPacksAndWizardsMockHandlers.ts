import { useAuthSessionStore } from "../stores/authSessionStore";

export interface MockWizardSession {
  id: string;
  wizard_type: "sdlc_tech_lead" | "ops_manager" | "secops_admin";
  user_id: string;
  scope_id: string;
  current_step_index: number;
  total_steps: number;
  dbos_workflow_id: string;
  status: "IN_PROGRESS" | "COMPLETED" | "ABANDONED";
  completed_steps: number[];
  rag_reciprocity_verified: boolean;
  state_jsonb: Record<string, unknown>;
}

const DEFAULT_USER_UUID = "0195f000-0000-7000-8000-000000000203";
const DEFAULT_SCOPE_UUID = "0195f000-0000-7000-8000-000000000301";
const DEMO_WORKSPACE_UUID = "0195f000-0000-7000-8000-000000000399";
const TRACE_ID = "0195f000000070008000000000000999";

const MOCK_DECLARATIVE_PACKS = [
  {
    id: "orcia-pack-sdlc",
    slug: "sdlc",
    name: "Pack Ingénierie Logicielle & SDLC (SAFe / Mon Compte)",
    version: "1.0.0",
    description:
      "Pack déclaratif SDLC pour qualification, architecture, implémentation et revue.",
    rbac_namespace: "engineering",
    bundle_sha256: "ada15c957c260000000000000000000000000000000000000000000000000001",
    agents_count: 4,
    skills_count: 4,
    gates_count: 6,
    vsm_count: 1,
    workflows_count: 4,
    agents_slugs: ["architecte-technique", "lead-qa", "product-manager", "tech-lead"],
    skills_slugs: ["audit-architecture", "plan-test", "qualification-prd", "revue-pr"],
    gates_slugs: ["gate-arch", "gate-prd", "gate-qa", "gate-sec", "gate-ux", "gate-vsm"],
    required_connectors: [
      {
        connector_type: "mcp:jira",
        required_scopes: ["read", "write"],
        used_for: "Synchronisation des tickets SAFe",
      },
      {
        connector_type: "mcp:git",
        required_scopes: ["read"],
        used_for: "Analyse des dépôts et PR",
      },
    ],
    connector_health: [
      {
        connector_type: "mcp:jira",
        required_scopes: ["read", "write"],
        used_for: "Synchronisation des tickets SAFe",
        health: {
          connector_type: "mcp:jira",
          ok: true,
          latency_ms: 12,
          error_message: null,
        },
      },
      {
        connector_type: "mcp:git",
        required_scopes: ["read"],
        used_for: "Analyse des dépôts et PR",
        health: {
          connector_type: "mcp:git",
          ok: true,
          latency_ms: 8,
          error_message: null,
        },
      },
    ],
    quick_actions: [],
  },
  {
    id: "orcia-pack-docs",
    slug: "orcia-docs",
    name: "Pack Documentation & Aide Contextuelle ORCIA",
    version: "1.0.0",
    description: "Pack déclaratif d'aide contextuelle et validation documentaire.",
    rbac_namespace: "docs",
    bundle_sha256: "4c27a14932ee0000000000000000000000000000000000000000000000000002",
    agents_count: 1,
    skills_count: 1,
    gates_count: 1,
    vsm_count: 0,
    workflows_count: 1,
    agents_slugs: ["redacteur-technique"],
    skills_slugs: ["validation-aide"],
    gates_slugs: ["gate-docs"],
    required_connectors: [],
    connector_health: [],
    quick_actions: [],
  },
];

let wizardSessions: MockWizardSession[] = [];
let wizardSeq = 0;

export function resetVitestPacksAndWizardsMockState(): void {
  wizardSessions = [];
  wizardSeq = 0;
}

export function seedVitestWizardSessions(sessions: readonly MockWizardSession[]): void {
  wizardSessions = sessions.map((s) => ({
    ...s,
    completed_steps: [...s.completed_steps],
    state_jsonb: { ...s.state_jsonb },
  }));
  wizardSeq = Math.max(wizardSeq, sessions.length);
}

function isObserverRequest(reqHeaders: Headers): boolean {
  const accessMode = (reqHeaders.get("x-orcia-access-mode") ?? "").trim().toUpperCase();
  const observerHdr = (reqHeaders.get("x-orcia-observer-mode") ?? "").trim().toLowerCase();
  const activeHatHdr = (reqHeaders.get("x-orcia-active-hat") ?? "").trim().toUpperCase();
  const session = useAuthSessionStore.getState();
  const storeRoles = (session.roles ?? []).map((r) => String(r).toUpperCase());
  const storeHat = String(session.activeHat ?? "").toUpperCase();
  return (
    accessMode === "READ_ONLY_OBSERVER" ||
    observerHdr === "1" ||
    observerHdr === "true" ||
    activeHatHdr === "OBSERVER" ||
    Boolean(session.readOnlyObserver) ||
    storeHat === "OBSERVER" ||
    storeRoles.includes("OBSERVER")
  );
}

function observerProblem(
  problemResponse: (
    status: number,
    errorCode: string,
    title: string,
    detail: string,
    instance: string,
  ) => Response,
  path: string,
): Response {
  return problemResponse(
    403,
    "ERR_OBSERVER_MODE_READ_ONLY",
    "Mode observateur en lecture seule",
    "Les mutations sont refusées en mode observateur lecture seule.",
    path,
  );
}

function normalizeWizardType(raw: unknown): MockWizardSession["wizard_type"] {
  if (raw === "ops_manager" || raw === "secops_admin") {
    return raw;
  }
  return "sdlc_tech_lead";
}

function sanitizeStepPayload(
  rawPayload: unknown,
  path: string,
  problemResponse: (
    status: number,
    errorCode: string,
    title: string,
    detail: string,
    instance: string,
  ) => Response,
): { payload: Record<string, unknown>; error?: Response } {
  const payload =
    rawPayload && typeof rawPayload === "object" && !Array.isArray(rawPayload)
      ? { ...(rawPayload as Record<string, unknown>) }
      : {};
  for (const key of Object.keys(payload)) {
    const low = key.toLowerCase();
    if (
      low.includes("password") ||
      low.includes("secret") ||
      low.includes("api_key") ||
      low.includes("private_key")
    ) {
      return {
        payload,
        error: problemResponse(
          422,
          "ERR_VALIDATION_ERROR",
          "Clé secrète en clair interdite",
          `Plaintext secret key '${key}' is forbidden in wizard state_jsonb; use secret_input.`,
          path,
        ),
      };
    }
  }
  return { payload };
}

export function handleVitestPacksAndWizardsRoute(params: {
  readonly path: string;
  readonly method: string;
  readonly parsedUrl: URL;
  readonly body: Record<string, unknown>;
  readonly reqHeaders: Headers;
  readonly jsonResponse: (payload: unknown, status?: number) => Response;
  readonly problemResponse: (
    status: number,
    errorCode: string,
    title: string,
    detail: string,
    instance: string,
  ) => Response;
}): Response | null {
  const { path, method, parsedUrl, body, reqHeaders, jsonResponse, problemResponse } = params;

  if (path === "/api/v1/packs" && method === "GET") {
    return jsonResponse({ packs: MOCK_DECLARATIVE_PACKS });
  }

  if (path === "/api/v1/packs/health" && method === "GET") {
    const connectors = MOCK_DECLARATIVE_PACKS.flatMap((p) => p.connector_health ?? []);
    const healthyCount = connectors.filter((c) => c.health?.ok).length;
    return jsonResponse({
      connectors,
      healthy_count: healthyCount,
      total_count: connectors.length,
      all_healthy: healthyCount === connectors.length,
      checked_at_iso: "2026-11-20T12:00:00Z",
    });
  }

  const exportPackMatch = /^\/api\/v1\/packs\/export\/([^/]+)$/.exec(path);
  if (exportPackMatch && method === "POST") {
    if (isObserverRequest(reqHeaders)) {
      return observerProblem(problemResponse, path);
    }
    const workspaceId = decodeURIComponent(exportPackMatch[1] ?? "workspace");
    const packId = parsedUrl.searchParams.get("pack_id") ?? "orcia-pack-sdlc";
    const matchedPack =
      MOCK_DECLARATIVE_PACKS.find((p) => p.id === packId) ?? MOCK_DECLARATIVE_PACKS[0];
    const packSlug = matchedPack?.slug ?? "sdlc";
    const safeWs =
      workspaceId.replace(/[^A-Za-z0-9_.-]+/g, "-").replace(/^-+|-+$/g, "") || "workspace";
    const filename = `${packSlug}-${safeWs.slice(0, 64)}.zip`;
    const zipBlob = new Blob(["PK\x05\x06" + "\x00".repeat(18)], {
      type: "application/zip",
    });
    return new Response(zipBlob, {
      status: 200,
      headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": `attachment; filename="${filename}"`,
      },
    });
  }

  if (path === "/api/v1/wizards" && method === "GET") {
    return jsonResponse({
      sessions: wizardSessions,
      trace_id: TRACE_ID,
    });
  }

  const getWizardSessionMatch = /^\/api\/v1\/wizards\/sessions\/([^/]+)$/.exec(path);
  if (getWizardSessionMatch && method === "GET") {
    const sessionId = decodeURIComponent(getWizardSessionMatch[1] ?? "");
    const existing = wizardSessions.find((s) => s.id === sessionId);
    if (!existing) {
      return problemResponse(
        404,
        "ERR_RESOURCE_NOT_FOUND",
        "Session wizard introuvable",
        `Wizard session '${sessionId}' introuvable.`,
        path,
      );
    }
    return jsonResponse(existing);
  }

  if (path === "/api/v1/wizards/sessions" && method === "POST") {
    if (isObserverRequest(reqHeaders)) {
      return observerProblem(problemResponse, path);
    }
    const wizardType = normalizeWizardType(body.wizard_type);
    const scopeId =
      typeof body.scope_id === "string" && body.scope_id.trim()
        ? body.scope_id.trim()
        : DEFAULT_SCOPE_UUID;
    const existing = wizardSessions.find(
      (s) =>
        s.wizard_type === wizardType &&
        s.scope_id === scopeId &&
        s.status === "IN_PROGRESS",
    );
    if (existing) {
      return jsonResponse(existing);
    }
    wizardSeq += 1;
    const suffix = String(wizardSeq).padStart(4, "0");
    const sessionId = `0195f000-0000-7000-8000-00000000${suffix}`;
    const created: MockWizardSession = {
      id: sessionId,
      wizard_type: wizardType,
      user_id: DEFAULT_USER_UUID,
      scope_id: scopeId,
      current_step_index: 1,
      total_steps: 5,
      dbos_workflow_id: `dbos:wizard:${wizardType}:${DEFAULT_USER_UUID}:${scopeId}`,
      status: "IN_PROGRESS",
      completed_steps: [],
      rag_reciprocity_verified: false,
      state_jsonb: {},
    };
    wizardSessions = [created, ...wizardSessions];
    return jsonResponse(created);
  }

  const wizardStepMatch = /^\/api\/v1\/wizards\/sessions\/([^/]+)\/(steps|step-back)$/.exec(
    path,
  );
  if (wizardStepMatch && method === "POST") {
    if (isObserverRequest(reqHeaders)) {
      return observerProblem(problemResponse, path);
    }
    const sessionId = decodeURIComponent(wizardStepMatch[1] ?? "");
    const action = wizardStepMatch[2];
    const target = wizardSessions.find((s) => s.id === sessionId);
    if (!target) {
      return problemResponse(
        404,
        "ERR_RESOURCE_NOT_FOUND",
        "Session wizard introuvable",
        `Wizard session '${sessionId}' introuvable.`,
        path,
      );
    }
    const stepIndex = Number(body.step_index ?? target.current_step_index ?? 1);
    if (!Number.isInteger(stepIndex) || stepIndex < 1 || stepIndex > target.total_steps) {
      return problemResponse(
        422,
        "ERR_VALIDATION_ERROR",
        "Numéro d'étape invalide",
        `step_index must be between 1 and ${target.total_steps}.`,
        path,
      );
    }
    const sanitized = sanitizeStepPayload(body.step_payload, path, problemResponse);
    if (sanitized.error) {
      return sanitized.error;
    }

    const isStepBack = action === "step-back" || Boolean(body.step_back);
    const nextState: Record<string, unknown> = { ...target.state_jsonb };

    if (isStepBack) {
      if (Object.keys(sanitized.payload).length > 0) {
        const existingStep = nextState[`step_${stepIndex}`];
        const baseStep =
          existingStep && typeof existingStep === "object" && !Array.isArray(existingStep)
            ? (existingStep as Record<string, unknown>)
            : {};
        nextState[`step_${stepIndex}`] = { ...baseStep, ...sanitized.payload };
      }
      const updated: MockWizardSession = {
        ...target,
        current_step_index: Math.max(1, stepIndex - 1),
        status: "IN_PROGRESS",
        state_jsonb: nextState,
      };
      wizardSessions = [updated, ...wizardSessions.filter((s) => s.id !== sessionId)];
      return jsonResponse(updated);
    }

    nextState[`step_${stepIndex}`] = {
      ...sanitized.payload,
      fail_fast_verified: true,
    };
    const completed = Array.from(new Set([...target.completed_steps, stepIndex])).sort(
      (a, b) => a - b,
    );
    const isFinal = stepIndex >= target.total_steps;
    const updated: MockWizardSession = {
      ...target,
      current_step_index: isFinal ? target.total_steps : stepIndex + 1,
      status: isFinal ? "COMPLETED" : "IN_PROGRESS",
      completed_steps: completed,
      rag_reciprocity_verified: isFinal || target.rag_reciprocity_verified,
      state_jsonb: nextState,
    };
    wizardSessions = [updated, ...wizardSessions.filter((s) => s.id !== sessionId)];
    return jsonResponse(updated);
  }

  if (path === "/api/v1/wizards/demo-workspace" && method === "POST") {
    if (isObserverRequest(reqHeaders)) {
      return observerProblem(problemResponse, path);
    }
    return jsonResponse({
      workspace_id: DEMO_WORKSPACE_UUID,
      workspace_slug: "demo-zero-empty-state",
      workspace_name: "Espace de Démonstration Pré-rempli (Zero Empty-State)",
      ontology_concepts_seeded: 12,
      kb_documents_indexed: 4,
      published_workflow_uri: "orcia://catalog/workflows/architecture-review",
      rag_reciprocity_verified: true,
      plaintext_secrets_count: 0,
    });
  }

  return null;
}
