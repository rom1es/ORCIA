export interface MockUserPreferencesState {
  user_id: string;
  theme: "light" | "dark" | "system";
  locale: "fr" | "en";
  default_hat: string;
  default_assistant_hat: string;
  assistant_tone: "balanced" | "concise" | "detailed";
  personal_instructions: string;
  auto_open_contextual_help: boolean;
  notifications_enabled: boolean;
  assistant_behavior_redirect_uri: string;
}

export interface MockMcpTokenRecord {
  token_id: string;
  user_id: string;
  label: string;
  token_prefix: string;
  token_sha256: string;
  expires_in_days: 30 | 90;
  rpm_limit: number;
  allowed_workspace_slugs: string[];
  exposed_capabilities: string[];
  target_kind: "SPACE" | "AGENT";
  target_slug: string;
  mcp_endpoint_uri: string;
  ide_json_snippet: string;
  revoked: boolean;
}

let prefsState: MockUserPreferencesState = {
  user_id: "u-vitest-user",
  theme: "light",
  locale: "fr",
  default_hat: "ANALYST_PM_PO",
  default_assistant_hat: "ANALYST_PM_PO",
  assistant_tone: "balanced",
  personal_instructions: "",
  auto_open_contextual_help: true,
  notifications_enabled: true,
  assistant_behavior_redirect_uri: "/assistant?modal=settings",
};

let mcpTokensState: MockMcpTokenRecord[] = [];
let mcpTokenSeq = 0;

export interface MockUserProfileSummaryState {
  user_id: string;
  display_name: string;
  handle: string;
  email: string;
  primary_role: string;
  roles: string[];
  led_business_units: string[];
  ontology_business_units: string[];
  led_teams: string[];
  member_teams: string[];
  total_tokens: number;
  peak_daily_tokens: number;
  longest_streak_days: number;
  current_streak_days: number;
  popular_items: Array<{
    item_type: "AGENT" | "PROCESS" | "SKILL" | "TOOL";
    item_key: string;
    title: string;
    usage_count: number;
    target_route: string;
  }>;
  trace_id: string;
}

const DEFAULT_MOCK_PROFILE_SUMMARY: MockUserProfileSummaryState = {
  user_id: "u-vitest-user",
  display_name: "Utilisateur ORCIA",
  handle: "utilisateur",
  email: "utilisateur@orcia.ia",
  primary_role: "PLATFORM_ADMIN",
  roles: ["PLATFORM_ADMIN"],
  led_business_units: [],
  ontology_business_units: [],
  led_teams: [],
  member_teams: [],
  total_tokens: 0,
  peak_daily_tokens: 0,
  longest_streak_days: 0,
  current_streak_days: 0,
  popular_items: [],
  trace_id: "0195f000-0000-7000-8000-000000002040",
};

let profileSummaryState: MockUserProfileSummaryState = { ...DEFAULT_MOCK_PROFILE_SUMMARY };

export function seedVitestUserProfileSummary(
  patch: Partial<MockUserProfileSummaryState>,
): void {
  profileSummaryState = { ...DEFAULT_MOCK_PROFILE_SUMMARY, ...patch };
}

export function resetVitestUserSettingsMockState(): void {
  profileSummaryState = { ...DEFAULT_MOCK_PROFILE_SUMMARY };
  prefsState = {
    user_id: "u-vitest-user",
    theme: "light",
    locale: "fr",
    default_hat: "ANALYST_PM_PO",
    default_assistant_hat: "ANALYST_PM_PO",
    assistant_tone: "balanced",
    personal_instructions: "",
    auto_open_contextual_help: true,
    notifications_enabled: true,
    assistant_behavior_redirect_uri: "/assistant?modal=settings",
  };
  mcpTokensState = [];
  mcpTokenSeq = 0;
}

