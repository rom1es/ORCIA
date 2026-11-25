import type {
  ControlCenterWorkspaceGovItem,
  ScopeOptionItem,
  UnifiedScopeOptionGroup,
} from "@orcia/ui";
import { resolveLocaleForFlag } from "../i18n";
import { SHELL_SCOPE_OPTIONS_BY_LOCALE } from "../i18n/locales/shell_scope_labels";
import type { ConfiguredOrgUnit } from "./platformSetupStore";

export interface UnifiedScopeSelectorState {
  readonly groups: readonly UnifiedScopeOptionGroup[];
  readonly allSpacesOption: ScopeOptionItem;
  readonly activeScopeValue: string;
  readonly scopeLabel: string;
}

export function resolveEffectiveWorkspaceId(
  activeScopeId: string,
  workspaces: readonly ControlCenterWorkspaceGovItem[],
  currentUserId?: string | null,
): string {
  if (workspaces.length === 0) return "";
  const cleanedScopeId = activeScopeId.startsWith("scope-ws-")
    ? activeScopeId.slice("scope-ws-".length)
    : activeScopeId;
  const directWs = workspaces.find(
    (ws) => ws.workspaceId === cleanedScopeId || ws.slug === cleanedScopeId,
  );
  if (directWs) return directWs.workspaceId;
  const orgWs = workspaces.find((ws) => ws.ownerOrgUnitId === cleanedScopeId);
  if (orgWs) return orgWs.workspaceId;
  const normalizedUser = (currentUserId ?? "").trim().toLowerCase();
  const personalWs =
    (normalizedUser
      ? workspaces.find(
          (ws) =>
            ws.visibilityMode === "PRIVATE_USER" &&
            (ws.ownerUserId ?? "").trim().toLowerCase() === normalizedUser,
        )
      : undefined) ??
    workspaces.find((ws) => ws.visibilityMode === "PRIVATE_USER");
  return personalWs?.workspaceId ?? workspaces[0]!.workspaceId;
}

export function buildUnifiedScopeSelectorState(params: {
  readonly isFr: boolean;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly activeScopeId: string;
  readonly labels?: {
    readonly workspaceLabel?: string;
    readonly personalGroupLabel?: string;
    readonly otherSpacesGroupLabel?: string;
    readonly allMySpacesOption?: string;
  };
}): UnifiedScopeSelectorState {
  const { isFr, orgUnits, workspaces, activeScopeId, labels } = params;
  const fallbackLabels = SHELL_SCOPE_OPTIONS_BY_LOCALE[resolveLocaleForFlag(isFr)];
  const personalGroupLabel = labels?.personalGroupLabel ?? fallbackLabels.personalGroupLabel;
  const otherSpacesGroupLabel =
    labels?.otherSpacesGroupLabel ?? fallbackLabels.otherSpacesGroupLabel;
  const allMySpacesLabel = labels?.allMySpacesOption ?? fallbackLabels.allMySpacesOption;
  const scopeLabel = labels?.workspaceLabel ?? fallbackLabels.workspaceLabel;

  const groups: UnifiedScopeOptionGroup[] = [];
  const privateWorkspaces = workspaces.filter((ws) => ws.visibilityMode === "PRIVATE_USER");
  if (privateWorkspaces.length > 0) {
    groups.push({
      label: personalGroupLabel,
      options: privateWorkspaces.map((ws) => ({
        id: ws.workspaceId,
        label: ws.name,
      })),
    });
  }

  const sharedWorkspaces = workspaces.filter((ws) => ws.visibilityMode !== "PRIVATE_USER");
  const assignedWorkspaceIds = new Set<string>();
  for (const unit of orgUnits) {
    const unitWorkspaces = sharedWorkspaces.filter((ws) => ws.ownerOrgUnitId === unit.id);
    if (unitWorkspaces.length === 0) continue;
    unitWorkspaces.forEach((ws) => assignedWorkspaceIds.add(ws.workspaceId));
    groups.push({
      label: unit.name,
      options: unitWorkspaces.map((ws) => ({
        id: ws.workspaceId,
        label: ws.name,
      })),
    });
  }

  const remainingShared = sharedWorkspaces.filter(
    (ws) => !assignedWorkspaceIds.has(ws.workspaceId),
  );
  if (remainingShared.length > 0) {
    const byOwnerName = new Map<string, ControlCenterWorkspaceGovItem[]>();
    for (const ws of remainingShared) {
      const groupName = (ws.ownerOrgUnitName ?? "").trim() || otherSpacesGroupLabel;
      const list = byOwnerName.get(groupName) ?? [];
      list.push(ws);
      byOwnerName.set(groupName, list);
    }
    for (const [groupName, wsList] of byOwnerName.entries()) {
      groups.push({
        label: groupName,
        options: wsList.map((ws) => ({
          id: ws.workspaceId,
          label: ws.name,
        })),
      });
    }
  }

  const matchedWorkspace = workspaces.find((ws) => ws.workspaceId === activeScopeId);
  return {
    groups,
    allSpacesOption: { id: "scope-global", label: allMySpacesLabel },
    activeScopeValue: matchedWorkspace ? matchedWorkspace.workspaceId : "scope-global",
    scopeLabel,
  };
}
