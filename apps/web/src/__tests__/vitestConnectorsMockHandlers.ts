/**
 * Story 17.4 — Mock Handlers for Enterprise Connectors, User Passthrough Tokens & Workspace Datasources.
 */

export interface MockEnterpriseConnectorItem {
  id: string;
  connector_kind: "GITLAB" | "JIRA" | "CONFLUENCE" | "OIDC_SSO" | "S3_OBJECT_STORE";
  name: string;
  base_url: string;
  auth_mode: "OAUTH2_PASSTHROUGH" | "PERSONAL_ACCESS_TOKEN" | "OIDC_FEDERATION" | "SERVICE_SECRET";
  enabled: boolean;
  admin_secret_status: {
    configured: boolean;
    fingerprint: string | null;
    updated_at_iso: string | null;
  };
  created_at_iso: string;
  updated_at_iso: string;
}

export interface MockUserPassthroughTokenItem {
  connector_id: string;
  external_author_login: string | null;
  secret_fingerprint: string;
  status: "ACTIVE" | "REVOKED";
  updated_at_iso: string;
}

export interface MockWorkspaceDatasourceItem {
  id: string;
  workspace_id: string;
  alias: string;
  scheme: string;
  uri: string;
  connector_id: string | null;
  sync_identity_mode: "SERVICE_ACCOUNT" | "TEAM_REFERENT_USER";
  service_account_id: string | null;
  referent_user_id: string | null;
  source_nature?: "DOCUMENT_KB" | "WORK_TRACKER" | "SOURCE_CODE" | "RELATIONAL_SCHEMA";
  sync_mode?: "POLLING_24H" | "WEBHOOK_PUSH";
  target_scope?: string | null;
  target_ref?: string | null;
  codegraph_enabled?: boolean;
  codegraph_auth_mode?: "SERVICE_ACCOUNT" | "WORKSPACE_LEAD_TOKEN";
  codegraph_owner_user_id?: string | null;
  codegraph_status?: "DISABLED" | "INDEXING" | "READY" | "PAUSED_REFERENT_RENEWAL_REQUIRED" | "ERROR";
  freshness_status?: "SYNCED" | "STALE" | "SYNC_ERROR" | "PENDING_INITIAL_SYNC";
  last_sync_at_iso?: string | null;
  created_at_iso: string;
}

let connectors: MockEnterpriseConnectorItem[] = [];
let connectorSeq = 0;
let userTokens: MockUserPassthroughTokenItem[] = [];
let datasources: MockWorkspaceDatasourceItem[] = [];
let datasourceSeq = 0;

export function resetVitestConnectorsMockState(): void {
  connectors = [];
  connectorSeq = 0;
  userTokens = [];
  datasources = [];
  datasourceSeq = 0;
}

export function seedVitestConnectorsInitialData(params?: {
  connectors?: MockEnterpriseConnectorItem[];
  datasources?: MockWorkspaceDatasourceItem[];
}): void {
  if (params?.connectors) connectors = [...params.connectors];
  if (params?.datasources) datasources = [...params.datasources];
}

interface HandleConnectorsRouteParams {
  method: string;
  path: string;
  parsedUrl: URL;
  body: Record<string, unknown>;
  reqHeaders: Headers;
  firstAdmin: { email: string; displayName: string } | null;
  orgUnits: Array<{ id: string; name: string; slug: string; kind: "BU" | "TEAM"; billing_enabled: boolean }>;
  jsonResponse: (data: unknown, status?: number) => Response;
  problemResponse: (status: number, title: string, detail: string, errorCode: string) => Response;
}

