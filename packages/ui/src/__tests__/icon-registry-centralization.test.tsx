// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { ContextualInfoTriggerButton } from "../components/ContextualInfoTriggerButton";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import {
  getOrciaIconDefinition,
  getOrciaIconGlyph,
  ORCIA_EIGHT_MENU_ICON_NAMES,
  ORCIA_ICONS,
  ORCIA_MODULE_ICON_NAMES,
  ORCIA_SCOPE_LEVEL_ICON_NAMES,
  OrciaIcon,
  type OrciaIconName,
} from "../components/icons";
import { AssistantResponseFooterActionsAndCitations } from "../primitives/AssistantResponseFooterActionsAndCitations";
import { AssistantSpeedSelectorAndStreamView } from "../primitives/AssistantSpeedSelectorAndStreamView";
import { FourZoneDirectionCShell } from "../primitives/FourZoneDirectionCShell";
import { GlobalSidebar } from "../shell/GlobalSidebar";
import { ScopeSwitcher } from "../shell/ScopeSwitcher";
import type { UiShellLabels } from "../shell/types";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const UI_SRC_DIR = path.join(REPO_ROOT, "packages/ui/src");
const WEB_SRC_DIR = path.join(REPO_ROOT, "apps/web/src");
const ICONS_MODULE_DIR = path.join(UI_SRC_DIR, "components/icons");

function walkSourceFiles(dir: string): string[] {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (
        entry.name !== "__tests__" &&
        entry.name !== "node_modules" &&
        entry.name !== "generated"
      ) {
        files.push(...walkSourceFiles(fullPath));
      }
    } else if (entry.isFile() && /\.(ts|tsx)$/.test(entry.name)) {
      files.push(fullPath);
    }
  }
  return files;
}

const MINIMAL_SHELL_LABELS: UiShellLabels = {
  brandTitle: "ORCIA",
  brandSubtitle: "Orchestration",
  scopeSwitcherButtonLabel: "Périmètre",
  scopeSwitcherDialogTitle: "Sélectionner un périmètre",
  scopeSwitcherCloseLabel: "Fermer",
  sidebarNavigationAriaLabel: "Navigation principale",
  sidebarToggleCollapseLabel: "Replier",
  sidebarToggleExpandLabel: "Déplier",
  assistantDockToggleCollapseLabel: "Replier l'assistant",
  assistantDockToggleExpandLabel: "Déplier l'assistant",
  localeSwitchLabel: "Langue",
  humanProfilePrefixLabel: "Profil",
  staleWarningBadgeLabel: "Obsolète",
  modules: {
    cockpit: "Cockpit",
    inbox: "Mon Assistant",
    catalog: "Agents & Compétences",
    ontology: "Vocabulaire",
    gates: "Mes Processus",
    finops: "Coûts & Activité",
    admin: "Mes Espaces",
    bootstrap: "Configuration",
  },
  mobileTabs: {
    inbox: "Inbox",
    chat: "Chat",
    briefing: "Briefing",
  },
  scopeLevels: {
    GLOBAL: "Global",
    BU: "BU",
    TEAM: "Équipe",
    WORKSPACE: "Espace",
  },
  accessModes: {
    CONTRIBUTOR_ACTION_REQUIRED: "Contributeur",
    READ_ONLY_OBSERVER: "Observateur",
  },
  assistantDockTitle: "Mon Assistant",
  assistantDockSubtitle: "Contexte",
  assistantPermissionBrokerReadyLabel: "Prêt",
  assistantInputPlaceholder: "Votre question...",
  assistantSendLabel: "Envoyer",
};