export function handleVitestUserSettingsRoute(ctx: {
  path: string;
  method: string;
  body: Record<string, unknown>;
  isObserver: boolean;
  jsonResponse: (payload: unknown, status?: number) => Response;
  problemResponse: (
    status: number,
    detail: string,
    title: string,
    errorCode: string,
  ) => Response;
}): Response | null {
  const { path, method, body, isObserver, jsonResponse, problemResponse } = ctx;

  if (path === "/api/v1/users/me/preferences") {
    if (method === "GET") {
      return jsonResponse({
        ...prefsState,
        trace_id: "0195f000-0000-7000-8000-000000000999",
      });
    }
    if (method === "PATCH") {
      const nextHat =
        typeof body.default_assistant_hat === "string"
          ? body.default_assistant_hat
          : typeof body.default_hat === "string"
            ? body.default_hat
            : prefsState.default_assistant_hat;
      prefsState = {
        ...prefsState,
        theme: (body.theme as MockUserPreferencesState["theme"]) ?? prefsState.theme,
        locale: (body.locale as MockUserPreferencesState["locale"]) ?? prefsState.locale,
        default_hat: nextHat,
        default_assistant_hat: nextHat,
        assistant_tone:
          (body.assistant_tone as MockUserPreferencesState["assistant_tone"]) ??
          prefsState.assistant_tone,
        personal_instructions:
          typeof body.personal_instructions === "string"
            ? body.personal_instructions
            : prefsState.personal_instructions,
        auto_open_contextual_help:
          typeof body.auto_open_contextual_help === "boolean"
            ? body.auto_open_contextual_help
            : prefsState.auto_open_contextual_help,
        notifications_enabled:
          typeof body.notifications_enabled === "boolean"
            ? body.notifications_enabled
            : prefsState.notifications_enabled,
      };
      return jsonResponse({
        ...prefsState,
        trace_id: "0195f000-0000-7000-8000-000000000999",
      });
    }
  }

  if (path === "/api/v1/users/me/mcp-tokens") {
    if (method === "GET") {
      return jsonResponse({
        tokens: mcpTokensState,
        trace_id: "0195f000-0000-7000-8000-000000000999",
      });
    }
    if (method === "POST") {
      if (isObserver) {
        return problemResponse(
          403,
          "Mode observateur lecture seule",
          "Mutation interdite",
          "ERR_OBSERVER_MODE_READ_ONLY",
        );
      }
      mcpTokenSeq += 1;
      const targetKind = body.target_kind === "AGENT" ? "AGENT" : "SPACE";
      const targetSlug = String(body.target_slug || "default").trim();
      const endpointUri =
        targetKind === "AGENT"
          ? `/api/v1/mcp/agents/${targetSlug}`
          : `/api/v1/mcp/spaces/${targetSlug}`;
      const plaintext = `pat_mcp_vitest_${mcpTokenSeq}_${Math.random().toString(36).slice(2, 12)}`;
      const record: MockMcpTokenRecord = {
        token_id: `0195f000-0000-7000-8000-0000000020${String(mcpTokenSeq).padStart(2, "0")}`,
        user_id: "u-vitest-user",
        label: String(body.label || `IDE MCP (${targetKind} · ${targetSlug})`),
        token_prefix: `${plaintext.slice(0, 14)}...`,
        token_sha256: `sha256_mock_${mcpTokenSeq}`,
        expires_in_days: body.expires_in_days === 90 ? 90 : 30,
        rpm_limit: Number(body.rpm_limit || 60),
        allowed_workspace_slugs: Array.isArray(body.allowed_workspace_slugs)
          ? (body.allowed_workspace_slugs as string[])
          : [targetSlug],
        exposed_capabilities: Array.isArray(body.exposed_capabilities)
          ? (body.exposed_capabilities as string[])
          : ["ASSISTANT"],
        target_kind: targetKind,
        target_slug: targetSlug,
        mcp_endpoint_uri: endpointUri,
        ide_json_snippet: JSON.stringify(
          {
            mcpServers: {
              [`orcia-${targetKind.toLowerCase()}-${targetSlug}`]: {
                url: `https://orcia.internal${endpointUri}`,
                headers: { Authorization: "Bearer ${ORCIA_MCP_PAT}" },
              },
            },
          },
          null,
          2,
        ),
        revoked: false,
      };
      mcpTokensState = [record, ...mcpTokensState];
      return jsonResponse(
        {
          plaintext_token: plaintext,
          record,
          trace_id: "0195f000-0000-7000-8000-000000000999",
        },
        201,
      );
    }
  }

  if (path.startsWith("/api/v1/users/me/mcp-tokens/") && method === "DELETE") {
    if (isObserver) {
      return problemResponse(
        403,
        "Mode observateur lecture seule",
        "Mutation interdite",
        "ERR_OBSERVER_MODE_READ_ONLY",
      );
    }
    const tokenId = decodeURIComponent(path.slice("/api/v1/users/me/mcp-tokens/".length));
    const idx = mcpTokensState.findIndex((t) => t.token_id === tokenId);
    if (idx < 0) {
      return problemResponse(404, "Jeton introuvable", "Introuvable", "ERR_RESOURCE_NOT_FOUND");
    }
    const updated = { ...mcpTokensState[idx]!, revoked: true };
    mcpTokensState[idx] = updated;
    return jsonResponse(updated);
  }

  if (path === "/api/v1/users/me/profile-summary" && method === "GET") {
    return jsonResponse(profileSummaryState);
  }

  return null;
}
