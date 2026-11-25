export type FinopsScopeLevel = "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
export type FinopsPillScopeKey = "WORKSPACE" | "TEAM" | "GLOBAL";

export interface FinopsScopeCapabilities {
  readonly canViewGlobal: boolean;
  readonly canViewBu: boolean;
  readonly canViewTeam: boolean;
  readonly allowedScopePills: readonly FinopsPillScopeKey[];
  readonly allowedModalScopes: readonly FinopsScopeLevel[];
}

export function resolveFinopsScopeCapabilities(
  roles: readonly string[],
): FinopsScopeCapabilities {
  const normalized = new Set(roles.map((r) => r.trim().toUpperCase()).filter(Boolean));
  const canViewGlobal =
    normalized.has("PLATFORM_ADMIN") ||
    normalized.has("SECOPS") ||
    normalized.has("OBSERVER");
  const canViewBu =
    canViewGlobal || normalized.has("BU_DIRECTOR") || normalized.has("BU_LEAD");
  const canViewTeam = canViewBu || normalized.has("TEAM_LEAD");

  const allowedScopePills: FinopsPillScopeKey[] = ["WORKSPACE"];
  if (canViewTeam) {
    allowedScopePills.push("TEAM");
  }
  if (canViewGlobal) {
    allowedScopePills.push("GLOBAL");
  }

  const allowedModalScopes: FinopsScopeLevel[] = [];
  if (canViewGlobal) {
    allowedModalScopes.push("GLOBAL");
  }
  if (canViewBu) {
    allowedModalScopes.push("BU");
  }
  if (canViewTeam) {
    allowedModalScopes.push("TEAM");
  }
  allowedModalScopes.push("WORKSPACE");

  return {
    canViewGlobal,
    canViewBu,
    canViewTeam,
    allowedScopePills,
    allowedModalScopes,
  };
}

export function deriveAuthorizedFinopsScope(params: {
  readonly activeScopeNodeLevel?: string;
  readonly capabilities: FinopsScopeCapabilities;
  readonly hasBuId: boolean;
  readonly hasTeamId: boolean;
}): FinopsScopeLevel {
  const { activeScopeNodeLevel, capabilities, hasBuId, hasTeamId } = params;

  if (activeScopeNodeLevel === "WORKSPACE") {
    return "WORKSPACE";
  }
  if (activeScopeNodeLevel === "TEAM") {
    return capabilities.canViewTeam ? "TEAM" : "WORKSPACE";
  }
  if (activeScopeNodeLevel === "BU") {
    if (capabilities.canViewBu) {
      return "BU";
    }
    return capabilities.canViewTeam ? "TEAM" : "WORKSPACE";
  }
  if (capabilities.canViewGlobal) {
    return "GLOBAL";
  }
  if (capabilities.canViewBu && hasBuId) {
    return "BU";
  }
  if (capabilities.canViewTeam && hasTeamId) {
    return "TEAM";
  }
  if (capabilities.canViewBu) {
    return "BU";
  }
  if (capabilities.canViewTeam) {
    return "TEAM";
  }
  return "WORKSPACE";
}
