import type { ControlCenterWorkspaceGovItem } from "@orcia/ui";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import {
  formatI18nTemplate,
  resolveDictionaryForFlag,
  resolveLocaleForFlag,
} from "../../../i18n";
import { formatCountNoun } from "../../../stores/authSessionStore";

export interface OrgTreeRowItem {
  readonly unit: ConfiguredOrgUnit;
  readonly depth: number;
  readonly isSubBu: boolean;
  readonly parentNode: ConfiguredOrgUnit | undefined;
  readonly childrenCount: number;
  readonly attachedTeamsCount: number;
  readonly attachedWorkspacesCount: number;
  readonly childUnits: readonly { readonly id: string; readonly slug: string; readonly name: string }[];
  readonly attachedWorkspaces: readonly { readonly id: string; readonly slug: string; readonly name: string }[];
}

export function buildIndentedOrgTree(
  orgUnits: readonly ConfiguredOrgUnit[],
  workspaces: readonly ControlCenterWorkspaceGovItem[] = [],
): readonly OrgTreeRowItem[] {
  const byId = new Map<string, ConfiguredOrgUnit>();
  for (const unit of orgUnits) {
    byId.set(unit.id, unit);
  }

  const childrenByParent = new Map<string, ConfiguredOrgUnit[]>();
  for (const unit of orgUnits) {
    const rawParent = unit.parentId;
    const effectiveParent =
      rawParent && rawParent !== "scope-global" && byId.has(rawParent)
        ? rawParent
        : "scope-global";
    const list = childrenByParent.get(effectiveParent) ?? [];
    list.push(unit);
    childrenByParent.set(effectiveParent, list);
  }

  for (const siblings of childrenByParent.values()) {
    siblings.sort((a, b) => {
      const rankA = a.level === "BU" ? 0 : 1;
      const rankB = b.level === "BU" ? 0 : 1;
      return rankA - rankB;
    });
  }

  const wsCountByOwner = new Map<string, number>();
  for (const ws of workspaces) {
    if (ws.ownerOrgUnitId) {
      wsCountByOwner.set(ws.ownerOrgUnitId, (wsCountByOwner.get(ws.ownerOrgUnitId) ?? 0) + 1);
    }
  }

  const rows: OrgTreeRowItem[] = [];
  const visited = new Set<string>();

  const visit = (parentKey: string, depth: number) => {
    const children = childrenByParent.get(parentKey) ?? [];
    for (const unit of children) {
      if (visited.has(unit.id)) {
        continue;
      }
      visited.add(unit.id);
      const parentNode =
        unit.parentId && unit.parentId !== "scope-global"
          ? byId.get(unit.parentId)
          : undefined;
      const directChildren = childrenByParent.get(unit.id) ?? [];
      const childUnits = directChildren.map((c) => ({ id: c.id, slug: c.slug, name: c.name }));
      const attachedTeamsCount = directChildren.filter((c) => c.level === "TEAM").length;
      const localWsCount = wsCountByOwner.get(unit.id) ?? 0;
      const fallbackWorkspaces = workspaces
        .filter((w) => w.ownerOrgUnitId === unit.id)
        .map((w) => {
          const wsAny = w as unknown as Record<string, unknown>;
          return {
            id: w.workspaceId,
            slug: String(wsAny.slug || w.workspaceId),
            name: w.name,
          };
        });
      const rowAttachedWs =
        unit.attachedWorkspaces && unit.attachedWorkspaces.length > 0
          ? unit.attachedWorkspaces
          : fallbackWorkspaces;
      const attachedWorkspacesCount = Math.max(
        unit.attachedWorkspacesCount ?? 0,
        localWsCount,
        rowAttachedWs.length,
      );
      rows.push({
        unit,
        depth,
        isSubBu: unit.level === "BU" && parentNode?.level === "BU",
        parentNode,
        childrenCount: directChildren.length,
        attachedTeamsCount,
        attachedWorkspacesCount,
        childUnits,
        attachedWorkspaces: rowAttachedWs,
      });
      visit(unit.id, depth + 1);
    }
  };

  visit("scope-global", 0);

  for (const unit of orgUnits) {
    if (!visited.has(unit.id)) {
      const directChildren = childrenByParent.get(unit.id) ?? [];
      const childUnits = directChildren.map((c) => ({ id: c.id, slug: c.slug, name: c.name }));
      const localWsCount = wsCountByOwner.get(unit.id) ?? 0;
      const fallbackWorkspaces = workspaces
        .filter((w) => w.ownerOrgUnitId === unit.id)
        .map((w) => {
          const wsAny = w as unknown as Record<string, unknown>;
          return {
            id: w.workspaceId,
            slug: String(wsAny.slug || w.workspaceId),
            name: w.name,
          };
        });
      const rowAttachedWs =
        unit.attachedWorkspaces && unit.attachedWorkspaces.length > 0
          ? unit.attachedWorkspaces
          : fallbackWorkspaces;
      rows.push({
        unit,
        depth: 0,
        isSubBu: false,
        parentNode: undefined,
        childrenCount: directChildren.length,
        attachedTeamsCount: directChildren.filter((c) => c.level === "TEAM").length,
        attachedWorkspacesCount: Math.max(
          unit.attachedWorkspacesCount ?? 0,
          localWsCount,
          rowAttachedWs.length,
        ),
        childUnits,
        attachedWorkspaces: rowAttachedWs,
      });
    }
  }

  return rows;
}

export function getDescendantOrgUnitIds(
  orgUnits: readonly ConfiguredOrgUnit[],
  targetId: string,
): ReadonlySet<string> {
  const excluded = new Set<string>([targetId]);
  let changed = true;
  while (changed) {
    changed = false;
    for (const unit of orgUnits) {
      if (!excluded.has(unit.id) && excluded.has(unit.parentId)) {
        excluded.add(unit.id);
        changed = true;
      }
    }
  }
  return excluded;
}

export function getEligibleParentBuUnits(
  orgUnits: readonly ConfiguredOrgUnit[],
  editingUnitId?: string,
): readonly ConfiguredOrgUnit[] {
  const excluded = editingUnitId
    ? getDescendantOrgUnitIds(orgUnits, editingUnitId)
    : new Set<string>();
  return orgUnits.filter((u) => u.level === "BU" && !excluded.has(u.id));
}

export function buildNonEmptyDeleteSummary(params: {
  readonly unitName: string;
  readonly childrenCount: number;
  readonly attachedWorkspacesCount: number;
  readonly isFr: boolean;
}): string {
  const { unitName, childrenCount, attachedWorkspacesCount, isFr } = params;
  const resolvedLocale = resolveLocaleForFlag(isFr);
  const orgCopy = resolveDictionaryForFlag(isFr, resolvedLocale).featureAdminCatalogSettings.orgTree;
  const parts: string[] = [];
  if (childrenCount > 0) {
    parts.push(
      formatCountNoun(
        childrenCount,
        orgCopy.subUnitSingular,
        orgCopy.subUnitPlural,
        resolvedLocale,
      ),
    );
  }
  if (attachedWorkspacesCount > 0) {
    parts.push(
      formatCountNoun(
        attachedWorkspacesCount,
        orgCopy.workspaceSingular,
        orgCopy.workspacePlural,
        resolvedLocale,
      ),
    );
  }
  const summary = parts.join(orgCopy.joinAnd);
  return formatI18nTemplate(orgCopy.deleteRefusedTemplate, {
    unitName,
    summary,
  });
}
