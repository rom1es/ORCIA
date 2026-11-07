import type {
  UiAssistantFolderItem,
  UiAssistantPromptTelemetryRecord,
  UiAssistantResponseFormat,
  UiAssistantResponseTone,
} from "@orcia/ui";

export const SAVED_ASSISTANT_FOLDERS_STORAGE_KEY =
  "orcia.assistant_saved_folders.v1";
export const SAVED_ASSISTANT_ACTIVE_FOLDER_ID_STORAGE_KEY =
  "orcia.assistant_active_folder_id.v1";
export const SAVED_ASSISTANT_GOVERNANCE_PREFS_STORAGE_KEY =
  "orcia.assistant_governance_prefs.v1";
export const SAVED_ASSISTANT_ACTIVE_CONVERSATION_ID_STORAGE_KEY =
  "orcia.assistant.active_conversation_id.v1";
export const SAVED_ASSISTANT_PROMPT_TELEMETRY_LOG_STORAGE_KEY =
  "orcia.assistant.prompt_telemetry_log.v1";

const fallbackStore = new Map<string, string>();

export interface SavedAssistantGovernancePrefs {
  readonly responseTone: UiAssistantResponseTone;
  readonly favoriteFormat: UiAssistantResponseFormat;
  readonly defaultHat: string;
  readonly personalInstructions: string;
  readonly workspaceInstructions: string;
  readonly mcpExposeAssistant: boolean;
}

export const DEFAULT_ASSISTANT_GOVERNANCE_PREFS: SavedAssistantGovernancePrefs = {
  responseTone: "BALANCED",
  favoriteFormat: "STRUCTURED_SECTIONS",
  defaultHat: "PM",
  personalInstructions:
    "Privilégier des réponses claires, citer les documents utilisés et mettre en évidence les points d'attention.",
  workspaceInstructions:
    "Respecter le vocabulaire métier de l'équipe et s'appuyer en priorité sur les documents de référence de l'espace.",
  mcpExposeAssistant: true,
};

function readRawKey(key: string): string | null {
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.getItem === "function"
  ) {
    try {
      const val = window.localStorage.getItem(key);
      if (val !== null) return val;
    } catch {
      // Fall back to in-memory map
    }
  }
  return fallbackStore.get(key) ?? null;
}

function writeRawKey(key: string, value: string): void {
  fallbackStore.set(key, value);
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.setItem === "function"
  ) {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      // Ignore quota errors
    }
  }
}

export function clearAssistantFoldersAndPrefsStorage(): void {
  fallbackStore.clear();
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.removeItem === "function"
  ) {
    try {
      window.localStorage.removeItem(SAVED_ASSISTANT_FOLDERS_STORAGE_KEY);
      window.localStorage.removeItem(SAVED_ASSISTANT_ACTIVE_FOLDER_ID_STORAGE_KEY);
      window.localStorage.removeItem(SAVED_ASSISTANT_GOVERNANCE_PREFS_STORAGE_KEY);
      window.localStorage.removeItem(SAVED_ASSISTANT_ACTIVE_CONVERSATION_ID_STORAGE_KEY);
      window.localStorage.removeItem(SAVED_ASSISTANT_PROMPT_TELEMETRY_LOG_STORAGE_KEY);
    } catch {
      // Ignore storage errors
    }
  }
}

export function readSavedAssistantFolders(): readonly UiAssistantFolderItem[] {
  const raw = readRawKey(SAVED_ASSISTANT_FOLDERS_STORAGE_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (item): item is UiAssistantFolderItem =>
        typeof item === "object" &&
        item !== null &&
        typeof (item as UiAssistantFolderItem).folderId === "string" &&
        typeof (item as UiAssistantFolderItem).title === "string",
    );
  } catch {
    return [];
  }
}

export function writeSavedAssistantFolders(
  folders: readonly UiAssistantFolderItem[],
): void {
  writeRawKey(SAVED_ASSISTANT_FOLDERS_STORAGE_KEY, JSON.stringify(folders));
}

export function readSavedActiveFolderId(): string {
  return readRawKey(SAVED_ASSISTANT_ACTIVE_FOLDER_ID_STORAGE_KEY) ?? "";
}

export function writeSavedActiveFolderId(folderId: string): void {
  writeRawKey(SAVED_ASSISTANT_ACTIVE_FOLDER_ID_STORAGE_KEY, folderId);
}

export function readSavedActiveConversationId(): string | null {
  const val = readRawKey(SAVED_ASSISTANT_ACTIVE_CONVERSATION_ID_STORAGE_KEY);
  return val && val.trim() ? val.trim() : null;
}

