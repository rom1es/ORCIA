import { backendState, jsonResponse, problemResponse } from "./mockBackendState";

export function handleAgentsAndSkillsMockRoute(params: {
  path: string;
  method: string;
  body: Record<string, unknown>;
}): Response | null {
  const { path, method, body } = params;

  if (path === "/api/v1/agents-and-skills" && method === "GET") {
    const setupPacks = Array.isArray(backendState.platformSetupState?.packs)
      ? (backendState.platformSetupState.packs as Array<Record<string, unknown>>)
      : [];
    const hasSdlcPack = setupPacks.some(
      (p) => String(p.packKey ?? p.pack_key ?? "") === "orcia-pack-sdlc",
    );
    const seededPackAgents =
      hasSdlcPack && !backendState.agents.some((a) => a.agent_id === "agent-architecte-solution")
        ? [
            {
              agent_id: "agent-architecte-solution",
              slug: "architecte-solution",
              handle: "@architecte-solution",
              name: "Architecte Solution",
              role_mission: "Cadrer les dossiers d'architecture et ADR.",
              instructions: "Construire le dossier d'architecture en 14 points.",
              thinking_level: "complex",
              skill_ids: [],
              visibility_scope: "PACK",
              source_pack_key: "orcia-pack-sdlc",
              pack_slug: "sdlc",
              qualified_ref: "@sdlc/architecte-solution",
              is_colliding: false,
              collision_pack_slugs: ["sdlc"],
              resolution_tier: "SYSTEM_PACK",
              enabled_in_workspace: true,
              mcp_exposed: false,
              posture: "PRODUCER",
              human_partner_role: "ARCHITECT",
              test_bench_validated: true,
              test_bench_status: "PASSED",
              lifecycle_status: "ACTIVE",
            },
          ]
        : [];
    return jsonResponse({
      agents: [...backendState.agents, ...seededPackAgents],
      skills: backendState.skills,
    });
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
    const existing = backendState.agents.find((a) => a.agent_id === agentId);
    const benchStatus = String(
      body.test_bench_status ??
        (body.test_bench_validated === true
          ? "PASSED"
          : (existing?.test_bench_status ?? "UNTESTED")),
    );
    const lifecycleStatus = String(
      body.lifecycle_status ??
        (benchStatus === "PASSED" ? "ACTIVE" : (existing?.lifecycle_status ?? "DRAFT")),
    );
    const mcpExposed = Boolean(body.mcp_exposed ?? existing?.mcp_exposed ?? false);
    if (mcpExposed && lifecycleStatus === "DRAFT") {
      return problemResponse(
        422,
        "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED",
        "Exposition externe interdite sur un agent en brouillon (DRAFT)",
        "Cet agent est en brouillon (DRAFT) et ne peut pas être exposé en outil externe MCP.",
        path,
      );
    }
    const entry = {
      agent_id: agentId,
      slug,
      handle: `@${slug}`,
      name: String(body.name ?? existing?.name ?? "Agent"),
      role_mission: String(body.role_mission ?? existing?.role_mission ?? ""),
      instructions: String(body.instructions ?? existing?.instructions ?? ""),
      thinking_level: String(body.thinking_level ?? existing?.thinking_level ?? "medium"),
      skill_ids: Array.isArray(body.skill_ids) ? body.skill_ids : (existing?.skill_ids ?? []),
      visibility_scope: String(body.visibility_scope ?? existing?.visibility_scope ?? "TEAM"),
      source_pack_key: existing?.source_pack_key ?? null,
      enabled_in_workspace: existing?.enabled_in_workspace ?? true,
      mcp_exposed: mcpExposed,
      test_bench_validated: benchStatus === "PASSED",
      test_bench_status: benchStatus,
      lifecycle_status: lifecycleStatus,
    };
    backendState.agents = [...backendState.agents.filter((a) => a.agent_id !== agentId), entry];
    return jsonResponse(entry);
  }
  if (path.startsWith("/api/v1/agents-and-skills/agents/") && path.endsWith("/duplicate") && method === "POST") {
    return jsonResponse({ agent_id: `agent-copie-${backendState.recordedCalls.length}`, name: String(body.new_name ?? "Agent (Copie)") });
  }
  if (path.startsWith("/api/v1/agents-and-skills/agents/") && path.endsWith("/governance") && method === "PATCH") {
    const agentId = decodeURIComponent(path.slice("/api/v1/agents-and-skills/agents/".length, -"/governance".length));
    const existing = backendState.agents.find((a) => a.agent_id === agentId);
    if (!existing) {
      return problemResponse(
        404,
        "ERR_RESOURCE_NOT_FOUND",
        "Ressource introuvable",
        `Agent '${agentId}' introuvable.`,
        path,
      );
    }
    const nextLifecycle = String(body.lifecycle_status ?? existing.lifecycle_status ?? "DRAFT");
    const nextMcp =
      nextLifecycle === "DRAFT" && body.mcp_exposed !== true
        ? false
        : Boolean(body.mcp_exposed ?? existing.mcp_exposed ?? false);
    if (nextMcp && nextLifecycle === "DRAFT") {
      return problemResponse(
        422,
        "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED",
        "Exposition externe interdite sur un agent en brouillon (DRAFT)",
        "Cet agent est en brouillon (DRAFT) et ne peut pas être exposé en outil externe MCP.",
        path,
      );
    }
    const updated = {
      ...existing,
      ...body,
      lifecycle_status: nextLifecycle,
      mcp_exposed: nextMcp,
    };
    backendState.agents = backendState.agents.map((a) => (a.agent_id === agentId ? updated : a));
    return jsonResponse(updated);
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
    if (existing) {
      backendState.agents = backendState.agents.map((a) =>
        a.agent_id === agentId
          ? {
              ...a,
              test_bench_validated: true,
              test_bench_status: "PASSED",
              lifecycle_status: "ACTIVE",
            }
          : a,
      );
    }
    return jsonResponse({
      agent_id: agentId,
      test_bench_status: "PASSED",
      lifecycle_status: "ACTIVE",
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
