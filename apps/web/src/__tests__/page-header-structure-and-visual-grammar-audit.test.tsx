// @vitest-environment jsdom
import fs from "node:fs";
import path from "node:path";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import { clearSavedActiveScopeId } from "../components/useShellContainerState";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const BU_ID = "0195f297-0000-7000-8000-000000000001";
const TEAM_ID = "0195f297-0000-7000-8000-000000000002";
const WS_ID = "0195f297-0000-7000-8000-000000000003";

const RAW_UNICODE_EMOJI_RE = /[\u{1F300}-\u{1FAFF}\u26A0\u2705\u274C\u2728\u26A1\u2B50\uFE0F]/u;
const FORBIDDEN_HEADER_EMOJI_RE = /[\u{1F916}\u{1F6E0}\u{1F50C}\u{1F512}\u{1F4C1}\u{1F4E6}\u{1F9ED}\u{1F9E0}\u{1F4DA}]/u;
const RAW_HEX_COLOR_RE = /#[0-9a-fA-F]{3,8}\b/;

function collectSourceFiles(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  const files: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...collectSourceFiles(full));
    } else if (entry.isFile() && !entry.name.includes(".test.") && /\.(ts|tsx)$/.test(entry.name)) {
      files.push(full);
    }
  }
  return files;
}

function stripCommentsAndSanitizerRegexes(source: string): string {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "")
    .replace(/\/\^\\s\*\\\[\(\?:[^\n]+\//g, "");
}

const AUDITED_ROUTES: readonly string[] = [
  "/cockpit",
  "/assistant",
  "/processes",
  "/agents",
  "/spaces",
  "/organization",
  "/finops",
  "/help",
  "/settings",
  "/settings/packs",
  "/profile",
  "/activity",
];

const ZONE4_PRIMARY_ROUTES = new Set([
  "/cockpit",
  "/assistant",
  "/processes",
  "/agents",
  "/spaces",
  "/organization",
  "/finops",
]);

function seedAuditWorkspaceState(): void {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: BU_ID,
          name: "Division Operations",
          slug: "div-ops",
          kind: "BU",
          level: "BU",
          parentId: null,
          billingEnabled: true,
        },
        {
          id: TEAM_ID,
          name: "Core Platform Team",
          slug: "team-core",
          kind: "TEAM",
          level: "TEAM",
          parentId: BU_ID,
          billingEnabled: true,
        },
      ],
      workspaces: [
        {
          workspaceId: WS_ID,
          slug: "core-space-297",
          name: "Core Space 29.7",
          ownerOrgUnitId: TEAM_ID,
          ownerOrgUnitName: "Core Platform Team",
          visibilityMode: "STANDARD",
          lifecyclePhase: "RUN",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
      llm_tiers: [
        {
          id: "llm-297",
          provider: "openai",
          model_id: "gpt-4o-mini",
          tier: "standard",
          enabled: true,
        },
      ],
    },
    { email: "admin297@orcia.test", displayName: "Admin 297", roles: ["PLATFORM_ADMIN"] },
  );

  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "mock-token-297", // pragma: allowlist secret
    email: "admin297@orcia.test",
    displayName: "Admin 297",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "ARCHITECT",
    readOnlyObserver: false,
  });
}

async function mountAuditedRoute(path: string, locale: "fr" | "en"): Promise<void> {
  seedAuditWorkspaceState();
  const origFetch = globalThis.fetch;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = typeof input === "string" ? input : (input as Request).url;
    if (url.includes("/api/v1/users/me/preferences") && (!init?.method || init.method === "GET")) {
      return new Response(
        JSON.stringify({
          theme: "light",
          locale,
          default_assistant_hat: "ARCHITECT",
          auto_open_contextual_help: false,
          notifications_enabled: true,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    return origFetch(input, init);
  });

  const qc = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [path] });
  const router = createOrciaRouter({ queryClient: qc, history });
  await router.load();
  render(
    <I18nProvider initialLocale={locale}>
      <QueryClientProvider client={qc}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </I18nProvider>,
  );
}

beforeEach(() => {
  resetVitestApiBackend();
  clearPlatformSetupStorage();
  clearSavedActiveScopeId();
});

afterEach(() => {
  vi.restoreAllMocks();
  cleanup();
  resetAuthSessionStore();
});

