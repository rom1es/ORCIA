import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const WEB_SRC_DIR = path.join(REPO_ROOT, "apps/web/src");
const UI_SRC_DIR = path.join(REPO_ROOT, "packages/ui/src");

/**
 * Non-panel atomic UI sub-controls in `@orcia/ui` where `display: "none"` is used
 * strictly for native `<input type="file">`, collapsible reasoning accordions, or
 * internal legacy element deduplication flags (never business panels).
 */
const UI_NON_PANEL_DISPLAY_NONE_ALLOWLIST = new Set<string>([
  "packages/ui/src/primitives/AssistantPromptPlusAndAutocomplete.tsx",
  "packages/ui/src/primitives/AssistantThinkingSubWindow.tsx",
  "packages/ui/src/primitives/AssistantActiveStreamContent.tsx",
  "packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx",
  "packages/ui/src/primitives/AssistantModelAndEffortPopover.tsx",
  "packages/ui/src/primitives/AssistantGovernanceModeATabs.tsx",
  "packages/ui/src/primitives/AssistantFoldersAndCollaborativeThreadView.tsx",
]);

function collectTsFiles(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  const results: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (
      entry.name === "node_modules" ||
      entry.name === "dist" ||
      entry.name === "__tests__" ||
      entry.name === "generated"
    ) {
      continue;
    }
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...collectTsFiles(full));
    } else if (
      entry.isFile() &&
      !entry.name.includes(".test.") &&
      (entry.name.endsWith(".ts") || entry.name.endsWith(".tsx"))
    ) {
      results.push(full);
    }
  }
  return results;
}

describe("CI Guardrail — Zero Hidden Legacy Panels & 100% Portaled Dialogs", () => {
  it("forbids display: none in all apps/web/src modules and on all business panels in packages/ui/src", () => {
    const displayNoneRegex = /display\s*:\s*["']none["']/;
    const webViolations: string[] = [];

    for (const filePath of collectTsFiles(WEB_SRC_DIR)) {
      const content = fs.readFileSync(filePath, "utf8");
      const lines = content.split("\n");
      const rel = path.relative(REPO_ROOT, filePath);
      lines.forEach((line, idx) => {
        if (displayNoneRegex.test(line)) {
          webViolations.push(`${rel}:${idx + 1} -> ${line.trim()}`);
        }
      });
    }

    const uiPanelViolations: string[] = [];
    for (const filePath of collectTsFiles(UI_SRC_DIR)) {
      const rel = path.relative(REPO_ROOT, filePath);
      if (UI_NON_PANEL_DISPLAY_NONE_ALLOWLIST.has(rel)) continue;
      const content = fs.readFileSync(filePath, "utf8");
      const lines = content.split("\n");
      lines.forEach((line, idx) => {
        if (displayNoneRegex.test(line)) {
          uiPanelViolations.push(`${rel}:${idx + 1} -> ${line.trim()}`);
        }
      });
    }

    expect(webViolations).toEqual([]);
    expect(uiPanelViolations).toEqual([]);
  });

  it("ensures 100% of role='dialog' modals in packages/ui/src/primitives and apps/web/src are portaled via OrciaDialog or DialogPrimitive.Portal", () => {
    const candidateFiles = [
      ...collectTsFiles(path.join(UI_SRC_DIR, "primitives")),
      ...collectTsFiles(WEB_SRC_DIR),
    ];

    const unportaledDialogs: string[] = [];
    for (const filePath of candidateFiles) {
      const content = fs.readFileSync(filePath, "utf8");
      const rel = path.relative(REPO_ROOT, filePath);
      const hasRawRoleDialog = /role\s*=\s*["']dialog["']/.test(content);
      const hasDialogContent = content.includes("DialogPrimitive.Content");
      const usesPortal =
        content.includes("DialogPrimitive.Portal") || content.includes("OrciaDialog");

      if (hasRawRoleDialog && !usesPortal) {
        unportaledDialogs.push(`${rel} declares inline role="dialog" without OrciaDialog/DialogPrimitive.Portal`);
      }
      if (hasDialogContent && !usesPortal) {
        unportaledDialogs.push(`${rel} uses DialogPrimitive.Content without DialogPrimitive.Portal`);
      }
    }

    expect(unportaledDialogs).toEqual([]);
  });
});
