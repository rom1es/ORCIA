import type {
  ControlCenterDatasourceItem,
  ControlCenterRunItem,
  ControlCenterWorkspaceGovItem,
  SubWorkflowLayerViewItem,
  UiCatalogExplorerItemView,
  UiInferenceEffort,
  UiInferenceTier,
  UiOntologyConceptView,
  UiPermissionVerb,
} from "@orcia/ui";
import { ignoreBenignStorageError } from "../utils/benignBrowserError";
import {
  cleanAuditSummaryJargon,
  formatHumanReadableScopePath,
  normalizeConfiguredAuditEvent,
} from "./platformSetupAuditHelpers";

export {
  cleanAuditSummaryJargon,
  formatHumanReadableScopePath,
  normalizeConfiguredAuditEvent,
};

export const PLATFORM_ADMIN_STORAGE_KEY = "orcia.platform_admin.v1";
export const PLATFORM_SETUP_STATE_STORAGE_KEY = "orcia.platform_setup_state.v1";
export const PLATFORM_BOOT_EPOCH_STORAGE_KEY = "orcia.boot_epoch.v1";

const fallbackMemoryStorage = new Map<string, string>();

export function clearPlatformSetupStorage(): void {
  fallbackMemoryStorage.clear();
  const resetHook = (globalThis as Record<string, unknown>).__ORCIA_RESET_VITEST_BACKEND__;
  if (typeof resetHook === "function") resetHook();
  if (typeof window !== "undefined" && window.localStorage && typeof window.localStorage.removeItem === "function") {
    try {
      window.localStorage.removeItem(PLATFORM_ADMIN_STORAGE_KEY);
      window.localStorage.removeItem(PLATFORM_SETUP_STATE_STORAGE_KEY);
      window.localStorage.removeItem(PLATFORM_BOOT_EPOCH_STORAGE_KEY);
      window.localStorage.removeItem("orcia.assistant_saved_conversations.v1");
    } catch (err: unknown) {
      ignoreBenignStorageError("platformSetup.clear", err);
    }
  }
}

export function readStorageItem(key: string): string | null {
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.getItem === "function"
  ) {
    try {
      return window.localStorage.getItem(key);
    } catch (err: unknown) {
      ignoreBenignStorageError("platformSetup.read", err);
    }
  }
  return fallbackMemoryStorage.get(key) ?? null;
}

export function writeStorageItem(key: string, value: string | null): void {
  if (value === null) {
    fallbackMemoryStorage.delete(key);
  } else {
    fallbackMemoryStorage.set(key, value);
  }
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.setItem === "function" &&
    typeof window.localStorage.removeItem === "function"
  ) {
    try {
      if (value === null) {
        window.localStorage.removeItem(key);
      } else {
        window.localStorage.setItem(key, value);
      }
    } catch (err: unknown) {
      ignoreBenignStorageError("platformSetup.write", err);
    }
  }
}

export function syncBrowserBootEpoch(serverBootEpoch: string | null | undefined): boolean {
  const normalized = serverBootEpoch?.trim() ?? "";
  if (!normalized) {
    return false;
  }
  const previous = readStorageItem(PLATFORM_BOOT_EPOCH_STORAGE_KEY);
  if (previous !== null && previous !== normalized) {
    clearPlatformSetupStorage();
    writeStorageItem("orcia.auth.session.v1", null);
    writeStorageItem(PLATFORM_BOOT_EPOCH_STORAGE_KEY, normalized);
    return true;
  }
  writeStorageItem(PLATFORM_BOOT_EPOCH_STORAGE_KEY, normalized);
  return false;
}

export interface AttachedWorkspaceRef {
  readonly id: string;
  readonly slug: string;
  readonly name: string;
}

export interface ConfiguredOrgUnit {
  readonly id: string;
  readonly name: string;
  readonly slug: string;
  readonly level: "BU" | "TEAM";
  readonly parentId: string;
  readonly billingEnabled?: boolean;
  readonly leadUserId?: string | null;
  readonly leadUserIds?: readonly string[];
  readonly ontologyLeadUserIds?: readonly string[];
  readonly memberUserIds?: readonly string[];
  readonly attachedWorkspacesCount?: number;
  readonly attachedWorkspaces?: readonly AttachedWorkspaceRef[];
}

export interface ConfiguredRbacGrant {
  readonly id: string;
  readonly subjectType: "ROLE" | "USER" | "SERVICE_PRINCIPAL";
  readonly subjectId: string;
  readonly scopePath: string;
  readonly verb: UiPermissionVerb;
  readonly effect: "ALLOW" | "DENY" | "INHERITANCE_BLOCK";
  readonly resourceKind?: "ALL" | "WORKFLOW" | "AGENT" | "DATASOURCE" | "CONNECTOR";
}

export type LlmAuthMode = "api_key" | "env_var" | "none_local";

export interface ConfiguredLlmTierMapping {
  readonly tier: UiInferenceTier;
  readonly primaryModel: string;
  readonly secondaryModel: string;
  readonly modelFamily: string;
  readonly defaultEffort: UiInferenceEffort;
  readonly endpointUrl?: string;
  readonly authMode?: LlmAuthMode;
  readonly apiKeyConfigured?: boolean;
}

export interface ConfiguredPackItem {
  readonly packKey: string;
  readonly version: string;
  readonly scopePath: string;
  readonly status: "DRAFT" | "VALIDATED" | "PUBLISHED";
}

