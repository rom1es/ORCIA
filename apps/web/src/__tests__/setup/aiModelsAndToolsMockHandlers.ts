import { backendState, jsonResponse } from "./mockBackendState";

export function handleAiModelsAndToolsRoute(params: {
  path: string;
  method: string;
  parsedUrl: URL;
  body: Record<string, unknown>;
}): Response | null {
  const { path, method, parsedUrl, body } = params;

  if (path.startsWith("/api/v1/audit/ledger") && method === "GET") {
    if (path.includes("/provenance")) {
      const runId = path.split("/")[5] ?? "0195f000-0000-7000-8000-000000000001";
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
      const runId = path.split("/")[5] ?? "0195f000-0000-7000-8000-000000000001";
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

  if (path === "/api/v1/bootstrap/welcome-setup/llm-test" && method === "POST") {
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

  if (path === "/api/v1/bootstrap/welcome-setup/progressive-llm" && method === "POST") {
    return jsonResponse({ status: "registered", endpoint_key: body.endpoint_key ?? "medium" });
  }

  if (path === "/api/v1/settings/ai-models/mappings" && method === "GET") {
    let items = backendState.aiModelMappings;
    const usage = parsedUrl.searchParams.get("usage");
    const isActive = parsedUrl.searchParams.get("is_active");
    if (usage) items = items.filter((m) => m.usage === usage);
    if (isActive !== null) items = items.filter((m) => String(m.is_active) === isActive);
    return jsonResponse({ items, total: items.length });
  }

  if (path === "/api/v1/settings/ai-models/mappings" && method === "POST") {
    const newId = `0195f000-0000-7000-8300-${String(backendState.aiModelMappings.length + 1).padStart(12, "0")}`;
    const created: Record<string, unknown> = {
      id: newId,
      scope_level: String(body.scope_level ?? "GLOBAL"),
      scope_id: body.scope_id ?? null,
      display_name: String(body.display_name ?? body.model_name ?? "Modèle IA"),
      inference_tier: String(body.inference_tier ?? "medium"),
      effort: String(body.effort ?? "balanced"),
      provider_slug: String(body.provider_slug ?? "openai"),
      model_family: String(body.model_family ?? "OpenAI"),
      model_name: String(body.model_name ?? "gpt-4o-mini"),
      fallback_model_name: body.fallback_model_name ?? null,
      endpoint_uri: String(body.endpoint_uri ?? "https://api.openai.com/v1"),
      auth_mode: String(body.auth_mode ?? "api_key"),
      protocol_mode: String(body.protocol_mode ?? "openai_compatible"),
      usage: String(body.usage ?? "chat"),
      is_active: body.is_active !== undefined ? Boolean(body.is_active) : true,
      draining: false,
      health_status: "OPERATIONAL",
      created_at: "2026-11-18T10:00:00Z",
    };
    backendState.aiModelMappings = [...backendState.aiModelMappings, created];
    return jsonResponse(created, 201);
  }

  const aiMappingItemMatch = /^\/api\/v1\/settings\/ai-models\/mappings\/([^/]+)$/.exec(path);
  if (aiMappingItemMatch && method === "PATCH") {
    const mappingId = decodeURIComponent(aiMappingItemMatch[1] ?? "");
    let updated: Record<string, unknown> | null = null;
    backendState.aiModelMappings = backendState.aiModelMappings.map((m) => {
      if (m.id === mappingId) {
        updated = { ...m, ...body };
        return updated;
      }
      return m;
    });
    if (!updated) return jsonResponse({ error_code: "ERR_RESOURCE_NOT_FOUND" }, 404);
    return jsonResponse(updated);
  }
  if (aiMappingItemMatch && method === "DELETE") {
    const mappingId = decodeURIComponent(aiMappingItemMatch[1] ?? "");
    backendState.aiModelMappings = backendState.aiModelMappings.filter((m) => m.id !== mappingId);
    return jsonResponse({ deleted: true, mapping_id: mappingId });
  }
  const aiMappingActionMatch = /^\/api\/v1\/settings\/ai-models\/mappings\/([^/]+)\/(test|delete-impact)$/.exec(path);
  if (aiMappingActionMatch) {
    const mappingId = decodeURIComponent(aiMappingActionMatch[1] ?? "");
    const action = aiMappingActionMatch[2];
    if (action === "delete-impact") {
      return jsonResponse({ mapping_id: mappingId, active_runs_count: 0, requires_drain: false });
    }
    return jsonResponse({ ok: true, mapping_id: mappingId, latency_ms: 21, status: "OPERATIONAL" });
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
      target_model_id: "01930000-0000-7000-8000-000000000099",
      target_model_name: "text-embedding-3-small",
      message: "Réindexation globale lancée",
    });
  }

  if (path === "/api/v1/mcp/test-bench" && method === "POST") {
    return jsonResponse({ steps: [], discovered_capabilities: [], can_activate: true });
  }

  if (path === "/api/v1/settings/connectors/test-and-discover" && method === "POST") {
    const tools = Array.isArray(body.raw_tool_names)
      ? body.raw_tool_names.map((t) => ({
          tool_name: String(t),
          description: `Capacité découverte : ${String(t)}`,
          qualification: String(t).toLowerCase().includes("update") || String(t).toLowerCase().includes("create")
            ? "WRITE_STAGED_REQUIRED"
            : "READ_ONLY",
          badge_fr: String(t).toLowerCase().includes("update") || String(t).toLowerCase().includes("create")
            ? "Validation humaine requise"
            : "Lecture seule",
        }))
      : [];
    return jsonResponse({
      protocol: String(body.protocol ?? "MCP_STREAMABLE_HTTP_SSE"),
      endpoint_url: String(body.endpoint_url ?? "https://mcp.entreprise.interne/api"),
      identity_mode: String(body.identity_mode ?? "SECRET_REF"),
      steps: [
        { step_number: 1, step_code: "1_NETWORK_TLS_ANTI_SSRF", status: "PASS", detail_fr: "Réseau validé" },
        { step_number: 2, step_code: "2_AUTHENTICATION", status: "PASS", detail_fr: "Authentification validée" },
        { step_number: 3, step_code: "3_CONTRACT_DISCOVERY", status: "PASS", detail_fr: "Capacités découvertes" },
        { step_number: 4, step_code: "4_HOT_DRY_RUN", status: "PASS", detail_fr: "Essai à blanc validé" },
      ],
      discovered_capabilities: tools,
      can_activate: true,
      dry_run_audit_actor_type: "ADMIN_CONNECTION_TEST",
      dry_run_run_id: null,
      finops_meta_usage: { prompt_tokens: 42, completion_tokens: 18, cost_eur: 0.0002 },
    });
  }

  if (path === "/api/v1/mcp/exposure" && method === "GET") {
    const wsSlug = parsedUrl.searchParams.get("workspace_slug") ?? "global";
    return jsonResponse({
      workspace_slug: wsSlug,
      agents: [],
      exposed_tools: ["assistant.ask", "agent.invoke", "agent.list_exposed"],
      any_exposed: false,
    });
  }

  if (path === "/api/v1/mcp/exposure" && method === "PUT") {
    const wsSlug = String(body.workspace_slug ?? "global");
    const agentSlug = String(body.agent_slug ?? "governed-mcp-connector");
    const exposed = Boolean(body.mcp_exposed ?? true);
    return jsonResponse({
      agent_slug: agentSlug,
      workspace_slug: wsSlug,
      display_name: String(body.display_name ?? agentSlug),
      mcp_exposed: exposed,
      regime: String(body.regime ?? "GOVERNED_STAGED_COPILOT"),
      human_authored_required: Boolean(body.human_authored_required ?? false),
      exposed_tools: exposed
        ? ["assistant.ask", "agent.invoke", "agent.list_exposed", `agent.${agentSlug}`]
        : ["assistant.ask", "agent.invoke", "agent.list_exposed"],
    });
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

  if (path === "/api/v1/search" && method === "GET") {
    return jsonResponse({ hits: [] });
  }

  if (path === "/api/v1/settings/packs/installed" && method === "GET") {
    return jsonResponse({ packs: [] });
  }

  return null;
}
