import { createOrciaApiClient } from "@orcia/api-client";
import type {
  ControlCenterDatasourceItem,
  ControlCenterWorkspaceGovItem,
  ProductLifecyclePhaseType,
  UiScopeNode,
} from "@orcia/ui";
import {
  SHELL_AND_SEARCH_EN_LABELS,
  SHELL_AND_SEARCH_FR_LABELS,
} from "../i18n/locales/shell_and_search_labels";
import { resolveWebApiBaseUrl } from "../stores/authSessionStore";
import {
  formatHumanReadableScopePath,
  type ConfiguredAuditEvent,
  type ConfiguredOrgUnit,
  type ConfiguredPlatformAdmin,
  type ConfiguredWorkflowItem,
} from "./platformSetupStorageHelpers";

export interface CreateWorkspaceInput {
  readonly name: string;
  readonly slug: string;
  readonly visibilityMode: "STANDARD" | "CONFIDENTIAL_RESTRICTED" | "PRIVATE_USER";
  readonly lifecyclePhase: ProductLifecyclePhaseType;
  readonly ownerOrgUnitId?: string;
}

export interface RegisterDatasourceInput {
  readonly workspaceName: string;
  readonly alias: string;
  readonly scheme: "git" | "confluence" | "jira" | "db";
  readonly uri: string;
  readonly executionIdentity: "passthrough" | "service_account";
  readonly freshnessTtlDays: number;
}

export function resolveGlobalScopeLabel(isFr = true): string {
  const section = isFr ? SHELL_AND_SEARCH_FR_LABELS : SHELL_AND_SEARCH_EN_LABELS;
  return section.fourZoneShell.doubleSelector?.globalPlatformLabel ?? "ORCIA";
}

export const BASE_GLOBAL_SCOPE: UiScopeNode = {
  id: "scope-global",
  level: "GLOBAL",
  name: resolveGlobalScopeLabel(true),
  accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
};

