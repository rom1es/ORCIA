import { createOrciaApiClient, type WorkspacePatchResponse } from "@orcia/api-client";
import type {
  ControlCenterWorkspaceGovItem,
  ProductLifecyclePhaseType,
} from "@orcia/ui";
import {
  DICTIONARIES,
  formatI18nTemplate,
  type SupportedWebLocale,
} from "../i18n";
import { ClientCodedError } from "../lib/clientErrorCodes";
import { resolveWebApiBaseUrl } from "../stores/authSessionStore";
import {
  applyRegisterDatasource,
  BASE_GLOBAL_SCOPE,
  buildScopeNodes,
  resolveGlobalScopeLabel,
  type RegisterDatasourceInput,
} from "./platformSetupScopeAndDatasources";
import type {
  ConfiguredAuditEvent,
  ConfiguredOrgUnit,
  ConfiguredPlatformAdmin,
  ConfiguredWorkflowItem,
} from "./platformSetupStorageHelpers";

export {
  applyRegisterDatasource,
  BASE_GLOBAL_SCOPE,
  buildScopeNodes,
  resolveGlobalScopeLabel,
  type RegisterDatasourceInput,
};

export interface CreateWorkspaceInput {
  readonly name: string;
  readonly slug: string;
  readonly visibilityMode: "STANDARD" | "CONFIDENTIAL_RESTRICTED" | "PRIVATE_USER";
  readonly lifecyclePhase: ProductLifecyclePhaseType;
  readonly ownerOrgUnitId?: string;
}

export async function createWorkspaceViaServer(params: {
  readonly locale?: SupportedWebLocale;
  readonly input: CreateWorkspaceInput;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workflows: readonly ConfiguredWorkflowItem[];
  readonly platformAdmin: ConfiguredPlatformAdmin | null;
}): Promise<{
  readonly workspace: ControlCenterWorkspaceGovItem;
  readonly auditEvent: {
    readonly eventType: string;
    readonly summary: string;
    readonly scopeId: string;
    readonly scopePath: string;
    readonly scopeLabel: string;
  };
}> {
  const { locale = "fr", input, orgUnits, workflows, platformAdmin } = params;
  const dict = DICTIONARIES[locale];
  const copy = dict.shellChrome.platformSetupGovernance;
  const teamUnits = orgUnits.filter((u) => u.level === "TEAM");
  const resolvedOwnerUnit =
    orgUnits.find((u) => u.id === input.ownerOrgUnitId) ??
    teamUnits[0] ??
    orgUnits[orgUnits.length - 1];
  const ownerOrgUnitId = resolvedOwnerUnit?.id;
  const fallbackOwnerName =
    resolvedOwnerUnit?.name ??
    dict.fourZoneShell.doubleSelector?.globalPlatformLabel ??
    copy.globalScopeLabel;

  const client = createOrciaApiClient({ baseUrl: resolveWebApiBaseUrl(), locale });
  const created = await client.createWorkspace({
    name: input.name,
    slug: input.slug,
    visibility_mode: input.visibilityMode,
    lifecycle_phase: input.lifecyclePhase,
    ...(ownerOrgUnitId ? { owner_org_unit_id: ownerOrgUnitId } : {}),
  });

  if (!created || !created.id) {
    throw new ClientCodedError("ERR_CLIENT_INVALID_PAYLOAD", {
      detail: "workspace.id",
    });
  }

  const effectiveOwnerId = ownerOrgUnitId ?? created.owner_org_unit_id;
  const effectiveOwnerName =
    resolvedOwnerUnit?.name ?? created.owner_org_unit_name ?? fallbackOwnerName;

  const newWs: ControlCenterWorkspaceGovItem = {
    workspaceId: created.id,
    slug: created.slug || input.slug,
    name: created.name || input.name,
    visibilityMode: input.visibilityMode,
    ...(effectiveOwnerId ? { ownerOrgUnitId: effectiveOwnerId } : {}),
    ownerOrgUnitName: effectiveOwnerName,
    ...(input.visibilityMode === "PRIVATE_USER"
      ? { ownerUserId: platformAdmin?.email ?? "session-user" }
      : {}),
    lifecyclePhase: input.lifecyclePhase,
    suggestedWorkflows: workflows.map((w) => w.workflowKey),
    accessMode: created.access_mode ?? "CONTRIBUTOR_ACTION_REQUIRED",
    finopsCostUsd: created.finops_cost_usd ?? 0,
  };

  const modeLabel =
    input.visibilityMode === "PRIVATE_USER"
      ? copy.visibilityPrivatePersonalLabel
      : input.visibilityMode === "CONFIDENTIAL_RESTRICTED"
        ? copy.visibilityConfidentialLabel
        : copy.visibilityTeamCollectiveLabel;

  return {
    workspace: newWs,
    auditEvent: {
      eventType: "WorkspaceCreated",
      summary: formatI18nTemplate(copy.workspaceCreatedAuditTemplate, {
        name: newWs.name,
        slug: newWs.slug ?? input.slug,
        modeLabel,
        ownerName: effectiveOwnerName,
      }),
      scopeId: newWs.workspaceId,
      scopePath: newWs.slug ?? newWs.workspaceId,
      scopeLabel: formatI18nTemplate(copy.spaceScopePrefix, { name: newWs.name }),
    },
  };
}

