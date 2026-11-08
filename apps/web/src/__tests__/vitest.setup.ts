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

interface MockBackendState {
  firstAdmin: {
    email: string;
    displayName: string;
  } | null;
  platformSetupState: Record<string, unknown> | null;
  agents: Array<Record<string, unknown>>;
  skills: Array<Record<string, unknown>>;
  recordedCalls: RecordedVitestApiCall[];
}

const backendState: MockBackendState = {
  firstAdmin: null,
  platformSetupState: null,
  agents: [],
  skills: [],
  recordedCalls: [],
};

export function resetVitestApiBackend(): void {
  backendState.firstAdmin = null;
  backendState.platformSetupState = null;
  backendState.agents = [];
  backendState.skills = [];
  backendState.recordedCalls = [];
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
    });
  }

  if (path === "/api/v1/bootstrap/platform-setup-state" && method === "PUT") {
    backendState.platformSetupState = body;
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
    return jsonResponse({
      folder_id: `folder-${slug}-${backendState.recordedCalls.length}`,
      workspace_id: String(body.workspace_id ?? "ws-1"),
      title,
      pinned_notes_markdown: "",
      consolidated_summary: `Dossier thématique « ${title} »`,
      visibility_mode: "PRIVATE",
      has_restricted_sources: false,
      assembled_layer5_prompt_block: `Dossier actif : ${title}`,
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

  return jsonResponse({});
}

globalThis.fetch = vitestFetchTransport as typeof fetch;