export async function createWorkspaceViaServer(params: {
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
  const { input, orgUnits, workflows, platformAdmin } = params;
  const teamUnits = orgUnits.filter((u) => u.level === "TEAM");
  const resolvedOwnerUnit =
    orgUnits.find((u) => u.id === input.ownerOrgUnitId) ??
    teamUnits[0] ??
    orgUnits[orgUnits.length - 1];
  const ownerOrgUnitId = resolvedOwnerUnit?.id;
  const fallbackOwnerName = resolvedOwnerUnit?.name ?? resolveGlobalScopeLabel(true);

  const client = createOrciaApiClient({ baseUrl: resolveWebApiBaseUrl() });
  const created = await client.createWorkspace({
    name: input.name,
    slug: input.slug,
    visibility_mode: input.visibilityMode,
    lifecycle_phase: input.lifecyclePhase,
    ...(ownerOrgUnitId ? { owner_org_unit_id: ownerOrgUnitId } : {}),
  });

  if (!created || !created.id) {
    throw new Error(
      "Le serveur n'a pas retourné d'identifiant UUIDv7 valide pour le nouvel espace.",
    );
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
      ? "Privé personnel"
      : input.visibilityMode === "CONFIDENTIAL_RESTRICTED"
        ? "Confidentiel"
        : "Collectif d'équipe";

  return {
    workspace: newWs,
    auditEvent: {
      eventType: "WorkspaceCreated",
      summary: `Espace de travail "${newWs.name}" (${newWs.slug}, ${modeLabel}, facturé à ${effectiveOwnerName}) créé`,
      scopeId: newWs.workspaceId,
      scopePath: newWs.slug ?? newWs.workspaceId,
      scopeLabel: `Espace · ${newWs.name}`,
    },
  };
}

export function applyWorkspacePhaseUpdate(params: {
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
  const { workspaces, workspaceId, phase, appendAudit } = params;
  const targetWs = workspaces.find((w) => w.workspaceId === workspaceId);
  const nextWorkspaces = workspaces.map((ws) =>
    ws.workspaceId === workspaceId ? { ...ws, lifecyclePhase: phase } : ws,
  );
  const nextAudit = appendAudit(
    "WorkspacePhaseUpdated",
    `Espace "${targetWs?.name ?? workspaceId}" passé en phase ${phase}`,
    {
      scopeId: workspaceId,
      scopePath: targetWs?.slug ?? targetWs?.name ?? workspaceId,
      scopeLabel: `Espace · ${targetWs?.name ?? workspaceId}`,
    },
  );
  return { nextWorkspaces, nextAudit };
}

export function applyWorkspaceVisibilityUpdate(params: {
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
  const { workspaces, workspaceId, visibilityMode, appendAudit } = params;
  const targetWs = workspaces.find((w) => w.workspaceId === workspaceId);
  const nextWorkspaces = workspaces.map((ws) =>
    ws.workspaceId === workspaceId ? { ...ws, visibilityMode } : ws,
  );
  const modeLabel =
    visibilityMode === "PRIVATE_USER"
      ? "Privé personnel"
      : visibilityMode === "CONFIDENTIAL_RESTRICTED"
        ? "Confidentiel isolé"
        : "Collectif d'équipe";
  const nextAudit = appendAudit(
    "SettingsChanged",
    `Visibilité de l'Espace "${targetWs?.name ?? workspaceId}" mise à jour : ${modeLabel}`,
    {
      scopeId: workspaceId,
      scopePath: targetWs?.slug ?? targetWs?.name ?? workspaceId,
      scopeLabel: `Espace · ${targetWs?.name ?? workspaceId}`,
    },
  );
  return { nextWorkspaces, nextAudit };
}

export function applyRegisterDatasource(params: {
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly input: RegisterDatasourceInput;
  readonly appendAudit: (
    eventType: string,
    summary: string,
    meta?: { scopeId?: string; scopePath?: string; scopeLabel?: string },
  ) => readonly ConfiguredAuditEvent[];
}): {
  readonly nextDatasources: readonly ControlCenterDatasourceItem[];
  readonly nextAudit: readonly ConfiguredAuditEvent[];
} {
  const { datasources, input, appendAudit } = params;
  const id = `ds-${datasources.length + 1}`;
  const nextDatasources: readonly ControlCenterDatasourceItem[] = [
    ...datasources,
    {
      id,
      workspaceName: input.workspaceName,
      alias: input.alias,
      scheme: input.scheme,
      uri: input.uri,
      executionIdentity: input.executionIdentity,
      freshnessTtlDays: input.freshnessTtlDays,
      tripartiteStatus: "ALIGNED",
    },
  ];
  const identityLabel =
    input.executionIdentity === "passthrough"
      ? "Identité personnelle"
      : "Compte technique partagé";
  const nextAudit = appendAudit(
    "ConnectorConfigured",
    `Connecteur "${input.alias}" (${input.uri}) enregistré (${identityLabel})`,
    {
      scopePath: input.workspaceName,
      scopeLabel: formatHumanReadableScopePath(input.workspaceName),
    },
  );
  return { nextDatasources, nextAudit };
}

export function buildScopeNodes(
  orgUnits: readonly ConfiguredOrgUnit[],
  workspaces: readonly ControlCenterWorkspaceGovItem[],
): readonly UiScopeNode[] {
  return [
    BASE_GLOBAL_SCOPE,
    ...orgUnits.map((unit) => ({
      id: unit.id,
      level: unit.level,
      name: unit.name,
      parentId: unit.parentId,
      accessMode: "CONTRIBUTOR_ACTION_REQUIRED" as const,
    })),
    ...workspaces.map((ws) => ({
      id: ws.workspaceId,
      level: "WORKSPACE" as const,
      name: ws.name,
      parentId: ws.ownerOrgUnitId ?? orgUnits[orgUnits.length - 1]?.id ?? BASE_GLOBAL_SCOPE.id,
      accessMode: ws.accessMode,
    })),
  ];
}
