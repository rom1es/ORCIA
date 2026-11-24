import type { StatusBadgeTone, UiActivityScopeFilterOption } from "@orcia/ui";
import { DICTIONARIES, resolveLocaleForFlag, type SupportedWebLocale } from "../i18n";
import { formatShortDateTime } from "../lib/formatters";

export const EVENT_TYPE_FR_LABELS: Readonly<
  Record<string, { readonly label: string; readonly tone: StatusBadgeTone }>
> = DICTIONARIES.fr.routesAndWizards.activityEvents;

export const EVENT_TYPE_EN_LABELS: Readonly<
  Record<string, { readonly label: string; readonly tone: StatusBadgeTone }>
> = DICTIONARIES.en.routesAndWizards.activityEvents;

export function formatActivityTimestamp(
  timestampIso: string,
  isFr: boolean,
  locale?: SupportedWebLocale,
): string {
  return formatShortDateTime(timestampIso, resolveLocaleForFlag(isFr, locale));
}

export interface ScopeSourceOrgUnit {
  readonly id: string;
  readonly name: string;
  readonly slug: string;
  readonly level: "BU" | "TEAM";
  readonly parentId?: string;
}

export interface ScopeSourceWorkspace {
  readonly workspaceId: string;
  readonly name: string;
  readonly ownerOrgUnitId?: string;
  readonly visibilityMode?: string;
}

function collectDescendantUnits(
  rootId: string,
  orgUnits: readonly ScopeSourceOrgUnit[],
): readonly ScopeSourceOrgUnit[] {
  const out: ScopeSourceOrgUnit[] = [];
  const queue = [rootId];
  const seen = new Set<string>([rootId]);
  while (queue.length > 0) {
    const curr = queue.shift()!;
    for (const u of orgUnits) {
      if (u.parentId === curr && !seen.has(u.id)) {
        seen.add(u.id);
        out.push(u);
        queue.push(u.id);
      }
    }
  }
  return out;
}

export function buildActivityScopeOptions(
  orgUnits: readonly ScopeSourceOrgUnit[],
  workspaces: readonly ScopeSourceWorkspace[],
  labels: {
    entirePlatform: string;
    divisionPrefix: string;
    teamPrefix: string;
    privateSpacePrefix: string;
    spacePrefix: string;
  },
  options?: {
    readonly includeGlobal?: boolean;
  },
): UiActivityScopeFilterOption[] {
  const includeGlobal = options?.includeGlobal ?? true;
  const globalEntries: UiActivityScopeFilterOption[] = includeGlobal
    ? [
        {
          id: "scope-global",
          label: labels.entirePlatform,
          scopePath: "GLOBAL",
          level: "GLOBAL",
          childScopeIds: [
            ...orgUnits.map((u) => u.id),
            ...workspaces.map((w) => w.workspaceId),
          ],
          childScopePaths: [
            "GLOBAL",
            labels.entirePlatform,
            ...orgUnits.flatMap((u) => [u.slug, u.name]),
            ...workspaces.map((w) => w.name),
          ],
        },
      ]
    : [];

  return [
    ...globalEntries,
    ...orgUnits.map((u): UiActivityScopeFilterOption => {
      const childUnits = collectDescendantUnits(u.id, orgUnits);
      const childTeamIds = new Set([u.id, ...childUnits.map((c) => c.id)]);
      const childWorkspaces = workspaces.filter(
        (w) => w.ownerOrgUnitId && childTeamIds.has(w.ownerOrgUnitId),
      );
      const prefix = u.level === "BU" ? labels.divisionPrefix : labels.teamPrefix;
      return {
        id: u.id,
        label: `${prefix}${u.name}`,
        scopePath: u.slug,
        level: u.level,
        childScopeIds: [
          ...childUnits.map((c) => c.id),
          ...childWorkspaces.map((w) => w.workspaceId),
        ],
        childScopePaths: [
          u.slug,
          u.name,
          `${prefix}${u.name}`,
          ...childUnits.flatMap((c) => [c.slug, c.name]),
          ...childWorkspaces.flatMap((w) => [w.workspaceId, w.name]),
        ],
      };
    }),
    ...workspaces.map((ws): UiActivityScopeFilterOption => {
      const prefix =
        ws.visibilityMode === "PRIVATE_USER"
          ? labels.privateSpacePrefix
          : labels.spacePrefix;
      return {
        id: ws.workspaceId,
        label: `${prefix}${ws.name}`,
        scopePath: ws.name,
        level: "WORKSPACE",
        childScopeIds: [],
        childScopePaths: [ws.workspaceId, ws.name, `${prefix}${ws.name}`],
      };
    }),
  ];
}