export function handleVitestConnectorsRoute(params: HandleConnectorsRouteParams): Response | null {
  const { method, path, body, reqHeaders, firstAdmin, orgUnits, jsonResponse, problemResponse } = params;

  const accessMode = reqHeaders.get("x-orcia-access-mode")?.toUpperCase();
  const isObserver = accessMode === "READ_ONLY_OBSERVER";

  // 1. /api/v1/settings/connectors
  if (path === "/api/v1/settings/connectors") {
    if (method === "GET") {
      return jsonResponse({
        items: connectors,
        trace_id: "0195f000-0000-7000-8000-000000000999",
      });
    }

    if (method === "POST") {
      if (isObserver) {
        return problemResponse(403, "Mode observateur lecture seule", "Mutation interdite", "ERR_OBSERVER_MODE_READ_ONLY");
      }
      const rawBaseUrl = String(body.base_url ?? "").trim();
      if (rawBaseUrl.includes("169.254.169.254")) {
        return problemResponse(422, "URL non sécurisée", "Metadata IP interdite", "ERR_UNSAFE_CONNECTOR_ENDPOINT_URL");
      }
      connectorSeq += 1;
      const id = `conn-${connectorSeq}`;
      const now = new Date().toISOString();
      const hasSecret = Boolean(body.admin_secret_value);
      const newConn: MockEnterpriseConnectorItem = {
        id,
        connector_kind: (body.connector_kind as any) ?? "JIRA",
        name: String(body.name ?? `Connecteur ${connectorSeq}`),
        base_url: rawBaseUrl,
        auth_mode: (body.auth_mode as any) ?? "PERSONAL_ACCESS_TOKEN",
        enabled: body.enabled !== false,
        admin_secret_status: {
          configured: hasSecret,
          fingerprint: hasSecret ? `sha256:conn${connectorSeq}` : null,
          updated_at_iso: hasSecret ? now : null,
        },
        created_at_iso: now,
        updated_at_iso: now,
      };
      connectors.push(newConn);
      return jsonResponse(newConn, 201);
    }
  }

  // 1b. /api/v1/settings/connectors/{id}
  if (path.startsWith("/api/v1/settings/connectors/")) {
    const connId = path.slice("/api/v1/settings/connectors/".length);
    const existing = connectors.find((c) => c.id === connId);
    if (!existing) {
      return problemResponse(404, "Connecteur introuvable", "Introuvable", "ERR_RESOURCE_NOT_FOUND");
    }

    if (method === "DELETE") {
      if (isObserver) {
        return problemResponse(403, "Mode observateur lecture seule", "Mutation interdite", "ERR_OBSERVER_MODE_READ_ONLY");
      }
      connectors = connectors.filter((c) => c.id !== connId);
      userTokens = userTokens.filter((t) => t.connector_id !== connId);
      datasources = datasources.filter((d) => d.connector_id !== connId);
      return jsonResponse({ deleted: true, connector_id: connId, trace_id: "0195f000-0000-7000-8000-000000000999" });
    }

    if (method === "PATCH") {
      if (isObserver) {
        return problemResponse(403, "Mode observateur lecture seule", "Mutation interdite", "ERR_OBSERVER_MODE_READ_ONLY");
      }
      if (body.name !== undefined) existing.name = String(body.name);
      if (body.base_url !== undefined) existing.base_url = String(body.base_url);
      if (body.auth_mode !== undefined) existing.auth_mode = body.auth_mode as any;
      if (body.enabled !== undefined) existing.enabled = Boolean(body.enabled);
      if (body.admin_secret_value) {
        existing.admin_secret_status = {
          configured: true,
          fingerprint: `sha256:${connId}-upd`,
          updated_at_iso: new Date().toISOString(),
        };
      } else if (body.clear_admin_secret) {
        existing.admin_secret_status = {
          configured: false,
          fingerprint: null,
          updated_at_iso: null,
        };
      }
      existing.updated_at_iso = new Date().toISOString();
      return jsonResponse(existing);
    }
  }

  // 2. /api/v1/users/me/account-profile
  if (path === "/api/v1/users/me/account-profile" && method === "GET") {
    const userEmail = firstAdmin?.email ?? "romain.admin@orcia.fr";
    const userName = firstAdmin?.displayName ?? "Romain Admin";
    return jsonResponse({
      principal_id: userEmail,
      display_name: userName,
      email: userEmail,
      roles: ["PLATFORM_ADMIN", "SECOPS"],
      teams: orgUnits
        .filter((ou) => ou.kind === "TEAM")
        .map((ou) => ({
          id: ou.id,
          slug: ou.slug,
          name: ou.name,
          unit_type: "TEAM",
          billing_enabled: ou.billing_enabled,
          is_lead: true,
        })),
      billing_org_units: orgUnits
        .filter((ou) => ou.billing_enabled)
        .map((ou) => ({
          id: ou.id,
          slug: ou.slug,
          name: ou.name,
          unit_type: ou.kind,
          billing_enabled: true,
          is_lead: false,
        })),
      trace_id: "0195f000-0000-7000-8000-000000000999",
    });
  }

  // 3. /api/v1/users/me/passthrough-tokens
  if (path === "/api/v1/users/me/passthrough-tokens" && method === "GET") {
    const items = connectors.map((conn) => {
      const tok = userTokens.find((t) => t.connector_id === conn.id && t.status === "ACTIVE");
      return {
        connector_id: conn.id,
        connector_name: conn.name,
        connector_kind: conn.connector_kind,
        base_url: conn.base_url,
        auth_mode: conn.auth_mode,
        connected: Boolean(tok),
        external_author_login: tok?.external_author_login ?? null,
        secret_status: {
          configured: Boolean(tok),
          fingerprint: tok?.secret_fingerprint ?? null,
          updated_at_iso: tok?.updated_at_iso ?? null,
        },
      };
    });
    return jsonResponse({ items, trace_id: "0195f000-0000-7000-8000-000000000999" });
  }

  // 3b. /api/v1/users/me/passthrough-tokens/{connector_id}
  if (path.startsWith("/api/v1/users/me/passthrough-tokens/")) {
    const connId = path.slice("/api/v1/users/me/passthrough-tokens/".length);
    const conn = connectors.find((c) => c.id === connId);
    if (!conn) {
      return problemResponse(404, "Connecteur introuvable", "Introuvable", "ERR_RESOURCE_NOT_FOUND");
    }

    if (method === "PUT") {
      if (isObserver) {
        return problemResponse(403, "Mode observateur lecture seule", "Mutation interdite", "ERR_OBSERVER_MODE_READ_ONLY");
      }
      const login = (body.external_author_login as string) || null;
      const now = new Date().toISOString();
      const existingIdx = userTokens.findIndex((t) => t.connector_id === connId);
      const tokenEntry: MockUserPassthroughTokenItem = {
        connector_id: connId,
        external_author_login: login,
        secret_fingerprint: `sha256:usr-${connId}`, // pragma: allowlist secret
        status: "ACTIVE",
        updated_at_iso: now,
      };
      if (existingIdx >= 0) {
        userTokens[existingIdx] = tokenEntry;
      } else {
        userTokens.push(tokenEntry);
      }
      return jsonResponse({
        connector_id: conn.id,
        connector_name: conn.name,
        connector_kind: conn.connector_kind,
        base_url: conn.base_url,
        auth_mode: conn.auth_mode,
        connected: true,
        external_author_login: login,
        secret_status: {
          configured: true,
          fingerprint: tokenEntry.secret_fingerprint,
          updated_at_iso: now,
        },
      });
    }

    if (method === "DELETE") {
      if (isObserver) {
        return problemResponse(403, "Mode observateur lecture seule", "Mutation interdite", "ERR_OBSERVER_MODE_READ_ONLY");
      }
      userTokens = userTokens.filter((t) => t.connector_id !== connId);
      return jsonResponse({ revoked: true, connector_id: connId, trace_id: "0195f000-0000-7000-8000-000000000999" });
    }
  }

  // 4a. /api/v1/workspaces/{workspace_id}/datasources/{datasource_id}/sync
  const wsDsSyncMatch = /^\/api\/v1\/workspaces\/([^/]+)\/datasources\/([^/]+)\/sync$/.exec(path);
  if (wsDsSyncMatch && method === "POST") {
    if (isObserver) {
      return problemResponse(403, "Mode observateur lecture seule", "Mutation interdite", "ERR_OBSERVER_MODE_READ_ONLY");
    }
    const syncWsId = wsDsSyncMatch[1];
    const syncDsId = wsDsSyncMatch[2];
    const existing = datasources.find((d) => d.id === syncDsId && d.workspace_id === syncWsId);
    if (!existing) {
      return problemResponse(404, "Datasource introuvable", "Introuvable", "ERR_RESOURCE_NOT_FOUND");
    }
    existing.last_sync_at_iso = new Date().toISOString();
    existing.freshness_status = "SYNCED";
    return jsonResponse({
      datasource: existing,
      trace_id: "0195f000-0000-7000-8000-000000000999",
    });
  }

  // 4b. /api/v1/workspaces/{workspace_id}/datasources
  const wsDsMatch = /^\/api\/v1\/workspaces\/([^/]+)\/datasources(?:\/([^/]+))?$/.exec(path);
  if (wsDsMatch) {
    const wsId = decodeURIComponent(wsDsMatch[1] ?? "");
    const dsId = wsDsMatch[2] ? decodeURIComponent(wsDsMatch[2]) : null;

    if (!dsId && method === "GET") {
      const items = datasources
        .filter((d) => d.workspace_id === wsId)
        .map((d) => {
          let sync_status: "ACTIVE" | "PAUSED_REFERENT_RENEWAL_REQUIRED" = "ACTIVE";
          let sync_status_reason: string | null = null;
          if (d.sync_identity_mode === "TEAM_REFERENT_USER") {
            const hasTok = userTokens.some((t) => t.connector_id === d.connector_id && t.status === "ACTIVE");
            if (!hasTok) {
              sync_status = "PAUSED_REFERENT_RENEWAL_REQUIRED";
              sync_status_reason = "REFERENT_TOKEN_MISSING";
            }
          }
          return {
            ...d,
            sync_status,
            sync_status_reason,
          };
        });
      return jsonResponse({ items, trace_id: "0195f000-0000-7000-8000-000000000999" });
    }

    if (!dsId && method === "POST") {
      if (isObserver) {
        return problemResponse(403, "Mode observateur lecture seule", "Mutation interdite", "ERR_OBSERVER_MODE_READ_ONLY");
      }
      datasourceSeq += 1;
      const cgEnabled = Boolean(body.codegraph_enabled);
      const newDs: MockWorkspaceDatasourceItem = {
        id: `ds-${datasourceSeq}`,
        workspace_id: wsId,
        alias: String(body.alias ?? `ds-alias-${datasourceSeq}`),
        scheme: String(body.scheme ?? "jira"),
        uri: String(body.uri ?? "https://jira.corp.internal/corpus"),
        connector_id: (body.connector_id as string) || null,
        sync_identity_mode: (body.sync_identity_mode as any) ?? "SERVICE_ACCOUNT",
        service_account_id: (body.service_account_id as string) || null,
        referent_user_id: (body.referent_user_id as string) || null,
        source_nature: (body.source_nature as any) ?? "DOCUMENT_KB",
        sync_mode: (body.sync_mode as any) ?? "POLLING_24H",
        target_scope: (body.target_scope as string) || null,
        target_ref: (body.target_ref as string) || null,
        codegraph_enabled: cgEnabled,
        codegraph_auth_mode: (body.codegraph_auth_mode as any) ?? "SERVICE_ACCOUNT",
        codegraph_owner_user_id: (body.codegraph_owner_user_id as string) || null,
        codegraph_status: cgEnabled ? "READY" : "DISABLED",
        freshness_status: "PENDING_INITIAL_SYNC",
        last_sync_at_iso: null,
        created_at_iso: new Date().toISOString(),
      };
      datasources.push(newDs);

      let sync_status: "ACTIVE" | "PAUSED_REFERENT_RENEWAL_REQUIRED" = "ACTIVE";
      let sync_status_reason: string | null = null;
      if (newDs.sync_identity_mode === "TEAM_REFERENT_USER") {
        const hasTok = userTokens.some((t) => t.connector_id === newDs.connector_id && t.status === "ACTIVE");
        if (!hasTok) {
          sync_status = "PAUSED_REFERENT_RENEWAL_REQUIRED";
          sync_status_reason = "REFERENT_TOKEN_MISSING";
        }
      }

      return jsonResponse(
        {
          ...newDs,
          sync_status,
          sync_status_reason,
        },
        201,
      );
    }

    if (dsId && method === "DELETE") {
      if (isObserver) {
        return problemResponse(403, "Mode observateur lecture seule", "Mutation interdite", "ERR_OBSERVER_MODE_READ_ONLY");
      }
      datasources = datasources.filter((d) => d.id !== dsId || d.workspace_id !== wsId);
      return jsonResponse({ deleted: true, datasource_id: dsId, trace_id: "0195f000-0000-7000-8000-000000000999" });
    }

    if (dsId && method === "PATCH") {
      if (isObserver) {
        return problemResponse(403, "Mode observateur lecture seule", "Mutation interdite", "ERR_OBSERVER_MODE_READ_ONLY");
      }
      const existing = datasources.find((d) => d.id === dsId && d.workspace_id === wsId);
      if (!existing) {
        return problemResponse(404, "Datasource introuvable", "Introuvable", "ERR_RESOURCE_NOT_FOUND");
      }
      if (body.alias !== undefined) existing.alias = String(body.alias);
      if (body.uri !== undefined) existing.uri = String(body.uri);
      if (body.connector_id !== undefined) existing.connector_id = (body.connector_id as string) || null;
      if (body.sync_identity_mode !== undefined) existing.sync_identity_mode = body.sync_identity_mode as any;
      if (body.service_account_id !== undefined) existing.service_account_id = (body.service_account_id as string) || null;
      if (body.referent_user_id !== undefined) existing.referent_user_id = (body.referent_user_id as string) || null;
      if (body.source_nature !== undefined) existing.source_nature = body.source_nature as any;
      if (body.sync_mode !== undefined) existing.sync_mode = body.sync_mode as any;
      if (body.target_scope !== undefined) existing.target_scope = (body.target_scope as string) || null;
      if (body.target_ref !== undefined) existing.target_ref = (body.target_ref as string) || null;
      if (body.codegraph_enabled !== undefined) {
        existing.codegraph_enabled = Boolean(body.codegraph_enabled);
        existing.codegraph_status = existing.codegraph_enabled ? "READY" : "DISABLED";
      }
      if (body.codegraph_auth_mode !== undefined) existing.codegraph_auth_mode = body.codegraph_auth_mode as any;
      if (body.codegraph_owner_user_id !== undefined) existing.codegraph_owner_user_id = (body.codegraph_owner_user_id as string) || null;

      let sync_status: "ACTIVE" | "PAUSED_REFERENT_RENEWAL_REQUIRED" = "ACTIVE";
      let sync_status_reason: string | null = null;
      if (existing.sync_identity_mode === "TEAM_REFERENT_USER") {
        const hasTok = userTokens.some((t) => t.connector_id === existing.connector_id && t.status === "ACTIVE");
        if (!hasTok) {
          sync_status = "PAUSED_REFERENT_RENEWAL_REQUIRED";
          sync_status_reason = "REFERENT_TOKEN_MISSING";
        }
      }

      return jsonResponse({
        ...existing,
        sync_status,
        sync_status_reason,
      });
    }
  }

  return null;
}
