import {
  type ControlCenterWorkspaceGovItem,
  type EightFixedMenuKey,
  type UiScopeNode,
} from "@orcia/ui";
import type {
  ConfiguredLlmTierMapping,
  ConfiguredOrgUnit,
} from "./platformSetupStore";
import { resolveLocaleForFlag } from "../i18n";
import {
  SHELL_SCOPE_OPTIONS_BY_LOCALE,
} from "../i18n/locales/shell_scope_labels";
export { buildShellNotificationItems } from "./shellNotificationBuilder";
export {
  buildUnifiedScopeSelectorState,
  resolveEffectiveWorkspaceId,
  type UnifiedScopeSelectorState,
} from "./shellUnifiedScope";

export interface WorkspaceSwitcherOptionItem {
  readonly id: string;
  readonly label: string;
  readonly groupLabel: string;
}

export interface DoubleScopeSelectorState {
  readonly teamBuOptions: readonly { readonly id: string; readonly label: string }[];
  readonly activeTeamBuId: string;
  readonly workspaceSelectorOptions: readonly { readonly id: string; readonly label: string }[];
  readonly activeWorkspaceSelectorId: string;
}

export function buildDoubleScopeSelectorState(params: {
  readonly isFr: boolean;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly scopes: readonly UiScopeNode[];
  readonly activeScopeId: string;
}): DoubleScopeSelectorState {
  const { orgUnits, workspaces, scopes, activeScopeId } = params;
  const globalScopes = scopes.filter((s) => s.level === "GLOBAL");
  const buUnits = orgUnits.filter((u) => u.level === "BU");
  const teamUnits = orgUnits.filter((u) => u.level === "TEAM");

  const teamBuOptions = [
    ...globalScopes.map((s) => ({
      id: s.id,
      label: s.name,
    })),
    ...buUnits.map((bu) => ({
      id: bu.id,
      label: bu.name,
    })),
    ...teamUnits.map((team) => ({
      id: team.id,
      label: team.name,
    })),
  ];

  const matchedWorkspace = workspaces.find((ws) => ws.workspaceId === activeScopeId);
  const activeTeamBuId = matchedWorkspace
    ? (matchedWorkspace.ownerOrgUnitId &&
        teamBuOptions.some((o) => o.id === matchedWorkspace.ownerOrgUnitId)
        ? matchedWorkspace.ownerOrgUnitId
        : teamBuOptions[0]?.id ?? "scope-global")
    : teamBuOptions.some((o) => o.id === activeScopeId)
      ? activeScopeId
      : teamBuOptions[0]?.id ?? "scope-global";

  const selectedBu = buUnits.find((bu) => bu.id === activeTeamBuId);
  const childTeamIds = selectedBu
    ? new Set([
        selectedBu.id,
        ...teamUnits.filter((t) => t.parentId === selectedBu.id).map((t) => t.id),
      ])
    : null;
  const isTeamSelected = teamUnits.some((t) => t.id === activeTeamBuId);

  const filteredWorkspaces = workspaces.filter((ws) => {
    if (isTeamSelected) {
      return !ws.ownerOrgUnitId || ws.ownerOrgUnitId === activeTeamBuId;
    }
    if (childTeamIds) {
      return !ws.ownerOrgUnitId || childTeamIds.has(ws.ownerOrgUnitId);
    }
    return true;
  });

  const workspaceSelectorOptions = (
    filteredWorkspaces.length > 0 ? filteredWorkspaces : workspaces
  ).map((ws) => ({
    id: ws.workspaceId,
    label: ws.name,
  }));

  return {
    teamBuOptions,
    activeTeamBuId,
    workspaceSelectorOptions,
    activeWorkspaceSelectorId: matchedWorkspace ? matchedWorkspace.workspaceId : "",
  };
}