export function writeSavedActiveConversationId(conversationId: string | null): void {
  writeRawKey(SAVED_ASSISTANT_ACTIVE_CONVERSATION_ID_STORAGE_KEY, conversationId ?? "");
}

export function readSavedPromptTelemetryLog(): readonly UiAssistantPromptTelemetryRecord[] {
  const raw = readRawKey(SAVED_ASSISTANT_PROMPT_TELEMETRY_LOG_STORAGE_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (item): item is UiAssistantPromptTelemetryRecord =>
        typeof item === "object" &&
        item !== null &&
        typeof (item as UiAssistantPromptTelemetryRecord).turnId === "string" &&
        typeof (item as UiAssistantPromptTelemetryRecord).userPrompt === "string",
    );
  } catch {
    return [];
  }
}

export function writeSavedPromptTelemetryLog(
  records: readonly UiAssistantPromptTelemetryRecord[],
): void {
  writeRawKey(SAVED_ASSISTANT_PROMPT_TELEMETRY_LOG_STORAGE_KEY, JSON.stringify(records));
}

export function upsertSavedPromptTelemetryRecord(
  record: UiAssistantPromptTelemetryRecord,
): readonly UiAssistantPromptTelemetryRecord[] {
  const current = readSavedPromptTelemetryLog();
  const idx = current.findIndex((r) => r.turnId === record.turnId);
  const next =
    idx >= 0
      ? current.map((r, i) => (i === idx ? { ...r, ...record } : r))
      : [record, ...current].slice(0, 100);
  writeSavedPromptTelemetryLog(next);
  return next;
}

export function updatePromptTelemetryFeedback(
  turnId: string,
  feedback: "LIKE" | "DISLIKE" | null,
): readonly UiAssistantPromptTelemetryRecord[] {
  const current = readSavedPromptTelemetryLog();
  const next = current.map((r) =>
    r.turnId === turnId ? { ...r, userFeedback: feedback } : r,
  );
  writeSavedPromptTelemetryLog(next);
  return next;
}

export function readSavedAssistantGovernancePrefs(): SavedAssistantGovernancePrefs {
  const raw = readRawKey(SAVED_ASSISTANT_GOVERNANCE_PREFS_STORAGE_KEY);
  if (!raw) return DEFAULT_ASSISTANT_GOVERNANCE_PREFS;
  try {
    const parsed = JSON.parse(raw) as Partial<SavedAssistantGovernancePrefs>;
    return {
      responseTone:
        parsed.responseTone === "SYNTHETIC" ||
        parsed.responseTone === "BALANCED" ||
        parsed.responseTone === "DETAILED_CODE"
          ? parsed.responseTone
          : DEFAULT_ASSISTANT_GOVERNANCE_PREFS.responseTone,
      favoriteFormat:
        parsed.favoriteFormat === "BULLETS_SUMMARY" ||
        parsed.favoriteFormat === "STRUCTURED_SECTIONS" ||
        parsed.favoriteFormat === "STEP_BY_STEP"
          ? parsed.favoriteFormat
          : DEFAULT_ASSISTANT_GOVERNANCE_PREFS.favoriteFormat,
      defaultHat:
        typeof parsed.defaultHat === "string" && parsed.defaultHat.trim()
          ? parsed.defaultHat.trim()
          : DEFAULT_ASSISTANT_GOVERNANCE_PREFS.defaultHat,
      personalInstructions:
        typeof parsed.personalInstructions === "string"
          ? parsed.personalInstructions
          : DEFAULT_ASSISTANT_GOVERNANCE_PREFS.personalInstructions,
      workspaceInstructions:
        typeof parsed.workspaceInstructions === "string"
          ? parsed.workspaceInstructions
          : DEFAULT_ASSISTANT_GOVERNANCE_PREFS.workspaceInstructions,
      mcpExposeAssistant:
        typeof parsed.mcpExposeAssistant === "boolean"
          ? parsed.mcpExposeAssistant
          : DEFAULT_ASSISTANT_GOVERNANCE_PREFS.mcpExposeAssistant,
    };
  } catch {
    return DEFAULT_ASSISTANT_GOVERNANCE_PREFS;
  }
}

export function writeSavedAssistantGovernancePrefs(
  prefs: SavedAssistantGovernancePrefs,
): void {
  writeRawKey(SAVED_ASSISTANT_GOVERNANCE_PREFS_STORAGE_KEY, JSON.stringify(prefs));
}