describe("Story 29.7 — Page Header Structure, Monochrome Icons & Zone 4 Visual Grammar CI Guard", () => {
  for (const locale of ["fr", "en"] as const) {
    it.each(AUDITED_ROUTES)(
      `enforces canonical OrciaPageHeader, single h1, <=1 Cobalt header CTA, zero emojis, and Zone 4 order on %s (${locale})`,
      async (routePath) => {
        await mountAuditedRoute(routePath, locale);

        const workspace = await screen.findByTestId("four-zone-central-workspace");
        await waitFor(() => {
          expect(workspace.querySelectorAll("header.orcia-ds-page-header").length).toBe(1);
        });

        const header = workspace.querySelector("header.orcia-ds-page-header") as HTMLElement;
        expect(workspace.querySelectorAll("h1").length).toBe(1);
        expect(header.querySelectorAll(".orcia-ds-btn-primary").length).toBeLessThanOrEqual(1);
        const legacyStrongHeaders = Array.from(header.querySelectorAll("strong")).filter(
          (el) => el.style.fontSize === "16px",
        );
        expect(legacyStrongHeaders).toEqual([]);

        expect(header.textContent ?? "").not.toMatch(RAW_UNICODE_EMOJI_RE);

        const tabStrips = workspace.querySelectorAll(".orcia-ds-tab-strip");
        for (const strip of tabStrips) {
          expect(strip.textContent ?? "").not.toMatch(RAW_UNICODE_EMOJI_RE);
        }

        const primaryBtns = workspace.querySelectorAll(".orcia-ds-btn-primary");
        for (const btn of primaryBtns) {
          expect(btn.textContent ?? "").not.toMatch(RAW_UNICODE_EMOJI_RE);
        }

        const sidebar = screen.getByTestId("four-zone-sidebar");
        expect(sidebar.textContent ?? "").not.toMatch(RAW_UNICODE_EMOJI_RE);

        if (ZONE4_PRIMARY_ROUTES.has(routePath)) {
          if (!screen.queryByTestId("four-zone-contextual-help-column")) {
            fireEvent.click(screen.getByTestId("topbar-contextual-help-toggle"));
          }
          const helpCol = await screen.findByTestId("four-zone-contextual-help-column");
          const whatForBox = await screen.findByTestId("contextual-help-what-for-box");
          const stepsBox = await screen.findByTestId("contextual-help-steps-box");
          expect(
            Boolean(whatForBox.compareDocumentPosition(stepsBox) & Node.DOCUMENT_POSITION_FOLLOWING),
          ).toBe(true);

          const sectionsList = helpCol.querySelector('[data-testid="contextual-help-sections-list"]');
          if (sectionsList) {
            expect(
              Boolean(
                stepsBox.compareDocumentPosition(sectionsList) & Node.DOCUMENT_POSITION_FOLLOWING,
              ),
            ).toBe(true);
          }

          if (routePath === "/organization") {
            expect(screen.queryByTestId("help-section-iam-org-tree")).toBeNull();
            expect(screen.getByTestId("help-section-org-hierarchy")).toBeDefined();
          }
        } else if (routePath === "/help") {
          expect(screen.queryByTestId("four-zone-contextual-help-column")).toBeNull();
          const helpToggle = screen.getByTestId("topbar-contextual-help-toggle") as HTMLButtonElement;
          expect(helpToggle.disabled).toBe(true);
          expect(helpToggle.getAttribute("aria-current")).toBe("page");
        }
      },
    );
  }

  it("enforces zero forbidden emojis and zero raw hex colors outside tokens CSS across locales, UI primitives, and features", () => {
    const targetDirs = [
      path.join(REPO_ROOT, "apps/web/src/i18n/locales"),
      path.join(REPO_ROOT, "packages/ui/src/primitives"),
      path.join(REPO_ROOT, "apps/web/src/features"),
    ];
    const emojiViolations: string[] = [];
    const hexViolations: string[] = [];

    for (const dir of targetDirs) {
      for (const filePath of collectSourceFiles(dir)) {
        const raw = fs.readFileSync(filePath, "utf8");
        const sanitized = stripCommentsAndSanitizerRegexes(raw);
        const rel = path.relative(REPO_ROOT, filePath);
        sanitized.split("\n").forEach((line, idx) => {
          if (FORBIDDEN_HEADER_EMOJI_RE.test(line)) {
            emojiViolations.push(`${rel}:${idx + 1} -> ${line.trim().slice(0, 80)}`);
          }
          if (RAW_HEX_COLOR_RE.test(line)) {
            hexViolations.push(`${rel}:${idx + 1} -> ${line.trim().slice(0, 80)}`);
          }
        });
      }
    }

    expect(emojiViolations).toEqual([]);
    expect(hexViolations).toEqual([]);
  });
});
