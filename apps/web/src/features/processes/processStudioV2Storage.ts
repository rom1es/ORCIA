import type { SupportedWebLocale } from "../../i18n";
import { getInitialWorkflowsV2 } from "./processStudioV2StructuralWorkflows";
import type { WorkflowDefinitionV2Item } from "./processStudioV2Types";

const WORKFLOWS_STORAGE_KEY = "orcia.processStudioV2.workflows.v1";
let memoryFallbackWorkflows: WorkflowDefinitionV2Item[] | null = null;

export function resetPersistedWorkflowsV2(): void {
  memoryFallbackWorkflows = null;
  if (typeof window !== "undefined" && typeof window.localStorage?.removeItem === "function") {
    window.localStorage.removeItem(WORKFLOWS_STORAGE_KEY);
  }
}

export function loadPersistedWorkflowsV2(
  locale: SupportedWebLocale = "fr",
): WorkflowDefinitionV2Item[] {
  if (typeof window !== "undefined" && typeof window.localStorage?.getItem === "function") {
    try {
      const raw = window.localStorage.getItem(WORKFLOWS_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as WorkflowDefinitionV2Item[];
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch (err: unknown) {
      if (typeof console !== "undefined") {
        console.debug(
          "[orcia:workflowsV2.load]",
          err instanceof Error ? err.message : String(err),
        );
      }
    }
  }
  return memoryFallbackWorkflows ?? getInitialWorkflowsV2(locale);
}

export function savePersistedWorkflowV2(
  updated: WorkflowDefinitionV2Item,
): WorkflowDefinitionV2Item[] {
  const current = loadPersistedWorkflowsV2();
  const idx = current.findIndex((w) => w.id === updated.id || w.slug === updated.slug);
  const next =
    idx >= 0
      ? current.map((w, i) => (i === idx ? updated : w))
      : [...current, updated];
  memoryFallbackWorkflows = next;
  if (typeof window !== "undefined" && typeof window.localStorage?.setItem === "function") {
    try {
      window.localStorage.setItem(WORKFLOWS_STORAGE_KEY, JSON.stringify(next));
    } catch (err: unknown) {
      if (typeof console !== "undefined") {
        console.debug(
          "[orcia:workflowsV2.save]",
          err instanceof Error ? err.message : String(err),
        );
      }
    }
  }
  return next;
}
