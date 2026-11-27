import { type UiModuleKey } from "@orcia/ui";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import React from "react";
import { expect, vi } from "vitest";
import { clearPlatformSetupStorage } from "../../components/platformSetupStore";
import { ShellContainer } from "../../components/ShellContainer";
import { ModuleWorkspaceView } from "../../components/ModuleWorkspaceView";
import { resetBackgroundAssistantStreamForTests } from "../../features/inbox/useAssistantStreamingTurn";
import { I18nProvider } from "../../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../../router";

export const mockShellPush = vi.fn();

export function resetShellTestState(): void {
  clearPlatformSetupStorage();
  resetBackgroundAssistantStreamForTests();
  delete (globalThis as Record<string, unknown>).__ORCIA_TEST_KEEP_STREAM_PENDING__;
}

export async function renderOrciaRoute(initialEntry: string) {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [initialEntry] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...view, queryClient, router };
}

export function renderShellModule(
  moduleKey: UiModuleKey,
  locale: "fr" | "en" = "fr",
  customChild?: React.ReactNode,
) {
  return render(
    <I18nProvider initialLocale={locale}>
      <ShellContainer onNavigate={mockShellPush}>
        {customChild ?? <ModuleWorkspaceView moduleKey={moduleKey} />}
      </ShellContainer>
    </I18nProvider>,
  );
}

export async function completeFirstBootAdminModal(params?: {
  readonly name?: string;
  readonly email?: string;
  readonly password?: string;
}): Promise<void> {
  fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), {
    target: { value: params?.name ?? "Romain Admin" },
  });
  fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), {
    target: { value: params?.email ?? "romain@orcia.fr" },
  });
  if (params?.password !== undefined) {
    fireEvent.change(screen.getByTestId("first-boot-admin-password-input"), {
      target: { value: params.password },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-password-confirm-input"), {
      target: { value: params.password },
    });
  }
  fireEvent.click(screen.getByTestId("first-boot-admin-submit-btn"));
  await waitFor(() => {
    expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
  });
}

export async function createOrgUnitViaModal(params: {
  readonly name: string;
  readonly level?: "BU" | "TEAM";
  readonly slug?: string;
  readonly expectedRowTestId?: string;
}): Promise<void> {
  await screen.findByTestId("open-create-org-unit-modal-btn");
  fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
  if (params.level) {
    fireEvent.change(screen.getByTestId("org-unit-level-select"), {
      target: { value: params.level },
    });
  }
  fireEvent.change(screen.getByTestId("org-unit-name-input"), {
    target: { value: params.name },
  });
  if (params.slug) {
    fireEvent.change(screen.getByTestId("org-unit-slug-input"), {
      target: { value: params.slug },
    });
  }
  fireEvent.click(screen.getByTestId("create-org-unit-btn"));
  if (params.expectedRowTestId) {
    await screen.findByTestId(params.expectedRowTestId);
  }
}

export async function createWorkspaceViaModal(params: {
  readonly name: string;
  readonly visibility?: "STANDARD" | "PRIVATE_USER";
  readonly ownerTeamId?: string;
}): Promise<void> {
  fireEvent.click(screen.getByTestId("toggle-create-workspace-form-btn"));
  if (params.ownerTeamId) {
    fireEvent.change(screen.getByTestId("workspace-owner-team-select"), {
      target: { value: params.ownerTeamId },
    });
  }
  if (params.visibility) {
    fireEvent.change(screen.getByTestId("workspace-visibility-select"), {
      target: { value: params.visibility },
    });
  }
  fireEvent.change(screen.getByTestId("workspace-name-input"), {
    target: { value: params.name },
  });
  fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));
}

export function ensureZone4HelpOpen(): void {
  if (!screen.queryByTestId("four-zone-contextual-help-column")) {
    fireEvent.click(screen.getByTestId("topbar-contextual-help-toggle"));
  }
}

export function walkTsFiles(dir: string): string[] {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== "__tests__") files.push(...walkTsFiles(fullPath));
    } else if (entry.isFile() && /\.(ts|tsx)$/.test(entry.name)) {
      files.push(fullPath);
    }
  }
  return files;
}

export function extractOpeningTags(source: string, tagName: "input" | "textarea" | "form"): string[] {
  const results: string[] = [];
  const regex = new RegExp(`<${tagName}\\b`, "g");
  let match: RegExpExecArray | null = null;
  while ((match = regex.exec(source)) !== null) {
    const startIdx = match.index;
    let idx = startIdx + match[0].length;
    let braceDepth = 0;
    let inSingleQuote = false;
    let inDoubleQuote = false;
    let inTemplate = false;
    while (idx < source.length) {
      const ch = source[idx];
      const prev = source[idx - 1];
      if (inSingleQuote) {
        if (ch === "'" && prev !== "\\") inSingleQuote = false;
      } else if (inDoubleQuote) {
        if (ch === '"' && prev !== "\\") inDoubleQuote = false;
      } else if (inTemplate) {
        if (ch === "`" && prev !== "\\") inTemplate = false;
      } else if (ch === "'") inSingleQuote = true;
      else if (ch === '"') inDoubleQuote = true;
      else if (ch === "`") inTemplate = true;
      else if (ch === "{") braceDepth++;
      else if (ch === "}") braceDepth = Math.max(0, braceDepth - 1);
      else if (ch === ">" && braceDepth === 0) {
        idx++;
        break;
      }
      idx++;
    }
    results.push(source.slice(startIdx, idx));
  }
  return results;
}
