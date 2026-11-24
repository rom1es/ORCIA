import { useAuthSessionStore } from "../stores/authSessionStore";

export interface MockOntologyOrgUnit {
  readonly id: string;
  readonly slug: string;
  readonly name: string;
  readonly kind: "BU" | "TEAM";
  readonly parent_id: string | null;
  readonly lead_user_ids?: readonly string[];
  readonly ontology_lead_user_ids?: readonly string[];
  readonly member_user_ids?: readonly string[];
}

export interface MockOntologyConcept {
  id: string;
  concept_key: string;
  canonical_term: string;
  level: string;
  scope_id: string;
  definition_text: string;
  parent_concept_id: string | null;
  synonyms: string[];
  banned_terms: string[];
  profile_translations: Record<string, string>;
  expected_schema: Record<string, string>;
  introduced_in_snapshot_id: string | null;
  snapshot_branch_status: string;
}

export interface MockOntologyPromotion {
  id: string;
  proposal_key: string;
  concept_key: string;
  canonical_term: string;
  source_level: string;
  target_level: string;
  target_scope_id: string;
  proposed_by_user_id: string;
  status: "PENDING_REVIEW" | "APPROVED" | "REJECTED";
  source_concept_id: string | null;
  source_scope_id: string | null;
  definition_text: string;
  reviewed_by_user_id: string | null;
  review_comment: string | null;
  collision_detected: boolean;
  colliding_definition: string | null;
}

let mockConcepts: MockOntologyConcept[] = [];
let mockPromotions: MockOntologyPromotion[] = [];
let mockTripartiteEdges: Array<Record<string, unknown>> = [];
let seq = 0;
let propSeq = 0;

export function resetVitestOntologyMockState(): void {
  mockConcepts = [];
  mockPromotions = [];
  mockTripartiteEdges = [];
  seq = 0;
  propSeq = 0;
}

export function seedVitestOntologyState(
  concepts: MockOntologyConcept[],
  promotions: MockOntologyPromotion[] = [],
): void {
  mockConcepts = concepts.map((c) => ({ ...c }));
  mockPromotions = promotions.map((p) => ({ ...p }));
  propSeq = promotions.length;
}

function resolveMockOntologyActor() {
  const session = useAuthSessionStore.getState();
  const roles = new Set<string>(
    [
      ...(session.roles ?? []).map((r) => String(r).toUpperCase()),
      ...(session.activeHat ? [String(session.activeHat).toUpperCase()] : []),
    ].filter(Boolean),
  );
  if (roles.size === 0 && !session.isAuthenticated) {
    roles.add("PLATFORM_ADMIN");
  }
  const email = (session.email ?? "admin@orcia.test").toLowerCase();
  const isObserver = session.readOnlyObserver || roles.has("OBSERVER");
  return { roles, email, isObserver };
}

function canWriteScope(
  actor: { roles: Set<string>; email: string; isObserver: boolean },
  level: string,
  scopeId: string,
  orgUnits: readonly MockOntologyOrgUnit[],
  workspaces: readonly Record<string, unknown>[],
): boolean {
  if (actor.isObserver) return false;
  if (actor.roles.has("PLATFORM_ADMIN")) return true;
  if (level === "1_ENTERPRISE") return false;
  const byId = new Map(orgUnits.map((u) => [u.id, u]));
  const hasBuAuth = (bu: MockOntologyOrgUnit): boolean => {
    let cur: MockOntologyOrgUnit | undefined = bu;
    const seen = new Set<string>();
    while (cur && !seen.has(cur.id)) {
      seen.add(cur.id);
      if ((cur.ontology_lead_user_ids ?? []).some((x) => x.toLowerCase() === actor.email)) return true;
      if (
        (actor.roles.has("BU_LEAD") || actor.roles.has("BU_DIRECTOR")) &&
        (cur.lead_user_ids ?? []).some((x) => x.toLowerCase() === actor.email)
      ) {
        return true;
      }
      cur = cur.parent_id ? byId.get(cur.parent_id) : undefined;
    }
    return false;
  };
  if (level === "2_DOMAIN") {
    const bu = orgUnits.find((u) => u.id === scopeId || u.slug === scopeId);
    return Boolean(bu && hasBuAuth(bu));
  }
  if (level === "3_TEAM") {
    const team = orgUnits.find((u) => u.id === scopeId || u.slug === scopeId);
    if (!team) return false;
    if (
      actor.roles.has("TEAM_LEAD") &&
      (team.lead_user_ids ?? []).some((x) => x.toLowerCase() === actor.email)
    ) {
      return true;
    }
    const parent = team.parent_id ? byId.get(team.parent_id) : undefined;
    return Boolean(parent && hasBuAuth(parent));
  }
  const ws = workspaces.find((w) => w.workspaceId === scopeId || w.id === scopeId);
  if (ws) {
    const ownerId = String(ws.ownerOrgUnitId ?? ws.owner_org_unit_id ?? "");
    const owner = orgUnits.find((u) => u.id === ownerId || u.slug === ownerId);
    if (owner) {
      if ((owner.member_user_ids ?? []).some((x) => x.toLowerCase() === actor.email)) return true;
      if ((owner.lead_user_ids ?? []).some((x) => x.toLowerCase() === actor.email)) return true;
      if (hasBuAuth(owner)) return true;
    }
  }
  return actor.roles.has("CONTRIBUTOR") || actor.roles.has("TEAM_LEAD");
}

