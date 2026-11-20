import {
  getOrciaIconGlyph,
  type ControlCenterWorkspaceGovItem,
  type EightFixedMenuKey,
  type UiScopeNode,
} from "@orcia/ui";
import type {
  ConfiguredLlmTierMapping,
  ConfiguredOrgUnit,
} from "./platformSetupStore";
export { buildShellNotificationItems } from "./shellNotificationBuilder";

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
  const { isFr, orgUnits, workspaces, scopes, activeScopeId } = params;
  const globalScopes = scopes.filter((s) => s.level === "GLOBAL");
  const buUnits = orgUnits.filter((u) => u.level === "BU");
  const teamUnits = orgUnits.filter((u) => u.level === "TEAM");

  const teamBuOptions = [
    ...globalScopes.map((s) => ({
      id: s.id,
      label: isFr ? `🌐 ${s.name}` : `🌐 ${s.name}`,
    })),
    ...buUnits.map((bu) => ({
      id: bu.id,
      label: `${getOrciaIconGlyph("organizationBu")} ${bu.name}`,
    })),
    ...teamUnits.map((team) => ({
      id: team.id,
      label: `${getOrciaIconGlyph("team")} ${team.name}`,
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
    label:
      ws.visibilityMode === "PRIVATE_USER"
        ? `🔒 ${ws.name}`
        : `📦 ${ws.name}`,
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

  const groupPrivateLabel = isFr
    ? `${getOrciaIconGlyph("lock")} Mes Espaces Privés`
    : `${getOrciaIconGlyph("lock")} My Private Spaces`;
  const groupTeamUnitLabel = isFr
    ? `${getOrciaIconGlyph("team")} Mes Équipes & Espaces · Équipe`
    : `${getOrciaIconGlyph("team")} My Teams & Spaces · Team`;
  const groupSharedWorkspaceLabel = isFr
    ? `📦 Espace · ${getOrciaIconGlyph("team")} Mes Équipes & Espaces`
    : `📦 Workspace · ${getOrciaIconGlyph("team")} My Teams & Spaces`;
  const groupSupervisionLabel = isFr
    ? `${getOrciaIconGlyph("organizationBu")} Supervision Organisation`
    : `${getOrciaIconGlyph("organizationBu")} Organization Supervision`;

  return [
    ...privateWorkspaces.map((ws) => {
      const ownerName = resolveOwnerName(ws);
      const prefix = isFr ? "🔒 Espace · " : "🔒 Workspace · ";
      return {
        id: ws.workspaceId,
        label: ownerName ? `${prefix}${ws.name} · ${ownerName}` : `${prefix}${ws.name}`,
        groupLabel: groupPrivateLabel,
      };
    }),
    ...teamUnits.map((team) => ({
      id: team.id,
      label: isFr
        ? `${getOrciaIconGlyph("team")} Équipe · ${team.name}`
        : `${getOrciaIconGlyph("team")} Team · ${team.name}`,
      groupLabel: groupTeamUnitLabel,
    })),
    ...sharedOrConfidentialWorkspaces.map((ws) => {
      const ownerName = resolveOwnerName(ws);
      const prefix = isFr ? "📦 Espace · " : "📦 Workspace · ";
      return {
        id: ws.workspaceId,
        label: ownerName ? `${prefix}${ws.name} · ${ownerName}` : `${prefix}${ws.name}`,
        groupLabel: groupSharedWorkspaceLabel,
      };
    }),
    ...buUnits.map((bu) => ({
      id: bu.id,
      label: isFr
        ? `${getOrciaIconGlyph("organizationBu")} Direction (BU) · ${bu.name}`
        : `${getOrciaIconGlyph("organizationBu")} Division (BU) · ${bu.name}`,
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
  if (!adminCreated) {
    const adminReason =
      day0AdminMissingReason ??
      (isFr
        ? "Créez d'abord le premier compte Administrateur pour accéder à cette section."
        : "Create the first Administrator account first to access this section.");
    return {
      assistant: adminReason,
      processes: adminReason,
      agents: adminReason,
      spaces: adminReason,
      finops: adminReason,
      configuration: adminReason,
      help: adminReason,
    };
  }
  const effectiveHasModels = hasModels ?? llmTiers.length > 0;
  const effectiveHasWorkspaces = hasWorkspaces ?? workspaces.length > 0;
  return {
    ...(!effectiveHasModels
      ? {
          assistant: isFr
            ? "Configurez au moins un modèle IA et rattachez une Équipe de facturation dans Configuration pour activer Mon Assistant."
            : "Configure at least one AI model and attach a billing Team in Configuration to enable My Assistant.",
          agents: isFr
            ? "Configurez un modèle IA ou activez un Pack et rattachez une Équipe de facturation dans Configuration pour déverrouiller Mes Agents."
            : "Configure an AI model or enable a Pack and attach a billing Team in Configuration to unlock My Agents.",
        }
      : {}),
    ...(!effectiveHasWorkspaces || !effectiveHasModels
      ? {
          processes: isFr
            ? "Créez un Espace de Travail rattaché à une Équipe de facturation et configurez un modèle IA pour activer Mes Processus."
            : "Create a Workspace attached to a billing Team and configure an AI model to enable My Processes.",
        }
      : {}),
    ...(!effectiveHasWorkspaces && !effectiveHasModels
      ? {
          finops: isFr
            ? "Configurez un modèle IA ou créez un Espace de Travail rattaché à une Équipe pour consulter le suivi des coûts."
            : "Configure an AI model or create a Workspace attached to a Team to view cost tracking.",
        }
      : {}),
  };
}
