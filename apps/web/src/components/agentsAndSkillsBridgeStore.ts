import type { UiManagedAgentItem, UiManagedSkillItem } from "@orcia/ui";

export const AGENTS_AND_SKILLS_STORAGE_KEY = "orcia.agents_and_skills.v1";
export const ASSISTANT_PREFILL_PROMPT_STORAGE_KEY =
  "orcia.assistant_prefill_prompt.v1";

export interface CachedAgentsAndSkillsState {
  readonly agents: readonly UiManagedAgentItem[];
  readonly skills: readonly UiManagedSkillItem[];
}

let fallbackMemoryState: CachedAgentsAndSkillsState = {
  agents: [],
  skills: [],
};
let fallbackPrefillPrompt: string | null = null;

export function resetCachedAgentsAndSkillsForTest(): void {
  fallbackMemoryState = { agents: [], skills: [] };
  fallbackPrefillPrompt = null;
  if (typeof window !== "undefined") {
    try {
      window.localStorage?.removeItem?.(AGENTS_AND_SKILLS_STORAGE_KEY);
      window.localStorage?.removeItem?.(ASSISTANT_PREFILL_PROMPT_STORAGE_KEY);
      window.sessionStorage?.removeItem?.(ASSISTANT_PREFILL_PROMPT_STORAGE_KEY);
    } catch {
      // Ignore storage errors
    }
  }
}

export function readCachedAgentsAndSkills(): CachedAgentsAndSkillsState {
  if (
    typeof window === "undefined" ||
    !window.localStorage ||
    typeof window.localStorage.getItem !== "function"
  ) {
    return fallbackMemoryState;
  }
  try {
    const raw = window.localStorage.getItem(AGENTS_AND_SKILLS_STORAGE_KEY);
    if (!raw) return fallbackMemoryState;
    const parsed = JSON.parse(raw) as Partial<CachedAgentsAndSkillsState>;
    const hydrated: CachedAgentsAndSkillsState = {
      agents: Array.isArray(parsed.agents) ? parsed.agents : [],
      skills: Array.isArray(parsed.skills) ? parsed.skills : [],
    };
    fallbackMemoryState = hydrated;
    return hydrated;
  } catch {
    return fallbackMemoryState;
  }
}

export function writeCachedAgentsAndSkills(
  state: CachedAgentsAndSkillsState,
): void {
  fallbackMemoryState = state;
  if (
    typeof window === "undefined" ||
    !window.localStorage ||
    typeof window.localStorage.setItem !== "function"
  ) {
    return;
  }
  try {
    window.localStorage.setItem(
      AGENTS_AND_SKILLS_STORAGE_KEY,
      JSON.stringify(state),
    );
  } catch {
    // Ignore storage errors
  }
}

export function writeAssistantPrefillPrompt(prefill: string): void {
  fallbackPrefillPrompt = prefill;
  if (typeof window !== "undefined") {
    try {
      window.localStorage?.setItem?.(
        ASSISTANT_PREFILL_PROMPT_STORAGE_KEY,
        prefill,
      );
      window.sessionStorage?.setItem?.(
        ASSISTANT_PREFILL_PROMPT_STORAGE_KEY,
        prefill,
      );
    } catch {
      // Ignore storage errors
    }
  }
}

export function consumeAssistantPrefillPrompt(): string | null {
  let found = fallbackPrefillPrompt;
  fallbackPrefillPrompt = null;
  if (typeof window !== "undefined") {
    try {
      const fromSession = window.sessionStorage?.getItem?.(
        ASSISTANT_PREFILL_PROMPT_STORAGE_KEY,
      );
      const fromLocal = window.localStorage?.getItem?.(
        ASSISTANT_PREFILL_PROMPT_STORAGE_KEY,
      );
      if (fromSession) {
        found = fromSession;
      } else if (fromLocal) {
        found = fromLocal;
      }
      window.sessionStorage?.removeItem?.(ASSISTANT_PREFILL_PROMPT_STORAGE_KEY);
      window.localStorage?.removeItem?.(ASSISTANT_PREFILL_PROMPT_STORAGE_KEY);
    } catch {
      // Ignore storage errors
    }
  }
  return found;
}