function resolveNextTarget(
  sourceLevel: string,
  sourceScopeId: string,
  orgUnits: readonly MockOntologyOrgUnit[],
  workspaces: readonly Record<string, unknown>[],
  explicitLevel?: string | null,
  explicitScopeId?: string | null,
): { targetLevel: string; targetScopeId: string } | null {
  if (sourceLevel === "1_ENTERPRISE") return null;
  if (sourceLevel === "4_WORKSPACE" || sourceLevel === "3_WORKSPACE") {
    const ws = workspaces.find((w) => w.workspaceId === sourceScopeId || w.id === sourceScopeId);
    const ownerId = String(ws?.ownerOrgUnitId ?? ws?.owner_org_unit_id ?? "");
    const owner = orgUnits.find((u) => u.id === ownerId || u.slug === ownerId);
    if (owner?.kind === "BU") {
      if (explicitLevel && explicitLevel !== "2_DOMAIN") return null;
      return { targetLevel: "2_DOMAIN", targetScopeId: explicitScopeId || owner.id };
    }
    if (explicitLevel && explicitLevel !== "3_TEAM") return null;
    return { targetLevel: "3_TEAM", targetScopeId: explicitScopeId || owner?.id || "scope-team" };
  }
  if (sourceLevel === "3_TEAM") {
    if (explicitLevel && explicitLevel !== "2_DOMAIN") return null;
    const team = orgUnits.find((u) => u.id === sourceScopeId || u.slug === sourceScopeId);
    return { targetLevel: "2_DOMAIN", targetScopeId: explicitScopeId || team?.parent_id || "scope-bu" };
  }
  if (explicitLevel && explicitLevel !== "1_ENTERPRISE") return null;
  return { targetLevel: "1_ENTERPRISE", targetScopeId: "scope-global" };
}

