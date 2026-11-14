import * as fs from "node:fs";
import * as path from "node:path";
import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import {
  FourZoneDirectionCShell,
  ORCIA_ICON_SVG_PATHS,
  ORCIA_ICONS,
  OrciaIcon,
  resolveUserRoleDisplayLabel,
  UserAccountDropdownAndSettingsModal,
  type FourZoneDirectionCShellLabels,
  type OrciaIconName,
} from "../index";

const SHELL_LABELS: FourZoneDirectionCShellLabels = {
  workspacePrefix: "Espace",
  searchTriggerPlaceholder: "Rechercher dans cet Espace...",
  contextualHelpButtonLabel: "Aide",
  notificationsButtonLabel: "Notifications",
  notificationsDrawerTitle: "Centre de notifications",
  notificationsEmptyText: "Aucune notification",
  sidebarAriaLabel: "Navigation principale",
  railCollapseLabel: "Replier le menu ([)",
  railExpandLabel: "Déplier le menu",
  packSelectorLabel: "Pack métier",
  helpColumnTitle: "Aide contextuelle",
  helpColumnExpectedTitle: "Attendu",
  helpColumnExpectedBody: "Description de la vue",
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

describe("Story 17.1 — Wireframe SVG Icons, CSS Button Reset & Sidebar Collapse Rail", () => {
  it("CA-17.1.1: defines @layer base button reset, .orcia-ds-btn-danger states, and borderless .orcia-sidebar-nav-btn in tokens.css", () => {
    const tokensPath = path.resolve(__dirname, "../styles/tokens.css");
    const css = fs.readFileSync(tokensPath, "utf8");

    expect(css).toMatch(/@layer\s+base\s*\{[\s\S]*?button\s*\{[\s\S]*?border:\s*0;/);
    expect(css).toContain(".orcia-ds-btn-danger:hover:not(:disabled)");
    expect(css).toContain(".orcia-ds-btn-danger:focus-visible");
    expect(css).toContain(".orcia-ds-btn-danger:disabled");
    expect(css).toContain(".orcia-sidebar-nav-btn");
    expect(css).toContain(".orcia-kbd-badge");
  });

  it("CA-17.1.2: renders monochrome 16px wireframe <svg> (stroke=currentColor, strokeWidth=1.75) for all OrciaIconName keys including nav.* and settings.*", () => {
    const requiredNewKeys: OrciaIconName[] = [
      "nav.collapse",
      "nav.expand",
      "nav.account",
      "settings.org",
      "settings.iam",
      "settings.models",
      "settings.connectors",
      "settings.packs",
    ];
    for (const key of requiredNewKeys) {
      expect(ORCIA_ICONS[key]).toBeDefined();
      expect(ORCIA_ICON_SVG_PATHS[key].length).toBeGreaterThan(0);
    }

    render(
      <div>
        {requiredNewKeys.map((key) => (
          <OrciaIcon key={key} name={key} testId={`svg-icon-${key}`} />
        ))}
      </div>,
    );

    for (const key of requiredNewKeys) {
      const wrapper = screen.getByTestId(`svg-icon-${key}`);
      expect(wrapper.getAttribute("aria-hidden")).toBe("true");
      const svg = wrapper.querySelector("svg");
      expect(svg).not.toBeNull();
      expect(svg?.getAttribute("width")).toBe("16");
      expect(svg?.getAttribute("height")).toBe("16");
      expect(svg?.getAttribute("viewBox")).toBe("0 0 24 24");
      expect(svg?.getAttribute("fill")).toBe("none");
      expect(svg?.getAttribute("stroke")).toBe("currentColor");
      expect(svg?.getAttribute("stroke-width")).toBe("1.75");
      expect(svg?.getAttribute("stroke-linecap")).toBe("round");
      expect(svg?.getAttribute("stroke-linejoin")).toBe("round");
      expect(svg?.querySelectorAll("path").length).toBeGreaterThan(0);
    }
  });

  it("CA-17.1.2: renders clean Sidebar header collapse bar with nav.collapse SVG + clean label + <kbd>[</kbd> when expanded, and centered nav.expand SVG with tooltip when collapsed", () => {
    render(
      <FourZoneDirectionCShell
        activeMenuKey="configuration"
        activeWorkspaceName="Plateforme Globale"
        activePackKey=""
        availablePacks={[]}
        userDisplayName="Romain"
        userHatLabel="Administrateur de la plateforme"
        pendingDecisionsTotal={0}
        labels={SHELL_LABELS}
        onSelectMenu={vi.fn()}
        renderSidebarFooter={(collapsed) => (
          <button
            type="button"
            data-testid="footer-account-btn"
            className={`orcia-sidebar-nav-btn ${collapsed ? "justify-center px-0 py-2" : "gap-2.5 px-2.5 py-2"}`}
          >
            <OrciaIcon name="nav.account" />
            {!collapsed && <span>Mon Compte</span>}
          </button>
        )}
      >
        <div>Contenu</div>
      </FourZoneDirectionCShell>,
    );

    const toggleBtn = screen.getByTestId("sidebar-rail-toggle-btn");
    const kbdBadge = screen.getByTestId("sidebar-rail-shortcut-kbd");
    expect(kbdBadge.tagName.toLowerCase()).toBe("kbd");
    expect(kbdBadge.textContent).toBe("[");
    // No raw '([' in visible label
    expect(toggleBtn.textContent).not.toContain("([)");
    expect(toggleBtn.textContent).toContain("Replier le menu");
    expect(toggleBtn.querySelector('[data-orcia-icon="nav.collapse"] svg')).not.toBeNull();

    // Active menu item uses borderless Direction C class & data-active="true"
    const configMenuBtn = screen.getByTestId("eight-menu-item-configuration");
    expect(configMenuBtn.className).toContain("orcia-sidebar-nav-btn");
    expect(configMenuBtn.getAttribute("data-active")).toBe("true");
    expect(configMenuBtn.querySelector("svg")).not.toBeNull();

    // Collapse to 68px rail
    fireEvent.click(toggleBtn);
    expect(screen.queryByTestId("sidebar-rail-shortcut-kbd")).toBeNull();
    expect(toggleBtn.getAttribute("title")).toBe("Déplier le menu ([)");
    expect(toggleBtn.getAttribute("aria-label")).toBe("Déplier le menu ([)");
    expect(toggleBtn.querySelector('[data-orcia-icon="nav.expand"] svg')).not.toBeNull();
    expect(screen.getByTestId("footer-account-btn").textContent).toBe("");
  });

  it("CA-17.1.3: supports controlled modalOpen on UserAccountDropdownAndSettingsModal and localized FR/EN governance roles", () => {
    expect(resolveUserRoleDisplayLabel("SECOPS", "fr")).toBe(
      "Responsable Sécurité & Habilitations",
    );
    expect(resolveUserRoleDisplayLabel("BU_LEAD", "en")).toBe("Business Unit Lead");
    expect(resolveUserRoleDisplayLabel("OBSERVER", "fr")).toBe("Observateur (Lecture seule)");

    const onModalOpenChange = vi.fn();
    render(
      <UserAccountDropdownAndSettingsModal
        userDisplayName="Claire"
        userEmail="claire@orcia.io"
        userRole="SECOPS"
        initialHat="SECOPS"
        initialLocale="fr"
        modalOpen={true}
        onModalOpenChange={onModalOpenChange}
        labels={{
          triggerAriaLabel: "Mon compte",
          dropdownWidthNote: "",
          hatSelectorLabel: "Rôle",
          themeQuickToggleLabel: "Thème",
          localeQuickToggleLabel: "Langue",
          openAccountSettingsLabel: "Paramètres de mon compte",
          openPassthroughSourcesLabel: "Sources personnelles",
          logoutButtonLabel: "Déconnexion",
          modalTitle: "Paramètres de mon compte",
          tab1PreferencesTitle: "Préférences",
          tab2SecurityTitle: "Profil & Sécurité",
          tab3PassthroughTitle: "Sources",
          tab4McpKeysTitle: "Clés MCP",
          customizeAssistantRedirectCta: "Personnaliser",
          testPassthroughTokenCta: "Tester",
          generateMcpTokenCta: "Générer",
          revokeMcpTokenCta: "Révoquer",
          targetWholeSpaceLabel: "Espace",
          targetSingleAgentLabel: "Agent",
          ideJsonReadyTitle: "Configuration IDE",
        }}
      />,
    );

    expect(screen.getByTestId("user-settings-modal")).toBeDefined();
    expect(screen.getByTestId("user-account-role-pill").textContent).toContain(
      "Responsable Sécurité & Habilitations",
    );
    fireEvent.click(screen.getByTestId("user-settings-modal-close-btn"));
    expect(onModalOpenChange).toHaveBeenCalledWith(false);
  });
});
