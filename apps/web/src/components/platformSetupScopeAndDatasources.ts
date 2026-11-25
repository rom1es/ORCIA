import type {
  ControlCenterDatasourceItem,
  ControlCenterWorkspaceGovItem,
  UiScopeNode,
} from "@orcia/ui";
import {
  DICTIONARIES,
  formatI18nTemplate,
  type SupportedWebLocale,
} from "../i18n";
import {
  SHELL_AND_SEARCH_EN_LABELS,
  SHELL_AND_SEARCH_FR_LABELS,
} from "../i18n/locales/shell_and_search_labels";
import {
  formatHumanReadableScopePath,
  type ConfiguredAuditEvent,
  type ConfiguredOrgUnit,
} from "./platformSetupStorageHelpers";

export interface RegisterDatasourceInput {
  readonly workspaceName: string;
  readonly alias: string;
  readonly scheme: "git" | "confluence" | "jira" | "db";
  readonly uri: string;
  readonly executionIdentity: "passthrough" | "service_account";
  readonly freshnessTtlDays: number;
}

export function resolveGlobalScopeLabel(useFrench = true): string {
  const section = useFrench ? SHELL_AND_SEARCH_FR_LABELS : SHELL_AND_SEARCH_EN_LABELS;
  return section.fourZoneShell.doubleSelector?.globalPlatformLabel ?? "ORCIA";
}

export const BASE_GLOBAL_SCOPE: UiScopeNode = {
  id: "scope-global",
  level: "GLOBAL",
  name: resolveGlobalScopeLabel(true),
  accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
};

export function applyRegisterDatasource(params: {
  readonly locale?: SupportedWebLocale;
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
  const { locale = "fr", datasources, input, appendAudit } = params;
  const copy = DICTIONARIES[locale].shellChrome.platformSetupGovernance;
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
      ? copy.personalIdentityLabel
      : copy.sharedServiceAccountLabel;
  const nextAudit = appendAudit(
    "ConnectorConfigured",
    formatI18nTemplate(copy.connectorRegisteredAuditTemplate, {
      alias: input.alias,
      uri: input.uri,
      identityLabel,
    }),
    {
      scopePath: input.workspaceName,
      scopeLabel: formatHumanReadableScopePath(input.workspaceName, locale),
    },
  );
  return { nextDatasources, nextAudit };
}

export function buildScopeNodes(
  orgUnits: readonly ConfiguredOrgUnit[],
  workspaces: readonly ControlCenterWorkspaceGovItem[],
  locale: SupportedWebLocale = "fr",
): readonly UiScopeNode[] {
  const globalLabel =
    DICTIONARIES[locale].fourZoneShell.doubleSelector?.globalPlatformLabel ??
    BASE_GLOBAL_SCOPE.name;
  const globalScope: UiScopeNode = { ...BASE_GLOBAL_SCOPE, name: globalLabel };
  return [
    globalScope,
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