export async function patchWorkspaceViaServer(params: {
  readonly locale?: SupportedWebLocale;
  readonly workspaceId: string;
  readonly payload: {
    readonly name?: string;
    readonly visibility_mode?: "STANDARD" | "CONFIDENTIAL_RESTRICTED" | "PRIVATE_USER";
    readonly lifecycle_phase?: ProductLifecyclePhaseType;
  };
}): Promise<WorkspacePatchResponse> {
  const client = createOrciaApiClient({
    baseUrl: resolveWebApiBaseUrl(),
    locale: params.locale ?? "fr",
  });
  return client.patchWorkspace(params.workspaceId, params.payload);
}

export function applyWorkspacePhaseUpdate(params: {
  readonly locale?: SupportedWebLocale;
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly workspaceId: string;
  readonly phase: ProductLifecyclePhaseType;
  readonly appendAudit: (
    eventType: string,
    summary: string,
    meta?: { scopeId?: string; scopePath?: string; scopeLabel?: string },
  ) => readonly ConfiguredAuditEvent[];
}): {
  readonly nextWorkspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly nextAudit: readonly ConfiguredAuditEvent[];
} {
  const { locale = "fr", workspaces, workspaceId, phase, appendAudit } = params;
  const copy = DICTIONARIES[locale].shellChrome.platformSetupGovernance;
  const targetWs = workspaces.find((w) => w.workspaceId === workspaceId);
  const wsName = targetWs?.name ?? workspaceId;
  const nextWorkspaces = workspaces.map((ws) =>
    ws.workspaceId === workspaceId ? { ...ws, lifecyclePhase: phase } : ws,
  );
  const nextAudit = appendAudit(
    "WorkspacePhaseUpdated",
    formatI18nTemplate(copy.workspacePhaseUpdatedAuditTemplate, { name: wsName, phase }),
    {
      scopeId: workspaceId,
      scopePath: targetWs?.slug ?? targetWs?.name ?? workspaceId,
      scopeLabel: formatI18nTemplate(copy.spaceScopePrefix, { name: wsName }),
    },
  );
  return { nextWorkspaces, nextAudit };
}

export function applyWorkspaceVisibilityUpdate(params: {
  readonly locale?: SupportedWebLocale;
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly workspaceId: string;
  readonly visibilityMode: "STANDARD" | "CONFIDENTIAL_RESTRICTED" | "PRIVATE_USER";
  readonly appendAudit: (
    eventType: string,
    summary: string,
    meta?: { scopeId?: string; scopePath?: string; scopeLabel?: string },
  ) => readonly ConfiguredAuditEvent[];
}): {
  readonly nextWorkspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly nextAudit: readonly ConfiguredAuditEvent[];
} {
  const { locale = "fr", workspaces, workspaceId, visibilityMode, appendAudit } = params;
  const copy = DICTIONARIES[locale].shellChrome.platformSetupGovernance;
  const targetWs = workspaces.find((w) => w.workspaceId === workspaceId);
  const wsName = targetWs?.name ?? workspaceId;
  const nextWorkspaces = workspaces.map((ws) =>
    ws.workspaceId === workspaceId ? { ...ws, visibilityMode } : ws,
  );
  const modeLabel =
    visibilityMode === "PRIVATE_USER"
      ? copy.visibilityPrivatePersonalLabel
      : visibilityMode === "CONFIDENTIAL_RESTRICTED"
        ? copy.visibilityConfidentialIsolatedLabel
        : copy.visibilityTeamCollectiveLabel;
  const nextAudit = appendAudit(
    "SettingsChanged",
    formatI18nTemplate(copy.workspaceVisibilityUpdatedAuditTemplate, {
      name: wsName,
      modeLabel,
    }),
    {
      scopeId: workspaceId,
      scopePath: targetWs?.slug ?? targetWs?.name ?? workspaceId,
      scopeLabel: formatI18nTemplate(copy.spaceScopePrefix, { name: wsName }),
    },
  );
  return { nextWorkspaces, nextAudit };
}