export function handleVitestOntologyRoute(params: {
  path: string;
  method: string;
  parsedUrl?: URL;
  body: Record<string, unknown>;
  orgUnits: readonly MockOntologyOrgUnit[];
  workspaces: readonly Record<string, unknown>[];
  jsonResponse: (payload: unknown, status?: number) => Response;
  problemResponse: (
    status: number,
    errorCode: string,
    title: string,
    detail: string,
    instance: string,
  ) => Response;
}): Response | null {
  const { path, method, parsedUrl, body, orgUnits, workspaces, jsonResponse, problemResponse } = params;
  const actor = resolveMockOntologyActor();

  if (path === "/api/v1/ontology-rag/state" && method === "GET") {
    return jsonResponse({
      concepts: mockConcepts,
      relations: [],
      promotions: mockPromotions,
      documents: [],
      tripartite_edges: mockTripartiteEdges,
      stale_alerts: [],
      trace_id: "trace-vitest",
    });
  }

  if (path === "/api/v1/ontology-rag/tripartite/audit-doc-vs-code" && method === "POST") {
    if (actor.isObserver) {
      return problemResponse(403, "ERR_OBSERVER_MODE_READ_ONLY", "Forbidden", "Read-only observer mode", path);
    }
    const confluenceUri = String(body.confluence_uri ?? "");
    const gitRepoUri = String(body.git_repo_uri ?? "");
    const gitSymbol = String(body.git_symbol ?? "main");
    const jiraKey = body.newer_done_jira_key ? String(body.newer_done_jira_key) : null;
    const edgeKey = `edge-${mockTripartiteEdges.length + 1}`;
    const wsId = String(
      body.workspace_id ?? workspaces[0]?.workspaceId ?? workspaces[0]?.id ?? "0195f000-0000-7000-8000-000000000301",
    );
    mockTripartiteEdges.push({
      id: `0195f000-0000-7000-8400-${String(mockTripartiteEdges.length + 1).padStart(12, "0")}`,
      edge_key: edgeKey,
      workspace_id: wsId,
      source_uri: confluenceUri,
      source_node_type: "CONFLUENCE_DOC",
      target_uri: gitRepoUri,
      target_node_type: "GIT_REPO",
      relation_type: "SPECIFIED_IN",
      jira_issue_key: jiraKey,
    });
    return jsonResponse({
      confluence_uri: confluenceUri,
      git_repo_uri: gitRepoUri,
      git_symbol: gitSymbol,
      qualification_marker: jiraKey ? "[DOC_OBSOLETE_SUSPECTED]" : "[ALIGNED]",
      justifying_jira_key: jiraKey,
      explanation: jiraKey
        ? `Divergence qualifiée via ${jiraKey}.`
        : "Documentation alignée avec le code.",
      trace_id: "trace-vitest",
    });
  }

  if (path === "/api/v1/ontology-rag/ontology/concepts" && method === "GET") {
    const writableScopes: Array<{ level: string; scope_id: string; label: string }> = [];
    if (canWriteScope(actor, "1_ENTERPRISE", "scope-global", orgUnits, workspaces)) {
      writableScopes.push({ level: "1_ENTERPRISE", scope_id: "scope-global", label: "Organisation (Global)" });
    }
    for (const u of orgUnits) {
      const lvl = u.kind === "BU" ? "2_DOMAIN" : "3_TEAM";
      if (canWriteScope(actor, lvl, u.id, orgUnits, workspaces)) {
        writableScopes.push({ level: lvl, scope_id: u.id, label: u.name });
      }
    }
    for (const ws of workspaces) {
      const wsId = String(ws.workspaceId ?? ws.id ?? "");
      if (wsId && canWriteScope(actor, "4_WORKSPACE", wsId, orgUnits, workspaces)) {
        writableScopes.push({ level: "4_WORKSPACE", scope_id: wsId, label: String(ws.name ?? wsId) });
      }
    }
    if (writableScopes.length === 0 && !actor.isObserver && actor.roles.has("PLATFORM_ADMIN")) {
      writableScopes.push({ level: "1_ENTERPRISE", scope_id: "scope-global", label: "Organisation (Global)" });
    }
    const items = mockConcepts.map((c) => {
      const next = actor.isObserver ? null : resolveNextTarget(c.level, c.scope_id, orgUnits, workspaces);
      return {
        ...c,
        can_edit: canWriteScope(actor, c.level, c.scope_id, orgUnits, workspaces),
        can_propose_promotion: Boolean(next),
        next_promotion_level: next?.targetLevel ?? null,
        next_promotion_scope_id: next?.targetScopeId ?? null,
      };
    });
    return jsonResponse({
      concepts: items,
      writable_levels: Array.from(new Set(writableScopes.map((s) => s.level))),
      writable_scopes: writableScopes,
      trace_id: "trace-vitest",
    });
  }

  if (path === "/api/v1/ontology-rag/ontology/concepts" && method === "POST") {
    const level = String(body.level ?? "4_WORKSPACE");
    const scopeId = String(body.scope_id ?? "scope-global");
    if (actor.isObserver) {
      return problemResponse(403, "ERR_OBSERVER_MODE_READ_ONLY", "Forbidden", "Read-only observer mode", path);
    }
    if (!canWriteScope(actor, level, scopeId, orgUnits, workspaces)) {
      return problemResponse(403, "ERR_SCOPE_ACCESS_DENIED", "Forbidden", "Forbidden ontology level write", path);
    }
    const term = String(body.canonical_term ?? "").trim();
    const conceptKey = String(body.concept_key ?? `concept-${++seq}`);
    const keyCollision = mockConcepts.find(
      (c) => c.concept_key === conceptKey && (c.level !== level || c.scope_id !== scopeId),
    );
    if (keyCollision) {
      return problemResponse(409, "ERR_ONTOLOGY_CONFLICT", "Conflict", "Cross-scope concept_key conflict", path);
    }
    const existingIdx = mockConcepts.findIndex(
      (c) => c.concept_key === conceptKey || (c.level === level && c.scope_id === scopeId && c.canonical_term.toLowerCase() === term.toLowerCase()),
    );
    const saved: MockOntologyConcept = {
      id: existingIdx >= 0 ? mockConcepts[existingIdx]!.id : `concept-uuid-${++seq}`,
      concept_key: existingIdx >= 0 ? mockConcepts[existingIdx]!.concept_key : conceptKey,
      canonical_term: term,
      level,
      scope_id: scopeId,
      definition_text: String(body.definition_text ?? term),
      parent_concept_id: (body.parent_concept_id as string | null | undefined) ?? null,
      synonyms: Array.isArray(body.synonyms) ? body.synonyms.map(String) : [],
      banned_terms: Array.isArray(body.banned_terms) ? body.banned_terms.map(String) : [],
      profile_translations: (body.profile_translations as Record<string, string>) ?? {},
      expected_schema: (body.expected_schema as Record<string, string>) ?? {},
      introduced_in_snapshot_id: null,
      snapshot_branch_status: "ACTIVE",
    };
    if (existingIdx >= 0) mockConcepts[existingIdx] = saved;
    else mockConcepts.push(saved);
    return jsonResponse(saved);
  }

  if (path === "/api/v1/ontology-rag/ontology/promotions" && method === "GET") {
    const statusFilter = parsedUrl?.searchParams.get("status");
    const proposals = mockPromotions
      .filter((p) => !statusFilter || p.status === statusFilter)
      .map((p) => ({
      ...p,
      impact_report: {
        concept_key: p.concept_key,
        canonical_term: p.canonical_term,
        proposed_change: `Promote ${p.canonical_term}`,
        transitively_affected_concepts: [],
        impacted_artifact_templates: [],
        impacted_workflow_uris: [],
        impacted_active_run_ids: [],
        has_immutable_axiom_conflict: false,
      },
      badge_color_token: "ontology-cyan",
      can_decide: canWriteScope(actor, p.target_level, p.target_scope_id, orgUnits, workspaces),
    }));
    return jsonResponse({
      proposals,
      pending_count: proposals.filter((p) => p.status === "PENDING_REVIEW").length,
      trace_id: "trace-vitest",
    });
  }

  if (path === "/api/v1/ontology-rag/ontology/promotions" && method === "POST") {
    if (actor.isObserver) {
      return problemResponse(403, "ERR_OBSERVER_MODE_READ_ONLY", "Forbidden", "Read-only observer mode", path);
    }
    const conceptKey = String(body.concept_key ?? "");
    const src = mockConcepts.find((c) => c.concept_key === conceptKey);
    if (!src) {
      return problemResponse(404, "ERR_RESOURCE_NOT_FOUND", "Not found", "Concept not found", path);
    }
    const next = resolveNextTarget(
      src.level,
      src.scope_id,
      orgUnits,
      workspaces,
      body.target_level ? String(body.target_level) : null,
      null,
    );
    if (!next) {
      return problemResponse(422, "ERR_ONTOLOGY_PROMOTION_STEP_INVALID", "Unprocessable Entity", "Level jump forbidden", path);
    }
    if (body.target_scope_id && String(body.target_scope_id).trim() && String(body.target_scope_id).trim() !== next.targetScopeId) {
      return problemResponse(403, "ERR_SCOPE_ACCESS_DENIED", "Forbidden", "Forged target_scope_id rejected", path);
    }
    const colliding = mockConcepts.find(
      (c) => c.level === next.targetLevel && c.scope_id === next.targetScopeId && c.canonical_term.toLowerCase() === src.canonical_term.toLowerCase(),
    );
    const propId = `prop-${++propSeq}`;
    const created: MockOntologyPromotion = {
      id: propId,
      proposal_key: `prop-${src.concept_key}-${propId}`,
      concept_key: src.concept_key,
      canonical_term: src.canonical_term,
      source_level: src.level,
      target_level: next.targetLevel,
      target_scope_id: next.targetScopeId,
      proposed_by_user_id: actor.email,
      status: "PENDING_REVIEW",
      source_concept_id: src.id,
      source_scope_id: src.scope_id,
      definition_text: src.definition_text,
      reviewed_by_user_id: null,
      review_comment: null,
      collision_detected: Boolean(colliding),
      colliding_definition: colliding?.definition_text ?? null,
    };
    mockPromotions.unshift(created);
    return jsonResponse({
      ...created,
      impact_report: {
        concept_key: created.concept_key,
        canonical_term: created.canonical_term,
        proposed_change: `Promote ${created.canonical_term}`,
        transitively_affected_concepts: [],
        impacted_artifact_templates: [],
        impacted_workflow_uris: [],
        impacted_active_run_ids: [],
        has_immutable_axiom_conflict: false,
      },
      badge_color_token: "ontology-cyan",
      can_decide: canWriteScope(actor, created.target_level, created.target_scope_id, orgUnits, workspaces),
    });
  }

  const decideMatch = /^\/api\/v1\/ontology-rag\/ontology\/promotions\/([^/]+)\/decide$/.exec(path);
  if (decideMatch && method === "POST") {
    if (actor.isObserver) {
      return problemResponse(403, "ERR_OBSERVER_MODE_READ_ONLY", "Forbidden", "Read-only observer mode", path);
    }
    const propId = decodeURIComponent(decideMatch[1] ?? "");
    const prop = mockPromotions.find((p) => p.id === propId || p.proposal_key === propId);
    if (!prop) {
      return problemResponse(404, "ERR_RESOURCE_NOT_FOUND", "Not found", "Proposal not found", path);
    }
    if (!canWriteScope(actor, prop.target_level, prop.target_scope_id, orgUnits, workspaces)) {
      return problemResponse(403, "ERR_SCOPE_ACCESS_DENIED", "Forbidden", "Reviewer lacks authority", path);
    }
    const decision = String(body.decision ?? "APPROVE");
    prop.status = decision === "APPROVE" ? "APPROVED" : "REJECTED";
    prop.reviewed_by_user_id = actor.email;
    prop.review_comment = body.review_comment ? String(body.review_comment) : null;
    let promotedConcept: MockOntologyConcept | null = null;
    if (decision === "APPROVE") {
      promotedConcept = {
        id: `concept-uuid-${++seq}`,
        concept_key: `${prop.concept_key}-${prop.target_level.toLowerCase()}`,
        canonical_term: prop.canonical_term,
        level: prop.target_level,
        scope_id: prop.target_scope_id,
        definition_text: prop.definition_text,
        parent_concept_id: prop.source_concept_id,
        synonyms: [],
        banned_terms: [],
        profile_translations: {},
        expected_schema: {},
        introduced_in_snapshot_id: null,
        snapshot_branch_status: "ACTIVE",
      };
      mockConcepts.push(promotedConcept);
    }
    return jsonResponse({
      proposal: {
        ...prop,
        impact_report: {
          concept_key: prop.concept_key,
          canonical_term: prop.canonical_term,
          proposed_change: `Promote ${prop.canonical_term}`,
          transitively_affected_concepts: [],
          impacted_artifact_templates: [],
          impacted_workflow_uris: [],
          impacted_active_run_ids: [],
          has_immutable_axiom_conflict: false,
        },
        badge_color_token: "ontology-cyan",
        can_decide: true,
      },
      promoted_concept: promotedConcept,
      status: prop.status,
      trace_id: "trace-vitest",
    });
  }

  return null;
}