describe("ORCIA Centralized Icon Registry (@orcia/ui) & Anti-Regression Audit", () => {
  afterEach(() => {
    cleanup();
  });

  it("Audit Gate 1: zero orphan inline <svg> tags exist in packages/ui/src/ or apps/web/src/ outside packages/ui/src/components/icons/", () => {
    const allFiles = [
      ...walkSourceFiles(UI_SRC_DIR),
      ...walkSourceFiles(WEB_SRC_DIR),
    ];
    const filesOutsideIconsModule = allFiles.filter(
      (f) => !f.startsWith(ICONS_MODULE_DIR),
    );

    const orphanSvgFiles: string[] = [];
    for (const filePath of filesOutsideIconsModule) {
      const content = fs.readFileSync(filePath, "utf-8");
      if (/<svg[\s>]/i.test(content)) {
        orphanSvgFiles.push(path.relative(REPO_ROOT, filePath));
      }
    }

    expect(
      orphanSvgFiles,
      `Found orphan inline <svg> outside packages/ui/src/components/icons/: ${orphanSvgFiles.join(", ")}`,
    ).toEqual([]);
  });

  it("Audit Gate 2: zero disconnected local icon dictionaries exist in shell or primitive components", () => {
    const fourZoneContent = fs.readFileSync(
      path.join(UI_SRC_DIR, "primitives/FourZoneDirectionCShell.tsx"),
      "utf-8",
    );
    const globalSidebarContent = fs.readFileSync(
      path.join(UI_SRC_DIR, "shell/GlobalSidebar.tsx"),
      "utf-8",
    );
    const scopeSwitcherContent = fs.readFileSync(
      path.join(UI_SRC_DIR, "shell/ScopeSwitcher.tsx"),
      "utf-8",
    );

    expect(fourZoneContent).toContain("ORCIA_EIGHT_MENU_ICON_NAMES");
    expect(globalSidebarContent).toContain("ORCIA_MODULE_ICON_NAMES");
    expect(scopeSwitcherContent).toContain("ORCIA_SCOPE_LEVEL_ICON_NAMES");
  });

  it("Audit Gate 2b: zero inline <span aria-hidden=\"true\"> icon glyphs remain in packages/ui/src/ or apps/web/src/ outside packages/ui/src/components/icons/", () => {
    const allFiles = [
      ...walkSourceFiles(UI_SRC_DIR),
      ...walkSourceFiles(WEB_SRC_DIR),
    ];
    const filesOutsideIconsModule = allFiles.filter(
      (f) => !f.startsWith(ICONS_MODULE_DIR),
    );

    const inlineAriaHiddenIconFiles: string[] = [];
    for (const filePath of filesOutsideIconsModule) {
      const content = fs.readFileSync(filePath, "utf-8");
      if (/<span\b[^>]*\baria-hidden=["']true["'][^/>]*>[^<>]+<\/span>/.test(content)) {
        inlineAriaHiddenIconFiles.push(path.relative(REPO_ROOT, filePath));
      }
    }

    expect(
      inlineAriaHiddenIconFiles,
      `Found inline <span aria-hidden="true"> glyphs outside packages/ui/src/components/icons/: ${inlineAriaHiddenIconFiles.join(", ")}`,
    ).toEqual([]);
  });

  it("Audit Gate 3: exposes a complete, strongly-typed ORCIA_ICONS registry and accessible <OrciaIcon /> primitive", () => {
    const iconNames = Object.keys(ORCIA_ICONS) as OrciaIconName[];
    expect(iconNames.length).toBeGreaterThanOrEqual(45);

    for (const name of iconNames) {
      const def = getOrciaIconDefinition(name);
      expect(def.glyph.length).toBeGreaterThan(0);
      expect(getOrciaIconGlyph(name)).toBe(def.glyph);
    }

    // Decorative icon by default (aria-hidden="true")
    const { unmount } = render(
      <OrciaIcon name="cockpit" testId="icon-decorative" />,
    );
    const dec = screen.getByTestId("icon-decorative");
    expect(dec.getAttribute("aria-hidden")).toBe("true");
    expect(dec.getAttribute("data-orcia-icon")).toBe("cockpit");
    expect(dec.textContent).toBe(ORCIA_ICONS.cockpit.glyph);
    unmount();

    // Semantic labelled icon (role="img" + aria-label)
    render(
      <OrciaIcon
        name="configuration"
        ariaLabel="Paramètres de configuration"
        testId="icon-labelled"
      />,
    );
    const labelled = screen.getByTestId("icon-labelled");
    expect(labelled.getAttribute("role")).toBe("img");
    expect(labelled.getAttribute("aria-label")).toBe(
      "Paramètres de configuration",
    );
    expect(labelled.getAttribute("aria-hidden")).toBeNull();
  });

  it("Audit Gate 4 (Single Source of Truth Reactivity): modifying an icon definition in ORCIA_ICONS immediately propagates to all consuming UI components", () => {
    const mutableRegistry = ORCIA_ICONS as Record<
      OrciaIconName,
      { glyph: string; category: string; description: string }
    >;

    const originalCockpit = mutableRegistry.cockpit.glyph;
    const originalSearch = mutableRegistry.search.glyph;
    const originalCopy = mutableRegistry.copy.glyph;
    const originalSendPlay = mutableRegistry.play.glyph;
    const originalInfoBadge = mutableRegistry.infoBadge.glyph;
    const originalAlertBadge = mutableRegistry.alertBadge.glyph;
    const originalScopeGlobal = mutableRegistry.globe.glyph;

    try {
      mutableRegistry.cockpit.glyph = "[CUSTOM_COCKPIT_ICON]";
      mutableRegistry.search.glyph = "[CUSTOM_SEARCH_ICON]";
      mutableRegistry.copy.glyph = "[CUSTOM_COPY_ICON]";
      mutableRegistry.play.glyph = "[CUSTOM_SEND_PLAY_ICON]";
      mutableRegistry.infoBadge.glyph = "[CUSTOM_INFO_BADGE]";
      mutableRegistry.alertBadge.glyph = "[CUSTOM_ALERT_BADGE]";
      mutableRegistry.globe.glyph = "[CUSTOM_GLOBE_ICON]";

      render(
        <div>
          <ContextualInfoTriggerButton
            sectionId="sec-test"
            label="Aide section"
          />
          <DisabledButtonAlertIndicator
            disabled={true}
            reason="Prérequis manquant"
            testIdSuffix="test-btn"
          />
          <GlobalSidebar
            modules={[
              {
                key: "cockpit",
                order: 1,
                route: "/cockpit",
                icon: ORCIA_MODULE_ICON_NAMES.cockpit,
                contributorBadgeCount: 0,
                hasStaleWarning: false,
                enabled: true,
              },
            ]}
            activeModuleKey="cockpit"
            scopes={[
              {
                id: "scope-global",
                name: "ORCIA Corp",
                level: "GLOBAL",
                accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
              },
            ]}
            activeScopeId="scope-global"
            isScopeSwitcherOpen={false}
            humanProfile={{
              displayName: "Alice",
              archetypeKey: "TECH_LEAD",
              accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
            }}
            collapsed={false}
            labels={MINIMAL_SHELL_LABELS}
            onSelectModule={() => {}}
            onToggleCollapsed={() => {}}
            onToggleScopeSwitcher={() => {}}
            onSelectScope={() => {}}
          />
          <AssistantResponseFooterActionsAndCitations
            responseText="Réponse synthétique"
          />
          <AssistantSpeedSelectorAndStreamView
            workspaceId="ws-1"
            userId="u-1"
            hat="TECH_LEAD"
            stepProgress={[]}
            labels={{
              headerTitle: "Mon Assistant",
              speed1PillLabel: "Vitesse 1",
              speed2PillLabel: "Vitesse 2",
              speed3DeepAuditPillLabel: "Audit approfondi",
              cacheHitBadge: "HIT",
              cacheMissBadge: "MISS",
              nodesDeterministicLabel: "Noeuds 1-4",
              ttftBadgePrefix: "TTFT",
              inputPlaceholder: "Posez votre question...",
              sendPromptCta: "Envoyer",
            }}
          />
          <FourZoneDirectionCShell
            activeMenuKey="cockpit"
            activeWorkspaceName="Espace Démo"
            activePackKey="orcia-pack-sdlc"
            availablePacks={["orcia-pack-sdlc"]}
            userDisplayName="Alice"
            userHatLabel="Tech Lead"
            pendingDecisionsTotal={0}
            labels={{
              workspacePrefix: "Espace",
              searchTriggerPlaceholder: "Rechercher...",
              contextualHelpButtonLabel: "Aide",
              notificationsButtonLabel: "Notifications",
              notificationsDrawerTitle: "Centre de notifications",
              notificationsEmptyText: "Aucune notification",
              sidebarAriaLabel: "Navigation",
              railCollapseLabel: "Replier",
              railExpandLabel: "Déplier",
              packSelectorLabel: "Pack",
              helpColumnTitle: "Aide contextuelle",
              helpColumnExpectedTitle: "Attendu",
              helpColumnExpectedBody: "Description",
              menuEntries: {
                cockpit: "Cockpit",
                assistant: "Mon Assistant",
                processes: "Mes Processus",
                agents: "Agents & Compétences",
                spaces: "Mes Espaces",
                finops: "Coûts & Activité",
                configuration: "Configuration",
                help: "Aide",
              },
            }}
            onSelectMenu={() => {}}
          >
            <div>Contenu principal</div>
          </FourZoneDirectionCShell>
        </div>,
      );

      // Verify immediate propagation across all components
      expect(
        screen.getByTestId("contextual-info-trigger-sec-test").textContent,
      ).toBe("[CUSTOM_INFO_BADGE]");
      expect(
        screen.getByTestId("disabled-button-alert-icon-test-btn").textContent,
      ).toContain("[CUSTOM_ALERT_BADGE]");
      expect(screen.getByTestId("scope-switcher-trigger").textContent).toContain(
        "[CUSTOM_GLOBE_ICON]",
      );
      expect(screen.getByTestId("assistant-action-copy-btn").textContent).toBe(
        "[CUSTOM_COPY_ICON]",
      );
      expect(screen.getByTestId("assistant-send-play-icon").textContent).toBe(
        "[CUSTOM_SEND_PLAY_ICON]",
      );
      expect(
        screen.getByTestId("topbar-federated-search-trigger").textContent,
      ).toContain("[CUSTOM_SEARCH_ICON]");
      expect(screen.getByTestId("eight-menu-item-cockpit").textContent).toContain(
        "[CUSTOM_COCKPIT_ICON]",
      );
      expect(ORCIA_EIGHT_MENU_ICON_NAMES.cockpit).toBe("cockpit");
    } finally {
      mutableRegistry.cockpit.glyph = originalCockpit;
      mutableRegistry.search.glyph = originalSearch;
      mutableRegistry.copy.glyph = originalCopy;
      mutableRegistry.play.glyph = originalSendPlay;
      mutableRegistry.infoBadge.glyph = originalInfoBadge;
      mutableRegistry.alertBadge.glyph = originalAlertBadge;
      mutableRegistry.globe.glyph = originalScopeGlobal;
    }
  });
});
