import { useAuthSessionStore } from "../../stores/authSessionStore";
import { backendState, jsonResponse, problemResponse } from "./mockBackendState";

function isObserverRequest(reqHeaders: Headers): boolean {
  const accessMode = (reqHeaders.get("x-orcia-access-mode") ?? "").toUpperCase();
  const activeHat = (reqHeaders.get("x-orcia-active-hat") ?? "PLATFORM_ADMIN").toUpperCase();
  const session = useAuthSessionStore.getState();
  return (
    accessMode === "READ_ONLY_OBSERVER" ||
    activeHat === "OBSERVER" ||
    Boolean(session.readOnlyObserver) ||
    session.roles.map((r) => String(r).toUpperCase()).includes("OBSERVER")
  );
}

export function handleWorkspacesAndCatalogRoute(params: {
  path: string;
  method: string;
  parsedUrl: URL;
  body: Record<string, unknown>;
  reqHeaders: Headers;
}): Response | null {
  const { path, method, parsedUrl, body, reqHeaders } = params;

  if (path === "/api/v1/workspaces" && method === "GET") {
    return jsonResponse({
      workspaces: backendState.workspaces,
      consolidated_finops_usd: 0,
      trace_id: "0195f000000070008000000000000999",
    });
  }

  if (path === "/api/v1/workspaces" && method === "POST") {
    const accessMode = (reqHeaders.get("x-orcia-access-mode") ?? "").toUpperCase();
    const activeHat = (reqHeaders.get("x-orcia-active-hat") ?? "PLATFORM_ADMIN").toUpperCase();
    if (accessMode === "READ_ONLY_OBSERVER" || activeHat === "OBSERVER") {
      return problemResponse(403, "ERR_OBSERVER_MODE_READ_ONLY", "Mode observateur en lecture seule", "Les mutations sont refusées en mode observateur lecture seule.", path);
    }
    const name = String(body.name ?? "").trim();
    if (!name) {
      return problemResponse(422, "ERR_VALIDATION_ERROR", "Nom d'espace requis", "Le nom de l'espace de travail ne peut pas être vide.", path);
    }
    const rawExplicitSlug = typeof body.slug === "string" ? body.slug.trim() : "";
    const slug =
      rawExplicitSlug && /^[a-z0-9-]+$/.test(rawExplicitSlug)
        ? rawExplicitSlug.slice(0, 120)
        : (rawExplicitSlug || name).toLowerCase().replace(/[^a-z0-9-]+/g, "-").replace(/^-|-$/g, "") || `ws-${backendState.workspaceSeq + 1}`;
    const rawOwnerId = typeof body.owner_org_unit_id === "string" && body.owner_org_unit_id.trim() ? body.owner_org_unit_id.trim() : null;
    const ownerUnit = rawOwnerId
      ? backendState.orgUnits.find((u) => u.id === rawOwnerId)
      : backendState.orgUnits.find((u) => u.kind === "TEAM") ?? backendState.orgUnits[0];
    const ownerOrgUnitId = ownerUnit?.id ?? rawOwnerId ?? "0192c4e0-0000-7000-8000-000000000101";
    const ownerOrgUnitName = ownerUnit?.name ?? "Plateforme Globale ORCIA";
    const visibilityMode = body.visibility_mode === "CONFIDENTIAL_RESTRICTED" || body.visibility_mode === "PRIVATE_USER" ? body.visibility_mode : "STANDARD";
    const lifecyclePhase = body.lifecycle_phase === "RUN" || body.lifecycle_phase === "MIGRATION" ? body.lifecycle_phase : "BUILD";

    backendState.workspaceSeq += 1;
    const id = `0195f000-0000-7000-8000-${String(backendState.workspaceSeq).padStart(12, "0")}`;
    const created = {
      id,
      slug,
      name,
      owner_org_unit_id: ownerOrgUnitId,
      owner_org_unit_name: ownerOrgUnitName,
      visibility_mode: visibilityMode,
      lifecycle_phase: lifecyclePhase,
      effective_role: "PLATFORM_ADMIN",
      access_mode: "CONTRIBUTOR_ACTION_REQUIRED",
      access_origin: "GLOBAL_ADMIN",
      finops_cost_usd: 0,
      trace_id: "0195f000000070008000000000000999",
    };
    backendState.workspaces = [...backendState.workspaces, created];
    return jsonResponse(created, 201);
  }

  const wsPatchMatch = path.match(/^\/api\/v1\/workspaces\/([^/]+)$/);
  if (wsPatchMatch && method === "PATCH") {
    if (isObserverRequest(reqHeaders)) {
      return problemResponse(
        403,
        "ERR_OBSERVER_MODE_READ_ONLY",
        "Mode observateur en lecture seule",
        "Les mutations sont refusées en mode observateur lecture seule.",
        path,
      );
    }
    const wsId = decodeURIComponent(wsPatchMatch[1] ?? "");
    const setupWorkspaces = Array.isArray(backendState.platformSetupState?.workspaces)
      ? (backendState.platformSetupState.workspaces as Array<Record<string, unknown>>)
      : [];
    const memWs = backendState.workspaces.find((w) => w.id === wsId || w.slug === wsId);
    const setupWs = setupWorkspaces.find(
      (w) => String(w.workspaceId ?? w.id ?? "") === wsId || String(w.slug ?? "") === wsId,
    );
    const target = memWs ?? setupWs;
    if (!target) {
      return problemResponse(404, "ERR_RESOURCE_NOT_FOUND", "Introuvable", "Espace introuvable.", path);
    }
    const wsSlug = String(target.slug ?? wsId);
    const curVis = String(target.visibility_mode ?? target.visibilityMode ?? "STANDARD").toUpperCase();
    const isPersonal = curVis === "PRIVATE_USER" || wsSlug.startsWith("personal-");
    const reqVis =
      typeof body.visibility_mode === "string" ? body.visibility_mode.trim().toUpperCase() : null;
    if (isPersonal && reqVis !== null && reqVis !== "PRIVATE_USER") {
      return problemResponse(
        403,
        "ERR_PRIVATE_WORKSPACE_VISIBILITY_LOCKED",
        "Visibilité d'espace personnel verrouillée",
        "Un espace personnel privé (PRIVATE_USER) ne peut pas changer de visibilité sur place.",
        path,
      );
    }
    if (!isPersonal && reqVis === "PRIVATE_USER") {
      return problemResponse(
        403,
        "ERR_PRIVATE_WORKSPACE_VISIBILITY_LOCKED",
        "Visibilité d'espace personnel verrouillée",
        "Un espace d'équipe ne peut pas devenir PRIVATE_USER sur place.",
        path,
      );
    }
    const nextName =
      typeof body.name === "string" && body.name.trim() ? body.name.trim() : String(target.name ?? wsId);
    const nextVis = reqVis ?? curVis;
    const nextPhase =
      typeof body.lifecycle_phase === "string" && ["BUILD", "RUN", "MIGRATION"].includes(body.lifecycle_phase)
        ? body.lifecycle_phase
        : String(target.lifecycle_phase ?? target.lifecyclePhase ?? "BUILD");
    const resolvedId = String(target.id ?? target.workspaceId ?? wsId);
    const ownerOuId = String(
      target.owner_org_unit_id ?? target.ownerOrgUnitId ?? "0192c4e0-0000-7000-8000-000000000101",
    );
    const ownerOuName = String(target.owner_org_unit_name ?? target.ownerOrgUnitName ?? "ORCIA");

    if (memWs) {
      backendState.workspaces = backendState.workspaces.map((w) =>
        w.id === resolvedId
          ? { ...w, name: nextName, visibility_mode: nextVis, lifecycle_phase: nextPhase }
          : w,
      );
    }
    if (backendState.platformSetupState && Array.isArray(backendState.platformSetupState.workspaces)) {
      backendState.platformSetupState = {
        ...backendState.platformSetupState,
        workspaces: (backendState.platformSetupState.workspaces as Array<Record<string, unknown>>).map(
          (w) =>
            String(w.workspaceId ?? w.id ?? "") === resolvedId
              ? { ...w, name: nextName, visibilityMode: nextVis, lifecyclePhase: nextPhase }
              : w,
        ),
      };
    }

    return jsonResponse({
      id: resolvedId,
      slug: wsSlug,
      name: nextName,
      owner_org_unit_id: ownerOuId,
      owner_org_unit_name: ownerOuName,
      visibility_mode: nextVis,
      lifecycle_phase: nextPhase,
      effective_role: "PLATFORM_ADMIN",
      access_mode: "CONTRIBUTOR_ACTION_REQUIRED",
      access_origin: "GLOBAL_ADMIN",
      finops_cost_usd: Number(target.finops_cost_usd ?? target.finopsCostUsd ?? 0),
      trace_id: "0195f000000070008000000000000999",
    });
  }

  const waiverMatch = path.match(/^\/api\/v1\/workspaces\/([^/]+)\/exception-waivers$/);
  if (waiverMatch) {
    const wsId = decodeURIComponent(waiverMatch[1] ?? "");
    if (method === "GET") {
      const activeOnly = parsedUrl.searchParams.get("active_only") === "true";
      const rows = backendState.workspaceWaivers.filter(
        (w) => String(w.workspace_id) === wsId && (!activeOnly || String(w.status) === "ACTIVE"),
      );
      return jsonResponse(rows);
    }
    if (method === "POST") {
      const accessMode = (reqHeaders.get("x-orcia-access-mode") ?? "").toUpperCase();
      const activeHat = (reqHeaders.get("x-orcia-active-hat") ?? "PLATFORM_ADMIN").toUpperCase();
      if (accessMode === "READ_ONLY_OBSERVER" || activeHat === "OBSERVER") {
        return problemResponse(403, "ERR_OBSERVER_MODE_READ_ONLY", "Mode observateur en lecture seule", "Les mutations sont refusées en mode observateur lecture seule.", path);
      }
      backendState.waiverSeq += 1;
      const waiverId = `0195f000-0000-7000-8100-${String(backendState.waiverSeq).padStart(12, "0")}`;
      const created = {
        waiver_id: waiverId,
        workspace_id: wsId,
        source_uri: String(body.source_uri ?? ""),
        source_sha256: String(body.source_sha256 ?? "sha256:workspace-source-baseline-0001"),
        conflict_rule_id: String(body.conflict_rule_id ?? ""),
        norm_level: String(body.norm_level ?? "3_WORKSPACE"),
        dna_chain: Array.isArray(body.dna_chain) ? body.dna_chain : [],
        approved_by_user_id: "0195f000-0000-7000-8000-000000000001",
        approved_by_role: activeHat,
        reason: String(body.reason ?? ""),
        status: "ACTIVE",
        expires_at: "2026-12-18T12:00:00Z",
        created_at: "2026-11-18T12:00:00Z",
      };
      backendState.workspaceWaivers = [
        created,
        ...backendState.workspaceWaivers.filter(
          (w) => !(String(w.workspace_id) === wsId && String(w.source_uri) === created.source_uri && String(w.conflict_rule_id) === created.conflict_rule_id),
        ),
      ];
      return jsonResponse(created);
    }
  }

  const dnaListMatch = path.match(/^\/api\/v1\/workspaces\/([^/]+)\/dna-mechanisms$/);
  if (dnaListMatch && method === "GET") {
    const wsId = decodeURIComponent(dnaListMatch[1] ?? "");
    const rows = backendState.dnaMechanisms
      .filter((entry) => String(entry.workspace_id) === wsId)
      .map((entry) => entry.mechanism as Record<string, unknown>);
    return jsonResponse(rows);
  }

  const dnaCompileMatch = path.match(/^\/api\/v1\/workspaces\/([^/]+)\/dna-mechanisms\/compile$/);
  if (dnaCompileMatch && method === "POST") {
    if (isObserverRequest(reqHeaders)) {
      return problemResponse(
        403,
        "ERR_OBSERVER_MODE_READ_ONLY",
        "Mode observateur en lecture seule",
        "Les mutations sont refusées en mode observateur lecture seule.",
        path,
      );
    }
    const wsId = decodeURIComponent(dnaCompileMatch[1] ?? "");
    const ruleId = String(body.rule_id ?? "RULE-01");
    const directiveTitle = String(body.directive_title ?? "Orientation Qualité");
    const normTitle = String(body.norm_title ?? `Règle ${ruleId}`);
    const requiredField = String(body.required_field ?? "reference_code");
    const existing = backendState.dnaMechanisms.find(
      (entry) =>
        String(entry.workspace_id) === wsId &&
        String((entry.mechanism as Record<string, unknown>).rule_id) === ruleId,
    );
    let mechanismId = existing
      ? String((existing.mechanism as Record<string, unknown>).mechanism_id)
      : "";
    if (!mechanismId) {
      backendState.dnaMechanismSeq += 1;
      mechanismId = `0195f000-0000-7000-8200-${String(backendState.dnaMechanismSeq).padStart(12, "0")}`;
    }
    const scriptName = `${ruleId.toLowerCase().replace(/[^a-z0-9_]/g, "_")}.star`;
    const mechanism: Record<string, unknown> = {
      mechanism_id: mechanismId,
      rule_id: ruleId,
      directive_title: directiveTitle,
      norm_title: normTitle,
      script_name: scriptName,
      starlark_code: `def check(ctx):\n    val = ctx.payload.get("${requiredField}", "")\n    if not val:\n        orcia_sys.emit_verdict("${ruleId}", "FAIL", "Champ ${requiredField} obligatoire")\n        return False\n    orcia_sys.emit_verdict("${ruleId}", "PASS", "Conforme")\n    return True`,
      sha256: `sha256:${ruleId.toLowerCase()}`,
      passing_test_payload:
        (body.passing_test_payload as Record<string, unknown> | undefined) ?? {
          [requiredField]: "ORCIA_VALID_01",
        },
      failing_test_payload:
        (body.failing_test_payload as Record<string, unknown> | undefined) ?? {
          [requiredField]: "invalid value!",
        },
      explanation_fr: `Vérifie automatiquement la conformité de la règle « ${ruleId} » avant chaque validation.`,
      self_corrected: Boolean(body.simulate_initial_bad_regex),
      compile_elapsed_ms: 1.4,
      verified_badge_fr: "✓ Vérifié automatiquement (cas valide + cas rejeté)",
      causal_breadcrumb: `Orientation ➔ Règle (${ruleId}) ➔ Contrôle automatique`,
      signed_and_active: true,
    };
    backendState.dnaMechanisms = [
      { workspace_id: wsId, mechanism },
      ...backendState.dnaMechanisms.filter(
        (entry) =>
          !(
            String(entry.workspace_id) === wsId &&
            String((entry.mechanism as Record<string, unknown>).rule_id) === ruleId
          ),
      ),
    ];
    return jsonResponse(mechanism);
  }

  const dnaActivateMatch = path.match(
    /^\/api\/v1\/workspaces\/([^/]+)\/dna-mechanisms\/([^/]+)\/activate$/,
  );
  if (dnaActivateMatch && method === "POST") {
    if (isObserverRequest(reqHeaders)) {
      return problemResponse(
        403,
        "ERR_OBSERVER_MODE_READ_ONLY",
        "Mode observateur en lecture seule",
        "Les mutations sont refusées en mode observateur lecture seule.",
        path,
      );
    }
    const wsId = decodeURIComponent(dnaActivateMatch[1] ?? "");
    const mechId = decodeURIComponent(dnaActivateMatch[2] ?? "");
    let activated: Record<string, unknown> | null = null;
    backendState.dnaMechanisms = backendState.dnaMechanisms.map((entry) => {
      const mech = entry.mechanism as Record<string, unknown>;
      if (String(entry.workspace_id) === wsId && String(mech.mechanism_id) === mechId) {
        activated = { ...mech, signed_and_active: true };
        return { workspace_id: wsId, mechanism: activated };
      }
      return entry;
    });
    if (!activated) {
      return problemResponse(
        404,
        "ERR_RESOURCE_NOT_FOUND",
        "Mécanisme ADN introuvable",
        `Mécanisme '${mechId}' introuvable pour l'espace '${wsId}'.`,
        path,
      );
    }
    return jsonResponse(activated);
  }

  if (path === "/api/v1/agents-and-skills" && method === "GET") {
    return jsonResponse({ agents: backendState.agents, skills: backendState.skills });
  }
  if (path === "/api/v1/agents-and-skills/skills" && method === "POST") {
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
    backendState.skills = [...backendState.skills.filter((s) => s.skill_id !== skillId), entry];
    return jsonResponse(entry);
  }
  if (path.startsWith("/api/v1/agents-and-skills/skills/") && path.endsWith("/execute") && method === "POST") {
    const skillId = decodeURIComponent(path.slice("/api/v1/agents-and-skills/skills/".length, -"/execute".length));
    const existing = backendState.skills.find((s) => s.skill_id === skillId);
    const name = String(existing?.name ?? skillId);
    const handle = String(existing?.command_handle ?? `/${skillId.replace(/^skill-/, "")}`);
    return jsonResponse({
      skill_id: skillId,
      output_text: `### ✅ Exécution de la compétence **${name}** (\`${handle}\`)\n- **Entrée analysée** : ${String(body.input_text ?? "").trim()}`,
    });
  }
  if (path.startsWith("/api/v1/agents-and-skills/skills/") && method === "DELETE") {
    const skillId = decodeURIComponent(path.slice("/api/v1/agents-and-skills/skills/".length));
    backendState.skills = backendState.skills.filter((s) => s.skill_id !== skillId);
    return jsonResponse({ deleted: true, skill_id: skillId });
  }
  if (path === "/api/v1/agents-and-skills/agents" && method === "POST") {
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
    backendState.agents = [...backendState.agents.filter((a) => a.agent_id !== agentId), entry];
    return jsonResponse(entry);
  }
  if (path.startsWith("/api/v1/agents-and-skills/agents/") && path.endsWith("/duplicate") && method === "POST") {
    return jsonResponse({ agent_id: `agent-copie-${backendState.recordedCalls.length}`, name: String(body.new_name ?? "Agent (Copie)") });
  }
  if (path.startsWith("/api/v1/agents-and-skills/agents/") && path.endsWith("/governance") && method === "PATCH") {
    const agentId = decodeURIComponent(path.slice("/api/v1/agents-and-skills/agents/".length, -"/governance".length));
    backendState.agents = backendState.agents.map((a) => (a.agent_id === agentId ? { ...a, ...body } : a));
    return jsonResponse({ agent_id: agentId, ...body });
  }
  if (path.startsWith("/api/v1/agents-and-skills/agents/") && path.endsWith("/skills") && method === "PATCH") {
    const agentId = decodeURIComponent(path.slice("/api/v1/agents-and-skills/agents/".length, -"/skills".length));
    const skillIds = Array.isArray(body.skill_ids) ? body.skill_ids : [];
    backendState.agents = backendState.agents.map((a) => (a.agent_id === agentId ? { ...a, skill_ids: skillIds } : a));
    return jsonResponse({ agent_id: agentId, skill_ids: skillIds });
  }
  if (path.startsWith("/api/v1/agents-and-skills/agents/") && path.endsWith("/execute") && method === "POST") {
    const agentId = decodeURIComponent(path.slice("/api/v1/agents-and-skills/agents/".length, -"/execute".length));
    const existing = backendState.agents.find((a) => a.agent_id === agentId);
    return jsonResponse({
      agent_id: agentId,
      response_text: `### ✅ Agent **${String(existing?.name ?? agentId)}**\n- **Demande traitée** : ${String(body.prompt ?? "").trim()}`,
    });
  }
  if (path.startsWith("/api/v1/agents-and-skills/agents/") && method === "DELETE") {
    const agentId = decodeURIComponent(path.slice("/api/v1/agents-and-skills/agents/".length));
    backendState.agents = backendState.agents.filter((a) => a.agent_id !== agentId);
    return jsonResponse({ deleted: true, agent_id: agentId });
  }

  return null;
}
