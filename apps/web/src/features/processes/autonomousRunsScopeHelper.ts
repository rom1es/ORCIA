import type { UiScopeNode } from "@orcia/ui";
import type { ControlCenterWorkspaceGovItem } from "@orcia/ui";

const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export interface AutonomousScopeTarget {
  readonly exactWorkspaceId: string | null;
  readonly orgScopeId: string | null;
}

export function resolveAutonomousScopeTarget(
  activeScopeId: string,
  scopes: readonly UiScopeNode[],
  workspaces: readonly ControlCenterWorkspaceGovItem[],
): AutonomousScopeTarget {
  const scopeRaw = activeScopeId.startsWith("scope-ws-")
    ? activeScopeId.slice("scope-ws-".length)
    : activeScopeId;
  if (!UUID_REGEX.test(scopeRaw)) {
    return { exactWorkspaceId: null, orgScopeId: null };
  }
  const matchingScope = scopes.find((s) => s.id === activeScopeId || s.id === scopeRaw);
  if (
    matchingScope?.level === "WORKSPACE" ||
    workspaces.some((w) => w.workspaceId === scopeRaw)
  ) {
    return { exactWorkspaceId: scopeRaw, orgScopeId: null };
  }
  if (matchingScope?.level === "BU" || matchingScope?.level === "TEAM") {
    return { exactWorkspaceId: null, orgScopeId: scopeRaw };
  }
  return { exactWorkspaceId: null, orgScopeId: null };
}

export function isHttp403Error(err: unknown): boolean {
  if (typeof err !== "object" || err === null) return false;
  if ("status" in err && Number((err as { status?: unknown }).status) === 403) {
    return true;
  }
  if ("problem" in err) {
    const prob = (err as { problem?: { status?: unknown; error_code?: unknown } }).problem;
    if (Number(prob?.status) === 403 || prob?.error_code === "ERR_SCOPE_ACCESS_DENIED") {
      return true;
    }
  }
  return false;
}
