import type {
  ControlCenterWorkspaceGovItem,
  OrciaIconName,
} from "@orcia/ui";
import { resolveDictionaryForFlag, resolveLocaleForFlag } from "../../i18n";

const RAW_UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const PERSONAL_UUID_SLUG_RE =
  /^personal-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isTechnicalWorkspaceSlug(
  rawSlug: string | undefined | null,
): boolean {
  const trimmed = (rawSlug ?? "").trim();
  if (!trimmed) return true;
  return PERSONAL_UUID_SLUG_RE.test(trimmed) || RAW_UUID_RE.test(trimmed);
}

export function toKebabWorkspaceSlug(name: string): string {
  const ascii = name
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return ascii.length > 0 ? ascii : "ws";
}

export function formatWorkspaceDisplaySlug(
  ws: Pick<ControlCenterWorkspaceGovItem, "name" | "slug">,
): string {
  const candidate = (ws.slug ?? "").trim();
  if (candidate && !isTechnicalWorkspaceSlug(candidate)) {
    return candidate;
  }
  return toKebabWorkspaceSlug(ws.name);
}

export function formatWorkspaceCreatedBannerId(
  ws: Pick<ControlCenterWorkspaceGovItem, "name" | "slug">,
): string {
  return formatWorkspaceDisplaySlug(ws);
}

export function sanitizeWorkspaceDestinationUri(
  uri: string,
  fallbackWorkspaceName: string,
): string {
  return uri.replace(
    /personal-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi,
    toKebabWorkspaceSlug(fallbackWorkspaceName),
  );
}

export function resolveWorkspaceVisibilityMeta(
  mode: string | undefined,
  isFr: boolean,
): {
  readonly iconName: OrciaIconName;
  readonly shortLabel: string;
  readonly fullLabel: string;
} {
  const locale = resolveLocaleForFlag(isFr);
  const sumCopy = resolveDictionaryForFlag(isFr, locale).featureWorkspaces.summaryCard;
  switch (mode) {
    case "PRIVATE_USER":
      return {
        iconName: "lock",
        shortLabel: sumCopy.visibilityShortPrivate,
        fullLabel: sumCopy.visibilityPrivate,
      };
    case "CONFIDENTIAL_RESTRICTED":
      return {
        iconName: "shield",
        shortLabel: sumCopy.visibilityShortConfidential,
        fullLabel: sumCopy.visibilityConfidential,
      };
    default:
      return {
        iconName: "team",
        shortLabel: sumCopy.visibilityShortStandard,
        fullLabel: sumCopy.visibilityStandard,
      };
  }
}

export function resolveWorkspacePhaseLabel(
  phase: string | undefined,
  isFr: boolean,
): string {
  const locale = resolveLocaleForFlag(isFr);
  const dnaCopy = resolveDictionaryForFlag(isFr, locale).featureWorkspaces.dnaAndWaivers;
  switch (phase) {
    case "RUN":
      return dnaCopy.phaseOperations;
    case "MIGRATION":
      return dnaCopy.phaseEvolution;
    default:
      return dnaCopy.phaseBuild;
  }
}
