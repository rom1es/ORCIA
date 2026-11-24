import type { ControlCenterDatasourceItem } from "@orcia/ui";
import type {
  CreateWorkspaceDatasourceRequest,
  WorkspaceDatasourceItemResponse,
} from "@orcia/api-client";
import type { RegisterDatasourceInput } from "../../../components/platformSetupWorkspaces";

export function toRegisterDatasourceInput(
  workspaceName: string,
  payload: CreateWorkspaceDatasourceRequest,
): RegisterDatasourceInput {
  return {
    workspaceName,
    alias: payload.alias,
    scheme: (payload.scheme as "git" | "confluence" | "jira" | "db") || "confluence",
    uri: payload.uri,
    executionIdentity:
      payload.sync_identity_mode === "SERVICE_ACCOUNT" ? "service_account" : "passthrough",
    freshnessTtlDays: 1,
  };
}

export function mapFallbackWorkspaceDatasources(
  fallbackDatasources: readonly ControlCenterDatasourceItem[],
  workspaceName: string,
  workspaceId: string,
): WorkspaceDatasourceItemResponse[] {
  if (fallbackDatasources.length === 0) return [];
  return fallbackDatasources
    .filter((d) => d.workspaceName === workspaceName)
    .map((d) => ({
      id: d.id,
      workspace_id: workspaceId,
      alias: d.alias,
      scheme: d.scheme,
      uri: d.uri,
      connector_id: null,
      sync_identity_mode:
        d.executionIdentity === "service_account" ? "SERVICE_ACCOUNT" : "TEAM_REFERENT_USER",
      service_account_id: null,
      referent_user_id: null,
      sync_status: "ACTIVE",
      sync_status_reason: null,
      source_nature: "DOCUMENT_KB",
      sync_mode: "POLLING_24H",
      target_scope: null,
      target_ref: null,
      last_sync_at_iso: null,
      last_probe_at_iso: null,
      fingerprint_hash: null,
      freshness_status: "PENDING_INITIAL_SYNC",
      codegraph_enabled: false,
      codegraph_auth_mode: "SERVICE_ACCOUNT",
      codegraph_owner_user_id: null,
      codegraph_status: "DISABLED",
      codegraph_last_indexed_at_iso: null,
      codegraph_head_sha: null,
      created_at_iso: "",
    }));
}