export function buildWorkspaceSwitcherOptions(params: {
  readonly isFr: boolean;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly scopes: readonly UiScopeNode[];
}): readonly WorkspaceSwitcherOptionItem[] {
  const { isFr, orgUnits, workspaces, scopes } = params;
  const privateWorkspaces = workspaces.filter((ws) => ws.visibilityMode === "PRIVATE_USER");
  const teamUnits = orgUnits.filter((u) => u.level === "TEAM");
  const buUnits = orgUnits.filter((u) => u.level === "BU");
  const sharedOrConfidentialWorkspaces = workspaces.filter(
    (ws) => ws.visibilityMode !== "PRIVATE_USER",
  );

  const resolveOwnerName = (ws: ControlCenterWorkspaceGovItem): string => {
    if (ws.ownerOrgUnitId) {
      const matched = orgUnits.find(
        (u) => u.id === ws.ownerOrgUnitId || u.slug === ws.ownerOrgUnitId,
      );
      if (matched) {
        return matched.name;
      }
    }
    return ws.ownerOrgUnitName ?? "";
  };

  const scopeLabels = SHELL_SCOPE_OPTIONS_BY_LOCALE[resolveLocaleForFlag(isFr)];

  const groupPrivateLabel = scopeLabels.groupPrivateSuffix;
  const groupTeamUnitLabel = scopeLabels.groupTeamUnitSuffix;
  const groupSharedWorkspaceLabel = `${scopeLabels.groupSharedWorkspacePrefix} ${scopeLabels.groupSharedWorkspaceSuffix}`;
  const groupSupervisionLabel = scopeLabels.groupSupervisionSuffix;

  return [
    ...privateWorkspaces.map((ws) => {
      const ownerName = resolveOwnerName(ws);
      return {
        id: ws.workspaceId,
        label: ownerName
          ? `${scopeLabels.privateSpacePrefix}${ws.name} · ${ownerName}`
          : `${scopeLabels.privateSpacePrefix}${ws.name}`,
        groupLabel: groupPrivateLabel,
      };
    }),
    ...teamUnits.map((team) => ({
      id: team.id,
      label: `${scopeLabels.teamPrefix}${team.name}`,
      groupLabel: groupTeamUnitLabel,
    })),
    ...sharedOrConfidentialWorkspaces.map((ws) => {
      const ownerName = resolveOwnerName(ws);
      return {
        id: ws.workspaceId,
        label: ownerName
          ? `${scopeLabels.sharedSpacePrefix}${ws.name} · ${ownerName}`
          : `${scopeLabels.sharedSpacePrefix}${ws.name}`,
        groupLabel: groupSharedWorkspaceLabel,
      };
    }),
    ...buUnits.map((bu) => ({
      id: bu.id,
      label: `${scopeLabels.buPrefix}${bu.name}`,
      groupLabel: groupSupervisionLabel,
    })),
    ...scopes
      .filter((s) => s.level === "GLOBAL")
      .map((s) => ({
        id: s.id,
        label: s.name,
        groupLabel: groupSupervisionLabel,
      })),
  ];
}

export function buildShellDisabledMenuKeys(params: {
  readonly isFr: boolean;
  readonly adminCreated?: boolean;
  readonly day0AdminMissingReason?: string;
  readonly llmTiers: readonly ConfiguredLlmTierMapping[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly hasModels?: boolean;
  readonly hasWorkspaces?: boolean;
}): Partial<Record<EightFixedMenuKey, string>> {
  const {
    isFr,
    adminCreated = true,
    day0AdminMissingReason,
    llmTiers,
    workspaces,
    hasModels,
    hasWorkspaces,
  } = params;
  const scopeLabels = SHELL_SCOPE_OPTIONS_BY_LOCALE[resolveLocaleForFlag(isFr)];
  if (!adminCreated) {
    const adminReason = day0AdminMissingReason ?? scopeLabels.disabledReasons.adminMissing;
    return {
      assistant: adminReason,
      processes: adminReason,
      agents: adminReason,
      spaces: adminReason,
      organization: adminReason,
      finops: adminReason,
      configuration: adminReason,
      help: adminReason,
    };
  }
  const effectiveHasModels = hasModels ?? llmTiers.length > 0;
  const effectiveHasWorkspaces = workspaces.length > 0 || Boolean(hasWorkspaces);
  return {
    ...(!effectiveHasModels
      ? {
          assistant: scopeLabels.disabledReasons.assistant,
          agents: scopeLabels.disabledReasons.agents,
        }
      : {}),
    ...(!effectiveHasWorkspaces || !effectiveHasModels
      ? {
          processes: scopeLabels.disabledReasons.processes,
        }
      : {}),
    ...(!effectiveHasWorkspaces && !effectiveHasModels
      ? {
          finops: scopeLabels.disabledReasons.finops,
        }
      : {}),
  };
}
