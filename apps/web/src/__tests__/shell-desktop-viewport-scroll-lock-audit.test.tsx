// @vitest-environment jsdom
import {
  FourZoneDirectionCShell,
  type FourZoneDirectionCShellLabels,
} from "@orcia/ui";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const STYLES_DIR = path.join(REPO_ROOT, "packages/ui/src/styles");
const PRIMITIVES_DIR = path.join(REPO_ROOT, "packages/ui/src/primitives");

const SHELL_LABELS: FourZoneDirectionCShellLabels = {
  workspacePrefix: "Espace",
  searchTriggerPlaceholder: "Rechercher...",
  contextualHelpButtonLabel: "Aide",
  notificationsButtonLabel: "Notifications",
  notificationsDrawerTitle: "Notifications",
  notificationsEmptyText: "Aucune notification",
  sidebarAriaLabel: "Navigation principale",
  railCollapseLabel: "Replier le menu",
  railExpandLabel: "Déplier le menu",
  packSelectorLabel: "Pack métier",
  helpColumnTitle: "Aide contextuelle",
  helpColumnExpectedTitle: "Attendu",
  helpColumnExpectedBody: "Aide de la vue",
  menuEntries: {
    cockpit: "Cockpit",
    assistant: "Mon Assistant",
    processes: "Mes Processus",
    agents: "Mes Agents",
    spaces: "Mes Espaces",
    finops: "Coûts & Budgets",
    configuration: "Configuration",
    help: "Aide",
  },
  activityMenuLabel: "Journal d'Activité",
};

function relativeLuminance(hex: string): number {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.slice(0, 2), 16) / 255;
  const g = parseInt(clean.slice(2, 4), 16) / 255;
  const b = parseInt(clean.slice(4, 6), 16) / 255;
  const toLinear = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
}