export interface ConfiguredWorkflowItem {
  readonly workflowKey: string;
  readonly title: string;
  readonly version: string;
  readonly status: "DRAFT" | "PUBLISHED";
  readonly prePrompt: string;
  readonly prePromptSha256: string;
  readonly requiredParams: readonly string[];
  readonly requiredMarkdownSections: readonly string[];
  readonly triggers: readonly string[];
  readonly layers: readonly SubWorkflowLayerViewItem[];
}

export interface ConfiguredAuditEvent {
  readonly id: string;
  readonly timestampIso: string;
  readonly eventType: string;
  readonly summary: string;
  readonly actorName?: string;
  readonly actorEmail?: string;
  readonly scopeId?: string;
  readonly scopePath?: string;
  readonly scopeLabel?: string;
}

export interface ConfiguredPlatformAdmin {
  readonly displayName: string;
  readonly email: string;
  readonly role: string;
  readonly memberTeamIds?: readonly string[];
}

export interface CachedPlatformSetupState {
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly rbacGrants: readonly ConfiguredRbacGrant[];
  readonly llmTiers: readonly ConfiguredLlmTierMapping[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly packs: readonly ConfiguredPackItem[];
  readonly workflows: readonly ConfiguredWorkflowItem[];
  readonly runs: readonly ControlCenterRunItem[];
  readonly catalogItems: readonly UiCatalogExplorerItemView[];
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly auditEvents: readonly ConfiguredAuditEvent[];
}

export const EMPTY_PLATFORM_SETUP_STATE: CachedPlatformSetupState = {
  orgUnits: [],
  rbacGrants: [],
  llmTiers: [],
  workspaces: [],
  datasources: [],
  packs: [],
  workflows: [],
  runs: [],
  catalogItems: [],
  ontologyConcepts: [],
  auditEvents: [],
};

export function readCachedPlatformAdmin(): ConfiguredPlatformAdmin | null {
  try {
    const raw = readStorageItem(PLATFORM_ADMIN_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<ConfiguredPlatformAdmin>;
    if (
      typeof parsed.displayName === "string" &&
      parsed.displayName.trim().length > 0 &&
      typeof parsed.email === "string" &&
      parsed.email.trim().length > 0
    ) {
      return {
        displayName: parsed.displayName.trim(),
        email: parsed.email.trim(),
        role: parsed.role ?? "PLATFORM_ADMIN",
        memberTeamIds: Array.isArray(parsed.memberTeamIds)
          ? parsed.memberTeamIds.filter((id): id is string => typeof id === "string")
          : [],
      };
    }
  } catch (err: unknown) {
    ignoreBenignStorageError("platformSetup.parseAdmin", err);
    return null;
  }
  return null;
}

export function writeCachedPlatformAdmin(admin: ConfiguredPlatformAdmin | null): void {
  writeStorageItem(PLATFORM_ADMIN_STORAGE_KEY, admin === null ? null : JSON.stringify(admin));
}

export function deduplicateConfiguredPacks(
  items: readonly ConfiguredPackItem[],
): readonly ConfiguredPackItem[] {
  const globalPackKeys = new Set(
    items.filter((p) => p.scopePath === "GLOBAL").map((p) => p.packKey),
  );
  const seen = new Set<string>();
  const result: ConfiguredPackItem[] = [];
  for (const item of items) {
    if (globalPackKeys.has(item.packKey) && item.scopePath !== "GLOBAL") {
      continue;
    }
    const key = `${item.packKey}::${item.scopePath}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    result.push(item);
  }
  return result;
}

export function readCachedPlatformSetupState(): CachedPlatformSetupState {
  try {
    const raw = readStorageItem(PLATFORM_SETUP_STATE_STORAGE_KEY);
    if (!raw) return EMPTY_PLATFORM_SETUP_STATE;
    const parsed = JSON.parse(raw) as Partial<CachedPlatformSetupState>;
    const cachedAdmin = readCachedPlatformAdmin();
    return {
      orgUnits: Array.isArray(parsed.orgUnits) ? parsed.orgUnits : [],
      rbacGrants: Array.isArray(parsed.rbacGrants) ? parsed.rbacGrants : [],
      llmTiers: Array.isArray(parsed.llmTiers) ? parsed.llmTiers : [],
      workspaces: Array.isArray(parsed.workspaces) ? parsed.workspaces : [],
      datasources: Array.isArray(parsed.datasources) ? parsed.datasources : [],
      packs: Array.isArray(parsed.packs) ? deduplicateConfiguredPacks(parsed.packs) : [],
      workflows: Array.isArray(parsed.workflows) ? parsed.workflows : [],
      runs: Array.isArray(parsed.runs) ? parsed.runs : [],
      catalogItems: Array.isArray(parsed.catalogItems) ? parsed.catalogItems : [],
      ontologyConcepts: Array.isArray(parsed.ontologyConcepts) ? parsed.ontologyConcepts : [],
      auditEvents: Array.isArray(parsed.auditEvents)
        ? parsed.auditEvents.map((ev) =>
            normalizeConfiguredAuditEvent(
              ev as Partial<ConfiguredAuditEvent> & Record<string, unknown>,
              cachedAdmin,
            ),
          )
        : [],
    };
  } catch (err: unknown) {
    ignoreBenignStorageError("platformSetup.parseState", err);
    return EMPTY_PLATFORM_SETUP_STATE;
  }
}

export function writeCachedPlatformSetupState(state: CachedPlatformSetupState | null): void {
  writeStorageItem(
    PLATFORM_SETUP_STATE_STORAGE_KEY,
    state === null ? null : JSON.stringify(state),
  );
}