function wcagContrastRatio(fgHex: string, bgHex: string): number {
  const l1 = relativeLuminance(fgHex);
  const l2 = relativeLuminance(bgHex);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

afterEach(() => {
  cleanup();
  resetAuthSessionStore();
  resetVitestApiBackend();
});

describe("Story 24.4 — Audit verrouillage scroll Desktop, CSS Tailwind v4 layering, contraste RGAA & Accostage", () => {
  it("verrouille html, body, #root à 100dvh + overflow: hidden sur @media (min-width: 768px) et charge tokens.css avant Tailwind v4", () => {
    const mainTsx = fs.readFileSync(path.join(REPO_ROOT, "apps/web/src/main.tsx"), "utf8");
    const tokensIdx = mainTsx.indexOf("@orcia/ui/styles/tokens.css");
    const tailwindIdx = mainTsx.indexOf("virtual:orcia-tailwind.css");
    expect(tokensIdx).toBeGreaterThan(-1);
    expect(tailwindIdx).toBeGreaterThan(-1);
    expect(tokensIdx).toBeLessThan(tailwindIdx);

    const shellCss = fs.readFileSync(path.join(STYLES_DIR, "tokens-shell.css"), "utf8");
    expect(shellCss).toMatch(
      /@media\s*\(min-width:\s*768px\)\s*\{[\s\S]*?html,\s*body,\s*#root\s*\{[\s\S]*?position:\s*relative;[\s\S]*?height:\s*100dvh;[\s\S]*?max-height:\s*100dvh;[\s\S]*?overflow:\s*hidden;/,
    );

    const allCss = fs
      .readdirSync(STYLES_DIR)
      .filter((n) => n.endsWith(".css"))
      .map((n) => fs.readFileSync(path.join(STYLES_DIR, n), "utf8"))
      .join("\n");
    expect(allCss).not.toMatch(/^\s*\.(?:flex|flex-col|grid|grid-cols-1)\s*\{/m);

    const componentsCss = fs.readFileSync(path.join(STYLES_DIR, "tokens-components.css"), "utf8");
    const tabRuleMatch = componentsCss.match(/\.orcia-ds-tab,\s*\[role="tab"\]\s*\{([^}]*)\}/);
    expect(tabRuleMatch).not.toBeNull();
    expect(tabRuleMatch?.[1]).not.toContain("transition");

    const darkCss = fs.readFileSync(path.join(STYLES_DIR, "tokens-dark.css"), "utf8");
    const fgMatch = darkCss.match(/--color-sidebar-active-fg:\s*(#[0-9a-fA-F]{6})/);
    const bgMatch = darkCss.match(/--color-sidebar-active-bg:\s*(#[0-9a-fA-F]{6})/);
    expect(fgMatch?.[1]).toBe("#93C5FD");
    expect(bgMatch?.[1]).toBe("#1E293B");
    expect(wcagContrastRatio(fgMatch![1]!, bgMatch![1]!)).toBeGreaterThanOrEqual(4.5);

    for (const file of [
      "FourZoneDirectionCShell.tsx",
      "FourZoneSidebarRail.tsx",
      "FourZoneHelpAsideColumn.tsx",
    ]) {
      const content = fs.readFileSync(path.join(PRIMITIVES_DIR, file), "utf8");
      expect(content).not.toContain("calc(100vh - 52px)");
    }
  });

  it("applique h-dvh max-h-dvh overflow-hidden en Desktop (1440px) vs min-h-screen en Mobile (390px) avec scroll interne sur les 3 colonnes", () => {
    const desktopRender = render(
      <FourZoneDirectionCShell
        activeMenuKey="cockpit"
        activeWorkspaceName="Plateforme"
        activePackKey=""
        availablePacks={[]}
        pendingDecisionsTotal={0}
        viewportWidth={1440}
        labels={SHELL_LABELS}
        onSelectMenu={vi.fn()}
      >
        <div>Contenu Desktop</div>
      </FourZoneDirectionCShell>,
    );

    const desktopShell = screen.getByTestId("four-zone-direction-c-shell");
    expect(desktopShell.className).toContain("relative");
    expect(desktopShell.className).toContain("h-dvh");
    expect(desktopShell.className).toContain("max-h-dvh");
    expect(desktopShell.className).toContain("overflow-hidden");
    expect(desktopShell.className).not.toContain("min-h-screen");

    const sidebar = screen.getByTestId("four-zone-sidebar");
    expect(sidebar.className).toContain("relative");
    expect(sidebar.className).toContain("h-full");
    expect(sidebar.className).toContain("min-h-0");
    expect(sidebar.className).toContain("overflow-y-auto");
    expect(sidebar.style.maxHeight).toBe("");

    const main = screen.getByTestId("four-zone-central-workspace");
    expect(main.className).toContain("relative");
    expect(main.className).toContain("h-full");
    expect(main.className).toContain("min-h-0");
    expect(main.className).toContain("overflow-y-auto");

    const helpCol = screen.getByTestId("four-zone-contextual-help-column");
    expect(helpCol.className).toContain("relative");
    expect(helpCol.className).toContain("h-full");
    expect(helpCol.className).toContain("min-h-0");
    expect(helpCol.className).toContain("overflow-y-auto");
    expect(helpCol.style.position).not.toBe("sticky");

    desktopRender.unmount();

    render(
      <FourZoneDirectionCShell
        activeMenuKey="cockpit"
        activeWorkspaceName="Plateforme"
        activePackKey=""
        availablePacks={[]}
        pendingDecisionsTotal={0}
        viewportWidth={390}
        labels={SHELL_LABELS}
        onSelectMenu={vi.fn()}
      >
        <div>Contenu Mobile</div>
      </FourZoneDirectionCShell>,
    );
    const mobileShell = screen.getByTestId("four-zone-direction-c-shell");
    expect(mobileShell.className).toContain("min-h-screen");
    expect(mobileShell.className).not.toContain("h-dvh");
  });

  it("compacte automatiquement ProgressiveDay0AccostageBanner sur /cockpit dès qu'un run ou arbitrage est présent (USER24-BUG-1)", async () => {
    seedVitestPlatformSetupState(
      {
        workspaces: [
          {
            workspaceId: "0195f000-0000-7000-8000-000000000244",
            slug: "ws-story-24-4",
            name: "Espace Cockpit 24.4",
            ownerOrgUnitId: "0192c4e0-0000-7000-8000-000000000101",
            ownerOrgUnitName: "Direction Produit",
            visibilityMode: "STANDARD",
            lifecyclePhase: "BUILD",
            accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
            finopsCostUsd: 0,
          },
        ],
        workflows: [
          {
            workflowKey: "assistant-agent",
            title: "Assistant Agent",
            version: "1.0.0",
            status: "PUBLISHED",
            prePrompt: "Analyser",
            prePromptSha256: "a".repeat(64),
            requiredParams: [],
            requiredMarkdownSections: [],
            triggers: [],
            layers: [],
          },
        ],
      },
      { email: "admin@orcia.ia", displayName: "Admin Orcia", roles: ["PLATFORM_ADMIN"] },
    );
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      isHydrating: false,
      email: "admin@orcia.ia",
      displayName: "Admin Orcia",
      roles: ["PLATFORM_ADMIN"],
    });

    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/cockpit"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <I18nProvider initialLocale="fr">
          <RouterProvider router={router} />
        </I18nProvider>
      </QueryClientProvider>,
    );

    const banner = await screen.findByTestId("progressive-day0-accostage-banner");
    expect(banner.getAttribute("data-compact")).toBe("false");
    expect(screen.getByTestId("welcome-setup-3step-wizard")).toBeDefined();

    // Launch a run from Cockpit -> banner auto-compacts to keep decisions & governance above the fold
    fireEvent.change(await screen.findByTestId("cockpit-run-title-input"), {
      target: { value: "Analyse Conformité Q4" },
    });
    fireEvent.click(screen.getByTestId("cockpit-launch-run-submit-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("progressive-day0-accostage-banner").getAttribute("data-compact")).toBe(
        "true",
      );
      expect(screen.queryByTestId("welcome-setup-3step-wizard")).toBeNull();
    });

    // User can still manually expand via toggle button
    fireEvent.click(screen.getByTestId("accostage-compact-toggle-btn"));
    expect(screen.getByTestId("progressive-day0-accostage-banner").getAttribute("data-compact")).toBe(
      "false",
    );
    expect(screen.getByTestId("welcome-setup-3step-wizard")).toBeDefined();
  });

  it("efface lastIssuedPlaintext au changement d'onglet et à la fermeture de UserSettingsModal (USER24-BUG-5)", async () => {
    seedVitestPlatformSetupState({}, { email: "dev@orcia.ia", displayName: "Dev Orcia" });
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      email: "dev@orcia.ia",
      displayName: "Dev Orcia",
      roles: ["BU_LEAD"],
    });

    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/cockpit"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <I18nProvider initialLocale="fr">
          <RouterProvider router={router} />
        </I18nProvider>
      </QueryClientProvider>,
    );

    fireEvent.keyDown(await screen.findByTestId("sidebar-open-my-account-btn"), { key: "Enter" });
    fireEvent.click(await screen.findByTestId("account-popover-personalization-btn"));
    fireEvent.click(await screen.findByTestId("user-settings-tab-IDE_MCP_KEYS"));

    fireEvent.change(screen.getByTestId("mcp-target-slug-input"), {
      target: { value: "mon-espace-finops" },
    });
    fireEvent.click(screen.getByTestId("mcp-generate-token-btn"));

    await screen.findByTestId("mcp-issued-plaintext-banner");
    expect(screen.getByTestId("mcp-tokens-list").textContent).not.toContain("IDE MCP (SPACE · default)");
    expect(screen.getByTestId("mcp-tokens-list").textContent).not.toContain("· 60 RPM");

    // Switching to another tab clears lastIssuedPlaintext
    fireEvent.click(screen.getByTestId("user-settings-tab-GENERAL"));
    fireEvent.click(screen.getByTestId("user-settings-tab-IDE_MCP_KEYS"));
    expect(screen.queryByTestId("mcp-issued-plaintext-banner")).toBeNull();
  });
});
